from server import http_get, options
import json
import logging.config
import os
import sys
import tarfile
import urllib2
import cmd

def send_post(host, action, data):
    port = options['HTTP_PORT']
    opener = urllib2.build_opener(urllib2.HTTPHandler)
    http_request = urllib2.Request("http://{0}:{1}/{2}".format(host, port, action), data)
    url = opener.open(http_request)
    result = int(url.read())
    url.close()
    return result

class RemoteEntry:
    
    def __init__(self,name,addr,isdir,size=0):
        self.name = name
        self.addr = addr
        self.isdir = isdir
        self.size = size
        self.local = (addr == options["SELF_ADDRESS"])

def do_get(entry):
    url = "http://{0}:{1}/entry/{2}".format(entry.addr, options['HTTP_PORT'], entry.name)
    
    try:
        opener = urllib2.build_opener(urllib2.HTTPHandler)
        http_request = urllib2.Request(url)
        http = opener.open(http_request)
        
        def read_in_chunks(http, chunk_size=16384):
            while True:
                data = http.read(chunk_size)
                if not data:
                    break
                yield data
        
        local_name = entry.name;
        if entry.isdir:
            local_name += '.tar'
        with open(local_name, 'w') as local_file:
            for piece in read_in_chunks(http):
                local_file.write(piece)
        http.close()
        
        if entry.isdir:
            tar = tarfile.open(local_name)
            tar.extractall()
            tar.close()
            os.remove(local_name)
    except urllib2.URLError:
        logging.warn("unable to get file")

def do_ls():
    port = options['HTTP_PORT']
    
    result = http_get("http://127.0.0.1:{0}/ls".format(port))
    share = json.loads(result)
    
    tmp = {}
    entries = {}
    for addr,point in share.iteritems():
        for name,entry in point.iteritems():
            entries["{0}@{1}".format(name,addr)] = RemoteEntry(name,addr,entry["isdir"],entry["size"])
            if tmp.has_key(name):
                tmp[name] += 1
            else:
                tmp[name] = 1
    for key,entry in entries.items():
        if tmp[entry.name] == 1:
            entries.pop(key)
            entries[entry.name] = entry
    return entries

def do_rm(entry):
    result = send_post(entry.addr, "rm", entry.name)
    if result == 0:
        logging.info("removed; OK")
    elif result == 1:
        logging.error("unable to remove; file or directory does not exist")

class LNSCmd(cmd.Cmd):
    
    prompt = '$ '
    
    def __init__(self,entries):
        self.entries = entries
        cmd.Cmd.__init__(self)
    
    def __ls(self):
        entries = do_ls()
        if not entries:
            return
        self.entries = entries
    
    def do_ls(self, line=""):
        self.__ls()
        for name,entry in iter(sorted(self.entries.iteritems())):
            if entry.isdir:
                if entry.local:
                    print "\033[1;32m*\033[0m {0}\t\033[1;34m{1}\033[0m".format(entry.size,name)
                else:
                    print "  {0}\t\033[1;34m{1}\033[0m".format(entry.size,name)
            else:
                if entry.local:
                    print "\033[1;32m*\033[0m {0}\t{1}".format(entry.size,name)
                else:
                    print "  {0}\t{1}".format(entry.size,name)
        pass
    
    def do_get(self, line):
        self.__ls()
        for path in line.split(' '):
            if not self.entries.has_key(path):
                logging.warn("unknown entry '{0}'".format(path))
            else:
                do_get(self.entries[path])
     
    def do_rm(self, line):
        self.__ls()
        for path in line.split(' '):
            if not self.entries.has_key(path):
                logging.warn("unknown entry '{0}'".format(path))
            else:
                do_rm(self.entries[path]) 
        
    def complete_get(self, text, line, begidx, endidx):
        return [k for k in self.entries.iterkeys() if k.startswith(text)]
    
    def complete_rm(self, text, line, begidx, endidx):
        return [k for k in self.entries.iterkeys() if k.startswith(text)]

if __name__ == '__main__':
    port = options['HTTP_PORT']
    logging.config.fileConfig("logging.cfg")
    entries = do_ls()
    lns_cmd = LNSCmd(entries)
    if len(sys.argv) is 1: # go to console mode
        try:  
            lns_cmd.cmdloop("lns says \'hello\'; try ls, get and rm")
        except urllib2.URLError:
            print "no connection to local share-point @127.0.0.1"
        except KeyboardInterrupt:
            print
        sys.exit()
    
    if sys.argv[1] == "share":
        path_list = []
        for path in sys.argv[2:]:
            fullpath = os.path.abspath(os.path.expanduser(path))
            # TODO validate path
            logging.info("sharing {0}".format(fullpath))
            path_list.append(fullpath)
        result = send_post("127.0.0.1", "share", json.dumps(path_list))
        if result == 0:
            logging.info("shared; OK")
        elif result == 1:
            logging.error("unable to share; file name already registered at local share-point")
        elif result == 2:
            logging.error("unable to share; file does not exist")
            
    elif sys.argv[1] == "ls":
        lns_cmd.do_ls()
    elif sys.argv[1] == "get":
        for path in sys.argv[2:]:
            lns_cmd.do_get(path)        
    elif sys.argv[1] == 'rm':
        for path in sys.argv[2:]:
            lns_cmd.do_rm(path)    
    pass
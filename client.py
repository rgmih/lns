from server import http_get, options
import json
import logging.config
import os
import sys
import tarfile
import urllib2
import cmd

def get_file(host, port, name, file_info):
    file_path = "http://{0}:{1}/entry/{2}".format(host, port, name)
    data = http_get(file_path)
    if file_info["isdir"]:
        name += '.tar'
    local_file = open(name, 'w')
    local_file.write(data)
    local_file.close()
    if file_info["isdir"]:
        tar = tarfile.open(name)
        tar.extractall()
        tar.close()
        os.remove(name)
    logging.info("GET 200: from '{0}'".format(file_path))

def send_post(host, action, data):
    port = options['HTTP_PORT']
    opener = urllib2.build_opener(urllib2.HTTPHandler)
    http_request = urllib2.Request("http://{0}:{1}/{2}".format(host, port, action), data)
    url = opener.open(http_request)
    result = int(url.read())
    url.close()
    return result

def remove_file(host, file_name):
    result = send_post(host, "rm", file_name)
    if result == 0:
        logging.info("removed; OK")
    elif result == 1:
        logging.error("unable to remove; file or directory does not exist")

def get_files():
    localhost = options['SELF_ADDRESS']
    port = options['HTTP_PORT']
    result = http_get("http://{0}:{1}/ls".format(localhost, port))
    share = json.loads(result)
    files = {}
    for host in share.iterkeys():
        for file_name in share[host].iterkeys():
            if not file_name in files:
                files[file_name] = {}
            hosts = files[file_name]
            hosts[host] = share[host][file_name]
    return files

def do_ls():
    host = options['SELF_ADDRESS']
    port = options['HTTP_PORT']
    try:
        result = http_get("http://{0}:{1}/ls".format(host,port))
        share = json.loads(result)
    except urllib2.URLError:
        logging.error("no connection to local share-point at {0}:{1}".format(host,port))
        return
    tmp = {}
    entries = {}
    for addr,point in share.iteritems():
        for name,entry in point.iteritems():
            entries["{0}@{1}".format(name,addr)] = {
                "name" : name,
                "addr" : addr,
                "size" : entry["size"],
                "isdir": entry["isdir"]
            }
            if tmp.has_key(name):
                tmp[name] += 1
            else:
                tmp[name] = 1
    for key,info in entries.items():
        if tmp[info["name"]] == 1:
            entries.pop(key)
            entries[info["name"]] = info
    return entries

class LNSCmd(cmd.Cmd):
    
    prompt = '$ '
    
    def __init__(self,entries):
        self.entries = entries
        cmd.Cmd.__init__(self)
    
    def do_ls(self, line):
        entries = do_ls()
        if not entries:
            return
        self.entries = entries
        for name,info in iter(sorted(entries.iteritems())):
            if info["isdir"]:
                print "  {0}\t\033[1;34m{1}\033[0m".format(info["size"],name)
            else:
                print "  {0}\t{1}".format(info["size"],name)
        pass
    
    def do_get(self, line):
        print line
        
    def complete_get(self, text, line, begidx, endidx):
        return [k for k in self.entries.iterkeys() if k.startswith(text)]
    
    def do_EOF(self, line):
        return True

if __name__ == '__main__':
    localhost = options['SELF_ADDRESS']
    port = options['HTTP_PORT']
    logging.config.fileConfig("logging.cfg")
    if len(sys.argv) is 1: # go to console mode
        try:
            entries = do_ls()
            LNSCmd(entries).cmdloop('lns says \'hello\'')
        except urllib2.URLError:
            print "no connection to local share-point"
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
        result = send_post(localhost, "share", json.dumps(path_list))
        if result == 0:
            logging.info("shared; OK")
        elif result == 1:
            logging.error("unable to share; file name already registered at local share-point")
        elif result == 2:
            logging.error("unable to share; file does not exist")
            
    elif sys.argv[1] == "ls":
        result = http_get("http://{0}:{1}/ls".format(localhost, port))
        logging.info(result)
    elif sys.argv[1] == "get":
        files = get_files()
        for path in sys.argv[2:]:
            parsed_path = path.partition('@')
            file_name = parsed_path[0]
            file_host = parsed_path[2]
            if file_name in files:
                hosts = files[file_name]
                if not file_host:
                    if len(hosts) == 1:
                        host = hosts.iterkeys().next()
                        get_file(host, port, file_name, hosts[host])
                    else:
                        logging.error("Error: ambiguous name '{0}'. You must specify a host: {1}".format(path, hosts.keys()))
                elif file_host in hosts:
                    file_info = hosts[file_host]
                    get_file(file_host, port, file_name, file_info)
                else:
                    logging.warn("File '{0}': not found".format(path))
    elif sys.argv[1] == 'rm':
        files = get_files()
        for path in sys.argv[2:]:
            parsed_path = path.partition('@')
            file_name = parsed_path[0]
            file_host = parsed_path[2]
            logging.info("deleting {0}".format(path))
            if file_name in files:
                hosts = files[file_name]
                if not file_host:
                    if len(hosts) == 1:
                        host = hosts.iterkeys().next()
                        remove_file(host, file_name)
                    else:
                        logging.error("Error: ambiguous name '{0}'. You must specify a host: {1}".format(path, hosts.keys()))
                elif file_host in hosts:
                    remove_file(file_host, file_name)
            else:
                logging.warn("unable to delete; file does not exist")
    pass
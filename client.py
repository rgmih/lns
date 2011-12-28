import sys
import os
import json
import urllib2
import logging.config
from server import http_get, options

def get_file(host, port, name):
    file_path = "http://{0}:{1}/entry/{2}".format(host, port, name)
    data = http_get(file_path)
    if (host != options['SELF_ADDRESS']):
        name += '@' + host
    local_file = open(name, 'w')
    local_file.write(data)
    local_file.close() 
    print "GET 200: from '{0}'".format(file_path)

if __name__ == '__main__':
    localhost = options['SELF_ADDRESS']
    port = options['HTTP_PORT']
    logging.config.fileConfig("logging.cfg")
    if len(sys.argv) is 1:
        # go to console mode
        print "console mode not supported yet"
        sys.exit()
    
    if sys.argv[1] == "share":
        path_list = []
        for path in sys.argv[2:]:
            fullpath = os.path.abspath(os.path.expanduser(path))
            # TODO validate path
            print "sharing {0}".format(fullpath)
            path_list.append(fullpath)
        print 
        opener = urllib2.build_opener(urllib2.HTTPHandler)
        http_request = urllib2.Request("http://{0}:{1}/share".format(localhost, port), json.dumps(path_list))
        url = opener.open(http_request)
        result = int(url.read())
        url.close()
        
        if result == 0:
            logging.info("shared; OK")
        elif result == 1:
            logging.error("unable to share; file name already registered at local share-point")
        elif result == 2:
            logging.error("unable to share; file does not exists")
    elif sys.argv[1] == "ls":
        opener = urllib2.build_opener(urllib2.HTTPHandler)
        http_request = urllib2.Request("http://{0}:{1}/ls".format(localhost, port))
        url = opener.open(http_request)
        print url.read()
        url.close()
    elif sys.argv[1] == "get":
        opener = urllib2.build_opener(urllib2.HTTPHandler)
        result = http_get("http://{0}:{1}/ls".format(localhost, port))
        share = json.loads(result)
        files = {}
        for host in share.iterkeys():
            for file_name in share[host].iterkeys():
                if not file_name in files:
                    files[file_name] = []
                hosts = files[file_name]
                hosts.append(host)
        
        for name in sys.argv[2:]:
            name_with_host = name.partition('@')
            file_name = name_with_host[0]
            file_host = name_with_host[2]
            if file_name in files:
                hosts = files[file_name]
                if not file_host:
                    if len(hosts) == 1:
                        get_file(localhost, port, file_name)
                    else:
                        print "Error: ambiguous file name '{0}'. You must specify a host: {1}".format(name, hosts)
                elif file_host in hosts:
                    get_file(file_host, port, file_name)
                else:
                    print "File '{0}': not found".format(name)
    pass
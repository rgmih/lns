from server import http_get, options
import json
import logging.config
import os
import sys
import tarfile
import urllib2

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
    print "GET 200: from '{0}'".format(file_path)

def send_post(action, data_list):
    localhost = options['SELF_ADDRESS']
    port = options['HTTP_PORT']
    opener = urllib2.build_opener(urllib2.HTTPHandler)
    http_request = urllib2.Request("http://{0}:{1}/{2}".format(localhost, port, action), json.dumps(data_list))
    url = opener.open(http_request)
    result = int(url.read())
    url.close()
    return result


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
        result = send_post("share", path_list)
        if result == 0:
            logging.info("shared; OK")
        elif result == 1:
            logging.error("unable to share; file name already registered at local share-point")
        elif result == 2:
            logging.error("unable to share; file does not exist")
            
    elif sys.argv[1] == "ls":
        result = http_get("http://{0}:{1}/ls".format(localhost, port))
        print result
    elif sys.argv[1] == "get":
        result = http_get("http://{0}:{1}/ls".format(localhost, port))
        share = json.loads(result)
        files = {}
        for host in share.iterkeys():
            for file_name in share[host].iterkeys():
                if not file_name in files:
                    files[file_name] = {}
                hosts = files[file_name]
                hosts[host] = share[host][file_name]
        
        for name in sys.argv[2:]:
            name_with_host = name.partition('@')
            file_name = name_with_host[0]
            file_host = name_with_host[2]
            if file_name in files:
                hosts = files[file_name]
                if not file_host:
                    if len(hosts) == 1:
                        host = hosts.iterkeys().next()
                        get_file(host, port, file_name, hosts[host])
                    else:
                        print "Error: ambiguous file name '{0}'. You must specify a host: {1}".format(name, hosts)
                elif file_host in hosts:
                    file_info = hosts[file_host]
                    get_file(file_host, port, file_name, file_info)
                else:
                    print "File '{0}': not found".format(name)
    elif sys.argv[1] == 'rm':
        path_list = []
        for path in sys.argv[2:]:
            print "deleting {0}".format(path)
            path_list.append(path)
        result = send_post("rm", path_list)
        if result == 0:
            logging.info("removed; OK")
        elif result == 1:
            logging.error("unable to remove; file or directory does not exist")
    pass
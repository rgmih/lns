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

if __name__ == '__main__':
    localhost = options['SELF_ADDRESS']
    port = options['HTTP_PORT']
    logging.config.fileConfig("logging.cfg")
    if len(sys.argv) is 1:
        # go to console mode
        logging.error("console mode not supported yet")
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
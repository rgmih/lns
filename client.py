import sys
import os
import json
import urllib2
import logging.config

if __name__ == '__main__':
    host = 'localhost'
    port = 8080
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
        http_request = urllib2.Request("http://{0}:{1}/share".format(host, port), json.dumps(path_list))
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
        http_request = urllib2.Request("http://{0}:{1}/ls".format(host, port))
        url = opener.open(http_request)
        print url.read()
        url.close()
    elif sys.argv[1] == "get":
        opener = urllib2.build_opener(urllib2.HTTPHandler)
        for name in sys.argv[2:]:
            http_request = urllib2.Request("http://{0}:{1}/entry/{2}".format(host, port, name))
            url = opener.open(http_request)
            local_file = open(name, 'w')
            local_file.write(url.read())
            local_file.close() 
    pass
import SocketServer
import logging.config
import socket
import thread
import time
import threading
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import json
import os
import copy
import urllib2

options = {
    "SELF_ADDRESS" : "192.168.1.2",
    "UDP_PORT" : 6500,
    "HTTP_PORT" : 8080
}

def send_broadcast(port, msg):
    out = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    out.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    out.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    out.sendto(msg, ('<broadcast>', port))
    out.close()

def http_get(url):
    opener = urllib2.build_opener(urllib2.HTTPHandler)
    http_request = urllib2.Request(url)
    http = opener.open(http_request)
    result = http.read()
    http.close()
    return result

class ShareResult:
    OK        = 0
    DUPLICATE = 1
    NOT_EXIST = 2
    INTERNAL  = 3

class Share:
    
    class Entry:
        def __init__(self,path):
            self.path = path
            self.size = os.path.getsize(path)
            self.isdir = os.path.isdir(path)
    
    class Point:
        def __init__(self,addr):
            self.addr = addr
            self.time = 0
    
    def __init__(self):
        self.__points = {}
        self.__lock = threading.Lock()
        self.__local_entries = {} # dictionary of files shared locally
    
    def attach(self, addr):
        with self.__lock:
            if addr in self.__points.keys():
                self.__points[addr].time = 0
                # logging.debug("reset time on {0} share-point".format(addr))
            else:
                self.__points[addr] = Share.Point(addr)
                logging.info("share-point found at {0}".format(addr))
    
    def update(self,t):
        with self.__lock:
            for addr,point in self.__points.iteritems():
                point.time += t
                # logging.debug("share-point at {0} time={1}".format(addr, point.time))
            for addr,point in self.__points.items():
                if point.time > 30: # no response from point for 30 seconds\
                    logging.info("share-point at {0} not reachable; removing", addr)
                    del self.__points[addr]
    
    def get_points(self):
        # returns snapshot of points
        with self.__lock:
            return copy.deepcopy(self.__points)
        
    def get_local_entries(self):
        with self.__lock:
            return copy.deepcopy(self.__local_entries)
    
    def share(self, path_list):
        # check if all files not already shared and exist
        with self.__lock:
            for path in path_list:
                if not os.path.exists(path):
                    logging.warn("unable to share {0}; file doesn't exist".format(path))
                    return ShareResult.NOT_EXIST
                name = os.path.basename(path)
                if name in self.__local_entries.iterkeys():
                    logging.warn("unable to share {0}; file name already registered at local share-point".format(name))
                    return ShareResult.DUPLICATE
                
                # TODO write to database
                self.__local_entries[name] = Share.Entry(path)
                logging.info("{0} shared; OK".format(path))
                
        return ShareResult.OK
        
    def connect(self):
        
        share = self
        
        # run UDP server
        class UDPHandler(SocketServer.BaseRequestHandler):
            def handle(self):
                data = self.request[0].strip()
                logging.debug("{0}: {1}".format(self.client_address[0], data))
                 
                cmd = data[4:8]
                if cmd == "HEY?": # response to HEY!-request
                    send_broadcast(options["UDP_PORT"], "LNS:HEY!:{0}".format(options["SELF_ADDRESS"]))
                elif cmd == "HEY!":
                    share.attach(data[9:])
                else:
                    logging.error("unexpected command={0} in {1}".format(cmd,data)) 
        
        self.__udp_server = SocketServer.ThreadingUDPServer(('', options["UDP_PORT"]), UDPHandler)
        thread.start_new_thread(lambda *args: self.__udp_server.serve_forever(), ('UDPServer',))
        logging.info("share udp server started")
        
        # run timer (UDP-broadcasting, share updating)
        class Timer:
            def __init__(self):
                self.__interval = 5
                self.__terminate_interval = 0.5
                self.__terminate = False
            
            def run(self):
                ts = self.__interval
                while not self.__terminate:
                    if ts > self.__interval:
                        share.update(self.__interval)
                        send_broadcast(options["UDP_PORT"], "LNS:HEY?")
                        ts = 0;
                    time.sleep(self.__terminate_interval)
                    ts += self.__terminate_interval
                logging.info("share timer terminated; OK")
                    
            def terminate(self):
                logging.info("terminating share timer")
                self.__terminate = True
                
        self.__timer = Timer()
        thread.start_new_thread(lambda *args: self.__timer.run(), ("Timer",))
        logging.info("share timer started")
        
        # run HTTP server
        class HTTPHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                response = ""
                if self.path == "/ls":
                    logging.debug("/js; querying all share-points")
                    total_list = {}
                    for addr in share.get_points().iterkeys():
                        # list files at given address
                        response = http_get("http://{0}:{1}/local".format(addr,options["HTTP_PORT"]))
                        total_list[addr] = json.loads(response)
                    
                    response = json.dumps(total_list)
                    
                elif self.path == "/local": # list local entries
                    logging.debug("/local; listing local entries")
                    entries = share.get_local_entries()
                    class EntryJSONEncoder(json.JSONEncoder):
                        def default(self, obj):
                            if isinstance(obj, Share.Entry):
                                return {"size": obj.size, "isdir": obj.isdir}
                            else:
                                return json.JSONEncoder.default(self, obj)
                    response = json.dumps(entries, cls=EntryJSONEncoder)
                
                self.send_response(200)
                self.send_header("Content-type", "text/plain")
                self.end_headers()
                self.wfile.write(response)
                
            def do_POST(self):
                if self.path == "/share":
                    length = int(self.headers['Content-Length'])
                    content = self.rfile.read(length)
                    path_list = json.loads(content)
                    result = share.share(path_list)
                    
                    self.send_response(200)
                    self.send_header("Content-type", "text/plain")
                    self.end_headers()
                    self.wfile.write(result)
                else:
                    self.send_error(404, "NOT FOUND")
                
        class ThreadingHTTPServer(SocketServer.ThreadingMixIn, HTTPServer):
            pass  
        
        self.__http_server = ThreadingHTTPServer(('', options["HTTP_PORT"]), HTTPHandler)
        thread.start_new_thread(lambda *args: self.__http_server.serve_forever(), ('HTTPServer',))
        logging.info("http server started") 
    
    def disconnect(self):
        self.__timer.terminate()
        self.__udp_server.shutdown()
        self.__udp_server.socket.close()
        logging.info("UDP server shutdown; OK")
        self.__http_server.shutdown()
        self.__http_server.socket.close()
        logging.info("HTTP server shutdown; OK")


if __name__ == '__main__':
    # initialize logging
    logging.config.fileConfig("logging.cfg")
    logging.info("lns daemon says 'hello'")
    
    # connect to share
    my_share = Share()
    my_share.connect()
    
    #time.sleep(13)
    #my_share.disconnect()
    
    # handle console?
    while True:
        time.sleep(1)
    
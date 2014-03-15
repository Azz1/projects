#!/usr/bin/python

from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer
from SocketServer import ThreadingMixIn
import threading
import argparse
import json
import time, datetime
import re
import os
import cgi
import sys
motorlib_path = os.path.abspath('../Adafruit')
sys.path.append(motorlib_path)
from Adafruit_Motor_Driver import StepMotor
 
class ControlPackage :
  # initialize vertical step motor
  motorV = StepMotor(0x60, debug=False)
  motorV.setFreq(1600)
  motorV.setPort("M3M4")

  # initialize horizontal step motor
  motorH = StepMotor(0x60, debug=False)
  motorH.setFreq(1600)
  motorH.setPort("M1M2")

  @staticmethod
  def release():
    ControlPackage.motorV.release()
    ControlPackage.motorH.release()

class LocalData(object):
  records = {'Alice': '2341', 'Beth': '9102', 'Cecil': '3258' }
 
class HTTPRequestHandler(BaseHTTPRequestHandler):
 
  def do_POST(self):
    if None != re.search('/api/v1/addrecord/*', self.path):
      ctype, pdict = cgi.parse_header(self.headers.getheader('content-type'))
      if ctype == 'application/json':
        length = int(self.headers.getheader('content-length'))
        data = cgi.parse_qs(self.rfile.read(length), keep_blank_values=1)
        recordID = self.path.split('/')[-1]
        LocalData.records[recordID] = data
        print "record %s is added successfully" % recordID
      else:
        data = {}
 
      self.send_response(200)
      self.end_headers()

    elif None != re.search('/api/motor/*', self.path): # motor control
      length = int(self.headers.getheader('content-length'))
      data = cgi.parse_qs(self.rfile.read(length), keep_blank_values=1)
      speed = int(data['speed'][0])
      steps = int(data['steps'][0])
      motorid = self.path.split('/')[-2]
      dir = self.path.split('/')[-1]
      print "motor %s move: [%s %s]" % (motorid, dir, speed)

      if motorid.lower() == 'v':
        ControlPackage.motorV.setSpeed(speed)
        ControlPackage.motorV.step(steps, dir.upper(), 'DOUBLE')
      else:
        ControlPackage.motorH.setSpeed(speed)
        ControlPackage.motorH.step(steps, dir.upper(), 'DOUBLE')
 
      status = True	# move success

      self.send_response(200)
      self.send_header('Content-Type', 'application/json')
      self.end_headers()
      self.wfile.write('{"status": "' + str(status) + '"}')

    else:
      self.send_response(403)
      self.send_header('Content-Type', 'application/json')
      self.end_headers()
 
    return
 
  def do_GET(self):
    if None != re.search('/api/v1/getrecord/*', self.path):
      recordID = self.path.split('/')[-1]
      if LocalData.records.has_key(recordID):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(LocalData.records[recordID])
      else:
        self.send_response(400, 'Bad Request: record does not exist')
        self.send_header('Content-Type', 'application/json')
        self.end_headers()

    elif None != re.search('/api/gettime$', self.path):	# get server time
      mytz="%+4.4d" % (time.timezone / -(60*60) * 100) # time.timezone counts westwards!
      dt  = datetime.datetime.now()
      dts = dt.strftime('%Y-%m-%d %H:%M:%S')  # %Z (timezone) would be empty
      nowstring="%s%s" % (dts,mytz)
 
      self.send_response(200)
      self.send_header('Content-Type', 'application/json')
      self.end_headers()
      self.wfile.write('{"time": "' + nowstring + '"}')

    elif None != re.search('/*.htm*', self.path):	# content html files
      filename = self.path.split('/')[-1]
      self.__retrieveFile(filename, 'text/html')
 
    elif None != re.search('/*.js', self.path):		# content js files
      filename = self.path.split('/')[-1]
      self.__retrieveFile(filename, 'application/javascript')

    elif None != re.search('/*.ico', self.path):		# content ico files
      filename = self.path.split('/')[-1]
      self.__retrieveFile(filename, 'image/x-icon')

    elif None != re.search('/*.gif', self.path):		# content gif files
      filename = self.path.split('/')[-1]
      self.__retrieveFile(filename, 'image/gif')

    elif None != re.search('/*.jpg', self.path):		# content jpeg files
      filename = self.path.split('/')[-1]
      self.__retrieveFile(filename, 'image/jpeg')

    elif None != re.search('/*.png', self.path):		# content png files
      filename = self.path.split('/')[-1]
      self.__retrieveFile(filename, 'image/png')

    elif None != re.search('/*.css', self.path):		# content css files
      filename = self.path.split('/')[-1]
      self.__retrieveFile(filename, 'text/css')

    elif None != re.search('/$', self.path):		# default index.html
      filename = 'index.html'
      self.__retrieveFile(filename, 'text/html')

    else:
      self.send_response(403)
      self.send_header('Content-Type', 'application/json')
      self.end_headers()
 
    return

  def __retrieveFile(self, filename, contenttype) :
    fullpath = os.path.realpath(__file__)
    filepath = os.path.dirname(fullpath) + '/content/' + filename
    print "retrieve file " + filepath

    if os.path.isfile(filepath) :
      self.send_response(200)
      self.send_header('Content-Type', contenttype)
      self.end_headers()
      with open(filepath, 'r') as content_file:
        content = content_file.read()
        self.wfile.write(content)
        return True
    else :
      self.send_response(403)
      self.send_header('Content-Type', contenttype)
      self.end_headers()
      return False
 
class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
  # Ctrl-C will cleanly kill all spawned threads
  daemon_threads = True

  # much faster rebinding
  allow_reuse_address = True
 
  def shutdown(self):
    self.socket.close()
    HTTPServer.shutdown(self)
 
class SimpleHttpServer():
  def __init__(self, ip, port):
    self.server = ThreadedHTTPServer((ip,port), HTTPRequestHandler)
  
  def start(self):
    self.server_thread = threading.Thread(target=self.server.serve_forever)
    # self.server_thread.daemon = True
    self.server_thread.start()
 
  def waitForThread(self):
    self.server_thread.join()
 
  def addRecord(self, recordID, jsonEncodedRecord):
    LocalData.records[recordID] = jsonEncodedRecord
 
  def stop(self):
    self.server.shutdown()
    self.waitForThread()
 
if __name__=='__main__':
  parser = argparse.ArgumentParser(description='HTTP Server')
  parser.add_argument('port', type=int, help='Listening port for HTTP Server')
  parser.add_argument('ip', help='HTTP Server IP')
  args = parser.parse_args()
 
  server = SimpleHttpServer(args.ip, args.port)
  print 'HTTP Server Running...........'
  try:
    server.start()
    #server.waitForThread()

    while True:
      time.sleep(1)
  except KeyboardInterrupt:
    server.stop()
    ControlPackage.release()


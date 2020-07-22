#!/usr/bin/python

#from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer
from http.server import BaseHTTPRequestHandler,HTTPServer
from socketserver import ThreadingMixIn
import threading
import queue
import argparse
import json
import http.cookies
import time, datetime
import re
import os
import glob
import cgi
import sys

import RPi.GPIO as GPIO

motorlib_path = os.path.abspath('../Adafruit')
sys.path.append(motorlib_path)
trackinglib_path = os.path.abspath('../StarLocator')
sys.path.append(trackinglib_path)

from StepMotor import ControlPackage
from StarTracking import StarTracking
import Camera
 
class HTTPRequestHandler(BaseHTTPRequestHandler):
 
  def __getCookie(self):
    if "Cookie" in self.headers:
      self.cookie = http.cookies.SimpleCookie(self.headers["Cookie"])
    else:
      self.cookie = http.cookies.SimpleCookie()
      self.cookie['refined'] = 'true'
      self.cookie['norefresh'] = 'false'
      self.cookie['cmode'] = 'day'
      self.cookie['rawmode'] = 'false'
      self.cookie['vflip'] = 'true'
      self.cookie['hflip'] = 'true'

  def __sendCookie(self):
    for c in self.cookie.values():
      self.send_header('Set-Cookie', c.output(header='').lstrip())

  def do_POST(self):

    self.__getCookie()

    if None != re.search('/api/refresh$', self.path):
      print( 'POST /api/refresh' )
      length = int(self.headers['content-length'])
      data = cgi.parse_qs(self.rfile.read(length).decode('UTF-8'), keep_blank_values=1)
      ControlPackage.ss = int(float(data['ss'][0]) * 1000)
      ControlPackage.iso = int(data['iso'][0])
      ControlPackage.brightness = int(data['br'][0])
      ControlPackage.sharpness = int(data['sh'][0])
      ControlPackage.contrast = int(data['co'][0])
      ControlPackage.saturation = int(data['sa'][0])
      ControlPackage.cmode = data['cmode'][0]
      ControlPackage.rawmode = data['rawmode'][0]
      ControlPackage.vflip = data['vflip'][0]
      ControlPackage.hflip = data['hflip'][0]

      if data['refpoints'][0] != "":
        x = data['refpoints'][0].split(",")
        if abs(float(x[0]) - float(x[2])) > 1.0 or abs(float(x[1]) - float(x[3])) > 1.0 :
          ControlPackage.ref0_x = float(x[0])
          ControlPackage.ref0_y = float(x[1])
          ControlPackage.ref1_x = float(x[2])
          ControlPackage.ref1_y = float(x[3])
          #print( 'Star tracking Ref Point ('+ str(ControlPackage.ref0_x) + ',' 
          #                                  + str(ControlPackage.ref0_y) + ') - ('
          #                                  + str(ControlPackage.ref1_x) + ','
          #                                  + str(ControlPackage.ref1_y) + ')' )

      ControlPackage.Validate()

      localtime, imgstr = ControlPackage.camera.snapshot()

      self.send_response(200)
      self.send_header('Content-Type', 'application/json')
      self.__sendCookie()
      self.end_headers()
      self.wfile.write(bytes('{"seq": ' + str(ControlPackage.imageseq) + ', "timestamp": "'+  time.strftime("%Y%m%d-%H%M%S", localtime) +'", "image": "' + imgstr + '"}', 'UTF-8'))

    elif None != re.search('/api/motor/*', self.path): # motor control
      ControlPackage.isTracking.clear()
      length = int(self.headers['content-length'])
      data = cgi.parse_qs(self.rfile.read(length).decode('utf-8'), keep_blank_values=1)
      speed = int(data['speed'][0])
      adj = int(data['adj'][0])
      steps = int(data['steps'][0])
      motorid = self.path.split('/')[-2]
      dir = self.path.split('/')[-1]
      #print "motor %s move: [%s %s]" % (motorid, dir, speed)

      status = True	# move success
      statstr = 'Motor move complete.'

      ControlPackage.move_method = 'DOUBLE'
      if motorid.lower() == 'v':
        try:
          if self.cookie['refined'].value == 'true':
      	    ControlPackage.move_method = 'MICROSTEP'
        except:
      	    ControlPackage.move_method = 'DOUBLE'

        ControlPackage.vspeed = speed
        ControlPackage.vadj = adj
        ControlPackage.vsteps = steps

        ControlPackage.threadLock.acquire()
        if dir.upper() == 'FORWARD' : v_dir = 'UP'
        else : v_dir = 'DOWN'
        ControlPackage.v_cmdqueue.put((v_dir, speed, adj, steps))
        ControlPackage.threadLock.release()

        if dir.upper() == 'FORWARD' and GPIO.input(ControlPackage.VH_pin):
          status = False
          statstr = 'Vertical highest limit reached!'

        if dir.upper() == 'BACKWARD' and GPIO.input(ControlPackage.VL_pin):
          status = False
          statstr = 'Vertical lowest limit reached!'

      elif motorid.lower() == 'h':
        ControlPackage.hspeed = speed
        ControlPackage.hadj = adj
        ControlPackage.hsteps = steps

        ControlPackage.threadLock.acquire()
        if dir.upper() == 'FORWARD' : h_dir = 'LEFT'
        else : h_dir = 'RIGHT'
        ControlPackage.h_cmdqueue.put((h_dir, speed, adj, steps))
        ControlPackage.threadLock.release()

        if dir.upper() == 'FORWARD' and GPIO.input(ControlPackage.HL_pin):
          status = False
          statstr = 'Horizontal leftmost limit reached!'

        if dir.upper() == 'BACKWARD' and GPIO.input(ControlPackage.HR_pin):
          status = False
          statstr = 'Horizontal rightmost limit reached!'

      else:
        ControlPackage.fspeed = speed
        ControlPackage.fadj = adj
        ControlPackage.fsteps = steps

        ControlPackage.threadLock.acquire()
        if dir.upper() == 'FORWARD' : f_dir = 'IN'
        else : f_dir = 'OUT'
        ControlPackage.f_cmdqueue.put((f_dir, speed, adj, steps))
        ControlPackage.threadLock.release()

      self.send_response(200)
      self.send_header('Content-Type', 'application/json')
      self.__sendCookie()
      self.end_headers()
      self.wfile.write(bytes('{"status": "' + str(status) + '", "detail": "' + statstr + '"}', 'UTF-8'))

    elif None != re.search('/api/starttracking', self.path): # motor control
      print( 'POST /api/statrtracking' )
      length = int(self.headers['content-length'])
      data = cgi.parse_qs(self.rfile.read(length).decode('utf-8'), keep_blank_values=1)

      if data['refpoints'][0] != "":
        x = data['refpoints'][0].split(",")
        if abs(float(x[0]) - float(x[2])) > 1.0 or abs(float(x[1]) - float(x[3])) > 1.0 :
          ControlPackage.ref0_x = float(x[0])
          ControlPackage.ref0_y = float(x[1])
          ControlPackage.ref1_x = float(x[2])
          ControlPackage.ref1_y = float(x[3])
          print( 'Star tracking Ref Point ('+ str(ControlPackage.ref0_x) + ',' 
                                          + str(ControlPackage.ref0_y) + ') - ('
                                          + str(ControlPackage.ref1_x) + ','
                                          + str(ControlPackage.ref1_y) + ')' )


      if data['myloclat'][0] == "" or data['myloclong'][0] == "" \
        or data['tgazadj'][0] == "" or data['tgaltadj'][0] == "" \
        or (data['altazradec'][0] == "ALTAZ"  \
         and ( data['tgaz'][0] == "" or data['tgalt'][0] == "" )) \
        or (data['altazradec'][0] == "RADEC" \
         and ( data['tgrah'][0] == "" or data['tgram'][0] == "" or data['tgras'][0] == "" \
          or data['tgdecdg'][0] == "" or data['tgdecm'][0] == "" or data['tgdecs'][0] == "") ) : 
        status = False	
        statstr = 'Star Tacking not started, check parameters!'

      else :
        
        ControlPackage.tgaz = 0.0
        ControlPackage.tgalt = 0.0
        ControlPackage.tgrah = 0.0
        ControlPackage.tgram = 0.0
        ControlPackage.tgras = 0.0
        ControlPackage.tgdecdg = 0.0
        ControlPackage.tgdecm = 0.0
        ControlPackage.tgdecs = 0.0
        ControlPackage.myloclat = float(data['myloclat'][0])
        ControlPackage.myloclong = float(data['myloclong'][0])
        ControlPackage.tgazadj = float(data['tgazadj'][0])
        ControlPackage.tgaltadj = float(data['tgaltadj'][0])

        if data['altazradec'][0] == "ALTAZ":
           ControlPackage.altazradec = 'ALTAZ'
           ControlPackage.tgaz = float(data['tgaz'][0])
           ControlPackage.tgalt = float(data['tgalt'][0])
        else:
           ControlPackage.altazradec = 'RADEC'
           ControlPackage.tgrah = float(data['tgrah'][0]) 
           ControlPackage.tgram = float(data['tgram'][0])
           ControlPackage.tgras = float(data['tgras'][0])
           ControlPackage.tgdecdg = float(data['tgdecdg'][0])
           ControlPackage.tgdecm = float(data['tgdecm'][0])
           ControlPackage.tgdecs = float(data['tgdecs'][0])

        vspeed = int(data['vspeed'][0])
        vsteps = int(data['vsteps'][0])
        hspeed = int(data['hspeed'][0])
        hsteps = int(data['hsteps'][0])

        #tr = StarTracking(ControlPackage.myloclat, ControlPackage.myloclong, ControlPackage.altazradec,
        #                ControlPackage.tgrah, ControlPackage.tgram, ControlPackage.tgras, ControlPackage.tgdecdg, ControlPackage.tgdecm, ControlPackage.tgdecs,
        #                ControlPackage.tgaz, ControlPackage.tgalt, 
        #                vspeed, vsteps, hspeed, hsteps)

        #print( 'Start star tracking ...' )
        #t = threading.Thread(target=tr.Track, args = ())
        #t.daemon = True
        #t.start()
        ControlPackage.isTracking.set()

        status = True	# start uccess
        statstr = 'Star Tracking Started.'

      print( statstr )
      self.send_response(200)
      self.send_header('Content-Type', 'application/json')
      self.__sendCookie()
      self.end_headers()
      self.wfile.write(bytes('{"status": "' + str(status) + '", "detail": "' + statstr + '"}','utf-8'))

    elif None != re.search('/api/adjoffset', self.path): # Direction offset adjustmnet 
      print( 'POST /api/adjoffset' )

      azadj, altadj = ControlPackage.newadj()

      self.send_response(200)
      self.send_header('Content-Type', 'application/json')
      self.__sendCookie()
      self.end_headers()
      self.wfile.write(bytes('{"azadj": "' + ("%.2f" % azadj) + '", "altadj": "' + ("%.2f" % altadj) + '"}','utf-8'))

    elif None != re.search('/api/halt', self.path): # Halt the system
      print( 'POST /api/halt' )
      if self.client_address[0].startswith('192') :	# halt system request only enabled from local IPs
        print( 'Halting the system from ' + self.client_address[0] + ' ...' )
        ControlPackage.camera.haltsys()


    else:
      self.send_response(403)
      self.send_header('Content-Type', 'application/json')
      self.__sendCookie()
      self.end_headers()
 
    return
 
  def do_GET(self):

    self.__getCookie()

    if None != re.search('/api/gettime', self.path):	# get server time
      mytz="%+4.4d" % (time.timezone / -(60*60) * 100) # time.timezone counts westwards!
      dt  = datetime.datetime.now()
      dts = dt.strftime('%Y-%m-%d %H:%M:%S')  # %Z (timezone) would be empty
      nowstring="%s%s" % (dts,mytz)

      if ControlPackage.cameraonly == "false":
        s = self.path.split('/')[-2]
        if s != "": ControlPackage.tgazadj = float(s)
        s = self.path.split('/')[-1]
        if s != "": ControlPackage.tgaltadj = float(s)
   
        if not ControlPackage.isTracking.is_set():
          tr = StarTracking(ControlPackage.myloclat, ControlPackage.myloclong, ControlPackage.altazradec,
                        ControlPackage.tgrah, ControlPackage.tgram, ControlPackage.tgras, 
                        ControlPackage.tgdecdg, ControlPackage.tgdecm, ControlPackage.tgdecs,
                        ControlPackage.tgaz, ControlPackage.tgalt, 
                        0, 0, 0, 0)
          ControlPackage.tgaz, ControlPackage.tgalt = tr.GetTarget()
          ControlPackage.curalt, ControlPackage.curaz = tr.read()
          ControlPackage.curalt += ControlPackage.tgaltadj
          ControlPackage.curaz += ControlPackage.tgazadj

      self.send_response(200)
      self.send_header('Content-Type', 'application/json')
      self.__sendCookie()
      self.end_headers()
      self.wfile.write(bytes('{' \
		        + '"time": "' + nowstring + '",' \
		        + '"curaz": "' + '%.4f' % ControlPackage.curaz + '",' \
		        + '"curalt": "' + '%.4f' % ControlPackage.curalt + '",' \
			+ '"tgaz": "' + '%.4f' % ControlPackage.tgaz + '",' \
			+ '"tgalt": "' + '%.4f' % ControlPackage.tgalt + '"' \
			+ '}', 'UTF-8'))

    elif None != re.search('/api/startvideo', self.path):	# start video
      print( 'GET /api/startvideo')

      ControlPackage.ss = int(float(self.path.split('/')[-6]) * 1000)
      ControlPackage.iso = int(self.path.split('/')[-5])
      ControlPackage.brightness = int(self.path.split('/')[-4])
      ControlPackage.sharpness = int(self.path.split('/')[-3])
      ControlPackage.contrast = int(self.path.split('/')[-2])
      ControlPackage.saturation = int(self.path.split('/')[-1])

      ControlPackage.camera.startvideo()
 
      self.send_response(200)
      self.send_header('Content-Type', 'application/json')
      self.__sendCookie()
      self.end_headers()
      self.wfile.write(bytes('{"status": "' + 'true' + '"}','utf-8'))

    elif None != re.search('/api/stopvideo$', self.path):	# stop video
      print( 'GET /api/stopvideo')
 
      ControlPackage.camera.stopvideo()

      self.send_response(200)
      self.send_header('Content-Type', 'application/json')
      self.__sendCookie()
      self.end_headers()
      self.wfile.write(bytes('{"status": "' + 'true' + '"}','utf-8'))

    elif None != re.search('/api/stoptracking$', self.path):	# stop tracking
      print( 'GET /api/stoptracking')
 
      ControlPackage.isTracking.clear()

      self.send_response(200)
      self.send_header('Content-Type', 'application/json')
      self.__sendCookie()
      self.end_headers()
      self.wfile.write(bytes('{"status": "' + 'true' + '"}','utf-8'))

    elif None != re.search('/api/init$', self.path):	# load initial params
      self.send_response(200)
      self.send_header('Content-Type', 'application/json')
      self.__sendCookie()
      self.end_headers()
      self.wfile.write(bytes('{' \
		        + '"vspeed": "' + str(ControlPackage.vspeed) + '",' \
		        + '"vsteps": "' + str(ControlPackage.vsteps) + '",' \
		        + '"hspeed": "' + str(ControlPackage.hspeed) + '",' \
		        + '"hsteps": "' + str(ControlPackage.hsteps) + '",' \
		        + '"fspeed": "' + str(ControlPackage.fspeed) + '",' \
		        + '"fsteps": "' + str(ControlPackage.fsteps) + '",' \
		        + '"ss": "' + str(ControlPackage.ss/1000.0) + '",' \
		        + '"iso": "' + str(ControlPackage.iso) + '",' \
		        + '"br": "' + str(ControlPackage.brightness) + '",' \
		        + '"sh": "' + str(ControlPackage.sharpness) + '",' \
		        + '"co": "' + str(ControlPackage.contrast) + '",' \
		        + '"sa": "' + str(ControlPackage.saturation) + '",' \
			+ '"tgaz": "' + str(ControlPackage.tgaz) + '",' \
			+ '"tgalt": "' + str(ControlPackage.tgalt) + '",' \
			+ '"tgrah": "' + str(ControlPackage.tgrah) + '",' \
			+ '"tgram": "' + str(ControlPackage.tgram) + '",' \
			+ '"tgras": "' + str(ControlPackage.tgras) + '",' \
			+ '"tgdecdg": "' + str(ControlPackage.tgdecdg) + '",' \
			+ '"tgdecm": "' + str(ControlPackage.tgdecm) + '",' \
			+ '"tgdecs": "' + str(ControlPackage.tgdecs) + '",' \
			+ '"tgazadj": "' + str(ControlPackage.tgazadj) + '",' \
			+ '"tgaltadj": "' + str(ControlPackage.tgaltadj) + '",' \
			+ '"myloclat": "' + str(ControlPackage.myloclat) + '",' \
			+ '"myloclong": "' + str(ControlPackage.myloclong) + '"' \
			+ '}', 'utf-8'))

    elif None != re.search('/api/snapshot', self.path):
      print( 'GET /api/snapshot')
      ControlPackage.ss = int(float(self.path.split('/')[-7]) * 1000)
      ControlPackage.iso = int(self.path.split('/')[-6])
      ControlPackage.brightness = int(self.path.split('/')[-5])
      ControlPackage.sharpness = int(self.path.split('/')[-4])
      ControlPackage.contrast = int(self.path.split('/')[-3])
      ControlPackage.saturation = int(self.path.split('/')[-2])
      ControlPackage.timelapse = int(self.path.split('/')[-1])

      ControlPackage.Validate()
      fname = ControlPackage.camera.snapshot_full()

      self.send_response(200)
      self.send_header('Content-Type', 'application/jpeg')
      self.send_header('Content-Disposition', 'inline;filename="' + fname.replace('temp/', '') + '"')

      self.__sendCookie()
      self.end_headers()
      with open(fname, 'rb') as content_file:
        content = content_file.read()
        self.wfile.write(content)

    elif None != re.search('/api/videoshot', self.path):
      print( 'GET /api/videoshot')
      ControlPackage.ss = int(float(self.path.split('/')[-7]) * 1000)
      ControlPackage.iso = int(self.path.split('/')[-6])
      ControlPackage.brightness = int(self.path.split('/')[-5])
      ControlPackage.sharpness = int(self.path.split('/')[-4])
      ControlPackage.contrast = int(self.path.split('/')[-3])
      ControlPackage.saturation = int(self.path.split('/')[-2])
      ControlPackage.videolen = int(self.path.split('/')[-1])

      ControlPackage.Validate()
      fname = ControlPackage.camera.videoshot()

      self.send_response(200)
      self.send_header('Content-Type', 'application/octet-stream')
      self.send_header('Content-Disposition', 'attachment;filename="' + fname.replace('temp/', '') + '"')

      self.__sendCookie()
      self.end_headers()
      with open(fname, 'rb') as content_file:
        content = content_file.read()
        self.wfile.write(content)

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
      self.__sendCookie()
      self.end_headers()
 
    return

  def __retrieveFile(self, filename, contenttype) :
    fullpath = os.path.realpath(__file__)
    filepath = os.path.dirname(fullpath) + '/content/' + filename
    print( "retrieve file " + filepath)

    if os.path.isfile(filepath) :
      self.send_response(200)
      self.send_header('Content-Type', contenttype)
      self.__sendCookie()
      self.end_headers()
      with open(filepath, 'r') as content_file:
        content = content_file.read()
        content = content.replace('[IPADDRESS]', ControlPackage.ip)
        self.wfile.write(content.encode('iso-8859-1'))
        return True
    else :
      self.send_response(403)
      self.send_header('Content-Type', contenttype)
      self.__sendCookie()
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
  parser.add_argument('camonly', help='Camera Only Mode')
  args = parser.parse_args()
 
  print( 'HTTP Server Running...........')
  if args.camonly  == 'Y': 
    ControlPackage.cameraonly = "true"
    print( '!!!!!!!!!!!!!!!!!! in Camer Only Mode !!!!!!!!!!!!!!!!!!!!!!!!')
  else :
    ControlPackage.cameraonly = "false"

  ControlPackage.ip = args.ip
    
  server = SimpleHttpServer(args.ip, args.port)
  try:
    server.start()
    #server.waitForThread()

    while True:
      time.sleep(1)
  except KeyboardInterrupt:
    ControlPackage.exitFlag.clear()
    server.stop()
    ControlPackage.release()


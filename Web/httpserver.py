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
import PIL
from PIL import Image
import base64
from cStringIO import StringIO

import RPi.GPIO as GPIO

#import picamera
motorlib_path = os.path.abspath('../Adafruit')
sys.path.append(motorlib_path)
from Adafruit_Motor_Driver import StepMotor
 
camera_lock = threading.Lock()

class ControlPackage :

  # Touch sensor GPIO pins
  VL_pin = 24
  VH_pin = 23
  HL_pin = 17
  HR_pin = 4

  GPIO.setmode(GPIO.BCM)

  GPIO.setup(VL_pin, GPIO.IN)
  GPIO.setup(VH_pin, GPIO.IN)
  GPIO.setup(HL_pin, GPIO.IN)
  GPIO.setup(HR_pin, GPIO.IN)

  # initialize the camera 
  #camera = picamera.PiCamera()
  width = 800
  height = 600
  brightness = 60
  #camera.vflip = False
  #camera.hflip = False
  #camera.brightness = 60

  # initialize vertical step motor
  motorV = StepMotor(0x60, debug=False)
  motorV.setFreq(1600)
  motorV.setPort("M3M4")
  motorV.setSensor(VH_pin, VL_pin)

  # initialize horizontal step motor
  motorH = StepMotor(0x60, debug=False)
  motorH.setFreq(1600)
  motorH.setPort("M1M2")
  motorH.setSensor(HL_pin, HR_pin)

  @staticmethod
  def release():
    ControlPackage.motorV.release()
    ControlPackage.motorH.release()
    #ControlPackage.camera.close()
    #del ControlPackage.camera

class HTTPRequestHandler(BaseHTTPRequestHandler):
 
  def do_POST(self):
    if None != re.search('/api/refresh$', self.path):
      print 'POST /api/refresh'
      try:
        # TAKE A PHOTO
        with camera_lock :
          #ControlPackage.camera.start_preview()
          #time.sleep(0.5)
          #ControlPackage.camera.capture('temp/image.jpg', format='jpeg', resize=(ControlPackage.width,ControlPackage.height))

          os.system('raspistill -o temp/image.jpg -w ' + str(ControlPackage.width) \
                     + ' -h ' + str(ControlPackage.height) \
                     + ' -sh 50 -hf -vf -br ' + str(ControlPackage.brightness))

      finally:
        pass
        #ControlPackage.camera.stop_preview()

      #READ IMAGE AND PUT ON SCREEN
      img = Image.open('temp/image.jpg')
      #basewidth = 800
      #wpercent = (basewidth/float(img.size[0]))
      #hsize = int((float(img.size[1])*float(wpercent)))
      #img = img.resize((basewidth,hsize), PIL.Image.ANTIALIAS)
      #img = img.transpose(Image.ROTATE_180)

      output = StringIO()
      img.save(output, format='JPEG')
      imgstr = base64.b64encode(output.getvalue()) 
      del img
      os.remove('temp/image.jpg')

      self.send_response(200)
      self.send_header('Content-Type', 'application/json')
      self.end_headers()
      self.wfile.write('{"image": "' + imgstr + '"}')

    elif None != re.search('/api/motor/*', self.path): # motor control
      length = int(self.headers.getheader('content-length'))
      data = cgi.parse_qs(self.rfile.read(length), keep_blank_values=1)
      speed = int(data['speed'][0])
      steps = int(data['steps'][0])
      motorid = self.path.split('/')[-2]
      dir = self.path.split('/')[-1]
      print "motor %s move: [%s %s]" % (motorid, dir, speed)

      status = True	# move success
      statstr = 'Motor move complete.'

      if motorid.lower() == 'v':
        ControlPackage.motorV.setSpeed(speed)
        ControlPackage.motorV.step(steps, dir.upper(), 'DOUBLE')
        ControlPackage.motorV.release()

        if dir.upper() == 'FORWARD' and GPIO.input(ControlPackage.VH_pin):
          status = False
          statstr = 'Vertical highest limit reached!'

        if dir.upper() == 'BACKWARD' and GPIO.input(ControlPackage.VL_pin):
          status = False
          statstr = 'Vertical lowest limit reached!'

      else:
        ControlPackage.motorH.setSpeed(speed)
        ControlPackage.motorH.step(steps, dir.upper(), 'DOUBLE')
        ControlPackage.motorH.release()
 
        if dir.upper() == 'FORWARD' and GPIO.input(ControlPackage.HL_pin):
          status = False
          statstr = 'Horizontal leftmost limit reached!'

        if dir.upper() == 'BACKWARD' and GPIO.input(ControlPackage.HR_pin):
          status = False
          statstr = 'Horizontal rightmost limit reached!'

      self.send_response(200)
      self.send_header('Content-Type', 'application/json')
      self.end_headers()
      self.wfile.write('{"status": "' + str(status) + '", "detail": "' + statstr + '"}')

    else:
      self.send_response(403)
      self.send_header('Content-Type', 'application/json')
      self.end_headers()
 
    return
 
  def do_GET(self):
    if None != re.search('/api/gettime$', self.path):	# get server time
      mytz="%+4.4d" % (time.timezone / -(60*60) * 100) # time.timezone counts westwards!
      dt  = datetime.datetime.now()
      dts = dt.strftime('%Y-%m-%d %H:%M:%S')  # %Z (timezone) would be empty
      nowstring="%s%s" % (dts,mytz)
 
      self.send_response(200)
      self.send_header('Content-Type', 'application/json')
      self.end_headers()
      self.wfile.write('{"time": "' + nowstring + '"}')

    elif None != re.search('/api/snapshot$', self.path):
      print 'GET /api/snapshot'
      try:
        # TAKE A PHOTO OF HIGH RESOLUTION
        with camera_lock :

          #ControlPackage.camera.start_preview()
          #time.sleep(0.5)
          #ControlPackage.camera.capture('temp/image.jpg', format='jpeg', resize=(ControlPackage.width,ControlPackage.height))

          os.system('raspistill -o temp/simage.jpg -hf -vf -br ' \
                                + str(ControlPackage.brightness))
      finally:
        pass
        #ControlPackage.camera.stop_preview()

      #READ IMAGE AND PUT ON SCREEN
      img = Image.open('temp/simage.jpg')
      #img = img.transpose(Image.ROTATE_180)

      img.save('temp/snapimg.jpg', format='JPEG')

      self.send_response(200)
      self.send_header('Content-Type', 'application/jpeg')
      self.send_header('Content-Disposition', 'inline')
      self.send_header('filename', 'snapshot.jpg')
      self.end_headers()
      with open('temp/snapimg.jpg', 'r') as content_file:
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


#!/usr/bin/python

from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer
from SocketServer import ThreadingMixIn
import threading
import argparse
import json
import Cookie
import time, datetime
import re
import os
import glob
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
videostarted = False

class ControlPackage :

  # Touch sensor GPIO pins
  VL_pin = 24
  VH_pin = 23
  HL_pin = 25
  HR_pin = 8
  #HL_pin = 17
  #HR_pin = 4

  GPIO.setmode(GPIO.BCM)

  GPIO.setup(VL_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
  GPIO.setup(VH_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
  GPIO.setup(HL_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
  GPIO.setup(HR_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

  # initialize the camera 
  #camera = picamera.PiCamera()
  width = 700
  height = 525
  brightness = 50	#0-100 50 default
  sharpness = 20	#-100-100 0 default
  contrast = 20		#-100-100 0 default
  saturation = 20	#-100-100 0 default
  ss = 4000		#microsecond
  iso = 400		#100-800 400 default
  videolen = 20		#video length
  imageseq = 0		#sequence id of refresh image
  simageseq = 0		#sequence id of snapshot image
  videoseq = 0		#sequence id of video snapshots
  max_keep_snapshots = 10	#max number of snapsnots keep in cache
  max_keep_videoshots = 5	#max number of videosnots keep in cache

  # initialize vertical step motor
  motorV = StepMotor(0x60, debug=False)
  motorV.setFreq(1600)
  motorV.setPort("M3M4")
  motorV.setSensor(VH_pin, VL_pin)
  vspeed = 30
  vsteps = 100

  # initialize horizontal step motor
  motorH = StepMotor(0x60, debug=False)
  motorH.setFreq(1600)
  motorH.setPort("M1M2")
  motorH.setSensor(HL_pin, HR_pin)
  hspeed = 5
  hsteps = 5

  @staticmethod
  def release():
    ControlPackage.motorV.release()
    ControlPackage.motorH.release()
    #ControlPackage.camera.close()
    #del ControlPackage.camera

  @staticmethod
  def Validate():
    if ControlPackage.brightness < 0: ControlPackage.brightness = 0
    elif ControlPackage.brightness > 100: ControlPackage.brightness = 100
    if ControlPackage.sharpness < -100: ControlPackage.sharpness = -100
    elif ControlPackage.sharpness > 100: ControlPackage.sharpness = 100
    if ControlPackage.contrast < -100: ControlPackage.contrast = -100
    elif ControlPackage.contrast > 100: ControlPackage.contrast = 100
    if ControlPackage.saturation < -100: ControlPackage.saturation = -100
    elif ControlPackage.saturation > 100: ControlPackage.saturation = 100
    if ControlPackage.iso < 100: ControlPackage.iso = 100
    elif ControlPackage.iso > 800: ControlPackage.iso = 800
    if ControlPackage.ss < 100 : ControlPackage.ss = 100

    if ControlPackage.vspeed <= 0 : ControlPackage.vspeed = 1
    if ControlPackage.vsteps <= 0 : ControlPackage.vsteps = 1
    if ControlPackage.hspeed <= 0 : ControlPackage.hspeed = 1
    if ControlPackage.hsteps <= 0 : ControlPackage.vsteps = 1


class HTTPRequestHandler(BaseHTTPRequestHandler):
 
  def __getCookie(self):
    if "Cookie" in self.headers:
      self.cookie = Cookie.SimpleCookie(self.headers["Cookie"])
    else:
      self.cookie = Cookie.SimpleCookie()
      self.cookie['refined'] = 'false'
      self.cookie['norefresh'] = 'false'
      self.cookie['cmode'] = 'day'

  def __sendCookie(self):
    for c in self.cookie.values():
      self.send_header('Set-Cookie', c.output(header='').lstrip())

  def do_POST(self):
    global camera_lock
    global videostarted 

    self.__getCookie()

    if None != re.search('/api/refresh$', self.path):
      print 'POST /api/refresh'
      try:
        length = int(self.headers.getheader('content-length'))
        data = cgi.parse_qs(self.rfile.read(length), keep_blank_values=1)
        ControlPackage.ss = int(float(data['ss'][0]) * 1000)
        ControlPackage.iso = int(data['iso'][0])
        ControlPackage.brightness = int(data['br'][0])
        ControlPackage.sharpness = int(data['sh'][0])
        ControlPackage.contrast = int(data['co'][0])
        ControlPackage.saturation = int(data['sa'][0])
	ControlPackage.Validate()

	ControlPackage.imageseq = ControlPackage.imageseq + 1
	localtime   = time.localtime()
	fname = 'temp/image-' + str(ControlPackage.imageseq) + '-' + time.strftime("%Y%m%d-%H%M%S", localtime) + '.jpg'

        # TAKE A PHOTO
        camera_lock.acquire(); 
        #ControlPackage.camera.start_preview()
        #time.sleep(0.5)
        #ControlPackage.camera.capture(fname, format='jpeg', resize=(ControlPackage.width,ControlPackage.height))

	# to enable -ss option, which is shutter speed, update the firmware sudo rpi-update
        cmdstr = 'raspistill -o ' + fname + ' -w ' + str(ControlPackage.width) \
                     + ' -h ' + str(ControlPackage.height) \
                     + ' -br ' + str(ControlPackage.brightness) \
                     + ' -ss ' + str(ControlPackage.ss) + ' -ISO ' + str(ControlPackage.iso) \
                     + ' -sh ' + str(ControlPackage.sharpness) + ' -co ' + str(ControlPackage.contrast) \
                     + ' -sa ' + str(ControlPackage.saturation) 
        print cmdstr
        os.system( cmdstr )

      except:	# use last available image if snapshot failed
	fname = 'temp/image-' + str(ControlPackage.imageseq-1) + '-*.jpg'
        for c in glob.glob(fname):
	    if os.path.isfile(c):
		fname = c
		break

      finally:
        camera_lock.release(); 
        #ControlPackage.camera.stop_preview()

      #READ IMAGE AND PUT ON SCREEN
      img = Image.open(fname)
      #basewidth = 800
      #wpercent = (basewidth/float(img.size[0]))
      #hsize = int((float(img.size[1])*float(wpercent)))
      #img = img.resize((basewidth,hsize), PIL.Image.ANTIALIAS)
      #img = img.transpose(Image.ROTATE_180)

      output = StringIO()
      img.save(output, format='JPEG')
      imgstr = base64.b64encode(output.getvalue()) 
      del img
      
      if ControlPackage.imageseq > ControlPackage.max_keep_snapshots:
          os.system('rm -f temp/image-' + str(ControlPackage.imageseq-ControlPackage.max_keep_snapshots) + '-*.jpg')

      self.send_response(200)
      self.send_header('Content-Type', 'application/json')
      self.__sendCookie()
      self.end_headers()
      self.wfile.write('{"seq": ' + str(ControlPackage.imageseq) + ', "timestamp": "'+  time.strftime("%Y%m%d-%H%M%S", localtime) +'", "image": "' + imgstr + '"}')

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

      move_method = 'DOUBLE'
      if motorid.lower() == 'v':
        try:
          if self.cookie['refined'].value == 'true':
      	    move_method = 'MICROSTEP'
        except:
      	    move_method = 'DOUBLE'

	ControlPackage.vspeed = speed
	ControlPackage.vsteps = steps
        ControlPackage.motorV.setSpeed(speed)
        ControlPackage.motorV.step(steps, dir.upper(), move_method)
        ControlPackage.motorV.release()

        if dir.upper() == 'FORWARD' and GPIO.input(ControlPackage.VH_pin):
          status = False
          statstr = 'Vertical highest limit reached!'

        if dir.upper() == 'BACKWARD' and GPIO.input(ControlPackage.VL_pin):
          status = False
          statstr = 'Vertical lowest limit reached!'

      else:
	ControlPackage.hspeed = speed
	ControlPackage.hsteps = steps
        ControlPackage.motorH.setSpeed(speed)
        ControlPackage.motorH.step(steps, dir.upper(), 'MICROSTEP')
        ControlPackage.motorH.release()
 
        if dir.upper() == 'FORWARD' and GPIO.input(ControlPackage.HL_pin):
          status = False
          statstr = 'Horizontal leftmost limit reached!'

        if dir.upper() == 'BACKWARD' and GPIO.input(ControlPackage.HR_pin):
          status = False
          statstr = 'Horizontal rightmost limit reached!'

      self.send_response(200)
      self.send_header('Content-Type', 'application/json')
      self.__sendCookie()
      self.end_headers()
      self.wfile.write('{"status": "' + str(status) + '", "detail": "' + statstr + '"}')

    else:
      self.send_response(403)
      self.send_header('Content-Type', 'application/json')
      self.__sendCookie()
      self.end_headers()
 
    return
 
  def do_GET(self):
    global camera_lock
    global videostarted 

    self.__getCookie()

    if None != re.search('/api/gettime$', self.path):	# get server time
      mytz="%+4.4d" % (time.timezone / -(60*60) * 100) # time.timezone counts westwards!
      dt  = datetime.datetime.now()
      dts = dt.strftime('%Y-%m-%d %H:%M:%S')  # %Z (timezone) would be empty
      nowstring="%s%s" % (dts,mytz)
 
      self.send_response(200)
      self.send_header('Content-Type', 'application/json')
      self.__sendCookie()
      self.end_headers()
      self.wfile.write('{"time": "' + nowstring + '"}')

    elif None != re.search('/api/startvideo', self.path):	# start video
      print 'GET /api/startvideo'

      ControlPackage.ss = int(float(self.path.split('/')[-6]) * 1000)
      ControlPackage.iso = int(self.path.split('/')[-5])
      ControlPackage.brightness = int(self.path.split('/')[-4])
      ControlPackage.sharpness = int(self.path.split('/')[-3])
      ControlPackage.contrast = int(self.path.split('/')[-2])
      ControlPackage.saturation = int(self.path.split('/')[-1])
 
      if not videostarted:
        time.sleep(5)
        cmdstr = 'sh runvideo.sh ' + str(int(ControlPackage.width/2.1875)) \
                     + ' ' + str(int(ControlPackage.height/2.1875)) \
                     + ' ' + str(ControlPackage.ss) + ' ' + str(ControlPackage.iso) \
                     + ' ' + str(ControlPackage.brightness) \
                     + ' ' + str(ControlPackage.sharpness) + ' ' + str(ControlPackage.contrast) \
                     + ' ' + str(ControlPackage.saturation) 
        print cmdstr
        os.system( cmdstr )
        videostarted = True
        time.sleep(8)

      self.send_response(200)
      self.send_header('Content-Type', 'application/json')
      self.__sendCookie()
      self.end_headers()
      self.wfile.write('{"status": "' + 'true' + '"}')

    elif None != re.search('/api/stopvideo$', self.path):	# stop video
      print 'GET /api/stopvideo'
 
      cmdstr = 'sh stopvideo.sh' 
      print cmdstr
      os.system( cmdstr )
      videostarted = False

      self.send_response(200)
      self.send_header('Content-Type', 'application/json')
      self.__sendCookie()
      self.end_headers()
      self.wfile.write('{"status": "' + 'true' + '"}')

    elif None != re.search('/api/init$', self.path):	# load initial params
      self.send_response(200)
      self.send_header('Content-Type', 'application/json')
      self.__sendCookie()
      self.end_headers()
      self.wfile.write('{' \
		        + '"vspeed": "' + str(ControlPackage.vspeed) + '",' \
		        + '"vsteps": "' + str(ControlPackage.vsteps) + '",' \
		        + '"hspeed": "' + str(ControlPackage.hspeed) + '",' \
		        + '"hsteps": "' + str(ControlPackage.hsteps) + '",' \
		        + '"ss": "' + str(ControlPackage.ss/1000.0) + '",' \
		        + '"iso": "' + str(ControlPackage.iso) + '",' \
		        + '"br": "' + str(ControlPackage.brightness) + '",' \
		        + '"sh": "' + str(ControlPackage.sharpness) + '",' \
		        + '"co": "' + str(ControlPackage.contrast) + '",' \
		        + '"sa": "' + str(ControlPackage.saturation) + '"' \
			+ '}')

    elif None != re.search('/api/snapshot', self.path):
      print 'GET /api/snapshot'
      try:
        ControlPackage.ss = int(float(self.path.split('/')[-6]) * 1000)
        ControlPackage.iso = int(self.path.split('/')[-5])
        ControlPackage.brightness = int(self.path.split('/')[-4])
        ControlPackage.sharpness = int(self.path.split('/')[-3])
        ControlPackage.contrast = int(self.path.split('/')[-2])
        ControlPackage.saturation = int(self.path.split('/')[-1])

	ControlPackage.Validate()

	ControlPackage.simageseq = ControlPackage.simageseq + 1
	localtime   = time.localtime()
	fname = 'temp/snapshot-' + str(ControlPackage.simageseq) + '-' + time.strftime("%Y%m%d-%H%M%S", localtime) + '.jpg'


        # TAKE A PHOTO OF HIGH RESOLUTION
        camera_lock.acquire(); 

        #ControlPackage.camera.start_preview()
        #time.sleep(0.5)
        #ControlPackage.camera.capture(fname, format='jpeg', resize=(ControlPackage.width,ControlPackage.height))

	cmdstr = 'raspistill -o ' + fname + ' -br ' \
                     + str(ControlPackage.brightness) \
                     + ' -ss ' + str(ControlPackage.ss) + ' -ISO ' + str(ControlPackage.iso) \
                     + ' -sh ' + str(ControlPackage.sharpness) + ' -co ' + str(ControlPackage.contrast) \
                     + ' -sa ' + str(ControlPackage.saturation) 
	print cmdstr
        os.system( cmdstr )

      finally:
        camera_lock.release(); 
        #ControlPackage.camera.stop_preview()

      #READ IMAGE AND PUT ON SCREEN
      #img = Image.open(fname)
      #img = img.transpose(Image.ROTATE_180)

      #img.save(fname, format='JPEG')

      if ControlPackage.simageseq > ControlPackage.max_keep_snapshots:
          os.system('rm -f temp/snapshot-' + str(ControlPackage.simageseq-ControlPackage.max_keep_snapshots) + '-*.jpg')


      self.send_response(200)
      self.send_header('Content-Type', 'application/jpeg')
      self.send_header('Content-Disposition', 'inline;filename="' + fname.replace('temp/', '') + '"')

      self.__sendCookie()
      self.end_headers()
      with open(fname, 'r') as content_file:
        content = content_file.read()
        self.wfile.write(content)

    elif None != re.search('/api/videoshot', self.path):
      print 'GET /api/videoshot'
      try:
        ControlPackage.ss = int(float(self.path.split('/')[-7]) * 1000)
        ControlPackage.iso = int(self.path.split('/')[-6])
        ControlPackage.brightness = int(self.path.split('/')[-5])
        ControlPackage.sharpness = int(self.path.split('/')[-4])
        ControlPackage.contrast = int(self.path.split('/')[-3])
        ControlPackage.saturation = int(self.path.split('/')[-2])
        ControlPackage.videolen = int(self.path.split('/')[-1])

	ControlPackage.Validate()

	ControlPackage.videoseq = ControlPackage.videoseq + 1
	localtime   = time.localtime()
	fname = 'temp/videoshot-' + str(ControlPackage.videoseq) + '-' + time.strftime("%Y%m%d-%H%M%S", localtime) + '.h264'

        # TAKE A PHOTO OF HIGH RESOLUTION
        camera_lock.acquire(); 

	cmdstr = 'raspivid -o ' + fname + ' -br ' \
                     + str(ControlPackage.brightness) \
                     + ' -ss ' + str(ControlPackage.ss) + ' -ISO ' + str(ControlPackage.iso) \
                     + ' -sh ' + str(ControlPackage.sharpness) + ' -co ' + str(ControlPackage.contrast) \
                     + ' -sa ' + str(ControlPackage.saturation) + ' -t ' + str(ControlPackage.videolen*1000)
	print cmdstr
        os.system( cmdstr )
    
      finally:
        camera_lock.release(); 

      if ControlPackage.videoseq > ControlPackage.max_keep_videoshots:
          os.system('rm -f temp/videoshot-' + str(ControlPackage.videoseq-ControlPackage.max_keep_videoshots) + '-*.h264')

      self.send_response(200)
      self.send_header('Content-Type', 'application/octet-stream')
      self.send_header('Content-Disposition', 'attachment;filename="' + fname.replace('temp/', '') + '"')

      self.__sendCookie()
      self.end_headers()
      with open(fname, 'r') as content_file:
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
    print "retrieve file " + filepath

    if os.path.isfile(filepath) :
      self.send_response(200)
      self.send_header('Content-Type', contenttype)
      self.__sendCookie()
      self.end_headers()
      with open(filepath, 'r') as content_file:
        content = content_file.read()
        self.wfile.write(content)
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


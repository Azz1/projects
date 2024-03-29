import time
import math
import os
import sys, traceback
import cv2
import queue
import picamera
import threading
import PIL
import numpy as np
from PIL import Image
import base64
from io import BytesIO
from StepMotor import ControlPackage
from collections import deque
from abc import ABCMeta, abstractmethod

cv2lib_path = os.path.abspath('../cv2')
sys.path.append(cv2lib_path)
from detect_bright_spots import CV2Helper

camera_lock = threading.Lock()
videostarted = False

# Abstract base class for camera 
class Camera :

  __metaclass__ = ABCMeta
         
  @abstractmethod
  def init(self): pass

  @abstractmethod
  def snapshot(self) : pass

  @abstractmethod
  def snapshot_full(self) : pass

  @abstractmethod
  def videoshot(self): pass

  @abstractmethod
  def startvideo(self): pass
 
  @abstractmethod
  def stopvideo(self): pass
 
  @abstractmethod
  def release(self): pass

# Camera using raspistill and raspivid commandline
class RaspiShellCamera(Camera):

  def init(self): pass

  def snapshot(self) : 
    global camera_lock
    global videostarted

    if videostarted: return

    track_err = False
    try:
      ControlPackage.imageseq = ControlPackage.imageseq + 1
      localtime   = time.localtime()
      fname = 'temp/image-' + str(ControlPackage.imageseq) + '-' + time.strftime("%Y%m%d-%H%M%S", localtime) + '.jpg'

      # TAKE A PHOTO
      camera_lock.acquire();
      #ControlPackage.camera.start_preview()
      #time.sleep(0.5)
      #ControlPackage.camera.capture(fname, format='jpeg', resize=(ControlPackage.width,ControlPackage.height))

      # to enable -ss option, which is shutter speed, update the firmware sudo rpi-update
      ss = ControlPackage.ss 
      if ss > 4000000: ss = 4000000

      roistr = ' -roi ' + str(ControlPackage.roi_l) + ',' + str(ControlPackage.roi_l) + ',' + str(ControlPackage.roi_w) + ',' + str(ControlPackage.roi_w) 
      cmdstr = 'raspistill -o ' + fname \
                     + (' -vf ' if ControlPackage.vflip == 'true' else '') \
                     + (' -hf ' if ControlPackage.hflip == 'true' else '') \
                     + ' -w ' + str(ControlPackage.width) \
                     + ' -h ' + str(ControlPackage.height) + roistr \
                     + ' -bm -br ' + str(ControlPackage.brightness) \
                     + (' -awb off -awbg 2.1,1.7 -ex off -ag {:.0f} -dg 3.0 -ss '.format(ControlPackage.iso/100) if ControlPackage.cmode == 'night' else ' -ss ') + str(ss) \
                     + (' -drc high -ev 10 -md 2 -ISO auto ' if ControlPackage.cmode == 'night' else (' -ISO ' + str(ControlPackage.iso))) \
                     + ' -st --nopreview -sh ' + str(ControlPackage.sharpness) + ' -co ' + str(ControlPackage.contrast) \
                     + ' -sa ' + str(ControlPackage.saturation)
      print( cmdstr)
      os.system( cmdstr )

    except:   # use last available image if snapshot failed
      fname = 'temp/image-' + str(ControlPackage.imageseq-1) + '-*.jpg'
      for c in glob.glob(fname):
        if os.path.isfile(c):
          fname = c
          break

    finally:
      camera_lock.release();

    #READ IMAGE AND PUT ON SCREEN
    imgstr = ""
    #if ControlPackage.isTracking.is_set():	#tracking mode, show tracking config
    if ControlPackage.ref0_x != ControlPackage.ref1_x or ControlPackage.ref0_y != ControlPackage.ref1_y:
                                                #Ref point defined, show tracking config
      try:
        print("Blur Limit: ", "{}".format(ControlPackage.tk_blur_limit), " Thresh Limit: ", "{}".format(ControlPackage.tk_thresh_limit))
        cvhelper = CV2Helper( blur_limit = ControlPackage.tk_blur_limit, thresh_limit = ControlPackage.tk_thresh_limit )
        # load the image, convert it to grayscale, and blur it
        img = cvhelper.loadimage(fname)
        [centers, radius, img] = cvhelper.processimage(mark = True)
        cvhelper.printcenters()
        cvhelper.setref(ControlPackage.ref0_x, ControlPackage.ref0_y, ControlPackage.ref1_x, ControlPackage.ref1_y)
        [idx, cntr, img] = cvhelper.find_tracking_point()
        if idx >= 0 :
          print("Tracking Point ", "#{}".format(idx+1), "- (", int(cntr[0]), ",", int(cntr[1]), ") ")

          ControlPackage.tk_delta_ra, ControlPackage.tk_delta_dec = cvhelper.calc_offset(cntr[0], cntr[1])
          print("\nDelta-RA:", ControlPackage.tk_delta_ra, " Delta-Dec:", ControlPackage.tk_delta_dec)
          if len(ControlPackage.tk_queue) >= ControlPackage.tk_queue.maxlen:
            ControlPackage.tk_queue.popleft()
          ControlPackage.tk_queue.append([localtime, ControlPackage.tk_delta_ra, ControlPackage.tk_delta_dec, cntr[0], cntr[1]])
        else :
          track_err = True

        ret, buf = cv2.imencode( '.jpg', img )
        imgstr = base64.b64encode( np.array(buf) ).decode("utf-8") 

      except:
        traceback.print_exc()
        img = Image.open(fname)

        #basewidth = 800
        #wpercent = (basewidth/float(img.size[0]))
        #hsize = int((float(img.size[1])*float(wpercent)))
        #img = img.resize((basewidth,hsize), PIL.Image.ANTIALIAS)
        #img = img.transpose(Image.ROTATE_180)

        output = BytesIO()
        img.save(output, format='JPEG')
        imgstr = base64.b64encode(output.getvalue()).decode("utf-8") 
        del img
        track_err = True

    else :
      img = Image.open(fname)

      #basewidth = 800
      #wpercent = (basewidth/float(img.size[0]))
      #hsize = int((float(img.size[1])*float(wpercent)))
      #img = img.resize((basewidth,hsize), PIL.Image.ANTIALIAS)
      #img = img.transpose(Image.ROTATE_180)

      output = BytesIO()
      img.save(output, format='JPEG')
      imgstr = base64.b64encode(output.getvalue()).decode("utf-8") 
      del img

    if ControlPackage.imageseq > ControlPackage.max_keep_snapshots:
      os.system('rm -f temp/image-' + str(ControlPackage.imageseq-ControlPackage.max_keep_snapshots) + '-*.jpg')


    return localtime, imgstr, track_err

  def snapshot_full(self) : 
    global camera_lock
    global videostarted

    if videostarted: return

    try:
      ControlPackage.simageseq = ControlPackage.simageseq + 1
      localtime   = time.localtime()

      fname = 'temp/snapshot-' + str(ControlPackage.simageseq) + '-' + time.strftime("%Y%m%d-%H%M%S", localtime) 
      if  ControlPackage.timelapse > 1:
        fname = fname + '-%02d'
      if ControlPackage.rawmode == 'true' :
        fname = fname + '-raw'
      fname = fname + '.jpg'


      # TAKE A PHOTO OF HIGH RESOLUTION
      camera_lock.acquire();

      #ControlPackage.camera.start_preview()
      #time.sleep(0.5)
      #ControlPackage.camera.capture(fname, format='jpeg', resize=(ControlPackage.width,ControlPackage.height))

      ts = ''
      tl = ControlPackage.ss/1000 + 2000
      tt = tl * (ControlPackage.timelapse-1)
      if ControlPackage.timelapse > 1:
        ts = '-tl ' + str(tl) + ' -t ' +  str(tt)
        
      roistr = ' -roi ' + str(ControlPackage.roi_l) + ',' + str(ControlPackage.roi_l) + ',' + str(ControlPackage.roi_w) + ',' + str(ControlPackage.roi_w) 
      cmdstr = 'raspistill ' + (' --raw ' if ControlPackage.rawmode == 'true' else '') + ' -o ' + fname \
		     + (' -vf ' if ControlPackage.vflip == 'true' else '') \
		     + (' -hf ' if ControlPackage.hflip == 'true' else '') \
		     + ' -bm -br ' + str(ControlPackage.brightness) + roistr \
                     + (' -awb off -awbg 2.1,1.7 -ex off -ag {:.0f} -dg 1.0 -ss '.format(ControlPackage.iso/100) if ControlPackage.cmode == 'night' else ' -ss ') + str(ControlPackage.ss) \
                     + (' -drc high -ev 10 -md 2 -ISO auto ' if ControlPackage.cmode == 'night' else (' -ISO ' + str(ControlPackage.iso))) \
                     + ' -sh ' + str(ControlPackage.sharpness) + ' -co ' + str(ControlPackage.contrast) \
                     + ' -st --nopreview -sa ' + str(ControlPackage.saturation) + ' ' + ts

                     #replacement parameters
                     #+ (' -ex night -ag 12.0 -dg 4.0 -ss ' if ControlPackage.cmode == 'night' else ' -ss ') + str(ControlPackage.ss) \
                     #+ (' -ISO auto ' if ControlPackage.cmode == 'night' else (' -ISO ' + str(ControlPackage.iso))) \
      print( cmdstr)
      os.system( cmdstr )

    finally:
      camera_lock.release();

    #READ IMAGE AND PUT ON SCREEN
    #img = Image.open(fname)
    #img = img.transpose(Image.ROTATE_180)

    #img.save(fname, format='JPEG')

    if ControlPackage.simageseq > ControlPackage.max_keep_snapshots:
      os.system('rm -f temp/snapshot-' + str(ControlPackage.simageseq-ControlPackage.max_keep_snapshots) + '-*.jpg')

    fname = fname.replace('-%02d', '-01')
    return fname

  def videoshot(self): 
    global camera_lock
    global videostarted

    try:
      ControlPackage.videoseq = ControlPackage.videoseq + 1
      localtime   = time.localtime()
      fname = 'temp/videoshot-' + str(ControlPackage.videoseq) + '-' + time.strftime("%Y%m%d-%H%M%S", localtime) + '.h264'

      # TAKE A PHOTO OF HIGH RESOLUTION
      camera_lock.acquire();

      roistr = ' -roi ' + str(ControlPackage.roi_l) + ',' + str(ControlPackage.roi_l) + ',' + str(ControlPackage.roi_w) + ',' + str(ControlPackage.roi_w) 
      cmdstr = 'raspivid -o ' + fname \
                     + (' -vf ' if ControlPackage.vflip == 'true' else '') \
                     + (' -hf ' if ControlPackage.hflip == 'true' else '') \
                     + ' -br ' + str(ControlPackage.brightness) + roistr \
                     + ' -ss ' + str(ControlPackage.ss) + ' -ISO ' + str(ControlPackage.iso) \
                     + ' -sh ' + str(ControlPackage.sharpness) + ' -co ' + str(ControlPackage.contrast) \
                     + ' --nopreview -sa ' + str(ControlPackage.saturation) + ' -t ' + str(ControlPackage.videolen*1000)
      print( cmdstr)
      os.system( cmdstr )

    finally:
      camera_lock.release();

    if ControlPackage.videoseq > ControlPackage.max_keep_videoshots:
      os.system('rm -f temp/videoshot-' + str(ControlPackage.videoseq-ControlPackage.max_keep_videoshots) + '-*.h264')

    return fname

  def startvideo(self): 
    global videostarted
    if not videostarted:
      try:
        camera_lock.acquire();
        time.sleep(5)
        cmdstr = 'sh runvideo.sh ' + str(int(ControlPackage.width/2.1875*2)) \
                     + ' ' + str(int(ControlPackage.height/2.1875*2)) \
                     + ' ' + str(ControlPackage.ss) + ' ' + str(ControlPackage.iso) \
                     + ' ' + str(ControlPackage.brightness) \
                     + ' ' + str(ControlPackage.sharpness) + ' ' + str(ControlPackage.contrast) \
                     + ' ' + str(ControlPackage.saturation) \
                     + ' ' + str(ControlPackage.roi_l) \
                     + ' ' + str(ControlPackage.roi_w) \
                     + (' -vf ' if ControlPackage.vflip == 'true' else '') \
                     + (' -hf ' if ControlPackage.hflip == 'true' else '')
        print( cmdstr)
        os.system( cmdstr )
        videostarted = True
        time.sleep(8)
      finally:
        camera_lock.release();

 
  def stopvideo(self): 
    global videostarted
    videostarted = False
    cmdstr = 'sh stopvideo.sh'
    print( cmdstr)
    os.system( cmdstr )

  def haltsys(self): 
    cmdstr = 'sudo halt'
    print( cmdstr)
    os.system( cmdstr )

 
  def release(self): pass

ControlPackage.camera = RaspiShellCamera()


#!/usr/bin/python

# Python library for Star Locator and tracking

from dateutil import tz
import RPi.GPIO as GPIO
import datetime
import os
import time
import sys
import math
import threading
import Queue
from array import *
from StarLocator import StarLocator

motorlib_path = os.path.abspath('../Adafruit')
sys.path.append(motorlib_path)
from StepMotor import StepMotor
from StepMotor import ControlPackage

lsm303lib_path = os.path.abspath('../Adafruit/Adafruit_LSM303')
sys.path.append(lsm303lib_path)
from Adafruit_LSM303 import Adafruit_LSM303

class StarTracking:

    # Parameters:
    #   Self Location:
    #     lat  - Latitude in degree
    #     long - Longitude in degree
    #
    #   Target:
    #     mode - ALTAZ, RADEC
    #     ra_h, ra_m, ra_s     - RA 
    #     dec_dg, dec_m, dec_s - DEC
    #     az   - AZ in degree	azadj - AZ adjustment
    #     alt  - ALT in degree	altadj - ALT adjustment

    def __init__(self, lat, long, mode, ra_h, ra_m, ra_s, dec_dg, dec_m, dec_s, az, alt, v_speed, v_steps, h_speed, h_steps):
	self.locator = StarLocator(lat, long)
	self.position = Adafruit_LSM303()
	self.mode = mode
	self.ra_h = ra_h	# target RA & DEC if mode <> ALTAZ
	self.ra_m = ra_m
	self.ra_s = ra_s
	self.dec_dg = dec_dg
	self.dec_m = dec_m
	self.dec_s = dec_s
	self.az = az		# target AZ & ALT if mode = ALTAZ
	self.alt = alt

	self.v_steps = v_steps	# initial motor params
	self.v_speed = v_speed
	self.h_steps = h_steps
	self.h_speed = h_speed
	
	ControlPackage.exitFlag.set()
    	self.motor_h = ControlPackage.motorH
    	self.motor_v = ControlPackage.motorV

    def GetTarget(self):
	if self.mode == "ALTAZ":
	    return (self.az, self.alt)
	else:
	    return self.locator.RaDec2AltAz1(self.ra_h, self.ra_m, self.ra_s, self.dec_dg, self.dec_m, self.dec_s, datetime.datetime.utcnow())

    def read(self):
	alt_arr = array('d', [0.0, 0.0, 0.0, 0.0, 0.0])
	az_arr = array('d', [0.0, 0.0, 0.0, 0.0, 0.0])

	for i in range(len(alt_arr)):
          alt_arr[i], pos_y, pos_z, az_arr[i] = self.position.read()
          time.sleep(0.1)
	   
	min_val = 9999.0
	max_val = -9999.0
	min_idx = 0
	max_idx = 0
	for i in range(len(alt_arr)):
	  if alt_arr[i] < min_val:
	    min_val = alt_arr[i]
	    min_idx = i
	  if alt_arr[i] > max_val:
	    max_val = alt_arr[i]
	    max_idx = i
	alt_arr[min_idx] = 0.0  
	alt_arr[max_idx] = 0.0  
	alt_i = 2.0
	if min_idx == max_idx: alt_i = 1.0
	
	min_val = 9999.0
	max_val = -9999.0
	min_idx = 0
	max_idx = 0
	for i in range(len(az_arr)):
	  if az_arr[i] < min_val:
	    min_val = az_arr[i]
	    min_idx = i
	  if az_arr[i] > max_val:
	    max_val = az_arr[i]
	    max_idx = i
	az_arr[min_idx] = 0.0  
	az_arr[max_idx] = 0.0  
	az_i = 2.0
	if min_idx == max_idx: az_i = 1.0

	return sum(alt_arr) / (len(alt_arr)-alt_i), sum(az_arr) / (len(az_arr)-az_i)

    def Track(self):
	min_v_offset = 0.5
	min_h_offset = 0.5
	last_v_offset = 0.0
	last_h_offset = 0.0
	v_offset = 0.0
	h_offset = 0.0
	v_dir = ""
	h_dir = ""

	init_v_steps = self.v_steps
	init_h_steps = self.h_steps
	min_v_steps = 10
	min_h_steps = 2
	last_v_steps = self.v_steps
	last_h_steps = self.h_steps
	v_steps = last_v_steps
	h_steps = last_h_steps

        try:
    	   while ControlPackage.isTracking.is_set():
	      target_az, target_alt = self.GetTarget()

              print "\nTarget location: \t(" + str(target_az) + ", \t" + str(target_alt) + ")"
   
              pos_alt, pos_az = self.read()
              print "Current position: \t(" + str(pos_az + ControlPackage.tgazadj) + ", \t" + str(pos_alt + ControlPackage.tgaltadj) + ")\n"
   
      	      ControlPackage.threadLock.acquire()
	      ControlPackage.tgaz = target_az
	      ControlPackage.tgalt = target_alt
	      ControlPackage.curaz = pos_az + ControlPackage.tgazadj
	      ControlPackage.curalt = pos_alt + ControlPackage.tgaltadj
              ControlPackage.threadLock.release()

	      v_offset = pos_alt + ControlPackage.tgaltadj - target_alt
	      h_offset = pos_az + ControlPackage.tgazadj - target_az
	      if h_offset > 180 : h_offset = h_offset - 360
	      elif h_offset < -180 : h_offset = 360 + h_offset

	      if math.fabs(v_offset) < min_v_offset and math.fabs(h_offset) < min_h_offset: pass
	      else:
	         if math.fabs(v_offset) < 1 : v_steps = min_v_steps
	         else : v_steps = init_v_steps

	         if math.fabs(h_offset) < 1 : h_steps = min_h_steps
	         else : h_steps = init_h_steps
	         
	         if v_offset > 0 : v_dir = "DOWN"
	         else : v_dir = "UP"

	         if h_offset > 0 : h_dir = "LEFT"
	         else : h_dir = "RIGHT"

	         if math.fabs(v_offset) >= min_v_offset :
      	            ControlPackage.threadLock.acquire()
		    ControlPackage.v_cmdqueue.put((v_dir, self.v_speed, v_steps))
                    ControlPackage.threadLock.release()
	         if h_offset >= 2 * min_h_offset or h_offset <= - min_h_offset: 
      	            ControlPackage.threadLock.acquire()
		    ControlPackage.h_cmdqueue.put((h_dir, self.h_speed, h_steps))
                    ControlPackage.threadLock.release()

	      last_v_offset = v_offset
	      last_h_offset = h_offset
	      last_v_steps = v_steps
	      last_h_steps = h_steps
              time.sleep(1.0)

        except KeyboardInterrupt:
	   print "Interruption accepted, exiting ..."
           ControlPackage.isTracking.clear()
           ControlPackage.exitFlag.clear()
    	   self.motor_h.join()
    	   self.motor_v.join()

	   raise

if __name__ == '__main__':

    from time import sleep

    tr = StarTracking(42.27069402, -83.04411196, "ALTAZ", 
			16.0, 41.0, 42.0, 36.0, 28.0, 0.0, 
			250.0, 20.0, 
			30, 100, 5, 50)

    print 'Start star tracking ...'
    ControlPackage.isTracking.set()
    tr.Track()


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
from StarLocator import StarLocator

motorlib_path = os.path.abspath('../Adafruit')
sys.path.append(motorlib_path)
from StepMotor import StepMotor

lsm303lib_path = os.path.abspath('../Adafruit/Adafruit_LSM303')
sys.path.append(lsm303lib_path)
from Adafruit_LSM303 import Adafruit_LSM303

web_path = os.path.abspath('../Web')
sys.path.append(web_path)
from httpserver import ControlPackage

exitFlag = threading.Event()
threadLock = threading.Lock()
v_cmdqueue = Queue.Queue()	#queue of objects (dir=UP/DOWN, speed, steps) UP-FWD, DOWN-BKWD
h_cmdqueue = Queue.Queue()	#queue of objects (dir=LEFT/RIGHT, speed, steps) LEFT-FWD, RIGHT-BKWD

class MotorControlThread (threading.Thread):
    def __init__(self, threadName):
        threading.Thread.__init__(self)
        self.threadName = threadName

	# initialize vertical step motor
  	self.motor = StepMotor(0x60, debug=False)
  	self.motor.setFreq(1600)
	if self.threadName == "H-Motor":
	   self.q = h_cmdqueue
  	   self.motor.setPort("M1M2")
  	   self.motor.setSensor(ControlPackage.HL_pin, ControlPackage.HR_pin)
	else:
	   self.q = v_cmdqueue
  	   self.motor.setPort("M3M4")
  	   self.motor.setSensor(ControlPackage.VH_pin, ControlPackage.VL_pin)


    def run(self):
        print "Starting " + self.threadName
	while exitFlag.is_set():
           dir = ""
           speed = 0
           steps = 0
	  
	   threadLock.acquire()
	   if not self.q.empty():
    	      (dir, speed, steps) = self.q.get()
           threadLock.release()
	   
	   if dir != "" : 

	      if self.threadName == "H-Motor":
	      # LEFT-FWD, RIGHT-BKWD
	         self.motor.setSpeed(speed)
	         if dir == "LEFT":
                    self.motor.step(steps, "FORWARD", "MICROSTEP")
                 else:
                    self.motor.step(steps, "BACKWARD", "MICROSTEP")
                 self.motor.release()

                 if dir.upper() == 'LEFT' and GPIO.input(ControlPackage.HL_pin):
                    print 'Horizontal leftmost limit reached!'

                 if dir.upper() == 'RIGHT' and GPIO.input(ControlPackage.HR_pin):
                    print 'Horizontal rightmost limit reached!'	
	      	
	      else:
	      # UP-FWD, DOWN-BKWD
	         self.motor.setSpeed(speed)
	         if dir == "UP":
                    self.motor.step(steps, "FORWARD", "MICROSTEP")
                 else:
                    self.motor.step(steps, "BACKWARD", "MICROSTEP")
                 self.motor.release()

                 if dir.upper() == 'UP' and GPIO.input(ControlPackage.VH_pin):
                    print 'Vertical highest limit reached!'

                 if dir.upper() == 'DOWN' and GPIO.input(ControlPackage.VL_pin):
                    print 'Vertical lowest limit reached!'	

           time.sleep(0.1)

        print "Exiting " + self.threadName

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
    #     az   - AZ in degree
    #     alt  - ALT in degree

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
	
	exitFlag.set()
	self.istracking = False
    	self.motor_h = MotorControlThread("H-Motor")
    	self.motor_v = MotorControlThread("V-Motor")
    	self.motor_h.daemon = True
    	self.motor_v.daemon = True
    	self.motor_h.start()
    	self.motor_v.start()

    def GetTarget(self):
	if self.mode == "ALTAZ":
	    return (self.az, self.alt)
	else:
	    return self.locator.RaDec2AltAz1(self.ra_h, self.ra_m, self.ra_s, self.dec_dg, self.dec_m, self.dec_s, datetime.datetime.utcnow())

    def Track(self):
	min_v_offset = 0.5
	min_h_offset = 0.5
	last_v_offset = 0.0
	last_h_offset = 0.0
	v_offset = 0.0
	h_offset = 0.0
	v_dir = ""
	h_dir = ""

	v_speed = 30
	h_speed = 5

	init_v_steps = 100
	init_h_steps = 5
	min_v_steps = 10
	min_h_steps = 1
	last_v_steps = 100
	last_h_steps = 5
	v_steps = last_v_steps
	h_steps = last_h_steps

        try:
    	   while True:
	      target_az, target_alt = self.GetTarget()
              print "Target: (" + str(target_az) + ", " + str(target_alt) + ")"
   
              pos_x, pos_y, pos_alt, pos_az = tr.position.read()
              print "Current position: (" + str(pos_az) + ", " + str(pos_alt) + ")"
   
	      v_offset = pos_alt - target_alt
	      h_offset = pos_az - target_az
	      if h_offset > 180 : h_offset = 360 - h_offset
	      elif h_offset < -180 : h_offset = 360 + h_offset

	      if math.fabs(v_offset) < min_v_offset and math.fabs(h_offset) < min_h_offset: pass
	      else:
	         if math.fabs(v_offset) < 5 : v_steps = min_v_steps
	         else : v_steps = init_v_steps

	         if math.fabs(h_offset) < 5 : h_steps = min_h_steps
	         else : h_steps = init_h_steps
	         
	         if v_offset > 0 : v_dir = "DOWN"
	         else : v_dir = "UP"

	         if h_offset > 0 : h_dir = "LEFT"
	         else : h_dir = "RIGHT"

	         if math.fabs(v_offset) >= min_v_offset :
      	            threadLock.acquire()
		    v_cmdqueue.put((v_dir, v_speed, v_steps))
                    threadLock.release()
	         if math.fabs(h_offset) >= min_h_offset : 
      	            threadLock.acquire()
		    h_cmdqueue.put((h_dir, h_speed, h_steps))
                    threadLock.release()

	      last_v_offset = v_offset
	      last_h_offset = h_offset
	      last_v_steps = v_steps
	      last_h_steps = h_steps
              time.sleep(1.0)

        except KeyboardInterrupt:
	   print "Interruption accepted, exiting ..."
           exitFlag.clear()
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
    tr.Track()


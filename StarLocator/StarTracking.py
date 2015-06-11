#!/usr/bin/python

# Python library for Star Locator and tracking

from dateutil import tz
import datetime
import os
import sys
import math
import threading
import Queue
from StarLocator import StarLocator

motorlib_path = os.path.abspath('../Adafruit')
sys.path.append(motorlib_path)
from Adafruit_Motor_Driver import StepMotor

lsm303lib_path = os.path.abspath('../Adafruit/Adafruit_LSM303')
sys.path.append(lsm303lib_path)
from Adafruit_LSM303 import Adafruit_LSM303

web_path = os.path.abspath('../Web')
sys.path.append(web_path)
from httpserver import ControlPackage

exitFlag = False
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
        print "Starting " + self.name

	while True:
	   threadLock.acquire()
	   if exitFlag: break
	   if not self.q.empty():
    	      print q.get()
           threadLock.release()

           time.sleep(0.1)

        print "Exiting " + self.name

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
	
	self.istracking = False

    def GetTarget(self):
	if self.mode == "ALTAZ":
	    return (self.az, self.alt)
	else:
	    return self.locator.RaDec2AltAz1(self.ra_h, self.ra_m, self.ra_s, self.dec_dg, self.dec_m, self.dec_s, datetime.datetime.utcnow())

    def Track(self):
	target_az, target_alt = self.GetTarget()
        print "Target: (" + str(target_az) + ", " + str(target_alt) + ")"

        pos_x, pos_y, pos_alt, pos_az = tr.position.read()
        print "Current position: (" + str(pos_az) + ", " + str(pos_alt) + ")"


if __name__ == '__main__':

    from time import sleep

    tr = StarTracking(42.27069402, -83.04411196, "ALTAZ", 
			16.0, 41.0, 42.0, 36.0, 28.0, 0.0, 
			220.0, 45.0, 
			30, 100, 5, 50)

    print 'Start star tracking ...'
    tr.Track()

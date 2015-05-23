#!/usr/bin/python

# Python library for Star Locator and tracking

from dateutil import tz
import datetime
import os
import sys
import math
from StarLocator import StarLocator

motorlib_path = os.path.abspath('../Adafruit')
sys.path.append(motorlib_path)
from Adafruit_Motor_Driver import StepMotor

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
    #     az   - AZ in degree
    #     alt  - ALT in degree

    def __init__(self, lat, long, mode, ra_h, ra_m, ra_s, dec_dg, dec_m, dec_s, az, alt):
	self.locator = StarLocator(lat, long)
	self.position = Adafruit_LSM303()
	self.mode = mode
	self.ra_h = ra_h
	self.ra_m = ra_m
	self.ra_s = ra_s
	self.dec_dg = dec_dg
	self.dec_m = dec_m
	self.dec_s = dec_s
	self.az = az
	self.alt = alt

    def GetTarget(self):
	if self.mode == "ALTAZ":
	    return (self.az, self.alt)
	else:
	    return self.locator.RaDec2AltAz1(self.ra_h, self.ra_m, self.ra_s, self.dec_dg, self.dec_m, self.dec_s, datetime.datetime.utcnow())

    def Track(self):
	target_az, target_alt = self.GetTarget()
        print "Target: (" + str(target_az) + ", " + str(target_alt) + ")"

        pos_alt, pos_y, pos_z, pos_az = tr.position.read()
        print "Current position: (" + str(pos_az) + ", " + str(pos_alt) + ")"


if __name__ == '__main__':

    from time import sleep

    tr = StarTracking(42.27069402, -83.04411196, "ALTAZ", 16.0, 41.0, 42.0, 36.0, 28.0, 0.0, 180.0, 45.0)

    print 'Start star tracking ...'
    tr.Track()

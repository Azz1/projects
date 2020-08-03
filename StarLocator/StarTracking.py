#!/usr/bin/python

# Python library for Star Locator and tracking

from dateutil.parser import tz
import RPi.GPIO as GPIO
import datetime
import os
import time
import sys
import math
import threading
import queue
from array import *
from StarLocator import StarLocator
from abc import ABCMeta, abstractmethod

motorlib_path = os.path.abspath('../Adafruit')
sys.path.append(motorlib_path)
from StepMotor import StepMotor
from StepMotor import ControlPackage

lsm303lib_path = os.path.abspath('../Adafruit/Adafruit_LSM303')
sys.path.append(lsm303lib_path)
from Adafruit_LSM303 import Adafruit_LSM303

# Abstract base class for stepper motor
class ITracking :

    __metaclass__ = ABCMeta

    @abstractmethod
    def Track(self): pass

class EQStarTracking(ITracking):
    
    def __init__(self):
        ControlPackage.exitFlag.set()
        self.motor_h = ControlPackage.motorH
        self.motor_v = ControlPackage.motorV

    def Track(self): 	# Track is called after each time refresh is done
        thresh_limit = 5
        trace_ref_cnt = 5
        ControlPackage.move_method = "MICROSTEP"

        #get average delta RA and DEC
        avg_d_ra = 0
        cnt = 0
        for i in range(len(ControlPackage.tk_queue), 0, -1) :
          avg_d_ra += ControlPackage.tk_queue[i-1][1]
          cnt += 1
          if cnt == trace_ref_cnt: break
        if cnt > 0: avg_d_ra /= cnt
        
        avg_d_dec = 0
        cnt = 0
        for i in range(len(ControlPackage.tk_queue), 0, -1) :
          avg_d_dec += ControlPackage.tk_queue[i-1][2]
          cnt += 1
          if cnt == trace_ref_cnt: break
        if cnt > 0: avg_d_dec /= cnt

        #get average delta x - y offset
        avg_d_x = 0
        cnt = 0
        for i in range(len(ControlPackage.tk_queue), 0, -1) :
          avg_d_x += ControlPackage.tk_queue[i-1][3] - ControlPackage.ref0_x
          cnt += 1
          if cnt == trace_ref_cnt: break
        if cnt > 0: avg_d_x /= cnt
        
        avg_d_y = 0
        cnt = 0
        for i in range(len(ControlPackage.tk_queue), 0, -1) :
          avg_d_y += ControlPackage.tk_queue[i-1][4] - ControlPackage.ref0_y
          cnt += 1
          if cnt == trace_ref_cnt: break
        if cnt > 0: avg_d_y /= cnt
        
        #determine move directions
        if ControlPackage.altazradec == "ALTAZ":   #ALT-AZ mode
          h_dir = ""
          if avg_d_x > thresh_limit : h_dir = "RIGHT"
          elif avg_d_x < -thresh_limit: h_dir = "LEFT"

          hsteps = math.ceil(abs(avg_d_x/50))
          
          v_dir = ""
          if avg_d_y > thresh_limit : v_dir = "DOWN"
          elif avg_d_y < -thresh_limit: v_dir = "UP"
          
          vsteps = abs(int(avg_d_y*10))

          if v_dir != "" :	# Vertical Motor control
            ControlPackage.v_cmdqueue.put((v_dir, ControlPackage.vspeed, ControlPackage.vadj, vsteps))
            time.sleep(2.0)

          if h_dir != "": 	# Horizontal Motor control
            ControlPackage.h_cmdqueue.put((h_dir, ControlPackage.hspeed, ControlPackage.hadj, hsteps))
            time.sleep(2.0)
          
        else :      # EQ mode
          v_dir = ""
          if avg_d_dec > thresh_limit : v_dir = ControlPackage.tk_pos_dir
          elif avg_d_dec < -thresh_limit: v_dir = ControlPackage.tk_neg_dir
          vsteps = abs(int(avg_d_dec/5))

          h_dir = ""
          if avg_d_ra > thresh_limit : 
            h_dir = "LEFT"
            new_h_speed = ControlPackage.hspeed * 4
          elif avg_d_ra < -thresh_limit : 
            h_dir = "LEFT"
            new_h_speed = ControlPackage.hspeed / 4
          hsteps = abs(int(avg_d_ra*3))


          if v_dir != "" :	# Dec Motor control
            ControlPackage.v_cmdqueue.put((v_dir, ControlPackage.vspeed, ControlPackage.vadj, vsteps))
            time.sleep(1.0)

          if h_dir != "": 	# RA Motor control
            ControlPackage.h_cmdqueue.put((h_dir, new_h_speed, ControlPackage.hadj, hsteps))
            time.sleep(6.0)
          
          # Default motion RA Left with default speed
          ControlPackage.h_cmdqueue.put(("LEFT", ControlPackage.hspeed, ControlPackage.hadj, 1000))


class AccStarTracking(ITracking):

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

    def __init__(self, lat, long, mode, ra_h, ra_m, ra_s, dec_dg, dec_m, dec_s, az, alt):
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

        self.v_steps = ControlPackage.vsteps
        self.v_adj = ControlPackage.vadj
        self.v_speed = ControlPackage.vspeed

        self.h_steps = ControlPackage.hsteps
        self.h_adj = ControlPackage.hadj
        self.h_speed = ControlPackage.hspeed

        if self.v_steps > 300: self.v_steps = 300
        if self.h_steps > 20: self.h_steps = 20

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
        min_v_offset = 0.2
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

              print( "\nTarget location: \t(" + str(target_az) + ", \t" + str(target_alt) + ")")
   
              pos_alt, pos_az = self.read()
              print( "Current position: \t(" + str(pos_az + ControlPackage.tgazadj) + ", \t" + str(pos_alt + ControlPackage.tgaltadj) + ")\n")
   
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
                    ControlPackage.v_cmdqueue.put((v_dir, self.v_speed, self.v_adj, v_steps))
                    ControlPackage.threadLock.release()
                 if h_offset >= 2 * min_h_offset or h_offset <= - min_h_offset: 
                    ControlPackage.threadLock.acquire()
                    ControlPackage.h_cmdqueue.put((h_dir, self.h_speed, self.h_adj, h_steps))
                    ControlPackage.threadLock.release()

              last_v_offset = v_offset
              last_h_offset = h_offset
              last_v_steps = v_steps
              last_h_steps = h_steps
              time.sleep(1.0)

        except KeyboardInterrupt:
          print( "Interruption accepted, exiting ...")
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

    print( 'Start star tracking ...')
    ControlPackage.isTracking.set()
    tr.Track()


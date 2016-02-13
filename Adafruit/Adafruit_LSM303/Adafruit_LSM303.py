#!/usr/bin/python

# Python library for Adafruit Flora Accelerometer/Compass Sensor (LSM303).
# This is pretty much a direct port of the current Arduino library and is
# similarly incomplete (e.g. no orientation value returned from read()
# method).  This does add optional high resolution mode to accelerometer
# though.

# Copyright 2013 Adafruit Industries

# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

import ConfigParser, os
import math
from Adafruit_I2C import Adafruit_I2C


class Adafruit_LSM303(Adafruit_I2C):

    # Minimal constants carried over from Arduino library
    LSM303_ADDRESS_ACCEL = (0x32 >> 1)  # 0011001x
    LSM303_ADDRESS_MAG   = (0x3C >> 1)  # 0011110x
                                             # Default    Type
    LSM303_REGISTER_ACCEL_CTRL_REG1_A = 0x20 # 00000111   rw
    LSM303_REGISTER_ACCEL_CTRL_REG4_A = 0x23 # 00000000   rw
    LSM303_REGISTER_ACCEL_OUT_X_L_A   = 0x28
    LSM303_REGISTER_MAG_CRB_REG_M     = 0x01
    LSM303_REGISTER_MAG_MR_REG_M      = 0x02
    LSM303_REGISTER_MAG_OUT_X_H_M     = 0x03

    # Gain settings for setMagGain()
    LSM303_MAGGAIN_1_3 = 0x20 # +/- 1.3
    LSM303_MAGGAIN_1_9 = 0x40 # +/- 1.9
    LSM303_MAGGAIN_2_5 = 0x60 # +/- 2.5
    LSM303_MAGGAIN_4_0 = 0x80 # +/- 4.0
    LSM303_MAGGAIN_4_7 = 0xA0 # +/- 4.7
    LSM303_MAGGAIN_5_6 = 0xC0 # +/- 5.6
    LSM303_MAGGAIN_8_1 = 0xE0 # +/- 8.1

    MX_MIN = 0.0
    MX_MAX = 0.0
    MY_MIN = 0.0
    MY_MAX = 0.0
    MZ_MIN = 0.0
    MZ_MAX = 0.0

    def __init__(self, busnum=-1, debug=False, hires=False):

        # Accelerometer and magnetometer are at different I2C
        # addresses, so invoke a separate I2C instance for each
        self.accel = Adafruit_I2C(self.LSM303_ADDRESS_ACCEL, busnum, debug)
        self.mag   = Adafruit_I2C(self.LSM303_ADDRESS_MAG  , busnum, debug)

        # Enable the accelerometer
        self.accel.write8(self.LSM303_REGISTER_ACCEL_CTRL_REG1_A, 0x27)
        # Select hi-res (12-bit) or low-res (10-bit) output mode.
        # Low-res mode uses less power and sustains a higher update rate,
        # output is padded to compatible 12-bit units.
        if hires:
            self.accel.write8(self.LSM303_REGISTER_ACCEL_CTRL_REG4_A,
              0b00001000)
        else:
            self.accel.write8(self.LSM303_REGISTER_ACCEL_CTRL_REG4_A, 0)
  
        # Enable the magnetometer
        self.mag.write8(self.LSM303_REGISTER_MAG_MR_REG_M, 0x00)

        fullpath = os.path.realpath(__file__)
        filepath = os.path.dirname(fullpath) + '/../../magcalibrate.conf' 
        config = ConfigParser.ConfigParser()
        config.readfp(open(filepath))
	self.MX_MIN = config.getfloat('mag', 'XMIN')
	self.MX_MAX = config.getfloat('mag', 'XMAX')
	self.MY_MIN = config.getfloat('mag', 'YMIN')
	self.MY_MAX = config.getfloat('mag', 'YMAX')
	self.MZ_MIN = config.getfloat('mag', 'ZMIN')
	self.MZ_MAX = config.getfloat('mag', 'ZMAX')
	#print "Read from config file:"
	#print "\tXMIN: {0}".format(self.MX_MIN)
	#print "\tXMAX: {0}".format(self.MX_MAX)
	#print "\tYMIN: {0}".format(self.MY_MIN)
	#print "\tYMAX: {0}".format(self.MY_MAX)
	#print "\tZMIN: {0}".format(self.MZ_MIN)
	#print "\tZMAX: {0}".format(self.MZ_MAX)


    # Interpret signed 12-bit acceleration component from list
    def accel12(self, list, idx):
        n = list[idx] | (list[idx+1] << 8) # Low, high bytes
        if n > 32767: n -= 65536           # 2's complement signed
        return n >> 4                      # 12-bit resolution


    # Interpret signed 16-bit magnetometer component from list
    def mag16(self, list, idx):
        n = (list[idx] << 8) | list[idx+1]   # High, low bytes
        return n if n < 32768 else n - 65536 # 2's complement signed


    def read(self):

        # Read the accelerometer
        list = self.accel.readList(
          self.LSM303_REGISTER_ACCEL_OUT_X_L_A | 0x80, 6)

	x = self.accel12(list, 0)
	y = self.accel12(list, 2)
	z = self.accel12(list, 4)

        #print 'raw acc readings: ({0} {1} {2})'.format(x, y, z)

        xAngle = math.atan2( x, (math.sqrt(y*y + z*z)))
   	yAngle = math.atan2( y, (math.sqrt(x*x + z*z)))
   	zAngle = math.atan2( math.sqrt(x*x + y*y), z)	

	alpha = xAngle
	gamma = yAngle

        # Read the magnetometer
        list = self.mag.readList(self.LSM303_REGISTER_MAG_OUT_X_H_M, 6)

	#x = self.mag16(list, 0)
	#y = self.mag16(list, 2)
	#z = self.mag16(list, 4)
	x = self.mag16(list, 0)
	z = self.mag16(list, 2)
	y = self.mag16(list, 4)

	#x1 = x
	#y1 = y
	#z1 = z
	x1 = self.normalize(x, self.MX_MIN, self.MX_MAX)
	y1 = self.normalize(y, self.MY_MIN, self.MY_MAX)
	z1 = self.normalize(z, self.MZ_MIN, self.MZ_MAX)

	#title compensate
	xh = x1*math.cos(alpha) + y1*math.sin(alpha)*math.sin(gamma) - z1*math.cos(gamma)*math.sin(alpha);
  	yh = y1*math.cos(gamma) + z1*math.sin(gamma);

	#heading = (math.atan2(y1,x1) * 180) / math.pi 	#sensor is pointed backward
	heading = (math.atan2(yh,xh) * 180) / math.pi  	#sensor is pointed backward

	if heading > 0 : heading = heading - 360
	heading += 360	
  
	#convert accelerometer x, y, z angle to degree
   	xAngle *= 180.00 / math.pi 
	yAngle *= 180.00 / math.pi  
	zAngle *= 180.00 / math.pi

        res = ( xAngle, yAngle, zAngle, heading )

        return res

    def normalize(self, m, vmin, vmax):
        r = (vmax - vmin)/2.0
        z = vmax - r
        return (m - z) / r

    def readmag(self):

        # Read the magnetometer
        list = self.mag.readList(self.LSM303_REGISTER_MAG_OUT_X_H_M, 6)

	#x = self.mag16(list, 0)
	#y = self.mag16(list, 2)
	#z = self.mag16(list, 4)
	x = self.mag16(list, 0)
	z = self.mag16(list, 2)
	y = self.mag16(list, 4)

	#x1 = x
	#y1 = y
	#z1 = z
	x1 = self.normalize(x, self.MX_MIN, self.MX_MAX)
	y1 = self.normalize(y, self.MY_MIN, self.MY_MAX)
	z1 = self.normalize(z, self.MZ_MIN, self.MZ_MAX)

	heading = (math.atan2(y1,x1) * 180) / math.pi  

	if heading > 0 : heading = heading - 360
	heading += 360	

        res = ( x, y, z, heading )

        return res


    def setMagGain(gain=LSM303_MAGGAIN_1_3):
        self.mag.write8( LSM303_REGISTER_MAG_CRB_REG_M, gain)


# Simple example prints accel/mag data once per second:
if __name__ == '__main__':

    from time import sleep

    lsm = Adafruit_LSM303()

    print '[(Accelerometer X, Y, Z), (Magnetometer X, Y, Z, orientation)]'

    x_max = 0.0
    x_min = 0.0
    y_max = 0.0
    y_min = 0.0
    z_max = 0.0
    z_min = 0.0

    try:
      while True:
        # print lsm.read()
        x, y, z, heading = lsm.readmag()

	if x < x_min: x_min = x
	if x > x_max: x_max = x

	if y < y_min: y_min = y
	if y > y_max: y_max = y

	if z < z_min: z_min = z
	if z > z_max: z_max = z

        print '({0}, {1}, {2}) - heading: {3}'.format(x,y,z,heading)
        sleep(1) # Output is fun to watch if this is commented out

    except KeyboardInterrupt:
        print "Interruption accepted, exiting ...\n"
        print "XMIN={0}".format(x_min)
        print "XMAX={0}".format(x_max)
        print "YMIN={0}".format(y_min)
        print "YMAX={0}".format(y_max)
        print "ZMIN={0}".format(z_min)
        print "ZMAX={0}".format(z_max)


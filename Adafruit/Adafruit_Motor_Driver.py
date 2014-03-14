#!/usr/bin/python

import time
import math
from Adafruit_I2C import Adafruit_I2C

# ============================================================================
# Adafruit DC Driver
# ============================================================================

class DCM :
  i2c = None

  # Registers/etc.
  __SUBADR1            = 0x02
  __SUBADR2            = 0x03
  __SUBADR3            = 0x04
  __MODE1              = 0x00
  __PRESCALE           = 0xFE
  __LED0_ON_L          = 0x06
  __LED0_ON_H          = 0x07
  __LED0_OFF_L         = 0x08
  __LED0_OFF_H         = 0x09
  __ALLLED_ON_L        = 0xFA
  __ALLLED_ON_H        = 0xFB
  __ALLLED_OFF_L       = 0xFC
  __ALLLED_OFF_H       = 0xFD
  # __PWMX                  = 8
  # __AIN2X                  = 9
  # __AIN1X                  = 10

  def __init__(self, address=0x60, debug=False):
    self.i2c = Adafruit_I2C(address,1)
    self.address = address
    self.debug = debug
    self.i2c.debug = debug
    if (self.debug):
      print "Reseting PCA9685"
    self.i2c.write8(self.__MODE1, 0x00)

  def setDCMport(self, port):
    "Select DC Shield port"
    if port == 'M2':
      self.__PWMX   = 13
      self.__AIN2X  = 12
      self.__AIN1X  = 11
      self.motor = 'M2'
    elif port == 'M3':
      self.__PWMX   = 2
      self.__AIN2X  = 3
      self.__AIN1X  = 4
      self.motor = 'M3'
    elif port == 'M4':
      self.__PWMX   = 7
      self.__AIN2X  = 6
      self.__AIN1X  = 5
      self.motor = 'M4'
    else:
      self.__PWMX   = 8
      self.__AIN2X  = 9
      self.__AIN1X  = 10
      self.motor = 'M1'
    if (self.debug):
      print "DC Shield port %s selected with next parameters:" % port
      print "PWM = %d " % self.__PWMX
      print "AIN1 = %d " % self.__AIN1X
      print "AIN2 = %d " % self.__AIN2X

  def setDCMFreq(self, freq):
    "Sets the PWM frequency"
    prescaleval = 25000000.0    # 25MHz
    prescaleval /= 4096.0       # 12-bit
    prescaleval /= float(freq)
    prescaleval -= 1.0
    if (self.debug):
      print "Setting PWM frequency to %d Hz" % freq
      print "Estimated pre-scale: %d" % prescaleval
    prescale = math.floor(prescaleval + 0.5)
    if (self.debug):
      print "Final pre-scale: %d" % prescale

    oldmode = self.i2c.readU8(self.__MODE1);
    newmode = (oldmode & 0x7F) | 0x10             # sleep
    self.i2c.write8(self.__MODE1, newmode)        # go to sleep
    self.i2c.write8(self.__PRESCALE, int(math.floor(prescale)))
    self.i2c.write8(self.__MODE1, oldmode)
    time.sleep(0.005)
    self.i2c.write8(self.__MODE1, oldmode | 0x80)

  def setDCM(self, channel, on, off):
    "Sets a single PWM channel"
    self.i2c.write8(self.__LED0_ON_L+4*channel, on & 0xFF)
    self.i2c.write8(self.__LED0_ON_H+4*channel, on >> 8)
    self.i2c.write8(self.__LED0_OFF_L+4*channel, off & 0xFF)
    self.i2c.write8(self.__LED0_OFF_H+4*channel, off >> 8)
    if (self.debug):
      self.readDCM(channel)  

  def readDCM(self, channel):
    print "LED%d_ON_L = %d" % (channel,self.i2c.readS8(self.__LED0_ON_L+4*channel))
    print "LED%d_ON_H = %d" % (channel,self.i2c.readS8(self.__LED0_ON_H+4*channel))
    print "LED%d_OFF_L = %d" % (channel,self.i2c.readS8(self.__LED0_OFF_L+4*channel))
    print "LED%d_OFF_H = %d" % (channel,self.i2c.readS8(self.__LED0_OFF_H+4*channel))
    print "---------"
   
  def setDCMSpeed(self, speed):
    "Sets a DC motor speed"
    if (self.debug):
      print "Setting %s speed to %d" % (self.motor,speed)
    if speed > 254:
        speed = 255
    speed = speed*16
    if (self.debug):
        print "Converted speed to %d" % speed
    self.setDCM(self.__PWMX, 0, speed)

  def run(self, direction):
    "Run DC with directions: FORWARD, BACKWARD, RELEASE"
    if (self.debug):
      print "Command send: ", direction
    if direction == 'FORWARD':
      self.setDCM(self.__AIN2X, 0, 0)
      self.setDCM(self.__AIN1X, 4096, 0)
    elif direction == 'BACKWARD':
      self.setDCM(self.__AIN1X, 0, 0)
      self.setDCM(self.__AIN2X, 4096, 0)
    elif direction == 'RELEASE':
      self.setDCM(self.__AIN2X, 0, 0)
      self.setDCM(self.__AIN1X, 0, 0)

# ============================================================================
# Adafruit Step Driver
# ============================================================================

class StepMotor :
  i2c = None
  revsteps = 200
  currentstep = 0
  steppingcounter = 0
  MICROSTEPS = 16  # 8 or 16


  # Registers/etc.
  __SUBADR1            = 0x02
  __SUBADR2            = 0x03
  __SUBADR3            = 0x04
  __MODE1              = 0x00
  __PRESCALE           = 0xFE
  __LED0_ON_L          = 0x06
  __LED0_ON_H          = 0x07
  __LED0_OFF_L         = 0x08
  __LED0_OFF_H         = 0x09
  __ALLLED_ON_L        = 0xFA
  __ALLLED_ON_H        = 0xFB
  __ALLLED_OFF_L       = 0xFC
  __ALLLED_OFF_H       = 0xFD

  def __init__(self, address=0x60, debug=False):
    self.i2c = Adafruit_I2C(address,1)
    self.address = address
    self.debug = debug
    self.i2c.debug = debug
    if (self.debug):
      print "Reseting PCA9685"
    self.i2c.write8(self.__MODE1, 0x00)
    if self.MICROSTEPS == 8 :
      self.microstepcurve = [0, 50, 98, 142, 180, 212, 236, 250, 255]
    else:
      self.microstepcurve = [0, 25, 50, 74, 98, 120, 141, 162, 180, 197, 212, 225, 236, 244, 250, 253, 255]

  def setPort(self, port):
    "Select Motor Shield port"
    if port == 'M1M2':
      self.__PWMAX  = 8
      self.__PWMBX  = 13
      self.__AIN1X  = 10
      self.__AIN2X  = 9
      self.__BIN1X  = 11
      self.__BIN2X  = 12
      #self.__BIN1X  = 12
      #self.__BIN2X  = 11
      self.motor = 'M1M2'
    else : # port == 'M3M4'
      self.__PWMAX  = 2
      self.__PWMBX  = 7
      self.__AIN1X  = 4
      self.__AIN2X  = 3
      self.__BIN1X  = 5
      self.__BIN2X  = 6
      self.motor = 'M3M4'

    if (self.debug):
      print "Motor Shield port %s selected with next parameters:" % port
      print "PWMA = %d " % self.__PWMAX
      print "PWMB = %d " % self.__PWMBX
      print "AIN1 = %d " % self.__AIN1X
      print "AIN2 = %d " % self.__AIN2X
      print "BIN1 = %d " % self.__BIN1X
      print "BIN2 = %d " % self.__BIN2X

  def setFreq(self, freq):
    "Sets the PWM frequency"
    prescaleval = 25000000.0    # 25MHz
    prescaleval /= 4096.0       # 12-bit
    prescaleval /= float(freq)
    prescaleval -= 1.0
    if (self.debug):
      print "Setting PWM frequency to %d Hz" % freq
      print "Estimated pre-scale: %d" % prescaleval
    prescale = math.floor(prescaleval + 0.5)
    if (self.debug):
      print "Final pre-scale: %d" % prescale

    oldmode = self.i2c.readU8(self.__MODE1);
    newmode = (oldmode & 0x7F) | 0x10             # sleep
    self.i2c.write8(self.__MODE1, newmode)        # go to sleep
    self.i2c.write8(self.__PRESCALE, int(math.floor(prescale)))
    self.i2c.write8(self.__MODE1, oldmode)
    time.sleep(0.005)
    self.i2c.write8(self.__MODE1, oldmode | 0x80)

  def _setPWM(self, channel, on, off):
    "Sets a single PWM channel"
    self.i2c.write8(self.__LED0_ON_L+4*channel, on & 0xFF)
    self.i2c.write8(self.__LED0_ON_H+4*channel, on >> 8)
    self.i2c.write8(self.__LED0_OFF_L+4*channel, off & 0xFF)
    self.i2c.write8(self.__LED0_OFF_H+4*channel, off >> 8)
    if (self.debug):
      self._readPWM(channel)  

  def _readPWM(self, channel):
    print "LED%d_ON_L = %d" % (channel,self.i2c.readS8(self.__LED0_ON_L+4*channel))
    print "LED%d_ON_H = %d" % (channel,self.i2c.readS8(self.__LED0_ON_H+4*channel))
    print "LED%d_OFF_L = %d" % (channel,self.i2c.readS8(self.__LED0_OFF_L+4*channel))
    print "LED%d_OFF_H = %d" % (channel,self.i2c.readS8(self.__LED0_OFF_H+4*channel))
    print "---------"
   
  def setPWM(self, pin, value) :
    if value > 4095 :
      self._setPWM(pin, 4096, 0)
    else:
      self._setPWM(pin, 0, value)

  def setPin(self, pin, value) :
    if value == 0:
      self._setPWM(pin, 0, 0)
    else:
      self._setPWM(pin, 4096, 0)

  def setSpeed(self, rpm):
    self.usperstep = 60000000 / (self.revsteps * rpm);
    self.steppingcounter = 0;

  def release(self):
    self.setPin(self.__AIN1X, 0)
    self.setPin(self.__AIN2X, 0)
    self.setPin(self.__BIN1X, 0)
    self.setPin(self.__BIN2X, 0)
    self.setPWM(self.__PWMAX, 0)
    self.setPWM(self.__PWMBX, 0)

  def step(self, steps, dir, style):
    uspers = self.usperstep
    ret = 0

    if style == 'INTERLEAVE':
      uspers /= 2
    elif style == 'MICROSTEP':
      uspers /= self.MICROSTEPS
      steps *= self.MICROSTEPS

    while steps > 0 :
      steps -= 1
      ret = self.onestep(dir, style)
      time.sleep(uspers/1000000) # in ms
      self.steppingcounter += (uspers % 1000)
      if self.steppingcounter >= 1000 :
        time.sleep(0.001)
        self.steppingcounter -= 1000
 
    if style == 'MICROSTEP' :
      while (ret != 0) and (ret != self.MICROSTEPS) :
        ret = self.onestep(dir, style)
        time.sleep(uspers/1000000) # in ms
        self.steppingcounter += (uspers % 1000)
        if self.steppingcounter >= 1000 :
          time.sleep(0.001)
          self.steppingcounter -= 1000

  def onestep(self, dir, style) :
    ocra = 255
    ocrb = 255
    
    # next determine what sort of stepping procedure we're up to
    if style == 'SINGLE' :
      if (self.currentstep/(self.MICROSTEPS/2)) % 2 : # we're at an odd step, weird
        if dir == 'FORWARD' :
          self.currentstep += self.MICROSTEPS/2 
        else :
          self.currentstep -= self.MICROSTEPS/2 

      else : # go to the next even step
        if dir == 'FORWARD' :
          self.currentstep += self.MICROSTEPS 
        else :
          self.currentstep -= self.MICROSTEPS 

    elif style == 'DOUBLE' :
      if not (self.currentstep/(self.MICROSTEPS/2) % 2) : # we're at an even step, weird
        if dir == 'FORWARD' :
          self.currentstep += self.MICROSTEPS/2
        else :
          self.currentstep -= self.MICROSTEPS/2

      else :           # go to the next odd step
        if dir == 'FORWARD': 
          self.currentstep += self.MICROSTEPS
        else :
          self.currentstep -= self.MICROSTEPS

    elif style == 'INTERLEAVE' :
      if dir == 'FORWARD' :
        self.currentstep += self.MICROSTEPS/2
      else :
        self.currentstep -= self.MICROSTEPS/2

    if style == 'MICROSTEP' :
      if dir == 'FORWARD' :
        self.currentstep += 1
      else :
        # BACKWARDS
        self.currentstep -= 1

      self.currentstep += self.MICROSTEPS*4
      self.currentstep %= self.MICROSTEPS*4

      ocra = ocrb = 0
      if (self.currentstep >= 0) and (self.currentstep < self.MICROSTEPS) :
        ocra = self.microstepcurve[self.MICROSTEPS - self.currentstep]
        ocrb = self.microstepcurve[self.currentstep]
      elif  (self.currentstep >= self.MICROSTEPS) and (self.currentstep < self.MICROSTEPS*2) :
        ocra = self.microstepcurve[self.currentstep - self.MICROSTEPS]
        ocrb = self.microstepcurve[self.MICROSTEPS*2 - self.currentstep]
      elif  (self.currentstep >= self.MICROSTEPS*2) and (self.currentstep < self.MICROSTEPS*3) :
        ocra = self.microstepcurve[self.MICROSTEPS*3 - self.currentstep]
        ocrb = self.microstepcurve[self.currentstep - self.MICROSTEPS*2]
      elif  (self.currentstep >= self.MICROSTEPS*3) and (self.currentstep < self.MICROSTEPS*4) :
        ocra = self.microstepcurve[self.currentstep - self.MICROSTEPS*3]
        ocrb = self.microstepcurve[self.MICROSTEPS*4 - self.currentstep]

    self.currentstep += self.MICROSTEPS*4
    self.currentstep %= self.MICROSTEPS*4

    self.setPWM(self.__PWMAX, ocra*16)
    self.setPWM(self.__PWMBX, ocrb*16)


    # release all
    self.latch_state = 0 # all motor pins to 0

    if style == 'MICROSTEP' :
      if (self.currentstep >= 0) and (self.currentstep < self.MICROSTEPS) :
        self.latch_state |= 0x03
      if (self.currentstep >= self.MICROSTEPS) and (self.currentstep < self.MICROSTEPS*2) :
        self.latch_state |= 0x06
      if (self.currentstep >= self.MICROSTEPS*2) and (self.currentstep < self.MICROSTEPS*3) :
        self.latch_state |= 0x0C
      if (self.currentstep >= self.MICROSTEPS*3) and (self.currentstep < self.MICROSTEPS*4) :
        self.latch_state |= 0x09

    else :
      if self.currentstep/(self.MICROSTEPS/2) == 0 :
        self.latch_state |= 0x1 # energize coil 1 only
      elif self.currentstep/(self.MICROSTEPS/2) == 1 :
        self.latch_state |= 0x3 # energize coil 1+2
      elif self.currentstep/(self.MICROSTEPS/2) == 2 :
        self.latch_state |= 0x2 # energize coil 2 only
      elif self.currentstep/(self.MICROSTEPS/2) == 3:
        self.latch_state |= 0x6 # energize coil 2+3
      elif self.currentstep/(self.MICROSTEPS/2) == 4:
        self.latch_state |= 0x4 # energize coil 3 only
      elif self.currentstep/(self.MICROSTEPS/2) == 5:
        self.latch_state |= 0xC # energize coil 3+4
      elif self.currentstep/(self.MICROSTEPS/2) == 6:
        self.latch_state |= 0x8 # energize coil 4 only
      elif self.currentstep/(self.MICROSTEPS/2)  == 7:
        self.latch_state |= 0x9 # energize coil 1+4
    
    if self.latch_state & 0x1 :
      self.setPin(self.__AIN2X, 1)
    else :
      self.setPin(self.__AIN2X, 0)
    
    if self.latch_state & 0x2 :
      self.setPin(self.__BIN1X, 1)
    else :
      self.setPin(self.__BIN1X, 0)
    
    if self.latch_state & 0x4 :
      self.setPin(self.__AIN1X, 1)
    else :
      self.setPin(self.__AIN1X, 0)
    
    if self.latch_state & 0x8 :
      self.setPin(self.__BIN2X, 1)
    else :
      self.setPin(self.__BIN2X, 0)
  
    return self.currentstep



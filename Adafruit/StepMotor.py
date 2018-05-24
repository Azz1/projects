import RPi.GPIO as GPIO
import time
import math
import threading
import Queue
import serial
from abc import ABCMeta, abstractmethod

# Abstract base class for stepper motor
class StepMotor :

  __metaclass__ = ABCMeta
         
  # GPIO Pins for vertical motor, horizontal motor and focus motor
  # For EasyDriver driven motors, the 5 pin seq represents:
  #	Step GPIO pin
  #	Direction GPIO pin
  #	Enable GPIO pin number.
  #	Reserved.

  Motor_V_Pin = [12, 16, 20, 21]
  Motor_H_Pin = [6, 13, 19, 26]
  Motor_F_Pin = [4, 17, 27, 22]

  @abstractmethod
  def step(self, steps, dir, style): pass

  @abstractmethod
  def setSensor(self, fpin, bpin) : pass

  @abstractmethod
  def setPort(self, port): pass

  @abstractmethod
  def setSpeed(self, rpm): pass
 
  @abstractmethod
  def release(self): pass

class ControlPackage :

  try:
    SerialData = serial.Serial(
               #port='/dev/ttyACM0',
               port='/dev/ttyUSB0',
               baudrate = 9600,
               parity=serial.PARITY_NONE,
               stopbits=serial.STOPBITS_ONE,
               bytesize=serial.EIGHTBITS,
               timeout=1
           )
  except serial.serialutil.SerialException:
    pass

  # Touch sensor GPIO pins
  VL_pin = 24
  VH_pin = 23
  HL_pin = 25
  HR_pin = 8
  #HL_pin = 17
  #HR_pin = 4

  GPIO.setwarnings(False)
  GPIO.setmode(GPIO.BCM)

  GPIO.setup(VL_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
  GPIO.setup(VH_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
  GPIO.setup(HL_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
  GPIO.setup(HR_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

  # initialize the camera 
  cameraonly = 'false'
  ip = ''
  rawmode = 'false'
  cmode = 'day'

  width = 700
  height = 525

#picamera v1.3
  roi_l = 0
#picamera v2
  #roi_l = 0.2
  roi_w = (1 - roi_l)**2

  brightness = 50	#0-100 50 default
  sharpness = 20	#-100-100 0 default
  contrast = 20		#-100-100 0 default
  saturation = 20	#-100-100 0 default
  ss = 4000		#microsecond
  iso = 400		#100-800 400 default
  videolen = 20		#video length
  timelapse = 1		#number of timelapse snapshot photos
  imageseq = 0		#sequence id of refresh image
  simageseq = 0		#sequence id of snapshot image
  videoseq = 0		#sequence id of video snapshots
  max_keep_snapshots = 10	#max number of snapsnots keep in cache
  max_keep_videoshots = 5	#max number of videosnots keep in cache

  # initialize step motors
  exitFlag = threading.Event()
  isTracking = threading.Event()
  threadLock = threading.Lock()
  #queue of objects (dir=UP/DOWN, speed, steps) UP-FWD, DOWN-BKWD
  v_cmdqueue = Queue.Queue()      
  #queue of objects (dir=LEFT/RIGHT, speed, steps) LEFT-FWD, RIGHT-BKWD
  h_cmdqueue = Queue.Queue()      
  #queue of objects (dir=IN/OUT, speed, steps) IN-FWD, OUT-BKWD
  f_cmdqueue = Queue.Queue()      

  # initialize vertical step motor
  vspeed = 30
  vsteps = 200

  # initialize horizontal step motor
  hspeed = 5
  hsteps = 8

  # initialize focus step motor
  fspeed = 5
  fsteps = 48

  # Tracking parameters

  # current direction
  curaz = 0.0
  curalt = 0.0

  # target direction
  tgaz = 0.0
  tgalt = 0.0
  tgrah = 0.0
  tgram = 0.0
  tgras = 0.0
  tgdecdg = 0.0
  tgdecm = 0.0
  tgdecs = 0.0

  #current location
  myloclat = 42.27
  myloclong = -83.04

  #error adjustment
  tgazadj = 0.0
  tgaltadj = 0.0

  altazradec = 'ALTAZ'

  @staticmethod
  def release():
    ControlPackage.motorV.release()
    ControlPackage.motorH.release()
    ControlPackage.camera.release()
    try:
      ControlPackage.SerialData.close()
    except serial.serialutil.SerialException:
      pass

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
    elif ControlPackage.iso > 1600: ControlPackage.iso = 1600
    if ControlPackage.ss < 100 : ControlPackage.ss = 100

    if ControlPackage.vspeed <= 0 : ControlPackage.vspeed = 1
    if ControlPackage.vsteps <= 0 : ControlPackage.vsteps = 1
    if ControlPackage.hspeed <= 0 : ControlPackage.hspeed = 1
    if ControlPackage.hsteps <= 0 : ControlPackage.vsteps = 1
    if ControlPackage.fspeed <= 0 : ControlPackage.fspeed = 1
    if ControlPackage.fsteps <= 0 : ControlPackage.fsteps = 1

  @staticmethod
  def newadj():
    ControlPackage.tgazadj = ControlPackage.tgaz - ControlPackage.curaz + ControlPackage.tgazadj
    ControlPackage.tgaltadj = ControlPackage.tgalt - ControlPackage.curalt + ControlPackage.tgaltadj
    return (ControlPackage.tgazadj, ControlPackage.tgaltadj)

class MotorControlThread (threading.Thread):
  def __init__(self, threadName):
    threading.Thread.__init__(self)
    self.threadName = threadName

    # initialize vertical step motor
    if self.threadName == "H-Motor":
      self.q = ControlPackage.h_cmdqueue

      #from Adafruit_Motor_Driver import AFStepMotor
      #self.motor = AFStepMotor(0x60, debug=False)

      #from EDStepMotor import EDStepMotor
      #self.motor = EDStepMotor(0x60, debug=False)

      from ArduinoSerialStepMotor import ArduinoSerialStepMotor
      self.motor = ArduinoSerialStepMotor(0x60, debug=False)

      self.motor.setPort("M1M2")
      self.motor.setSensor(ControlPackage.HL_pin, ControlPackage.HR_pin)

    elif self.threadName == "V-Motor":
      self.q = ControlPackage.v_cmdqueue

      #from GPIOStepMotor import GPIOStepMotor
      #self.motor = GPIOStepMotor(0x60, debug=False)

      from ArduinoSerialStepMotor import ArduinoSerialStepMotor
      self.motor = ArduinoSerialStepMotor(0x60, debug=False)


      self.motor.setFreq(1600)
      self.motor.setPort("M3M4")
      self.motor.setSensor(ControlPackage.VH_pin, ControlPackage.VL_pin)

    else:
      self.q = ControlPackage.f_cmdqueue

      from EDStepMotor import EDStepMotor
      self.motor = EDStepMotor(0x60, debug=False)
      self.motor.setPort("M5M6")
      self.motor.setSensor(0, 0)	# no sensor


  def release(self) :
    self.motor.release()

  def run(self):
    print "Starting " + self.threadName
    while ControlPackage.exitFlag.is_set():
      dir = ""
      speed = 0
      steps = 0
	  
      ControlPackage.threadLock.acquire()
      if not self.q.empty():
    	(dir, speed, steps) = self.q.get()
      ControlPackage.threadLock.release()
	   
      if dir != "" : 
        print self.threadName + ' ' + dir + ' Speed: ' + str(speed) + ' Steps: ' + str(steps)

        if self.threadName == "H-Motor":
	  # LEFT-FWD, RIGHT-BKWD
	  self.motor.setSpeed(speed)
	  if dir == "LEFT":
            self.motor.step(steps, "BACKWARD", "MICROSTEP")
          else:
            self.motor.step(steps, "FORWARD", "MICROSTEP")
          self.motor.release()

          if dir.upper() == 'LEFT' and GPIO.input(ControlPackage.HL_pin):
            print 'Horizontal leftmost limit reached!'

          if dir.upper() == 'RIGHT' and GPIO.input(ControlPackage.HR_pin):
            print 'Horizontal rightmost limit reached!'	
	      	
        elif self.threadName == "V-Motor":
	  # UP-FWD, DOWN-BKWD
	  self.motor.setSpeed(speed)
	  if dir == "UP":
            self.motor.step(steps, "FORWARD", "SINGLE")
          else:
            self.motor.step(steps, "BACKWARD", "SINGLE")
          self.motor.release()

          if dir.upper() == 'UP' and GPIO.input(ControlPackage.VH_pin):
            print 'Vertical highest limit reached!'

          if dir.upper() == 'DOWN' and GPIO.input(ControlPackage.VL_pin):
            print 'Vertical lowest limit reached!'	
	else:
	  # IN-FWD, OUT-BKWD
	  self.motor.setSpeed(speed)
	  if dir == "IN":
            self.motor.step(steps, "FORWARD", "MICROSTEP")
          else:
            self.motor.step(steps, "BACKWARD", "MICROSTEP")
          self.motor.release()

      time.sleep(0.1)

    print "Exiting " + self.threadName

ControlPackage.motorH = MotorControlThread("H-Motor")
ControlPackage.motorV = MotorControlThread("V-Motor")
ControlPackage.motorF = MotorControlThread("F-Motor")
ControlPackage.motorH.daemon = True
ControlPackage.motorV.daemon = True
ControlPackage.motorF.daemon = True
ControlPackage.exitFlag.set()
ControlPackage.motorH.start()
ControlPackage.motorV.start()
ControlPackage.motorF.start()


import RPi.GPIO as GPIO
import time
import math
import threading
import Queue
 
class StepMotor :
  # Global definations

  #GPIO Pins for vertical motor and horizontal motor
  Motor_V_Pin = [12, 16, 20, 21]
  Motor_H_Pin = [6, 13, 19, 26]

  # Operations

  StepCount1 = 4
  Seq1 = []
  Seq1 = range(0, StepCount1)
  #Seq1[0] = [1,0,1,0]	#DOUBLE MODE
  #Seq1[1] = [0,1,1,0]
  #Seq1[2] = [0,1,0,1]
  #Seq1[3] = [1,0,0,1]
  Seq1[0] = [1,0,0,0]	#SINGLE MODE
  Seq1[1] = [0,0,1,0]
  Seq1[2] = [0,1,0,0]
  Seq1[3] = [0,0,0,1]
  
  StepCount2 = 8
  Seq2 = []
  Seq2 = range(0, StepCount2)
  Seq2[0] = [1,0,0,0]	#HALF MODE
  Seq2[1] = [1,0,1,0]
  Seq2[2] = [0,0,1,0]
  Seq2[3] = [0,1,1,0]
  Seq2[4] = [0,1,0,0]
  Seq2[5] = [0,1,0,1]
  Seq2[6] = [0,0,0,1]
  Seq2[7] = [1,0,0,1]
 
  def __init__(self, address=0x60, debug=False):
    self.StepCount = StepMotor.StepCount2
    self.Seq = StepMotor.Seq2
 
  def setFreq(self, freq):	#not used
    pass

  def setPort(self, port):
    "Select Motor Shield port"
    if port == 'M3M4' or port == "V": 
      self.Motor_Pin = StepMotor.Motor_V_Pin
    else:
      self.Motor_Pin = StepMotor.Motor_H_Pin

    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
 
    GPIO.setup(self.Motor_Pin[0], GPIO.OUT)
    GPIO.setup(self.Motor_Pin[1], GPIO.OUT)
    GPIO.setup(self.Motor_Pin[2], GPIO.OUT)
    GPIO.setup(self.Motor_Pin[3], GPIO.OUT)
    self.current_step = 0
 

  def setSensor(self, fpin, bpin) :
    self.FWD_pin = fpin
    self.BKWD_pin = bpin

    GPIO.setmode(GPIO.BCM)
    GPIO.setup(self.FWD_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.setup(self.BKWD_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)


  def release(self):
    self.current_step = 0
    GPIO.output(self.Motor_Pin[0], 0)
    GPIO.output(self.Motor_Pin[1], 0)
    GPIO.output(self.Motor_Pin[2], 0)
    GPIO.output(self.Motor_Pin[3], 0)

  def setSpeed(self, rpm):
    self.delay = 60.0 / (50 * rpm) / self.StepCount;

  def step(self, steps, dir, style):
    if dir == 'FORWARD':
      self.forward(self.delay, steps)
    else:
      self.backwards(self.delay, steps)

  def checklimit(self, dir):
    #check sensor if reaching the limit
    if dir == 'FORWARD' and self.FWD_pin > 0:
      #print 'FORWARD pin %s check ...' % str(self.FWD_pin)
      if GPIO.input(self.FWD_pin) :
        time.sleep(0.03)
        if GPIO.input(self.FWD_pin) :      #check again after 0.1s in case of false positive
          print 'FORWARD pin %s raised!' % str(self.FWD_pin)
          return True

    elif dir == 'BACKWARD' and self.BKWD_pin > 0:
      #print 'BACKWARD pin %s check ...' % str(self.BKWD_pin)
      if GPIO.input(self.BKWD_pin) :
        time.sleep(0.03)
        if GPIO.input(self.BKWD_pin) :     #check again after 0.1s in case of false positive
          print 'BACKWARD pin %s raised!' % str(self.BKWD_pin)
          return True

    return False


  def backwards(self, delay, steps):  		#H-Right, V-Down
    self.current_step = 0

    for i in range(0, steps):
      if self.checklimit('BACKWARD'):
        break
      self.setStep(self.Seq[self.current_step][0], self.Seq[self.current_step][1], self.Seq[self.current_step][2], self.Seq[self.current_step][3])
      time.sleep(self.delay)
      self.current_step += 1
      if self.current_step >= self.StepCount :
	 self.current_step = 0

    self.release()
 
  def forward(self, delay, steps):  		#H-Left, V-Up
    #self.current_step -= 1
    #if self.current_step < 0 :
    #  self.current_step = self.StepCount-1
    self.current_step = self.StepCount-1

    for i in range(0, steps):
      if self.checklimit('FORWARD'):
        break
      self.setStep(self.Seq[self.current_step][0], self.Seq[self.current_step][1], self.Seq[self.current_step][2], self.Seq[self.current_step][3])
      time.sleep(self.delay)
      self.current_step -= 1
      if self.current_step < 0 :
	 self.current_step = self.StepCount-1

    self.release()

  def setStep(self, w1, w2, w3, w4):
    GPIO.output(self.Motor_Pin[0], w1)
    GPIO.output(self.Motor_Pin[1], w2)
    GPIO.output(self.Motor_Pin[2], w3)
    GPIO.output(self.Motor_Pin[3], w4)
 
class ControlPackage :

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

  # initialize step motors
  exitFlag = threading.Event()
  isTracking = threading.Event()
  threadLock = threading.Lock()
  #queue of objects (dir=UP/DOWN, speed, steps) UP-FWD, DOWN-BKWD
  v_cmdqueue = Queue.Queue()      
  #queue of objects (dir=LEFT/RIGHT, speed, steps) LEFT-FWD, RIGHT-BKWD
  h_cmdqueue = Queue.Queue()      

  # initialize vertical step motor
  #motorV = StepMotor(0x60, debug=False)
  #motorV.setFreq(1600)
  #motorV.setPort("M3M4")
  #motorV.setSensor(VH_pin, VL_pin)
  vspeed = 30
  vsteps = 100

  # initialize horizontal step motor
  #motorH = StepMotor(0x60, debug=False)
  #motorH.setFreq(1600)
  #motorH.setPort("M1M2")
  #motorH.setSensor(HL_pin, HR_pin)
  hspeed = 5
  hsteps = 8

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

class MotorControlThread (threading.Thread):
  def __init__(self, threadName):
    threading.Thread.__init__(self)
    self.threadName = threadName

    # initialize vertical step motor
    self.motor = StepMotor(0x60, debug=False)
    self.motor.setFreq(1600)
    if self.threadName == "H-Motor":
      self.q = ControlPackage.h_cmdqueue
      self.motor.setPort("M1M2")
      self.motor.setSensor(ControlPackage.HL_pin, ControlPackage.HR_pin)
    else:
      self.q = ControlPackage.v_cmdqueue
      self.motor.setPort("M3M4")
      self.motor.setSensor(ControlPackage.VH_pin, ControlPackage.VL_pin)

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
	# adjust to the next closest n step counts
        if steps < self.motor.StepCount : steps = self.motor.StepCount
        else : 
          while steps % self.motor.StepCount <> 0 :
            steps += 1
        print self.threadName + ' ' + dir + ' Speed: ' + str(speed) + ' Steps: ' + str(steps)

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

ControlPackage.motorH = MotorControlThread("H-Motor")
ControlPackage.motorV = MotorControlThread("V-Motor")
ControlPackage.motorH.daemon = True
ControlPackage.motorV.daemon = True
ControlPackage.exitFlag.set()
ControlPackage.motorH.start()
ControlPackage.motorV.start()

# Main body

if __name__ == '__main__':

  try:
    motor = StepMotor(0x60, debug=False)
    motor.setFreq(1600)
    motor.setPort("M3M4")
    motor.setSensor(23, 24)

    while True:
      speed = raw_input("Speed RPM?")
      if speed == "q":
        motor.release()
        break
      motor.setSpeed(int(speed))
      steps = raw_input("How many steps forward? ")
      motor.step(int(steps), 'FORWARD', '')
      steps = raw_input("How many steps backwards? ")
      motor.step(int(steps), 'BACKWARD', '')

  except KeyboardInterrupt:
    motor.release()
    GPIO.cleanup

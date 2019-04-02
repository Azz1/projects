import RPi.GPIO as GPIO
import time
import math
import threading
import Queue
from StepMotor import StepMotor

# Stepper motor control via raw GPIO
class GPIOStepMotor(StepMotor) :
  # Global definations

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
    self.StepCount = GPIOStepMotor.StepCount2
    self.Seq = GPIOStepMotor.Seq2
 
  def setFreq(self, freq):	#not used
    pass

  def setPort(self, port):
    "Select Motor Shield port"
    if port == 'M3M4' or port == "V": 
      self.Motor_Pin = StepMotor.Motor_V_Pin
    elif port == 'M1M2' or port == "H": 
      self.Motor_Pin = StepMotor.Motor_H_Pin
    else:
      self.Motor_Pin = StepMotor.Motor_F_Pin

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

    if fpin > 0 and bin > 0 :
      GPIO.setmode(GPIO.BCM)
      GPIO.setup(self.FWD_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
      GPIO.setup(self.BKWD_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)


  def release(self):
    self.current_step = 0
    GPIO.output(self.Motor_Pin[0], 0)
    GPIO.output(self.Motor_Pin[1], 0)
    GPIO.output(self.Motor_Pin[2], 0)
    GPIO.output(self.Motor_Pin[3], 0)

  def setSpeed(self, rpm, adj=0):
    self.delay = 60.0 / (50 * rpm) / self.StepCount;

  def step(self, steps, dir, style):
    # adjust to the next closest n step counts
    if steps < self.StepCount : steps = self.StepCount
    else :
      while steps % self.StepCount <> 0 :
        steps += 1

    if dir == 'FORWARD':
      self.forward(self.delay, steps)
    else:
      self.backwards(self.delay, steps)

  def checklimit(self, dir):
    #check sensor if reaching the limit

    #if dir == 'FORWARD' and self.FWD_pin > 0:
    #  #print 'FORWARD pin %s check ...' % str(self.FWD_pin)
    #  if GPIO.input(self.FWD_pin) :
    #    time.sleep(0.03)
    #    if GPIO.input(self.FWD_pin) :      #check again after 0.1s in case of false positive
    #      print 'FORWARD pin %s raised!' % str(self.FWD_pin)
    #      return True
    #elif dir == 'BACKWARD' and self.BKWD_pin > 0:
    #  #print 'BACKWARD pin %s check ...' % str(self.BKWD_pin)
    #  if GPIO.input(self.BKWD_pin) :
    #    time.sleep(0.03)
    #    if GPIO.input(self.BKWD_pin) :     #check again after 0.1s in case of false positive
    #      print 'BACKWARD pin %s raised!' % str(self.BKWD_pin)
    #      return True

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
 
# Main body

if __name__ == '__main__':

  try:
    motor = GPIOStepMotor(0x60, debug=False)
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

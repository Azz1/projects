import RPi.GPIO as GPIO
import time
import math
 
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

    GPIO.setmode(GPIO.BCM)
 
    GPIO.setup(self.Motor_Pin[0], GPIO.OUT)
    GPIO.setup(self.Motor_Pin[1], GPIO.OUT)
    GPIO.setup(self.Motor_Pin[2], GPIO.OUT)
    GPIO.setup(self.Motor_Pin[3], GPIO.OUT)
 

  def setSensor(self, fpin, bpin) :
    self.FWD_pin = fpin
    self.BKWD_pin = bpin

    GPIO.setmode(GPIO.BCM)
    GPIO.setup(self.FWD_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.setup(self.BKWD_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)


  def release(self):
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
    for i in range(0, steps):
      if self.checklimit('BACKWARD'):
        break
      for j in range(0, self.StepCount):
        self.setStep(self.Seq[j][0], self.Seq[j][1], self.Seq[j][2], self.Seq[j][3])
        time.sleep(self.delay)
    self.release()
 
  def forward(self, delay, steps):  		#H-Left, V-Up
    for i in range(0, steps):
      if self.checklimit('FORWARD'):
        break
      for j in range(0, self.StepCount):
        self.setStep(self.Seq[self.StepCount-1-j][0], self.Seq[self.StepCount-1-j][1], self.Seq[self.StepCount-1-j][2], self.Seq[self.StepCount-1-j][3])
        time.sleep(self.delay)
    self.release()

  def setStep(self, w1, w2, w3, w4):
    GPIO.output(self.Motor_Pin[0], w1)
    GPIO.output(self.Motor_Pin[1], w2)
    GPIO.output(self.Motor_Pin[2], w3)
    GPIO.output(self.Motor_Pin[3], w4)
 
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

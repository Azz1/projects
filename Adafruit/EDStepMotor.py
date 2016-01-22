import RPi.GPIO as GPIO
import time
import math
import threading
from StepMotor import StepMotor

# EasyDriver controlled stepper motor
class EDStepMotor(StepMotor) :
  # Global definations

  # Operations

  def __init__(self, address=0x60, debug=False):
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
    pass

  def step(self, steps, dir, style):
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
    self.release()
 
  def forward(self, delay, steps):  		#H-Left, V-Up
    self.current_step = self.StepCount-1
    self.release()

# Main body

if __name__ == '__main__':

  try:
    motor = EDStepMotor(0x60, debug=False)
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

import RPi.GPIO as GPIO
import time
import math
import os
import sys
import threading
from StepMotor import StepMotor

trackinglib_path = os.path.abspath('../EasyDriver')
sys.path.append(trackinglib_path)

import easydriver as ed

# EasyDriver controlled stepper motor
class EDStepMotor(StepMotor) :
  # Global definations

  # Operations

  def __init__(self, address=0x60, debug=False):
    pass
 
  def setPort(self, port):
    # Select Motor Shield port

    if port == 'M3M4' or port == "V": 
      self.Motor_Pin = StepMotor.Motor_V_Pin
    elif port == 'M1M2' or port == "H": 
      self.Motor_Pin = StepMotor.Motor_H_Pin
    else:
      self.Motor_Pin = StepMotor.Motor_F_Pin

    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
 
    GPIO.setup(self.Motor_Pin[0], GPIO.OUT)	# Step GPIO pin
    GPIO.setup(self.Motor_Pin[1], GPIO.OUT)	# Direction GPIO pin
    GPIO.setup(self.Motor_Pin[2], GPIO.OUT) 	# Microstep 1 GPIO pin number.
    GPIO.setup(self.Motor_Pin[3], GPIO.OUT) 	# Microstep 2 GPIO pin number.
    GPIO.setup(self.Motor_Pin[4], GPIO.OUT) 	# Microstep 3 GPIO pin number.
    self.current_step = 0
 
    """
    Arguments to pass or set up after creating the instance.
    Step GPIO pin number.
    Delay between step pulses in seconds.
    Direction GPIO pin number.
    Microstep 1 GPIO pin number.
    Microstep 2 GPIO pin number.
    Microstep 3 GPIO pin number.
    Sleep GPIO pin number.
    Enable GPIO pin number.
    Reset GPIO pin number.
    Name as a string.
    """
    self.stepper = ed.easydriver(self.Motor_Pin[0], 0.004, self.Motor_Pin[1], self.Motor_Pin[2], self.Motor_Pin[3], self.Motor_Pin[4])

  def setSensor(self, fpin, bpin) :
    self.FWD_pin = fpin
    self.BKWD_pin = bpin

    if fpin > 0 and bpin > 0 :
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
    self.delay = 60.0 / (50 * rpm) / 8;

  def step(self, steps, dir, style):
    if dir == 'FORWARD':
      self.forward(self.delay, steps, style)
    else:
      self.backwards(self.delay, steps, style)

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

  def backwards(self, delay, steps, style):  		#H-Right, V-Down, F-Out
    self.stepper.set_direction(False)
    self.stepper.set_delay(delay)
    if style == "MICROSTEP" :
      self.stepper.set_sixteenth_step()
    else :
      self.stepper.set_full_step()

    for i in range(0,steps):
      if not self.checklimit("BACKWARD") :
        self.stepper.step()
 
  def forward(self, delay, steps, style):  		#H-Left, V-Up, F-In
    self.stepper.set_direction(True)
    self.stepper.set_delay(delay)
    if style == "MICROSTEP" :
      self.stepper.set_sixteenth_step()
    else :
      self.stepper.set_full_step()

    for i in range(0,steps):
      if not self.checklimit("FORWARD") :
        self.stepper.step()


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

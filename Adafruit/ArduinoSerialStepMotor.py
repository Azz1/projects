import RPi.GPIO as GPIO
import time
import math
import os
import sys
import serial
import threading
from StepMotor import StepMotor
from StepMotor import ControlPackage

# Arduino Serial Command controlled stepper motor
class ArduinoSerialStepMotor(StepMotor) :
  # Global definations

  # Operations

  def __init__(self, address=0x60, debug=False):
    pass
 
  def setFreq(self, freq):      #not used
    pass

  def setPort(self, port):
    # Select Motor Shield port
    self.serial = ControlPackage.SerialData

    if port == 'M3M4' or port == "V": 
      self.Motor_No = 2 
    elif port == 'M1M2' or port == "H": 
      self.Motor_No = 1 

    self.current_step = 0
 
  def setSensor(self, fpin, bpin) :
    self.FWD_pin = fpin
    self.BKWD_pin = bpin

    if fpin > 0 and bpin > 0 :
      GPIO.setmode(GPIO.BCM)
      GPIO.setup(self.FWD_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
      GPIO.setup(self.BKWD_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)


  def release(self):
    self.current_step = 0

  def setSpeed(self, rpm):
    self.serial.write('<stepspeed ' + str(self.Motor_No) + ' ' + str(rpm) + '>')

  def step(self, steps, dir, style):
    self.serial.write('<touch 0>')	# enable onboard touch sensors
    if dir == 'FORWARD':
      self.serial.write('<stepper ' + str(self.Motor_No) + ' ' + str(steps) + ' F ' + style[0:1] + '>')
    else:
      self.serial.write('<stepper ' + str(self.Motor_No) + ' ' + str(steps) + ' B ' + style[0:1] + '>')
    time.sleep(1)
    self.serial.write('<steprel ' + str(self.Motor_No) + '>')

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

# Main body

if __name__ == '__main__':

  try:
    motor = ArduinoSerialStepMotor(0x60, debug=False)
    motor.setPort("M1M2")
    motor.setSensor(8, 25)

    while True:
      speed = raw_input("Speed RPM?")
      if speed == "q":
        motor.release()
        break
      motor.setSpeed(int(speed))
      steps = raw_input("How many steps forward? ")
      motor.step(int(steps), 'FORWARD', 'S')
      steps = raw_input("How many steps backwards? ")
      motor.step(int(steps), 'BACKWARD', 'M')

  except KeyboardInterrupt:
    motor.release()
    GPIO.cleanup

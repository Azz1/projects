#!/usr/bin/python

from Adafruit_Motor_Driver import StepMotor
import time

# ===========================================================================
# Example Code
# ===========================================================================


# Initialise the Step motor object using the default address and set frequency
stepm = StepMotor(0x60, debug=False)
stepm.setFreq(1600)

# Set Step Motor Shield port for each device
motor = stepm
motor.setPort('M1M2')
#motor.setPort('M3M4')

# Set Step Motor speed
motor.setSpeed(30)

try :
  print 'Single coil steps'
  motor.step(100, 'FORWARD', 'SINGLE')
  motor.step(100, 'BACKWARD', 'SINGLE')

  print 'Double coil steps'
  motor.step(100, 'FORWARD', 'DOUBLE')
  motor.step(100, 'BACKWARD', 'DOUBLE')

  print 'Interleave coil steps'
  motor.step(100, 'FORWARD', 'INTERLEAVE')
  motor.step(100, 'BACKWARD', 'INTERLEAVE')

  print 'Microstep steps'
  motor.step(100, 'FORWARD', 'MICROSTEP')
  motor.step(100, 'BACKWARD', 'MICROSTEP')

  time.sleep(1)
  motor.release()

except KeyboardInterrupt:
  motor.release()

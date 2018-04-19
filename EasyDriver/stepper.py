#!/usr/bin/python
# -*- coding: utf-8 -*-

# Simple example of the easydriver Python library.
# Dave Finch 2013

import sys
import easydriver as ed


# Direction of rotation is dependent on how the motor is connected.
# If the motor runs the wrong way swap the values of cw and ccw.
cw = True
ccw = False

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

# Create an instance of the easydriver class.
# Not using sleep, enable or reset in this example.
stepper = ed.easydriver(4, 0.004, 17, 27, 22)

# Set motor direction to clockwise.
stepper.set_direction(cw)

# Set the motor to run in 1 of a step per pulse.

stepper.set_full_step()

# Do some steps.
for i in range(0,200):
    stepper.step()

x = raw_input("Press enter for next test")

stepper.set_direction(ccw)
# Set the motor to run in 1/2 of a step per pulse.

stepper.set_half_step()

# Do some steps.
for i in range(0,400):
    stepper.step()

x = raw_input("Press enter for next test")

stepper.set_direction(cw)
# Set the motor to run in 1/4 of a step per pulse.

stepper.set_quarter_step()

# Do some steps.
for i in range(0,800):
    stepper.step()

x = raw_input("Press enter for next test")

stepper.set_direction(ccw)
# Set the motor to run in 1/8 of a step per pulse.
stepper.set_eighth_step()

# Do some steps.
for i in range(0,1600):
    stepper.step()

# Clean up (just calls GPIO.cleanup() function.)
stepper.finish()


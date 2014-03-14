#!/usr/bin/python

from Adafruit_Motor_Driver import DCM
import time

# ===========================================================================
# Example Code
# ===========================================================================


# Initialise the DC motor object using the default address and set frequency
# dcm = DCM(0x60, debug=True)
# dcm.setDCMFreq(1000)

dcm = DCM(0x60, debug=True)
dcm.setDCMFreq(1600)

# Set DC Motor Shield port for each device
DCmotorA = dcm
DCmotorA.setDCMport('M1')
# DCmotorB = dcm
# DCmotorB.setDCMport('M2')

# Set DC Motor speed
DCmotorA.setDCMSpeed(150)
# DCmotorB.setDCMSpeed(200)

DCmotorA.run('FORWARD')

time.sleep(1)
DCmotorA.run('RELEASE')

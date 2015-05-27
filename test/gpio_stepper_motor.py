
# Stepper Driver Module
# Copyright (c) 2012 Kevin Cazabon
# kevin@cazabon.com

# This is intended for driving multiple stepper motors simultaneously through two 4-bit shift registers (or only using 4 bits on each of two 8-bit registers)
# Contact Kevin Cazabon for schematics on the driver board

import time
import math

import wiringpi
wiringpi.wiringPiSetup()

# NOTE:  if you want to use RPi.GPIO instead of wiringpi, just modify the GPIO_OUT and GPIO_IN classes below... all else should be fine after that.
#       However, this was only tested with v. 0.2 of RPi.GPIO, so double check it!
#
#
#from RPi.GPIO import *  # ideally this should just be tacked at the bottom of the GPIO module itself
#from RPi.GPIO import _GetValidId, _ExportedIds

#class GPIO_OUT:
#    """To attain higher write performance on the RPi GPIO (up to about 5x), keep the device open as a file
#instead of opening/closing it each time you write to it.  Contributed by Kevin Cazabon"""
#    
#    def __init__(self, channel):
#        self.channel = channel
#        setup(self.channel, OUT)
#        
#        self.id = _GetValidId(self.channel)
#
#        if self.id not in _ExportedIds or _ExportedIds[self.id] != OUT:
#            raise WrongDirectionException
#        
#        self.f = open('/sys/class/gpio/gpio%s/value'%self.id, 'w')
#
#        # try to guarantee that we don't leave the file open by mistake
#        atexit.register(self.__del__)
#
#    def __del__(self):
#        if not self.f.closed:
#            self.f.flush()
#            self.f.close()
#            
#    def output(self, value):
#        self.f.write('1' if value else '0')
#        self.f.flush()
#
#    def close(self):
#        self.__del__()

#class GPIO_IN:
#    def __init__(self, channel):
#        self.channel = channel
#        
#        setup(self.channel, IN)
#
#    def __del__(self):
#        pass
#            
#    def input(self):
#        # High = True, Low = False
#        if input(self.channel) == 1:
#            return True
#        else:
#            return False
#
#    def close(self):
#        self.__del__()


# a few constants
INITIAL_RAMP_TIMEPERSTEP = 0.1
FORWARD = 1
REVERSE = -1


class GPIO_OUT:
    """To attain higher write performance on the RPi GPIO (up to about 10x), keep the device open as a file
instead of opening/closing it each time you write to it.  Contributed by Kevin Cazabon"""
    
    def __init__(self, channel, postSleep = None):
        self.channel = channel
        self.postSleep = postSleep
        
        wiringpi.pinMode(self.channel, 1)
        
    def __del__(self):
        pass
            
    def output(self, value):
        wiringpi.digitalWrite(self.channel, 1 if value else 0)
        if self.postSleep:
            time.sleep(self.postSleep)

    def close(self):
        self.__del__()

class GPIO_IN:
    def __init__(self, channel):
        self.channel = channel
        
        wiringpi.pinMode(self.channel, 2)

    def __del__(self):
        pass
            
    def input(self):
        # High = True, Low = False
        if wiringpi.digitalRead(self.channel) == 1:
            return True
        else:
            return False

    def close(self):
        self.__del__()


# FIXME - things left to do for this class:
#
#   - fix the timing for steps/second - it's close, but there's loop/etc. overhead that results in fewer steps than intended.
#   - some sort of calibration of that may be needed if I can't figure out a better way.
# 
class stepper:
    def __init__(self, dataPin, clockPin, latchPin, limitPin, startLocked = False, latchSleep = None):
        self.d = GPIO_OUT(dataPin)
        self.c = GPIO_OUT(clockPin)
        self.l = GPIO_OUT(latchPin)
        self.limit = GPIO_IN(limitPin)
        self.latchSleep = latchSleep
        
        self.stepPattern = [True, True, False, False]
        self.halfStepPattern = [[True, False, False, False], [True, False, False, True], [False, False, False, True], [False, False, True, True], [False, False, True, False], [False, True, True, False], [False, True, False, False], [True, True, False, False]]
        
        self.currentPhase = [False, False, False, False]    # not used yet...
        
        self.stepCount = 0
        
        if startLocked:
            self.lock()
    
    def lock(self):
        self.step(FORWARD, 1)

    def deEnergize(self, motor1 = True, motor2 = True):
        self.d.output(False)
        self.c.output(False)
        self.l.output(False)
        
        # shift 8 blank bits onto the shift register, then latch it.
        for i in range(8):
            self.c.output(True)
            self.c.output(False)
        
        self.l.output(True)
        self.l.output(False)

    def step(self, steps = 1, stepsPerSecond = None, direction = FORWARD, overrideLimit = False):
        # forward can be done by simply cascading one bit at a time through the register - much faster!
        
        if (direction != FORWARD and steps > 0) or (direction == FORWARD and steps < 0):
            return self.stepReverse(abs(steps), stepsPerSecond, overrideLimit)
            
        self.c.output(False)
        self.l.output(False)
        
        for i in range(int(self.stepCount + 1), int(self.stepCount + 1) + steps, 1):
            start = time.time()
            if overrideLimit:
                print "*** Limit Switch Over-Ridden! Careful! ***"
            else:
                if not self.limit.input():
                    print "*** Limit Sensed - cannot move further ***"
                    self.stepCount = i
                    return -1
                            
            self.c.output(False)
            self.d.output(self.stepPattern[i%len(self.stepPattern)])
            self.c.output(True)

            # data should be loaded... latch it to the output!
            self.l.output(True)
            self.l.output(False)
            
            # ensure we're going the right-ish speed
            duration = time.time() - start
            if stepsPerSecond > 0:
                if duration < 1.0/float(stepsPerSecond):
                    time.sleep((1.0/float(stepsPerSecond)) - duration)

        # we must have completed all steps without hitting the limit switch
        self.stepCount = i
        return 0
    
    def complexStep(self, pattern, stepCounter, overrideLimit):
        # load all pattern bits into the shift register before latching
        # this only does one step - you'll have to call it multiple times
        if overrideLimit:
            print "*** Limit Switch Over-Ridden! Careful! ***"
        else:
            if not self.limit.input():
                print "*** Limit Sensed - cannot move further ***"
                return -1

        self.c.output(False)
        self.l.output(False)
        
        for i in range(len(pattern)):
            self.d.output(pattern[i])
            self.c.output(True)
            self.c.output(False)
        
        self.l.output(True)
        
        self.stepCount = self.stepCount + stepCounter
        
        return 0
    
    def stepReverse(self, steps = 1, stepsPerSecond = None, overrideLimit = False):
        for i in range(abs(steps)):
            start = time.time()
            # load the four data points into motor1
            stepNumber = int(self.stepCount - 1)%len(self.stepPattern)
            
            # stepNumber will be counting down.  Shift the step pattern left accordingly
            pattern = self.stepPattern[stepNumber:] + self.stepPattern[:stepNumber]
                
            if self.complexStep(pattern, -1, overrideLimit) != 0:
                # Limit sensed during movement, bail.
                return -1
            
            # ensure we're going the right-ish speed
            duration = time.time() - start
            if stepsPerSecond > 0:
                if duration < 1.0/float(stepsPerSecond):
                    time.sleep((1.0/float(stepsPerSecond)) - duration)
            
        return 0

    def halfStep(self, steps = 1, stepsPerSecond = None, direction = FORWARD, overrideLimit = False):
        if (direction != FORWARD and steps > 0) or (direction == FORWARD and steps < 0):
            return self.halfStepReverse(abs(steps))
        
        for i in range(steps):
            start = time.time()
            stepNumber = int(((float(self.stepCount) + 0.5)*2.0) % len(self.halfStepPattern))
            pattern = self.halfStepPattern[stepNumber]
            if self.complexStep(pattern, 0.5, overrideLimit) != 0:
                # Limit sensed during movement, bail.
                return -1
            
            # ensure we're going the right-ish speed
            duration = time.time() - start
            if stepsPerSecond > 0:
                if duration < 1.0/float(stepsPerSecond):
                    time.sleep((1.0/float(stepsPerSecond)) - duration)
            
        return 0

    def halfStepReverse(self, steps = 1, stepsPerSecond = None, overrideLimit = False):
        for i in range(abs(steps)):
            start = time.time()
            stepNumber = int(((float(self.stepCount) - 0.5)*2.0) % len(self.halfStepPattern))
            pattern = self.halfStepPattern[stepNumber]
            if self.complexStep(pattern, -0.5, overrideLimit) != 0:
                # Limit sensed during movement, bail.
                return -1
            
            # ensure we're going the right-ish speed
            duration = time.time() - start
            if stepsPerSecond > 0:
                if duration < 1.0/float(stepsPerSecond):
                    time.sleep((1.0/float(stepsPerSecond)) - duration)
            
        return 0

    def stepTime(self, startTime, normalTime, rampSteps, thisStepNumber):
        # this needs some work for constant acceleration - but it's a start.
        x = float(thisStepNumber)/float(rampSteps)
        x2 = 1 - math.sin(x * math.pi/2.0)
        
        timeThisStep =  normalTime + (x2 * (startTime - normalTime))
            
        return timeThisStep
    
    def ramp(self, function, startSpeed, finalSpeed, rampSteps):
        if startSpeed == 0:
            startSpeed = 50
        if finalSpeed == 0:
            finalSpeed = 50
        for i in range(abs(rampSteps)):
            start = time.time()
            if startSpeed > finalSpeed:
                thisStepTime = self.stepTime(1.0/float(startSpeed), 1.0/float(finalSpeed), rampSteps, i)
            else:
                thisStepTime = self.stepTime(1.0/float(finalSpeed), 1.0/float(startSpeed), rampSteps, rampSteps - i)
                
            if function(1, None) != 0:
                # Limit sensed during movement, bail.
                return -1
            
            # ensure we're going the right-ish speed
            # do that here because of the extra overhead of the math for stepTime
            duration = time.time() - start
            if thisStepTime > 0:
                if duration < thisStepTime:
                    time.sleep(thisStepTime - duration)
            

        
if __name__ == "__main__":
    # a whole series of testing...
    print "#" *80
    print "Stepper Motor Driver Test - using WiringPi setups"
    print "#" *80
    print

    # define your stepper and the outputs/limit switch to use
    s = stepper(6, 4, 5, 0)
    #s2 = stepper(1,0,4,7)
    
    
    print"Motor 1 100 steps / 0.01"
    for i in range(100):
        s.step(1)
        time.sleep(0.01)
    
    time.sleep(2)
    s.deEnergize()
    time.sleep(2)
    
    #print "Motor 2 100 steps / 0.01"
    #for i in range(100):
    #    s2.step(1)
    #    time.sleep(0.01)    
    
    #time.sleep(2)
    #s2.deEnergize()
    #time.sleep(2)
    
    print"Motor 1 100 steps reverse / 0.01"
    for i in range(100):
        s.stepReverse(1)
        time.sleep(0.01)
    
    time.sleep(2)
    s.deEnergize()
    time.sleep(2)
    
    #print "Motor 2 100 steps reverse / 0.01"
    #for i in range(100):
    #    s2.stepReverse(1)
    #    time.sleep(0.01)    
    
    #time.sleep(2)
    #s2.deEnergize()
    #time.sleep(2)  

    print"Motor 1 100 half-steps / 0.01"
    for i in range(100):
        s.halfStep(1)
        time.sleep(0.01)
    
    time.sleep(2)
    s.deEnergize()
    time.sleep(2)
    
    #print "Motor 2 100 half-steps / 0.01"
    #for i in range(100):
    #    s2.halfStep(1)
    #    time.sleep(0.01)    
    
    #time.sleep(2)
    #s2.deEnergize()
    #time.sleep(2)
    
    
    print"Motor 1 100 half-steps reverse / 0.01"
    for i in range(100):
        s.halfStepReverse(1)
        time.sleep(0.01)
    
    time.sleep(2)
    s.deEnergize()
    time.sleep(2)
    
    #print "Motor 2 100 half-steps reverse / 0.01"
    #for i in range(100):
    #    s2.halfStepReverse(1)
    #    time.sleep(0.01)    
    
    #time.sleep(2)
    #s2.deEnergize()
    #time.sleep(2)
    
    print "*"*80
    print "ramping up to max speed forward"
    print "*"*80
    print
    
    print "100/sec"
    s.step(100,100)
    print "150/sec"
    s.step(150,150)
    print "200/sec"
    s.step(200,200)
    print "250/sec"
    s.step(250,250)
    print "300/sec"
    s.step(300,300)
    print "350/sec"
    s.step(350,350)
    print "400/sec"
    s.step(400,400)
    print "450/sec"
    s.step(450,450)
    print "500/sec"
    s.step(500,500)
    print "550/sec"
    s.step(550,550)
    print "600/sec"
    s.step(600,600)
    print "650/sec"
    s.step(650,650)
    print "700/sec"
    s.step(700,700)
    print "750/sec"
    s.step(750,750)
    print "800/sec"
    s.step(800,800)
    
    s.deEnergize()
    time.sleep(2)
    
    print "trying reverse (complex step)"
    print "100/sec"
    s.stepReverse(100,100)
    print "150/sec"
    s.stepReverse(150,150)
    print "200/sec"
    s.stepReverse(200,200)
    print "250/sec"
    s.stepReverse(250,250)
    print "300/sec"
    s.stepReverse(300,300)
    print "350/sec"
    s.stepReverse(350,350)
    print "400/sec"
    s.stepReverse(400,400)
    print "450/sec"
    s.stepReverse(450,450)
    print "500/sec"
    s.stepReverse(500,500)
    
    s.deEnergize()
    time.sleep(2)
    
    print "trying half-step (complex step)"
    print "100/sec"
    s.halfStep(100,100)
    print "150/sec"
    s.halfStep(150,150)
    print "200/sec"
    s.halfStep(200,200)
    print "250/sec"
    s.halfStep(250,250)
    print "300/sec"
    s.halfStep(300,300)
    print "350/sec"
    s.halfStep(350,350)
    print "400/sec"
    s.halfStep(400,400)
    print "450/sec"
    s.halfStep(450,450)
    print "500/sec"
    s.halfStep(500,500)

    s.deEnergize()
    time.sleep(2)
    
    print "testing step timing accuracy over 1000 steps in multiple modes"
    start = time.time()
    s.step(1000, 200)
    print "1000 steps @ 200/sec, actually: %s /sec" %(1000.0/((time.time()-start)))
    
    start = time.time()
    s.step(1000, 400)
    print "1000 steps @ 400/sec, actually: %s /sec" %(1000.0/((time.time()-start)))
    
    start = time.time()
    s.stepReverse(1000, 200)
    print "1000 steps reverse @ 200/sec, actually: %s /sec" %(1000.0/((time.time()-start)))
    
    start = time.time()
    s.stepReverse(1000, 400)
    print "1000 steps reverse @ 400/sec, actually: %s /sec" %(1000.0/((time.time()-start)))
    
    start = time.time()
    s.halfStep(1000, 200)
    print "1000 halfSteps @ 200/sec, actually: %s /sec" %(1000.0/((time.time()-start)))
    
    start = time.time()
    s.halfStepReverse(1000, 400)
    print "1000 halfSteps reverse @ 400/sec, actually: %s /sec" %(1000.0/((time.time()-start)))
    
    
    s.deEnergize()
    time.sleep(2)
    
    print"*"*80
    print
    
    print "testing ramp"
    s.ramp(s.step, 0, 200, 100)
    s.step(100, 200)
    s.ramp(s.step, 200, 0, 100)
    
    s.deEnergize()
    time.sleep(2)
    
    print "testing ramp in halfStepReverse"
    s.ramp(s.halfStepReverse, 0, 200, 100)
    s.halfStepReverse(100, 200)
    s.ramp(s.halfStepReverse, 200, 0, 100)
    
    s.deEnergize()
    time.sleep(2)

    print "multi-ramp"
    s.ramp(s.step, 0, 200, 200)
    s.step(400,200)
    s.ramp(s.step, 200,400,400)
    s.step(800,400)
    s.ramp(s.step, 400,600,600)
    s.step(1200,600)
    s.ramp(s.step, 600,300,300)
    s.step(600,300)
    s.ramp(s.step, 300,0,300)
  
    s.deEnergize()
    time.sleep(2)

    print "multi-ramp to reverse"
    s.ramp(s.step, 0, 200, 200)
    s.step(400,200)
    s.ramp(s.step, 200,400,400)
    s.step(800,400)
    s.ramp(s.step, 400,200,200)
    s.step(200,200)
    s.ramp(s.step, 200,0,200)
    s.ramp(s.stepReverse, 0,200,200)
    s.stepReverse(300, 200)
  
    s.deEnergize()
    time.sleep(2)

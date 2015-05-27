import RPi.GPIO as GPIO
import time
 
# Global definations

enable_pin = 18
coil_A_1_pin = 4
coil_A_2_pin = 17
coil_B_1_pin = 23
coil_B_2_pin = 24
 
# Operations

def forward(delay, steps):  
  for i in range(0, steps):
    setStep(1, 0, 1, 0)
    time.sleep(delay)
    setStep(0, 1, 1, 0)
    time.sleep(delay)
    setStep(0, 1, 0, 1)
    time.sleep(delay)
    setStep(1, 0, 0, 1)
    time.sleep(delay)
 
def backwards(delay, steps):  
  for i in range(0, steps):
    setStep(1, 0, 0, 1)
    time.sleep(delay)
    setStep(0, 1, 0, 1)
    time.sleep(delay)
    setStep(0, 1, 1, 0)
    time.sleep(delay)
    setStep(1, 0, 1, 0)
    time.sleep(delay)
 
def setStep(w1, w2, w3, w4):
  GPIO.output(coil_A_1_pin, w1)
  GPIO.output(coil_A_2_pin, w2)
  GPIO.output(coil_B_1_pin, w3)
  GPIO.output(coil_B_2_pin, w4)
 
def release():
  GPIO.output(coil_A_1_pin, 0)
  GPIO.output(coil_A_2_pin, 0)
  GPIO.output(coil_B_1_pin, 0)
  GPIO.output(coil_B_2_pin, 0)
  GPIO.cleanup

def init():
  GPIO.setmode(GPIO.BCM)
 
  GPIO.setup(enable_pin, GPIO.OUT)
  GPIO.setup(coil_A_1_pin, GPIO.OUT)
  GPIO.setup(coil_A_2_pin, GPIO.OUT)
  GPIO.setup(coil_B_1_pin, GPIO.OUT)
  GPIO.setup(coil_B_2_pin, GPIO.OUT)
 
  GPIO.output(enable_pin, 1)

# Main body

try:
  init()

  while True:
    delay = raw_input("Delay between steps (milliseconds)?")
    if delay == "q":
      release()
      break
    steps = raw_input("How many steps forward? ")
    forward(int(delay) / 1000.0, int(steps))
    steps = raw_input("How many steps backwards? ")
    backwards(int(delay) / 1000.0, int(steps))

except KeyboardInterrupt:
  release()

import RPi.GPIO as GPIO
import time
 
# Global definations

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
 
Motor_Pin = Motor_V_Pin
StepCount = StepCount2
Seq = Seq2

def forward(delay, steps):  		#H-Right, V-Down
  for i in range(0, steps):
    for j in range(0, StepCount):
      setStep(Seq[j][0], Seq[j][1], Seq[j][2], Seq[j][3])
      time.sleep(delay)
  release()
 
def backwards(delay, steps):  		#H-Left, V-Up
  for i in range(0, steps):
    for j in range(0, StepCount):
      setStep(Seq[StepCount-1-j][0], Seq[StepCount-1-j][1], Seq[StepCount-1-j][2], Seq[StepCount-1-j][3])
      time.sleep(delay)
  release()

 
def setStep(w1, w2, w3, w4):
  GPIO.output(Motor_Pin[0], w1)
  GPIO.output(Motor_Pin[1], w2)
  GPIO.output(Motor_Pin[2], w3)
  GPIO.output(Motor_Pin[3], w4)
 
def release():
  GPIO.output(Motor_Pin[0], 0)
  GPIO.output(Motor_Pin[1], 0)
  GPIO.output(Motor_Pin[2], 0)
  GPIO.output(Motor_Pin[3], 0)
  GPIO.cleanup

def init():
  GPIO.setmode(GPIO.BCM)
 
  GPIO.setup(Motor_Pin[0], GPIO.OUT)
  GPIO.setup(Motor_Pin[1], GPIO.OUT)
  GPIO.setup(Motor_Pin[2], GPIO.OUT)
  GPIO.setup(Motor_Pin[3], GPIO.OUT)
 
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

from Adafruit_MotorHAT import Adafruit_MotorHAT, Adafruit_DCMotor
import RPi.GPIO as GPIO
import atexit
import time
from robotModule import robotModule

class PiHatMotorModule(robotModule):
    def __init__(self):
        GPIO.setmode(GPIO.BCM)
        self.drivingSpeed = 200
        self.mh = Adafruit_MotorHAT(addr=0x60)
        atexit.register(self.turnOffMotors)
        self.motorA = self.mh.getMotor(1)
        self.motorB = self.mh.getMotor(2)
        self.forward = [-1, 1, 1, -1]
        self.backward = [1, -1, -1, 1]
        self.left = [1, -1, 1, -1]
        self.right = [-1, 1, -1, 1]
        self.turnDelay = 0.1
        self.straightDelay = 0.5
        self.motorSpeedCorrection = [0, 0, 10, 10]
        
    def runMotor(self, motorIndex, direction, speed = 128):
        motor = self.mh.getMotor(motorIndex+1)
        if direction == 1:
            motor.setSpeed(speed)
            motor.run(Adafruit_MotorHAT.FORWARD)
        elif direction == -1:
            motor.setSpeed(speed)
            motor.run(Adafruit_MotorHAT.BACKWARD)
        elif direction == 0:
            motor.setSpeed(0)
        else:
            pass
            
    def eventHandler(self, args):
        print("Can there be multiple people sending commands at the same time?[0]")
        print(args)
        command = args['command']
        print(command)
        
        self.motorA.setSpeed(self.drivingSpeed)
        self.motorB.setSpeed(self.drivingSpeed)
        if command == 'F':
            for motorIndex in range(4):
                self.runMotor(motorIndex, self.forward[motorIndex], (self.drivingSpeed + self.motorSpeedCorrection[motorIndex]))
        if command == 'B':
            for motorIndex in range(4):
                self.runMotor(motorIndex, self.backward[motorIndex], (self.drivingSpeed + self.motorSpeedCorrection[motorIndex]))
        if command == 'L':
            for motorIndex in range(4):
                self.runMotor(motorIndex, self.left[motorIndex], (self.drivingSpeed + self.motorSpeedCorrection[motorIndex]))
        if command == 'R':
            for motorIndex in range(4):
                self.runMotor(motorIndex, self.right[motorIndex], (self.drivingSpeed + self.motorSpeedCorrection[motorIndex]))
        if command == 'stop':
            for motorIndex in range(4):
                self.runMotor(motorIndex, 0)
    
    def shutdown(self):
        self.turnOffMotors()
    
    def turnOffMotors(self):
        # pi hat motors
        self.mh.getMotor(1).run(Adafruit_MotorHAT.RELEASE)
        self.mh.getMotor(2).run(Adafruit_MotorHAT.RELEASE)
        self.mh.getMotor(3).run(Adafruit_MotorHAT.RELEASE)
        self.mh.getMotor(4).run(Adafruit_MotorHAT.RELEASE)


if __name__ == '__main__':
    mm = PiHatMotorModule()
    mm.runMotor(0,1)
    time.sleep(5)





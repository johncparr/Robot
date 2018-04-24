# CamJam EduKit 3 - Robotics
# Program by John Parr based on the CamJam worksheets and online resources
# Top

# Import the Library's
import RPi.GPIO as GPIO
import time
import sys
import termios
import tty
import threading

# Set the GPIO modes
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Set variables for the GPIO motor pins
pinMotorAForwards = 10
pinMotorABackwards = 9
pinMotorBForwards = 8
pinMotorBBackwards = 7

# Define GPIO pins to use for distance measurement on the Pi
pinTrigger = 17
pinEcho = 18

# Set pins as output and input
GPIO.setup(pinTrigger, GPIO.OUT)  # Trigger
GPIO.setup(pinEcho, GPIO.IN)  # Echo

# Variables
Distance = 0
Distances = [0, 0, 0]

# How many times to turn the pin on and off each second
Frequency = 20

# How long the pin stays on each cycle, as a percent (here, it's 40%)
DutyCycle = 40.0

# Last Duty Cycle used to allow smooth transitions in speed
LastDutyCycle = 0.0
SpeedSteps = 3

# Adj balances the forward drive
Adj = 0.06

# Time to turn 90 degrees
# TurnTimeRef = 0.7
TurnTimes = [0.0, 8.0, 1.20, 0.75, 0.5, 0.40, 0.38, 0.37, 0.35, 0.335, 0.3]
TurnTime = TurnTimes[4]

# Setting the duty cycle to 0 means the motors will not turn
Stop = 0

# set a string to hold the last action
Last = "S"

# Stop Flag
StopFlag = False

# Obsticle avoidance mode
Modes = ["Simple", "Choose2", "Choose3"]
Mode = Modes[0]
Choice = 0

# Circle Sizes
Small = 0.4
Large = 0.6

# Set the GPIO Pin mode
GPIO.setup(pinMotorAForwards, GPIO.OUT)
GPIO.setup(pinMotorABackwards, GPIO.OUT)
GPIO.setup(pinMotorBForwards, GPIO.OUT)
GPIO.setup(pinMotorBBackwards, GPIO.OUT)

# Set the GPIO to software PWM at 'Frequency' Hertz
pwmMotorAForwards = GPIO.PWM(pinMotorAForwards, Frequency)
pwmMotorABackwards = GPIO.PWM(pinMotorABackwards, Frequency)
pwmMotorBForwards = GPIO.PWM(pinMotorBForwards, Frequency)
pwmMotorBBackwards = GPIO.PWM(pinMotorBBackwards, Frequency)

# Start the software PWM with a duty cycle of 0 (i.e. not moving)
pwmMotorAForwards.start(Stop)
pwmMotorABackwards.start(Stop)
pwmMotorBForwards.start(Stop)
pwmMotorBBackwards.start(Stop)

# Subroutines


# Turn all motors off
def StopMotors():
    pwmMotorAForwards.ChangeDutyCycle(Stop)
    pwmMotorABackwards.ChangeDutyCycle(Stop)
    pwmMotorBForwards.ChangeDutyCycle(Stop)
    pwmMotorBBackwards.ChangeDutyCycle(Stop)


# Turn both motors forwards
def Forwards(Power):
    pwmMotorAForwards.ChangeDutyCycle(Power)
    pwmMotorABackwards.ChangeDutyCycle(Stop)
    pwmMotorBForwards.ChangeDutyCycle(Power * (1 - Adj))
    pwmMotorBBackwards.ChangeDutyCycle(Stop)


# Turn both motors backwards
def Backwards(Power):
    pwmMotorAForwards.ChangeDutyCycle(Stop)
    pwmMotorABackwards.ChangeDutyCycle(Power)
    pwmMotorBForwards.ChangeDutyCycle(Stop)
    pwmMotorBBackwards.ChangeDutyCycle(Power)


# Turn both motors backwards
def Backup(Power, distance):
    while distance <= 40:
        Backwards(Power)
        distance = Measure()
    StopMotors()


# Turn Right
def Right(Power):
    pwmMotorAForwards.ChangeDutyCycle(Stop)
    pwmMotorABackwards.ChangeDutyCycle(Power)
    pwmMotorBForwards.ChangeDutyCycle(Power)
    pwmMotorBBackwards.ChangeDutyCycle(Stop)


# Turn Left
def Left(Power):
    pwmMotorAForwards.ChangeDutyCycle(Power)
    pwmMotorABackwards.ChangeDutyCycle(Stop)
    pwmMotorBForwards.ChangeDutyCycle(Stop)
    pwmMotorBBackwards.ChangeDutyCycle(Power)


# Turn in a circle
def Circle(Power, Size):
    pwmMotorAForwards.ChangeDutyCycle(Power * Size)
    pwmMotorABackwards.ChangeDutyCycle(Stop)
    pwmMotorBForwards.ChangeDutyCycle(Power)
    pwmMotorBBackwards.ChangeDutyCycle(Stop)


# Accelerate Forwards
def AccelerateForwards(NewPower, OldPower):
    Step = (NewPower-OldPower)/SpeedSteps
    print(OldPower+Step)
    Forwards(OldPower+Step)
    time.sleep(0.25)
    print(NewPower-Step)
    Forwards(NewPower-Step)
    time.sleep(0.25)
    print(NewPower)
    Forwards(NewPower)


# Accelerate Backwards
def AccelerateBackwards(NewPower, OldPower):
    Step = (NewPower-OldPower)/SpeedSteps
    Backwards(OldPower+Step)
    time.sleep(0.25)
    Backwards(NewPower-Step)
    time.sleep(0.25)
    Backwards(NewPower)


# get control input
def getch():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch


def Continue():
    if (Last in("fF")):
        AccelerateForwards(DutyCycle, LastDutyCycle)
    if (Last in("bB")):
        AccelerateBackwards(DutyCycle, LastDutyCycle)
    if (Last in("c")):
        Circle(DutyCycle, Small)
    if (Last in("C")):
        Circle(DutyCycle, Large)


def Measure():
        # Set trigger to False (Low)
        GPIO.output(pinTrigger, False)

        # Allow module to settle
        time.sleep(0.25)

        # Send 10us pulse to trigger
        GPIO.output(pinTrigger, True)
        time.sleep(0.00001)
        GPIO.output(pinTrigger, False)

        # Start the timer
        StartTime = time.time()

        # The start time is reset until the Echo pin is taken high (==1)
        while GPIO.input(pinEcho) == 0:
            StartTime = time.time()

        # Stop when the Echo pin is no longer high - the end time
        while GPIO.input(pinEcho) == 1:
            StopTime = time.time()
        # If the sensor is too close to an object, the Pi cannot
        # see the echo quickly enough, so it has to detect that
        # problem and say what has happened
            if StopTime-StartTime >= 0.04:
                print("Hold on there! You're too close for me to see.")
                StopTime = StartTime
                break

        # Calculate pulse length
        ElapsedTime = StopTime - StartTime

        # Distance pulse travelled in that time is
        # time multiplied by the speed of sound (cm/s)
        distance = ElapsedTime * 34326

        # That was the distance there and back so halve the value
        distance = distance / 2

        print("\rDistance: %.1f cm" % distance)

        return distance


# Distance Control Thread
class DistanceControl (threading.Thread):
    def __init__(dctl, threadID, name, counter):
        threading.Thread.__init__(dctl)
        dctl.threadID = threadID
        dctl.name = name
        dctl.counter = counter

    def run(dctl):

        global Distance, StopFlag, DutyCycle, OldDutyCycle, TurnTime
        global Mode, Last, Adj, Choice
        global Distances, Large, Small

        while StopFlag is False:

            Distance = Measure()
            # In a big open space a zero distance is returned
            if (Distance == 0):
                Distance = 1000
                print("A long way to go")
            if (Distance <= 40):
                if (Distance >= 1):
                    if (Last != "S"):
                        # Go back a bit
                        Backup(20, Distance)
                        if (Mode == "Simple"):
                            print("%.1f cm so go Right" % Distance)
                            Right(DutyCycle)
                            time.sleep(TurnTime)
                            Continue()

                        elif (Mode == "Choose2"):
                            print("Choosing left or right")
                            Right(DutyCycle)
                            time.sleep(TurnTime)
                            StopMotors()
                            Distances[2] = Measure()
                            Right(DutyCycle)
                            time.sleep(TurnTime)
                            StopMotors()
#                            Distances[1] = Measure()
                            Right(DutyCycle)
                            time.sleep(TurnTime)
                            StopMotors()
                            Distances[0] = Measure()
                            Choice = max(Distances[0], Distances[2])
                            print("Choice: %.1f cm" % Choice)
                            if (Choice == Distances[2]):
                                Left(DutyCycle)
                                time.sleep(TurnTime*2)
                            Continue()

                        elif (Mode == "Choose3"):
                            print("Choosing left, right or turn round")
                            Right(DutyCycle)
                            time.sleep(TurnTime)
                            StopMotors()
                            Distances[2] = Measure()
                            Right(DutyCycle)
                            time.sleep(TurnTime)
                            StopMotors()
                            Distances[1] = Measure()
                            Right(DutyCycle)
                            time.sleep(TurnTime)
                            StopMotors()
                            Distances[0] = Measure()
                            Choice = max(Distances)
                            print("Choice: %.1f cm" % Choice)
                            if (Choice == Distances[2]):
                                Left(DutyCycle)
                                time.sleep(TurnTime*2)
                            elif (Choice == Distances[1]):
                                Left(DutyCycle)
                                time.sleep(TurnTime)
                            Continue()

            time.sleep(0.1)

        print("Exiting " + dctl.name)


#  Key Control Thread
class KeyControl (threading.Thread):
    def __init__(kctl, threadID, name, counter):
        threading.Thread.__init__(kctl)
        kctl.threadID = threadID
        kctl.name = name
        kctl.counter = counter

    def run(kctl):

        button_delay = 0.2
        global DutyCycle, TurnTime, TurnTimes, StopFlag
        global Last, Adj, LastDutyCycle, SpeedSteps, Mode, Modes
        global Large, Small

        while True:
            char = getch()
            print(char)

            if (char in("Pp")):
                print("Exit")
                StopMotors()
                StopFlag = True
                print("Exiting " + kctl.name)
                exit(0)

            if (char in("Ff")):
                print("Forward")
                AccelerateForwards(DutyCycle, LastDutyCycle)
                Last = char
#                time.sleep(1)

            elif (char in("Ll")):
                print("Left")
                Left(DutyCycle)
                time.sleep(TurnTime)
                StopMotors()

            elif (char in("kK")):
                print("Little Left")
                Left(DutyCycle)
                time.sleep(TurnTime / 3)
                if (Last == "S"):
                    StopMotors()
                Continue()

            elif (char in("Rr")):
                print("Right")
                Right(DutyCycle)
                time.sleep(TurnTime)
                StopMotors()

            elif (char in("eE")):
                print("Little Right")
                Right(DutyCycle)
                time.sleep(TurnTime / 3)
                if (Last == "S"):
                    StopMotors()
                Continue()

            elif (char in("Bb")):
                print("Back")
                AccelerateBackwards(DutyCycle, LastDutyCycle)
                Last = char
#                time.sleep(1)
#                StopMotors()

            elif (char in("Ss")):
                print("Stop")
                StopMotors()
                Last = "S"
                LastDutyCycle = 0

            elif (char == "C"):
                print("Big Circle")
                Circle(DutyCycle, Large)
                Last = char

            elif (char == "c"):
                print("Small Circle")
                Circle(DutyCycle, Small)
                Last = char

            elif(char in("Mm")):
                if (Mode == "Simple"):
                    Mode = "Choose2"
                    print(Mode)
                elif (Mode == "Choose2"):
                    Mode = "Choose3"
                    print(Mode)
                elif (Mode == "Choose3"):
                    Mode = "Simple"
                    print(Mode)

            elif (char in("1234567890")):
                LastDutyCycle = DutyCycle
                if (Last == "S"):
                    LastDutyCycle = 0
                if (char == "0"):
                    char = "10"
                DutyCycle = 10 * int(char)
                print("Power ", LastDutyCycle, " to ", DutyCycle)
                TurnTime = TurnTimes[int(char)]
                print("Turn time", TurnTime)

                Continue()

            time.sleep(button_delay)


# Create Threads
thread1 = KeyControl(1, "Key Control Thread", 1)
thread2 = DistanceControl(2, "Distance Control Thread", 1)

# Start the Threads
thread1.start()
thread2.start()
thread1.join()
thread2.join()
GPIO.cleanup()
print("Exiting Main Thread")

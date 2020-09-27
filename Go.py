# CamJam EduKit 3 - Robotics
# Program by John Parr based on the CamJam worksheets and online resources

# Import the Library's
import RPi.GPIO as GPIO
import time
import sys
import termios
import tty
import threading
import smbus
import math

# GPIO setup #################################################################
# Set the GPIO modes
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Set variables for the GPIO motor pins
pinMotorAForwards = 9
pinMotorABackwards = 10
pinMotorBForwards = 7
pinMotorBBackwards = 8

# Set the GPIO Pin mode
GPIO.setup(pinMotorAForwards, GPIO.OUT)
GPIO.setup(pinMotorABackwards, GPIO.OUT)
GPIO.setup(pinMotorBForwards, GPIO.OUT)
GPIO.setup(pinMotorBBackwards, GPIO.OUT)

# How many times to turn the pin on and off each second
Frequency = 20

# Set the GPIO to software PWM at 'Frequency' Hertz
pwmMotorAForwards = GPIO.PWM(pinMotorAForwards, Frequency)
pwmMotorABackwards = GPIO.PWM(pinMotorABackwards, Frequency)
pwmMotorBForwards = GPIO.PWM(pinMotorBForwards, Frequency)
pwmMotorBBackwards = GPIO.PWM(pinMotorBBackwards, Frequency)

# Setting the duty cycle to 0 means the motors will not turn
Stop = 0

# Start the software PWM with a duty cycle of 0 (i.e. not moving)
pwmMotorAForwards.start(Stop)
pwmMotorABackwards.start(Stop)
pwmMotorBForwards.start(Stop)
pwmMotorBBackwards.start(Stop)

# Define GPIO pins to use for distance measurement on the Pi
pinTrigger = 17
pinEcho = 18

# Set pins as output and input
GPIO.setup(pinTrigger, GPIO.OUT)  # Trigger
GPIO.setup(pinEcho, GPIO.IN)  # Echo


# Variables ##################################################################
# Distance is the measured distance to an Obsticle
Distance = 0

# Distances contains 3 distance measurements
Distances = [0, 0, 0]

# How long the pin stays on each cycle, as a percent (here, it's 40%)
DutyCycle = 40.0

# Last Duty Cycle used to allow smooth transitions in 3 SpeedSteps
LastDutyCycle = 0.0
SpeedSteps = 3

# Adj balances the forward drive to correct for drift left or right
Adj = 0.00

# AdjLeft and AdjRight are used in the compass mode to steer
AdjLeft = 0.0
AdjRight = 0.0

# Time to turn 90 degrees
# TurnAdj scales the entire Turntimes list for surface or battery conditions
TurnAdj = 1.4
TurnTimes = [0.0, 8.0, 1.20, 0.75, 0.5, 0.40, 0.38, 0.37, 0.35, 0.335, 0.3]
TurnTime = TurnTimes[4] * TurnAdj

# Set a flag indicate the robot is moving
Running = False

# Set char to blank. Holds the last key pressed
char = " "

# set a string to hold the last action. Default to S ie stopped
Last = "S"

# Stop Flag tells the threads if they should stop
StopFlag = False

# Obsticle avoidance mode. 3 choices. Default of Simple [0]
Modes = ["Simple", "Choose2", "Choose3"]
Mode = Modes[0]
Choice = 0
Backingup = False  # May not be needed now

# Auto is a flag set to true when avoiding an obsticle
Auto = False

# Compass Mode, the alternative to control by keys alone.
CompassMode = False

# Circle Sizes
Small = 0.4
Large = 0.6

# Set initial TargetHeading
TargetHeading = 0.0
LastHeading = 0.0
Correction = 0.0

# Compass correction data
Compass = []

with open('CompassCorr.txt') as reader:
    for line in reader:
        Compass.append(line.strip('\n'))

# Subroutines


# Turn all motors off
def StopMotors():
    pwmMotorAForwards.ChangeDutyCycle(Stop)
    pwmMotorABackwards.ChangeDutyCycle(Stop)
    pwmMotorBForwards.ChangeDutyCycle(Stop)
    pwmMotorBBackwards.ChangeDutyCycle(Stop)


# Turn both motors forwards
def Forwards(Power):
    pwmMotorAForwards.ChangeDutyCycle(Power * (1 - AdjRight))
    pwmMotorABackwards.ChangeDutyCycle(Stop)
    pwmMotorBForwards.ChangeDutyCycle(Power * (1 - AdjLeft) * (1 - Adj))
    pwmMotorBBackwards.ChangeDutyCycle(Stop)
    # print("\rRight: %5.1f, Left: %5.1f" % (AdjRight, AdjLeft))


# Turn both motors backwards
def Backwards(Power):
    pwmMotorAForwards.ChangeDutyCycle(Stop)
    pwmMotorABackwards.ChangeDutyCycle(Power)
    pwmMotorBForwards.ChangeDutyCycle(Stop)
    pwmMotorBBackwards.ChangeDutyCycle(Power)


# Turn both motors backwards away from an Obsticle
def Backup(Power):
    global Distance
    while Distance <= 40:
        Backwards(Power)
        # Distance = Measure()
    StopMotors()


# Turn Right
def Right(Power):
    pwmMotorAForwards.ChangeDutyCycle(Stop)
    pwmMotorABackwards.ChangeDutyCycle(Power)
    pwmMotorBForwards.ChangeDutyCycle(Power)
    pwmMotorBBackwards.ChangeDutyCycle(Stop)


# Turn Right under compass Control
def CRight(LH, TH):
    Right(DutyCycle)
    while LH < TH:
        LH = Heading()
        time.sleep(0.1)
    # StopMotors()


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
    Step = (NewPower - OldPower) / SpeedSteps

    Forwards(OldPower + Step)
    time.sleep(0.25)

    Forwards(NewPower - Step)
    time.sleep(0.25)

    Forwards(NewPower)


# Accelerate Backwards
def AccelerateBackwards(NewPower, OldPower):
    Step = (NewPower - OldPower) / SpeedSteps
    Backwards(OldPower + Step)
    time.sleep(0.25)
    Backwards(NewPower - Step)
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
    if (Last in ("fF")):
        AccelerateForwards(DutyCycle, LastDutyCycle)
    if (Last in ("bB")):
        AccelerateBackwards(DutyCycle, LastDutyCycle)
    if (Last in ("c")):
        Circle(DutyCycle, Small)
    if (Last in ("C")):
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
        if StopTime - StartTime >= 0.04:
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

    return distance


def TwosComptoInt(N):
    if (N > MaxInt):
        N -= TwosCompAdj
    return N


def Heading():

    # Read registers 3 to 8 for the XYZ data
    for x in range(3, 9):
        Regvalue[x] = bus.read_byte_data(address, x)

    # join the two 8 bit numbers to make a 16 bit
    X = (Regvalue[3] << 8) + Regvalue[4]
    Z = (Regvalue[5] << 8) + Regvalue[6]
    Y = (Regvalue[7] << 8) + Regvalue[8]

    # Convert the twos compliment format to a signed integer
    X = TwosComptoInt(X)
    Y = TwosComptoInt(Y)
    Z = TwosComptoInt(Z)

    # Calculate the heading in range 0 to 360
    if (Y > 0):
        Heading360 = 90 - (math.atan(X / Y) * 180 / math.pi)

    if (Y < 0):
        Heading360 = 270 - (math.atan(X / Y) * 180 / math.pi)

    if (Y == 0):
        if (X < 0):
            Heading360 = 180
        if (X > 0):
            Heading360 = 0
    # Calculate signed heading
    # Heading = math.atan(X/Y) * 180 / math.pi
    Heading = Heading360

    return Heading


# Set a new heading in the range 0 to 360 after inputing a change
def TargetHeadfn(Heading, Change):
    H = int(Heading)
    Hnew = H + Change
    if (Hnew < 0):
        Hnew += 360
    if (Hnew > 360):
        Hnew -= 360
    SensorChange = float(Compass[Hnew]) - float(Compass[H])
    NewHeading = Heading + SensorChange
    if (NewHeading < 0):
        NewHeading += 360
    if (NewHeading > 360):
        NewHeading -= 360
    return NewHeading


# Calculate Correction in range -180to +180
def Correctionfn():
    Correction = TargetHeading - LastHeading
    if Correction < -180:
        Correction += 360
    if Correction > 180:
        Correction -= 360
    return Correction


# Distance Control Thread
class DistanceControl (threading.Thread):
    def __init__(dctl, threadID, name, counter):
        threading.Thread.__init__(dctl)
        dctl.threadID = threadID
        dctl.name = name
        dctl.counter = counter

    def run(dctl):

        global Adj, AdjLeft, AdjRight, Auto, Backingup, char, Choice
        global CompassMode, Correction, Distance, Distances, DutyCycle, Large
        global Last, LastDutyCycle, LastHeading, Mode, Modes, Running, Small
        global SpeedSteps, Stop, StopFlag, TargetHeading, TurnAdj, TurnTime
        global TurnTimes

        while StopFlag is False:

            Distance = Measure()
            # In a big open space a zero distance is returned
            if (Distance == 0):
                Distance = 1000
                print("\rA long way to go")

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
        global Adj, AdjLeft, AdjRight, Auto, Backingup, char, Choice
        global CompassMode, Correction, Distance, Distances, DutyCycle, Large
        global Last, LastDutyCycle, LastHeading, Mode, Modes, Running, Small
        global SpeedSteps, Stop, StopFlag, TargetHeading, TurnAdj, TurnTime
        global TurnTimes

        while True:
            char = getch()

            if (char in ("Pp")):
                print("Exit")
                Running = False
                StopMotors()
                StopFlag = True
                print("Exiting " + kctl.name)
                exit(0)

            if (char in ("Ss")):
                print("Stop")
                TargetHeading = LastHeading
                Running = False
                StopMotors()
                Last = "S"
                LastDutyCycle = 0

            if (Auto is False):

                if (char in ("Ff")):
                    print("Forward")
                    # TargetHeading = LastHeading
                    AccelerateForwards(DutyCycle, LastDutyCycle)
                    Running = True
                    Last = char
    #                time.sleep(1)

                if (char in ("Hh")):
                    print("Heading")
                    TargetHeading = int(input('Heading 0-360'))
                    AccelerateForwards(DutyCycle, LastDutyCycle)
                    Running = True
                    Last = char

                elif (char in ("Ll")):
                    print("Left")
                    TargetHeading = TargetHeadfn(LastHeading, -90)
                    if (CompassMode is False):
                        Running = False
                        Left(DutyCycle)
                        time.sleep(TurnTime)
                        StopMotors()

                elif (char in ("kK")):
                    print("Little Left")
                    TargetHeading = TargetHeadfn(LastHeading, -30)
                    if (CompassMode is False):
                        Running = False
                        Left(DutyCycle)
                        time.sleep(TurnTime / 3)
                        if (Last == "S"):
                            StopMotors()
                        Continue()
                        Running = True

                elif (char in ("Rr")):
                    print("Right")
                    TargetHeading = TargetHeadfn(LastHeading, 90)
                    if (CompassMode is False):
                        Running = False
                        Right(DutyCycle)
                        time.sleep(TurnTime)
                        StopMotors()

                elif (char in ("eE")):
                    print("Little Right")
                    TargetHeading = TargetHeadfn(LastHeading, 30)
                    if (CompassMode is False):
                        Running = False
                        Right(DutyCycle)
                        time.sleep(TurnTime / 3)
                        if (Last == "S"):
                            StopMotors()
                        Continue()
                        Running = True

                elif (char in ("Bb")):
                    print("Back")
#                    Running = False
                    AccelerateBackwards(DutyCycle, LastDutyCycle)
                    Last = char
    #                time.sleep(1)
    #                StopMotors()

                elif (char == "C"):
                    print("Big Circle")
                    Running = False
                    Circle(DutyCycle, Large)
                    Last = char

                elif (char == "c"):
                    print("Small Circle")
                    Running = False
                    Circle(DutyCycle, Small)
                    Last = char

                elif(char in ("Mm")):
                    if (Mode == "Simple"):
                        Mode = "Choose2"
                        print(Mode)
                    elif (Mode == "Choose2"):
                        Mode = "Choose3"
                        print(Mode)
                    elif (Mode == "Choose3"):
                        Mode = "Simple"
                        print(Mode)

                elif(char in ("Nn")):
                    if (CompassMode):
                        CompassMode = False
                        AdjLeft = 0
                        AdjRight = 0
                        print("Compass Mode off")
                    elif (CompassMode is False):
                        CompassMode = True
                        print("Compass Mode active")

                elif (char in ("1234567890")):
                    LastDutyCycle = DutyCycle
                    if (Last == "S"):
                        LastDutyCycle = 0
                    if (char == "0"):
                        char = "10"
                    DutyCycle = 10 * int(char)
                    TurnTime = TurnTimes[int(char)] * TurnAdj
                    print("Turn time", TurnTime)

                Continue()

            time.sleep(button_delay)


#  Compass Control Thread
class CompassControl (threading.Thread):
    def __init__(cctl, threadID, name, counter):
        threading.Thread.__init__(cctl)
        cctl.threadID = threadID
        cctl.name = name
        cctl.counter = counter

    def run(cctl):

        global Adj, AdjLeft, AdjRight, Auto, Backingup, char, Choice
        global CompassMode, Correction, Distance, Distances, DutyCycle, Large
        global Last, LastDutyCycle, LastHeading, Mode, Modes, Running, Small
        global SpeedSteps, Stop, StopFlag, TargetHeading, TurnAdj, TurnTime
        global TurnTimes

        global bus, address, MaxInt, TwosCompAdj, Regvalue

        bus = smbus.SMBus(1)
        address = 0x1E
        bits = 16
        MaxInt = (2**(bits - 1)) - 1
        TwosCompAdj = 2**bits

        Regvalue = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

        # bus.write_byte_data(address, 0, 112)

        TargetHeading = Heading()

        # Sets HMC5883L Compass continuous mode. (Register 2, Mode 0)
        bus.write_byte_data(address, 2, 0)

        while StopFlag is False:

            LastHeading = Heading()
            Correction = Correctionfn()
            print("\rLast: %5.1f, Target %5.1f, Corr %5.1f" %
                  (LastHeading, TargetHeading, Correction))

            time.sleep(0.5)

        print("Exiting " + cctl.name)


class Drive (threading.Thread):
    def __init__(Dctl, threadID, name, counter):
        threading.Thread.__init__(Dctl)
        Dctl.threadID = threadID
        Dctl.name = name
        Dctl.counter = counter

    def run(Dctl):

        global Adj, AdjLeft, AdjRight, Auto, Backingup, char, Choice
        global CompassMode, Correction, Distance, Distances, DutyCycle, Large
        global Last, LastDutyCycle, LastHeading, Mode, Modes, Running, Small
        global SpeedSteps, Stop, StopFlag, TargetHeading, TurnAdj, TurnTime
        global TurnTimes

        # Set a parameter to control how aggressively to correct direction
        SteerFactor = 40

        while StopFlag is False:

            if (CompassMode):
                if(Correction > 0):
                    AdjLeft = 0
                    AdjRight = Correction / SteerFactor
                    if(AdjRight > 0.9):
                        AdjRight = 0.9
                if(Correction < 0):
                    AdjRight = 0
                    AdjLeft = (0 - Correction) / SteerFactor
                    if(AdjLeft > 0.9):
                        AdjLeft = 0.9

            # if (char in ("FfLlRrKkEeHh1234567890")):
                if (Running):
                    # AR = AdjRight
                    # AL = AdjLeft
                    # print("\rAdjRight: %5.3f, AdjLeft: %5.3f" % (AR, AL))
                    Forwards(DutyCycle)

            if (Distance <= 30):
                if (Distance >= 1):
                    if (Last != "S"):
                        # Stop Compass navigation
                        Running = False
                        Auto = True

                        # Go back a bit
                        Backup(40)

                        if (Mode == "Simple"):
                            if CompassMode:
                                TargetHeading = TargetHeadfn(LastHeading, 90)
                                CRight(LastHeading, TargetHeading)
                            elif CompassMode is False:
                                Right(DutyCycle)
                                time.sleep(TurnTime)
                            Running = True
                            Continue()

                        elif (Mode == "Choose2"):
                            print("Choosing left or right")
                            if (CompassMode):
                                pass

                            elif CompassMode is False:
                                Right(DutyCycle)
                                time.sleep(TurnTime)
                                StopMotors()
                                Distances[2] = Measure()
                                Right(DutyCycle)
                                time.sleep(TurnTime)
                                StopMotors()
                                Right(DutyCycle)
                                time.sleep(TurnTime)
                                StopMotors()
                                Distances[0] = Measure()
                                Choice = max(Distances[0], Distances[2])
                                # print("Choice: %.1f cm" % Choice)
                                if (Choice == Distances[2]):
                                    Left(DutyCycle)
                                    time.sleep(TurnTime * 2)
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
                            # print("Choice: %.1f cm" % Choice)
                            if (Choice == Distances[2]):
                                Left(DutyCycle)
                                time.sleep(TurnTime * 2)
                            elif (Choice == Distances[1]):
                                Left(DutyCycle)
                                time.sleep(TurnTime)
                            Continue()
                        Auto = False

        print("Exiting " + Dctl.name)


# Create Threads
thread1 = KeyControl(1, "Key Control Thread", 1)
thread2 = DistanceControl(2, "Distance Control Thread", 1)
thread3 = CompassControl(3, "Compass Control Thread", 1)
thread4 = Drive(4, "Drive Thread", 1)

# Start the Threads
thread1.start()
thread2.start()
thread3.start()
thread4.start()

# Join the threads
thread1.join()
thread2.join()
thread3.join()
thread4.join()

# Cleanup the GPIO
GPIO.cleanup()

print("Exiting Main Thread")

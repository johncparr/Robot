import smbus
import time
import math

bus = smbus.SMBus(1)
address = 0x1E
bits = 16
MaxInt = (2**(bits-1))-1
TwosCompAdj = 2**bits

Regvalue = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]


def read(reg):
    Data = bus.read_byte_data(address, reg)
    return Data


def TwosComptoInt(N):
    print(N, MaxInt)
    if (N > MaxInt):
        N -= TwosCompAdj
    return N


bus.write_byte_data(address, 0, 112)
bus.write_byte_data(address, 2, 0)

while True:

    #    for x in range(0, 3):
    #        Regvalue[x] = read(x)
    #        print (x, Regvalue[x])

    for x in range(3, 13):
        Regvalue[x] = read(x)
        print(x, Regvalue[x])

    X = (Regvalue[3] << 8) + Regvalue[4]
    Z = (Regvalue[5] << 8) + Regvalue[6]
    Y = (Regvalue[7] << 8) + Regvalue[8]

    X = TwosComptoInt(X)
    Y = TwosComptoInt(Y)
    Z = TwosComptoInt(Z)

    print(X, Y, Z)

    if (Y > 0):
        Heading = 90 - (math.atan(X/Y) * 180 / math.pi)

    if (Y < 0):
        Heading = 270 - (math.atan(X/Y) * 180 / math.pi)

    if (Y == 0):
        if (X < 0):
            Heading = 180
        if (X > 0):
            Heading = 0

    print("Heading ", Heading)

    time.sleep(5)

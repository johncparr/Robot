# Robot
<<<<<<< HEAD
Python3 code for a Raspberry Pi Robot

This code was written for a robot built with the CamJam EduKit 3. It may work with other hardware using a Raspberry Pi.

The Go.py code is intended to be run over SSH on the Pi. There are three threads running concurrently.

    The first listens for keys being pressed on the device used to connect over SSH with the Pi. These keys are interpreted
    as commands which the robot will follow.

    The second listens to a sonar sensor (part of the kit), and calculates the distance to the obstacle (if there is one)
    in front of the robot. If something is too close it takes action to avoid.

    The third takes input from a HMC5883L compass. The idea of this is to use the compass data to keep the robot moving in a straight line and also to make a turn left or right by a consistent amount at all speeds. You can switch compass mode on or off.

Without compass mode the robot can drift left or right. It will also turn to differing amounts when told to, depending on speed, the state of the
battery's or the surface on which its running.

I want to add more sensors to improve obstacle avoidance

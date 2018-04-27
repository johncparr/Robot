# Robot
Python3 code for a Raspberry Pi Robot

This code was written for a robot built with the CamJam EduKit 3. It may work with other hardware using a Raspberry Pi.

The Go.py code is intended to be run over SSH on the Pi. There are two threads running concurrently. 

    The first listens for keys being pressed on the device used to connect over SSH with the Pi. These keys are interpreted 
    as commands which the robot will follow.
    
    The second listens to a sonar sensor (part of the kit), and calculates the distance to the obstacle (if there is one)
    in front of the robot. If something is too close it takes action to avoid.
    
I have plans to add a compass so that the robot will run in a straight line and turns a specific amount on command. This first
version can drift left or right. It will also turn to differing amounts when told to, depending on speed, the state of the
batterys or the surface on which its running.

I also want to add more sensors to improve obstacle avoidance

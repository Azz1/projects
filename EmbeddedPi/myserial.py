#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
In this module, we create an interface for sending command to EmbeddedPi via UART

author: Jack Zhu
last edited: April 2014
License: LGPL 
"""
from subprocess import Popen, PIPE

class EmbeddedPi:


    def ReadMR(self):
        cmd = './main m'
        ret = Popen(cmd, shell=True, stdout=PIPE).communicate()[0]
        val = float(ret) - 169.4;
	if(val < 0):
	    val += 360;
        return val

    def ReadDistance(self):
        cmd = './main d'
        ret = Popen(cmd, shell=True, stdout=PIPE).communicate()[0]
        return float(ret)

if __name__ == '__main__':
    epi = EmbeddedPi()

    v = epi.ReadMR()
    print 'Direction = ' + str(v)

    v = epi.ReadDistance()
    print 'Distance = ' + str(v)

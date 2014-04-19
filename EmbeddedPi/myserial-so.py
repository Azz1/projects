#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
In this module, we create an interface for sending command to EmbeddedPi via UART

author: Jack Zhu
last edited: April 2014
License: LGPL 
"""

from ctypes import cdll,c_int,c_double

class EmbeddedPi:


    def __init__(self):
      lib = "libepi.so"
      self.dll = cdll.LoadLibrary(lib)

    def close(self):
        pass

    def ReadMR(self):
        mf = (lambda : self.dll.ReadMR())
        return mf()

    def ReadDistance(self):
        df = (lambda : self.dll.ReadDistance())
        return df()

if __name__ == '__main__':
    epi = EmbeddedPi()

    v = epi.ReadMR()
    print 'Direction = ' + str(v)

    v = epi.ReadDistance()
    print 'Distance = ' + str(v)
    epi.close()

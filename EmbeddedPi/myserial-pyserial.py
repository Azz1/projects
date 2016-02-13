#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
In this module, we create an interface for sending command to EmbeddedPi via UART

author: Jack Zhu
last edited: April 2014
License: LGPL 
"""

import sys
import time
import serial

def bytestring(n):
    return ''.join([chr((n>>(i*8))&0xFF) for i in range(n.bit_length()/8,-1,-1)])

class CommandInterface:
    def open(self, aport='/dev/ttyAMA0', abaudrate=115200) :
        self.sp = serial.Serial(
            port=aport,
            baudrate=abaudrate,     		# baudrate
            bytesize=serial.EIGHTBITS,          # number of databits
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            xonxoff=0,              		# enable software flow control
            rtscts=0,        # disable RTS/CTS flow control
            timeout=5         # set a timeout value, None for waiting forever
        )
	#print self.sp.getSettingsDict()
        time.sleep(0.5)
        
    def write(self, cmd):
        self.sp.write(chr(cmd))

    def read(self, len):
        return self.sp.read(len)

    def readinto(self, b):
        return self.sp.readinto(b)

    def flush(self):
        return self.sp.flush()

    def close(self):
        return self.sp.close()

    def inWaiting(self):
        return self.sp.inWaiting()

class Command:
    def __init__(self):
        self.header = 0xa5
        self.type = 0x00
        self.id = 0x00
        self.cmd = 0x00
        self.datalength = 0x00
        self.data = [0x00, 0x00, 0x00]
        self.trail = 0x5a

class Result:
    def __init__(self):
        self.retcode = 0
        self.datalength = 0
        self.data = [0x00,0x00,0x00]

class EmbeddedPi:


    def __init__(self):

        conf = {
                'port': '/dev/ttyAMA0',
                'baud': 115200,
                'address': 0x08000000,
                'erase': 0,
                'write': 0,
                'verify': 0,
                'read': 0
            }    

        self.uart = CommandInterface()
        self.uart.open(conf['port'], conf['baud'])
		
    def close(self):
        self.uart.close()

    def TransReceProcess(self, cmd):
        offset = 1

        result = Result()

        self.uart.write(cmd.header)
        sys.stdout.write( 'Send command: ' + "%02x"%(cmd.header) )
        self.uart.write(cmd.type)
        sys.stdout.write( ' ' + "%02x"%(cmd.type) )
        self.uart.write(cmd.id)
        sys.stdout.write( ' ' +  "%02x"%(cmd.id) )
        self.uart.write(cmd.cmd)
        sys.stdout.write( ' ' +  "%02x"%(cmd.cmd) )
        self.uart.write(cmd.datalength)
        sys.stdout.write( ' ' +  "%02x"%(cmd.datalength) )

        for i in range(0, cmd.datalength):
            self.uart.write(cmd.data[i])
            sys.stdout.write( ' ' +  "%02x "%(cmd.data[i]) )
        self.uart.write(cmd.trail)
        print ' ' + "%x"%(cmd.trail)
        self.uart.flush()
	time.sleep(0.05)

	while self.uart.inWaiting() == 0 :
	    time.sleep(0.05)

	len = self.uart.inWaiting()

	tmpBuf = bytearray()
	for i in range(len):
	    tmpBuf.append(0)

        len = self.uart.readinto(tmpBuf)
        #print 'Length=' + str(len)
        #print 'Read [' + "".join("%02x " %b for b in tmpBuf) + ']'
        if(len <= 0):
            result.retcode = -1
    
        else:
            result.datalength = tmpBuf[2+offset]
            data = bytearray()

            for i in range(0, result.datalength):
                data.append(tmpBuf[3+i+offset])
    
            data.append(0x00)
            result.data = data

            if((tmpBuf[0+offset] == 0xc9) or (tmpBuf[1+offset] == 0xa3)) :
                result.retcode = 1

            elif((tmpBuf[0+offset] == 0xb6) or (tmpBuf[1+offset] == 0xdc)) :
                result.retcode = 0

            else:
                result.retcode = -1

        return result


    def Echo(self):
        cmd = Command()
        cmd.type = 0x00
        cmd.id = 0x00
        cmd.cmd = 0x02
        cmd.datalength = 0
        result = self.TransReceProcess(cmd)
        print 'retcode = ' + str(result.retcode)
        print 'length = ' + str(result.datalength)
        print 'data = [' + "".join(map(chr, result.data)) + ']'

    def ReadMR(self):
        cmd = Command()
        cmd.type = 0x40
        cmd.id = 4
        cmd.cmd = 2
        cmd.datalength = 0
        result = self.TransReceProcess(cmd)
        MeasureValue = 0
        for i in (0, result.datalength): 
             MeasureValue += result.data[i] << (8*i)
        print 'retcode = ' + str(result.retcode)
        print 'length = ' + str(result.datalength)
        print 'data = [' + "".join("%02x" % b for b in result.data) + ']'
        print 'value = ' + str(MeasureValue)

    def ReadDistance(self):
        cmd = Command()
        cmd.type = 0x40
        cmd.id = 1
        cmd.cmd = 3
        cmd.datalength = 1
        cmd.data[0] = 0
        result = self.TransReceProcess(cmd)
        MeasureValue = 0
        for i in (0, result.datalength): 
             MeasureValue += result.data[i] << (8*i)
        print 'retcode = ' + str(result.retcode)
        print 'length = ' + str(result.datalength)
        print 'data = [' + "".join("%02x" % b for b in result.data) + ']'
        print 'value = ' + str(MeasureValue)
        
    def TestMotor(self):
        cmd = Command()
        cmd.type = 0x40
        cmd.id = 0
        cmd.cmd = 5
        cmd.datalength = 0
        cmd.data[0] = 0
        result = self.TransReceProcess(cmd)

        cmd.cmd = 6
        cmd.data[0] = 1
        cmd.data.append(bytestring(100))
        cmd.datalength = len(cmd.data)
        result = self.TransReceProcess(cmd)

        cmd.cmd = 7
        cmd.data[0] = 1
        cmd.data[1] = 1
        cmd.data[2] = 1
        cmd.data.append(bytestring(100))
        cmd.datalength = len(cmd.data)
        result = self.TransReceProcess(cmd)
        
        cmd.cmd = 8
        cmd.data[0] = 1
        cmd.datalength = 1
        result = self.TransReceProcess(cmd)

if __name__ == '__main__':
    epi = EmbeddedPi()
    epi.Echo()
    epi.close()


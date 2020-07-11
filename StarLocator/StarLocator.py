#!/usr/bin/python

# Python library for Star Locator and tracking

from dateutil.parser import tz
import datetime
import math


class StarLocator:

    def __init__(self, lat, long):
        self.LAT = lat
        self.LONG = long
        self.from_zone = tz.gettz('UTC')

        self.utcj2000 = datetime.datetime.strptime('2000-01-01 12:00:00', '%Y-%m-%d %H:%M:%S')

        # Tell the datetime object that it's in UTC time zone since 
        # datetime objects are 'naive' by default
        self.utcj2000 = self.utcj2000.replace(tzinfo=self.from_zone)


    # Convert RA,DEC plus LAT, LONG and time to ALT,AZ
    # Input:
    #   ra  - RA in degree
    #   dec - DEC in degree
    #   utcdt - UTC date time
    # Return:
    #   (AZ, ALT) in double in double
    def RaDec2AltAz(self, ra, dec, utcdt):
        utcdt = utcdt.replace(tzinfo=self.from_zone)
        days_dbl = (utcdt - self.utcj2000).total_seconds()/(24*60*60)
        #print "J2000:" + str(self.utcj2000)
        #print "Date:" + str(utcdt)
        #print "Days:" + str(days_dbl)
 	
        ut = (utcdt - utcdt.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds()/(60*60)
        #print("UT:" + str(ut))
        #print("LONG:" + str(self.LONG))
	
        lst = 100.46 + 0.985647 * days_dbl + self.LONG + 15.0*ut
        if lst < 0.0:
            lst += 360
        #print("LST:" + str(lst))

        ha = lst - ra
        if ha < 0.0:
            ha += 360
        #print "HA:" + str(ha)
        #print "DEC:" + str(dec)
	
        sinalt = math.sin(math.radians(dec)) * math.sin(math.radians(self.LAT)) + math.cos(math.radians(dec)) * math.cos(math.radians(self.LAT)) * math.cos(math.radians(ha))
        #print "sin(ALT):" + str(sinalt)
        alt = math.degrees(math.asin(sinalt))

        cosa = (math.sin(math.radians(dec)) - math.sin(math.radians(alt)) * math.sin(math.radians(self.LAT)))/(math.cos(math.radians(alt)) * math.cos(math.radians(self.LAT)))
        a = math.degrees(math.acos(cosa))
        if math.sin(math.radians(ha)) > 0:
            a = 360 -a
        return (a, alt)

    # Convert RA,DEC plus LAT, LONG and time to ALT,AZ
    # Input:
    #   ra  - RA in h:m:s
    #   dec - DEC in degree:m:s
    #   utcdt - UTC date time
    # Return:
    #   (AZ, ALT) in double in double
    def RaDec2AltAz1(self, ra_h, ra_m, ra_s, dec_dg, dec_m, dec_s, utcdt):
        ra = (ra_h + ra_m/60.0 + ra_s/3600.0) * 15.0
        dec = dec_dg + dec_m/60.0 + dec_s/3600.0 
        return self.RaDec2AltAz(ra, dec, utcdt)

# Simple example prints accel/mag data once per second:
if __name__ == '__main__':

    from time import sleep
    #sl = StarLocator(52.5, -1.9166667)
    #print sl.RaDec2AltAz1(16, 41, 42, 36, 28, 0, datetime.datetime(1998,8,10,23,10,0))

    sl = StarLocator(42.27069402, -83.04411196)

    print('Start star tracking ...')
    while True:
        print( sl.RaDec2AltAz1(6, 57, 0, 25, 33, 40, datetime.datetime.utcnow()))
        sleep(1) # Output is fun to watch if this is commented out


#!/usr/bin/python

# Python library for Star Locator and tracking

from datetime import datetime
from dateutil import tz
import math


class StarLocator:

    def __init__(self, lat, long):
	self.LAT = lat
	self.LONG = long
	from_zone = tz.gettz('UTC')

	self.utcj2000 = datetime.strptime('2000-01-01 00:00:00', '%Y-%m-%d %H:%M:%S')

	# Tell the datetime object that it's in UTC time zone since 
	# datetime objects are 'naive' by default
	self.utcj2000 = self.utcj2000.replace(tzinfo=from_zone)


    # Convert RA,DEC plus LAT, LONG and time to ALT,AZ
    # Input:
    #   ra  - RA in degree
    #   dec - DEC in degree
    #   utcdt - UTC date time
    # Return:
    #   (AZ, ALT) in double in double
    def RaDec2AltAz(self, ra, dec, utcdt):
	days_dbl = (utcdt - self.utcj2000)/datetime.timedelta(days=1)
 	ut = utcdt.time().total_seconds()/3600.0
	lst = 100.46 + 0.985647 * days_dbl + self.LONG + 15*ut
	if lst < 0.0:
	    lst += 360
	ha = lst - ra
	if ha < 0.0:
	    ha += 360
	
	sinalt = math.sin(math.radians(dec)) * math.sin(math.radians(self.LAT)) + math.cos(math.radians(self.LAT)) * math.cos(math.radians(ha))
	alt = math.asin(sinalt)

	cosa = (math.sin(math.radians(des)) - math.sin(math.radians(alt)) * math.sin(math.radians(self.LAT)))/(math.cos(math.radians(alt)) * math.cos(math.radians(self.LAT)))
	a = math.acos(cosa)
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
    def RaDec2AltAz(self, ra_h, ra_m, ra_s, dec_dg, dec_m, dec_s, utcdt):
	ra = (ra_h + ra_m/60.0 + ra_s/3600.0) * 15.0
	dec = dec_dg + dec_m/60.0 + dec_s/3600.0 
	return self.RaDec2AltAz(ra, dec, utcdt)

# Simple example prints accel/mag data once per second:
if __name__ == '__main__':

    from time import sleep
    sl = StarLocator(42.27069402, -83.04411196)

    print 'Start star tracking ...'
    while True:
        print sl.RaDec2AltAz(6, 57, 0, 25, 33, 40, datetime.utcnow())
        sleep(1) # Output is fun to watch if this is commented out


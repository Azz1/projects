
#!/usr/bin/python

# Python library for Star Locator and tracking

import math


class StarLocator:

    def __init__(self, lat, long):
	self.LAT = lat
	self.LONG = long

    # Convert RA,DEC plus LAT, LONG and time to ALT,AZ
    # Input:
    #   ra  - RA in degree
    #   dec - DEC in degree
    #   utcdt - UTC date time
    # Return:
    #   (ALT, AZ) in double in double
    def RaDec2AltAz(self, ra, dec, utcdt):
	return (0.0, 0.0)

    # Convert RA,DEC plus LAT, LONG and time to ALT,AZ
    # Input:
    #   ra  - RA in h:m:s
    #   dec - DEC in h:m:s
    #   utcdt - UTC date time
    # Return:
    #   (ALT, AZ) in double in double
    def RaDec2AltAz(self, ra_h, ra_m, ra_s, dec_h, dec_m, dec_s, utcdt):
	ra = (ra_h + ra_m/60.0 + ra_s/3600.0) * 15.0
	dec = (dec_h + dec_m/60.0 + dec_s/3600.0) * 15.0
	return self.RaDec2AltAz(ra, dec, utcdt)

# Simple example prints accel/mag data once per second:
if __name__ == '__main__':

    from time import sleep
    sl = new StarLocator(42.27069402, -83.04411196)

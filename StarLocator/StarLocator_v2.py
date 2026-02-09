#!/usr/bin/python
"""
Star Locator Module - Refactored with Config & Error Handling

Converts celestial coordinates (RA/DEC) to horizontal coordinates (ALT/AZ).
"""

import sys
import os
import math
import logging
from datetime import datetime
from typing import Tuple, Optional
from dataclasses import dataclass

# Add config module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dateutil import tz

from config import get_config, setup_logging, TelescopeConfig
from config.errors import (
    TelescopeError, 
    handle_errors, 
    validate_args,
    ErrorSeverity
)


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class CelestialCoords:
    """Right Ascension and Declination coordinates."""
    ra_hours: float = 0.0
    ra_minutes: float = 0.0
    ra_seconds: float = 0.0
    dec_degrees: float = 0.0
    dec_minutes: float = 0.0
    dec_seconds: float = 0.0
    
    @property
    def ra_decimal(self) -> float:
        """RA in decimal degrees."""
        ra_time = self.ra_hours + self.ra_minutes / 60.0 + self.ra_seconds / 3600.0
        return ra_time * 15.0  # Convert hours to degrees
    
    @property
    def dec_decimal(self) -> float:
        """DEC in decimal degrees."""
        sign = -1 if self.dec_degrees < 0 else 1
        return sign * (abs(self.dec_degrees) + self.dec_minutes / 60.0 + self.dec_seconds / 3600.0)


@dataclass
class HorizontalCoords:
    """Azimuth and Altitude coordinates."""
    azimuth: float = 0.0
    altitude: float = 0.0
    
    def __str__(self) -> str:
        return f"AZ: {self.azimuth:.4f}°, ALT: {self.altitude:.4f}°"


# =============================================================================
# Star Locator Class
# =============================================================================

class StarLocator:
    """
    Converts celestial coordinates to horizontal coordinates.
    
    Uses the standard astronomical transformation from equatorial (RA/DEC)
    to horizontal (ALT/AZ) coordinate systems.
    """
    
    # J2000.0 epoch reference
    J2000_EPOCH = datetime(2000, 1, 1, 12, 0, 0)
    
    # Constants for sidereal time calculation
    SIDEREAL_CONSTANT = 100.46
    SIDEREAL_RATE = 0.985647  # degrees per day
    SIDEREAL_HOUR_RATE = 15.0  # degrees per hour
    
    def __init__(
        self, 
        latitude: Optional[float] = None, 
        longitude: Optional[float] = None,
        config: Optional[TelescopeConfig] = None
    ):
        """
        Initialize StarLocator with observer location.
        
        Args:
            latitude: Observer latitude in degrees (N positive)
            longitude: Observer longitude in degrees (E positive)
            config: Optional TelescopeConfig, loads global if not provided
        """
        self.logger = logging.getLogger('telescope.locator')
        
        # Load config if not provided
        if config is None:
            config = get_config()
        
        # Use provided values or fall back to config
        self.latitude = latitude if latitude is not None else config.location.latitude
        self.longitude = longitude if longitude is not None else config.location.longitude
        
        # Pre-compute latitude trigonometry for efficiency
        self._lat_rad = math.radians(self.latitude)
        self._sin_lat = math.sin(self._lat_rad)
        self._cos_lat = math.cos(self._lat_rad)
        
        # Timezone handling
        self._utc_zone = tz.gettz('UTC')
        self._j2000_utc = self.J2000_EPOCH.replace(tzinfo=self._utc_zone)
        
        self.logger.debug(
            f"StarLocator initialized: lat={self.latitude:.4f}, lon={self.longitude:.4f}"
        )
    
    def _days_since_j2000(self, utc_time: datetime) -> float:
        """Calculate days since J2000.0 epoch."""
        if utc_time.tzinfo is None:
            utc_time = utc_time.replace(tzinfo=self._utc_zone)
        return (utc_time - self._j2000_utc).total_seconds() / 86400.0
    
    def _hours_since_midnight(self, utc_time: datetime) -> float:
        """Calculate hours since midnight UTC."""
        midnight = utc_time.replace(hour=0, minute=0, second=0, microsecond=0)
        return (utc_time - midnight).total_seconds() / 3600.0
    
    def _local_sidereal_time(self, utc_time: datetime) -> float:
        """
        Calculate Local Sidereal Time (LST) in degrees.
        
        LST = 100.46 + 0.985647 * d + longitude + 15 * UT
        where d = days since J2000.0
        """
        days = self._days_since_j2000(utc_time)
        ut_hours = self._hours_since_midnight(utc_time)
        
        lst = (
            self.SIDEREAL_CONSTANT + 
            self.SIDEREAL_RATE * days + 
            self.longitude + 
            self.SIDEREAL_HOUR_RATE * ut_hours
        )
        
        # Normalize to 0-360 degrees
        lst = lst % 360.0
        if lst < 0:
            lst += 360.0
        
        return lst
    
    @handle_errors(severity=ErrorSeverity.ERROR, reraise=True)
    @validate_args(
        ra=lambda x: 0 <= x < 360,
        dec=lambda x: -90 <= x <= 90
    )
    def ra_dec_to_alt_az(
        self, 
        ra: float, 
        dec: float, 
        utc_time: Optional[datetime] = None
    ) -> HorizontalCoords:
        """
        Convert RA/DEC to ALT/AZ coordinates.
        
        Args:
            ra: Right Ascension in degrees (0-360)
            dec: Declination in degrees (-90 to +90)
            utc_time: UTC datetime (uses current time if not provided)
            
        Returns:
            HorizontalCoords with azimuth and altitude
        """
        if utc_time is None:
            utc_time = datetime.utcnow()
        
        if utc_time.tzinfo is None:
            utc_time = utc_time.replace(tzinfo=self._utc_zone)
        
        # Calculate Local Sidereal Time and Hour Angle
        lst = self._local_sidereal_time(utc_time)
        ha = (lst - ra) % 360.0
        
        # Convert to radians for calculation
        ha_rad = math.radians(ha)
        dec_rad = math.radians(dec)
        
        sin_dec = math.sin(dec_rad)
        cos_dec = math.cos(dec_rad)
        cos_ha = math.cos(ha_rad)
        sin_ha = math.sin(ha_rad)
        
        # Calculate altitude
        sin_alt = (
            sin_dec * self._sin_lat + 
            cos_dec * self._cos_lat * cos_ha
        )
        
        # Clamp to valid range to avoid math domain errors
        sin_alt = max(-1.0, min(1.0, sin_alt))
        altitude = math.degrees(math.asin(sin_alt))
        
        # Calculate azimuth
        cos_alt = math.cos(math.radians(altitude))
        
        if abs(cos_alt) < 1e-10:
            # Object at zenith or nadir
            azimuth = 0.0
        else:
            cos_az = (sin_dec - sin_alt * self._sin_lat) / (cos_alt * self._cos_lat)
            # Clamp to valid range
            cos_az = max(-1.0, min(1.0, cos_az))
            azimuth = math.degrees(math.acos(cos_az))
            
            # Correct quadrant based on hour angle
            if sin_ha > 0:
                azimuth = 360.0 - azimuth
        
        self.logger.debug(
            f"RA/DEC ({ra:.2f}, {dec:.2f}) -> ALT/AZ ({altitude:.4f}, {azimuth:.4f})"
        )
        
        return HorizontalCoords(azimuth=azimuth, altitude=altitude)
    
    def celestial_to_horizontal(
        self, 
        coords: CelestialCoords, 
        utc_time: Optional[datetime] = None
    ) -> HorizontalCoords:
        """
        Convert CelestialCoords to HorizontalCoords.
        
        Args:
            coords: CelestialCoords object with RA/DEC
            utc_time: UTC datetime (uses current time if not provided)
            
        Returns:
            HorizontalCoords with azimuth and altitude
        """
        return self.ra_dec_to_alt_az(
            coords.ra_decimal, 
            coords.dec_decimal, 
            utc_time
        )
    
    def ra_dec_hms_to_alt_az(
        self,
        ra_h: float, ra_m: float, ra_s: float,
        dec_d: float, dec_m: float, dec_s: float,
        utc_time: Optional[datetime] = None
    ) -> HorizontalCoords:
        """
        Convert RA/DEC in sexagesimal format to ALT/AZ.
        
        Args:
            ra_h, ra_m, ra_s: Right Ascension (hours, minutes, seconds)
            dec_d, dec_m, dec_s: Declination (degrees, arcmin, arcsec)
            utc_time: UTC datetime
            
        Returns:
            HorizontalCoords with azimuth and altitude
        """
        coords = CelestialCoords(
            ra_hours=ra_h, ra_minutes=ra_m, ra_seconds=ra_s,
            dec_degrees=dec_d, dec_minutes=dec_m, dec_seconds=dec_s
        )
        return self.celestial_to_horizontal(coords, utc_time)
    
    # Legacy method name for backward compatibility
    def RaDec2AltAz(self, ra: float, dec: float, utcdt: datetime) -> Tuple[float, float]:
        """Legacy interface - returns (AZ, ALT) tuple."""
        result = self.ra_dec_to_alt_az(ra, dec, utcdt)
        return (result.azimuth, result.altitude)
    
    def RaDec2AltAz1(
        self, 
        ra_h: float, ra_m: float, ra_s: float,
        dec_dg: float, dec_m: float, dec_s: float,
        utcdt: datetime
    ) -> Tuple[float, float]:
        """Legacy interface - returns (AZ, ALT) tuple."""
        result = self.ra_dec_hms_to_alt_az(ra_h, ra_m, ra_s, dec_dg, dec_m, dec_s, utcdt)
        return (result.azimuth, result.altitude)


# =============================================================================
# Main / Demo
# =============================================================================

if __name__ == '__main__':
    from time import sleep
    
    # Setup logging
    setup_logging()
    logger = logging.getLogger('telescope')
    
    # Load config
    config = get_config()
    
    # Create locator with config
    locator = StarLocator(config=config)
    
    # Example: Track Betelgeuse (Alpha Orionis)
    # RA: 05h 55m 10s, DEC: +07° 24′ 25″
    betelgeuse = CelestialCoords(
        ra_hours=5, ra_minutes=55, ra_seconds=10,
        dec_degrees=7, dec_minutes=24, dec_seconds=25
    )
    
    logger.info(f"Tracking Betelgeuse from ({config.location.latitude}, {config.location.longitude})")
    logger.info("Press Ctrl+C to stop")
    
    try:
        while True:
            result = locator.celestial_to_horizontal(betelgeuse)
            logger.info(f"Betelgeuse: {result}")
            sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopped tracking")

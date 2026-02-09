#!/usr/bin/python
"""
Star Tracking Module - Refactored with Config & Error Handling

Provides star tracking functionality for both ALT-AZ and Equatorial mounts.
"""

import sys
import os
import time
import math
import logging
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Tuple, Optional, Deque, List, Callable
from collections import deque
from datetime import datetime
from enum import Enum

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import get_config, TelescopeConfig
from config.errors import (
    TelescopeError,
    TrackingError,
    TrackingLostError,
    MotorError,
    SensorError,
    handle_errors,
    retry_on_error,
    ErrorSeverity,
    get_error_handler
)

# Try to import hardware modules (may fail on non-Pi systems)
try:
    import RPi.GPIO as GPIO
    HAS_GPIO = True
except ImportError:
    HAS_GPIO = False
    GPIO = None


# =============================================================================
# Enums and Constants
# =============================================================================

class MountMode(Enum):
    """Telescope mount type."""
    ALTAZ = "ALTAZ"      # Altitude-Azimuth mount
    EQUATORIAL = "RADEC"  # Equatorial mount (RA/DEC)


class Direction(Enum):
    """Motor movement directions."""
    UP = "UP"
    DOWN = "DOWN"
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    FORWARD = "FORWARD"
    BACKWARD = "BACKWARD"


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class TrackingPoint:
    """Single tracking measurement point."""
    timestamp: datetime
    delta_ra: float = 0.0
    delta_dec: float = 0.0
    ref_x: float = 0.0
    ref_y: float = 0.0


@dataclass
class MotorCommand:
    """Command for motor controller."""
    direction: str
    speed: int
    adjustment: int
    steps: int


@dataclass
class Position:
    """Current telescope position."""
    azimuth: float = 0.0
    altitude: float = 0.0
    ra_offset: float = 0.0
    dec_offset: float = 0.0


@dataclass
class Target:
    """Target coordinates."""
    # For ALTAZ mode
    azimuth: float = 0.0
    altitude: float = 0.0
    
    # For RADEC mode
    ra_hours: float = 0.0
    ra_minutes: float = 0.0
    ra_seconds: float = 0.0
    dec_degrees: float = 0.0
    dec_minutes: float = 0.0
    dec_seconds: float = 0.0
    
    # Adjustments
    az_adjustment: float = 0.0
    alt_adjustment: float = 0.0


@dataclass
class TrackingState:
    """Thread-safe tracking state container."""
    is_tracking: threading.Event = field(default_factory=threading.Event)
    is_processing: threading.Event = field(default_factory=threading.Event)
    exit_flag: threading.Event = field(default_factory=threading.Event)
    lock: threading.Lock = field(default_factory=threading.Lock)
    
    # Tracking history
    history: Deque[TrackingPoint] = field(default_factory=lambda: deque(maxlen=20))
    
    # Reference points
    ref0_x: float = 0.0
    ref0_y: float = 0.0
    ref1_x: float = 0.0
    ref1_y: float = 0.0
    
    # Current state
    current: Position = field(default_factory=Position)
    target: Target = field(default_factory=Target)
    mode: MountMode = MountMode.ALTAZ
    
    # EQ mount settings
    positive_direction: str = "UP"
    negative_direction: str = "DOWN"
    
    def __post_init__(self):
        self.exit_flag.set()  # Allow running by default
        self.is_tracking.clear()
        self.is_processing.clear()


# =============================================================================
# Abstract Tracking Interface
# =============================================================================

class ITracking(ABC):
    """Abstract base class for tracking implementations."""
    
    @abstractmethod
    def track(self) -> None:
        """Execute one tracking cycle."""
        pass
    
    @abstractmethod
    def start(self) -> None:
        """Start tracking loop."""
        pass
    
    @abstractmethod
    def stop(self) -> None:
        """Stop tracking."""
        pass


# =============================================================================
# Motor Controller Interface
# =============================================================================

class MotorController:
    """Interface for motor control with error handling."""
    
    def __init__(
        self,
        name: str,
        command_queue: 'queue.Queue',
        config: TelescopeConfig,
        state: TrackingState
    ):
        self.logger = logging.getLogger(f'telescope.motor.{name}')
        self.name = name
        self.queue = command_queue
        self.config = config
        self.state = state
        
        # Get motor config based on name
        if name == "vertical":
            self.motor_config = config.motors.vertical
        elif name == "horizontal":
            self.motor_config = config.motors.horizontal
        else:
            self.motor_config = config.motors.focus
    
    @handle_errors(severity=ErrorSeverity.WARNING)
    def send_command(self, command: MotorCommand) -> bool:
        """Send command to motor queue."""
        with self.state.lock:
            self.queue.put((
                command.direction,
                command.speed,
                command.adjustment,
                command.steps
            ))
        self.logger.debug(
            f"Command sent: {command.direction} speed={command.speed} "
            f"steps={command.steps}"
        )
        return True
    
    def move(
        self,
        direction: str,
        speed: Optional[int] = None,
        steps: Optional[int] = None,
        adjustment: Optional[int] = None
    ) -> bool:
        """Convenience method for motor movement."""
        cmd = MotorCommand(
            direction=direction,
            speed=speed or self.motor_config.speed,
            steps=steps or self.motor_config.steps,
            adjustment=adjustment or self.motor_config.adjustment
        )
        return self.send_command(cmd)


# =============================================================================
# Weighted Average Calculator
# =============================================================================

class WeightedAverageCalculator:
    """Calculate weighted averages from tracking history."""
    
    def __init__(self, reference_count: int = 3):
        self.reference_count = reference_count
    
    def calculate(
        self,
        history: Deque[TrackingPoint],
        extractor: Callable[[TrackingPoint], float]
    ) -> float:
        """
        Calculate weighted average from tracking history.
        
        Args:
            history: Tracking point history
            extractor: Function to extract value from TrackingPoint
            
        Returns:
            Weighted average value
        """
        if not history:
            return 0.0
        
        total = 0.0
        weight_sum = 0.0
        count = 0
        
        # Iterate from most recent to oldest
        for i in range(len(history) - 1, -1, -1):
            if count >= self.reference_count:
                break
            
            weight = self.reference_count - count
            value = extractor(history[i])
            total += value * weight
            weight_sum += weight
            count += 1
        
        return total / weight_sum if weight_sum > 0 else 0.0


# =============================================================================
# Equatorial Tracking Implementation
# =============================================================================

class EquatorialTracking(ITracking):
    """
    Equatorial mount star tracking.
    
    Tracks objects by compensating for Earth's rotation using RA motor
    and correcting for drift in both RA and DEC.
    """
    
    def __init__(
        self,
        h_motor: MotorController,
        v_motor: MotorController,
        state: TrackingState,
        config: Optional[TelescopeConfig] = None
    ):
        self.logger = logging.getLogger('telescope.tracking.eq')
        self.config = config or get_config()
        self.state = state
        self.h_motor = h_motor
        self.v_motor = v_motor
        
        # Load tracking config
        self.threshold = self.config.tracking.threshold_limit
        self.trace_count = self.config.tracking.trace_reference_count
        self.ra_multiplier = self.config.tracking.ra_speed_multiplier
        self.ra_divisor = self.config.tracking.ra_speed_divisor
        self.default_sleep = self.config.tracking.default_ra_sleep
        
        self.calculator = WeightedAverageCalculator(self.trace_count)
        self.error_handler = get_error_handler()
        
        self._running = False
    
    def _calculate_averages(self) -> Tuple[float, float, float, float]:
        """Calculate weighted averages for RA, DEC, X, and Y offsets."""
        history = self.state.history
        
        avg_ra = self.calculator.calculate(history, lambda p: p.delta_ra)
        avg_dec = self.calculator.calculate(history, lambda p: p.delta_dec)
        avg_x = self.calculator.calculate(
            history, 
            lambda p: p.ref_x - self.state.ref0_x
        )
        avg_y = self.calculator.calculate(
            history,
            lambda p: p.ref_y - self.state.ref0_y
        )
        
        return avg_ra, avg_dec, avg_x, avg_y
    
    @handle_errors(severity=ErrorSeverity.ERROR)
    def track(self) -> None:
        """Execute one EQ tracking correction cycle."""
        avg_ra, avg_dec, avg_x, avg_y = self._calculate_averages()
        
        # DEC correction
        v_dir = ""
        if avg_dec > self.threshold:
            v_dir = self.state.positive_direction
        elif avg_dec < -self.threshold:
            v_dir = self.state.negative_direction
        
        vsteps = abs(int(avg_dec / 3))
        vsleep = min(vsteps, 5)
        
        # RA correction
        h_dir = ""
        hsteps = 0
        new_h_speed = self.h_motor.motor_config.speed
        
        if avg_ra > self.threshold:
            h_dir = "LEFT"
            new_h_speed = int(self.h_motor.motor_config.speed * self.ra_multiplier)
            hsteps = abs(int(avg_ra / 1.5))
        elif avg_ra < -self.threshold:
            h_dir = "LEFT"
            new_h_speed = int(self.h_motor.motor_config.speed / self.ra_divisor)
            hsteps = 1
        
        # Execute DEC correction
        if v_dir:
            self.logger.info(f"DEC correction: {v_dir} {vsteps} steps")
            self.v_motor.move(
                direction=v_dir,
                steps=vsteps
            )
            time.sleep(vsleep)
        
        # Execute RA correction
        if h_dir and new_h_speed > 0:
            self.logger.info(f"RA correction: {h_dir} {hsteps} steps @ {new_h_speed}")
            self.h_motor.move(
                direction=h_dir,
                speed=new_h_speed,
                steps=hsteps
            )
            
            hsleep = int(math.ceil(hsteps / 5))
            hsleep = max(5, min(hsleep, 20))
            self.logger.debug(f"RA action time: {hsleep}s")
            time.sleep(hsleep)
        
        # Default sidereal tracking motion
        self.logger.debug("Sidereal tracking motion")
        self.h_motor.move(
            direction="LEFT",
            steps=8000
        )
        time.sleep(self.default_sleep)
        
        self.state.is_processing.clear()
    
    def start(self) -> None:
        """Start tracking (called from external trigger)."""
        self.logger.info("EQ tracking started")
        self._running = True
        self.track()
    
    def stop(self) -> None:
        """Stop tracking."""
        self.logger.info("EQ tracking stopped")
        self._running = False


# =============================================================================
# ALT-AZ Tracking Implementation
# =============================================================================

class AltAzTracking(ITracking):
    """
    Altitude-Azimuth mount star tracking with accelerometer feedback.
    
    Uses LSM303 magnetometer/accelerometer for position feedback
    and corrects telescope position to track celestial objects.
    """
    
    def __init__(
        self,
        h_motor: MotorController,
        v_motor: MotorController,
        state: TrackingState,
        locator: 'StarLocator',
        position_sensor: Optional['Adafruit_LSM303'] = None,
        config: Optional[TelescopeConfig] = None
    ):
        self.logger = logging.getLogger('telescope.tracking.altaz')
        self.config = config or get_config()
        self.state = state
        self.h_motor = h_motor
        self.v_motor = v_motor
        self.locator = locator
        self.position_sensor = position_sensor
        
        # Load config
        self.min_v_offset = self.config.tracking.min_vertical_offset
        self.min_h_offset = self.config.tracking.min_horizontal_offset
        self.max_v_steps = self.config.tracking.max_vertical_steps
        self.max_h_steps = self.config.tracking.max_horizontal_steps
        self.min_v_steps = self.config.tracking.min_vertical_steps
        self.min_h_steps = self.config.tracking.min_horizontal_steps
        self.interval = self.config.tracking.tracking_interval
        
        # Magnetometer config
        self.samples = self.config.magnetometer.samples_per_read
        self.sample_interval = self.config.magnetometer.sample_interval
        
        self.error_handler = get_error_handler()
        self._running = False
    
    def _get_target_position(self) -> Tuple[float, float]:
        """Get target AZ/ALT position."""
        target = self.state.target
        
        if self.state.mode == MountMode.ALTAZ:
            return (target.azimuth, target.altitude)
        else:
            # Convert RA/DEC to ALT/AZ
            return self.locator.RaDec2AltAz1(
                target.ra_hours, target.ra_minutes, target.ra_seconds,
                target.dec_degrees, target.dec_minutes, target.dec_seconds,
                datetime.utcnow()
            )
    
    @retry_on_error(max_retries=3, delay=0.5, error_types=(SensorError,))
    def _read_position(self) -> Tuple[float, float]:
        """
        Read current position from magnetometer with outlier rejection.
        
        Takes multiple samples and removes min/max outliers.
        """
        if self.position_sensor is None:
            raise SensorError("Position sensor not initialized")
        
        alt_samples = []
        az_samples = []
        
        for _ in range(self.samples):
            try:
                alt, _, _, az = self.position_sensor.read()
                alt_samples.append(alt)
                az_samples.append(az)
                time.sleep(self.sample_interval)
            except Exception as e:
                self.logger.warning(f"Sensor read failed: {e}")
        
        if len(alt_samples) < 3:
            raise SensorError("Insufficient sensor readings")
        
        # Remove outliers (min and max)
        def filtered_average(samples: List[float]) -> float:
            if len(samples) <= 2:
                return sum(samples) / len(samples)
            
            sorted_samples = sorted(samples)
            # Remove one min and one max
            filtered = sorted_samples[1:-1]
            return sum(filtered) / len(filtered)
        
        return filtered_average(alt_samples), filtered_average(az_samples)
    
    def _normalize_offset(self, offset: float) -> float:
        """Normalize angular offset to -180 to +180 range."""
        if offset > 180:
            return offset - 360
        elif offset < -180:
            return 360 + offset
        return offset
    
    @handle_errors(severity=ErrorSeverity.ERROR)
    def track(self) -> None:
        """Execute one ALT-AZ tracking correction cycle."""
        # Get target
        target_az, target_alt = self._get_target_position()
        self.logger.debug(f"Target: AZ={target_az:.4f}, ALT={target_alt:.4f}")
        
        # Read current position
        try:
            pos_alt, pos_az = self._read_position()
        except SensorError as e:
            self.logger.error(f"Cannot read position: {e}")
            return
        
        # Apply adjustments
        current_az = pos_az + self.state.target.az_adjustment
        current_alt = pos_alt + self.state.target.alt_adjustment
        
        self.logger.debug(f"Current: AZ={current_az:.4f}, ALT={current_alt:.4f}")
        
        # Update state
        with self.state.lock:
            self.state.current.azimuth = current_az
            self.state.current.altitude = current_alt
        
        # Calculate offsets
        v_offset = current_alt - target_alt
        h_offset = self._normalize_offset(current_az - target_az)
        
        # Check if correction needed
        if abs(v_offset) < self.min_v_offset and abs(h_offset) < self.min_h_offset:
            self.logger.debug("Within tolerance, no correction needed")
            return
        
        # Calculate step sizes
        v_steps = self.min_v_steps if abs(v_offset) < 1 else self.max_v_steps
        h_steps = self.min_h_steps if abs(h_offset) < 1 else self.max_h_steps
        
        # Determine directions
        v_dir = "DOWN" if v_offset > 0 else "UP"
        h_dir = "LEFT" if h_offset > 0 else "RIGHT"
        
        # Execute corrections
        if abs(v_offset) >= self.min_v_offset:
            self.logger.info(f"ALT correction: {v_dir} {v_steps} steps")
            self.v_motor.move(direction=v_dir, steps=v_steps)
        
        if abs(h_offset) >= self.min_h_offset:
            self.logger.info(f"AZ correction: {h_dir} {h_steps} steps")
            self.h_motor.move(direction=h_dir, steps=h_steps)
    
    def start(self) -> None:
        """Start continuous tracking loop."""
        self.logger.info("ALT-AZ tracking started")
        self._running = True
        
        try:
            while self._running and self.state.is_tracking.is_set():
                self.track()
                time.sleep(self.interval)
        except KeyboardInterrupt:
            self.logger.info("Tracking interrupted by user")
        finally:
            self.stop()
    
    def stop(self) -> None:
        """Stop tracking."""
        self.logger.info("ALT-AZ tracking stopped")
        self._running = False
        self.state.is_tracking.clear()


# =============================================================================
# Tracking Manager
# =============================================================================

class TrackingManager:
    """
    High-level tracking manager.
    
    Coordinates tracking mode selection, motor control, and state management.
    """
    
    def __init__(self, config: Optional[TelescopeConfig] = None):
        self.logger = logging.getLogger('telescope.tracking')
        self.config = config or get_config()
        self.state = TrackingState()
        
        # Motor command queues
        import queue
        self.h_queue = queue.Queue()
        self.v_queue = queue.Queue()
        
        # Motor controllers
        self.h_motor = MotorController("horizontal", self.h_queue, self.config, self.state)
        self.v_motor = MotorController("vertical", self.v_queue, self.config, self.state)
        
        # Tracking implementations (lazy init)
        self._eq_tracker: Optional[EquatorialTracking] = None
        self._altaz_tracker: Optional[AltAzTracking] = None
        self._tracking_thread: Optional[threading.Thread] = None
    
    @property
    def eq_tracker(self) -> EquatorialTracking:
        """Get or create EQ tracker."""
        if self._eq_tracker is None:
            self._eq_tracker = EquatorialTracking(
                self.h_motor, self.v_motor, self.state, self.config
            )
        return self._eq_tracker
    
    def create_altaz_tracker(
        self,
        locator: 'StarLocator',
        position_sensor: Optional['Adafruit_LSM303'] = None
    ) -> AltAzTracking:
        """Create ALT-AZ tracker with dependencies."""
        self._altaz_tracker = AltAzTracking(
            self.h_motor, self.v_motor, self.state,
            locator, position_sensor, self.config
        )
        return self._altaz_tracker
    
    def set_target(
        self,
        mode: MountMode,
        az: float = 0, alt: float = 0,
        ra_h: float = 0, ra_m: float = 0, ra_s: float = 0,
        dec_d: float = 0, dec_m: float = 0, dec_s: float = 0,
        az_adj: float = 0, alt_adj: float = 0
    ) -> None:
        """Set tracking target."""
        self.state.mode = mode
        self.state.target = Target(
            azimuth=az, altitude=alt,
            ra_hours=ra_h, ra_minutes=ra_m, ra_seconds=ra_s,
            dec_degrees=dec_d, dec_minutes=dec_m, dec_seconds=dec_s,
            az_adjustment=az_adj, alt_adjustment=alt_adj
        )
        self.logger.info(f"Target set: mode={mode.value}")
    
    def add_tracking_point(self, point: TrackingPoint) -> None:
        """Add a tracking measurement point."""
        self.state.history.append(point)
    
    def start_tracking(self, threaded: bool = True) -> None:
        """Start tracking based on current mode."""
        self.state.is_tracking.set()
        
        if self.state.mode == MountMode.EQUATORIAL:
            tracker = self.eq_tracker
        elif self._altaz_tracker:
            tracker = self._altaz_tracker
        else:
            raise TrackingError("No tracker configured for current mode")
        
        if threaded:
            self._tracking_thread = threading.Thread(
                target=tracker.start,
                daemon=True
            )
            self._tracking_thread.start()
        else:
            tracker.start()
    
    def stop_tracking(self) -> None:
        """Stop tracking."""
        self.state.is_tracking.clear()
        if self._eq_tracker:
            self._eq_tracker.stop()
        if self._altaz_tracker:
            self._altaz_tracker.stop()
        
        if self._tracking_thread and self._tracking_thread.is_alive():
            self._tracking_thread.join(timeout=5)
    
    def trigger_eq_correction(self) -> None:
        """Trigger a single EQ tracking correction (called from refresh)."""
        if not self.state.is_tracking.is_set():
            return
        
        if self.state.is_processing.is_set():
            return  # Already processing
        
        self.state.is_processing.set()
        
        # Run in thread
        t = threading.Thread(target=self.eq_tracker.track, daemon=True)
        t.start()
    
    @property
    def is_tracking(self) -> bool:
        """Check if tracking is active."""
        return self.state.is_tracking.is_set()
    
    def update_adjustments(self) -> Tuple[float, float]:
        """Update and return new adjustments based on current error."""
        target = self.state.target
        current = self.state.current
        
        new_az_adj = target.azimuth - current.azimuth + target.az_adjustment
        new_alt_adj = target.altitude - current.altitude + target.alt_adjustment
        
        target.az_adjustment = new_az_adj
        target.alt_adjustment = new_alt_adj
        
        return (new_az_adj, new_alt_adj)


# =============================================================================
# Main / Demo
# =============================================================================

if __name__ == '__main__':
    from config import setup_logging
    
    # Setup
    setup_logging()
    logger = logging.getLogger('telescope')
    config = get_config()
    
    # Create manager
    manager = TrackingManager(config)
    
    # Set target (example: Polaris in ALTAZ mode)
    manager.set_target(
        mode=MountMode.ALTAZ,
        az=0.0,
        alt=42.0  # Approximate altitude for latitude ~42°
    )
    
    logger.info("Tracking manager initialized")
    logger.info(f"Mode: {manager.state.mode.value}")
    logger.info(f"Target: AZ={manager.state.target.azimuth}, ALT={manager.state.target.altitude}")
    
    # Note: Actual tracking requires hardware (motors, sensors)
    # This is just a demonstration of the refactored structure
    print("\nTracking system ready. Hardware required for actual operation.")

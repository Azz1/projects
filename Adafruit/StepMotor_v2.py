#!/usr/bin/python
"""
Stepper Motor Control Module - Refactored with Config System

Provides motor control and shared state management for telescope.
Maintains backward compatibility with legacy ControlPackage interface.
"""

import sys
import os
import time
import math
import logging
import threading
import queue
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Tuple, Deque
from collections import deque
from enum import Enum

# Add project path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import get_config, TelescopeConfig
from config.errors import (
    TelescopeError,
    MotorError,
    MotorLimitError,
    ConfigurationError,
    handle_errors,
    retry_on_error,
    ErrorSeverity
)

# Try to import hardware modules
try:
    import RPi.GPIO as GPIO
    HAS_GPIO = True
except ImportError:
    HAS_GPIO = False
    GPIO = None

try:
    import serial
    HAS_SERIAL = True
except ImportError:
    HAS_SERIAL = False
    serial = None


# =============================================================================
# Enums
# =============================================================================

class MotorDirection(Enum):
    """Motor movement directions."""
    UP = "UP"
    DOWN = "DOWN"
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    IN = "IN"
    OUT = "OUT"
    FORWARD = "FORWARD"
    BACKWARD = "BACKWARD"


class MotorStyle(Enum):
    """Motor stepping style."""
    SINGLE = "SINGLE"
    DOUBLE = "DOUBLE"
    MICROSTEP = "MICROSTEP"
    INTERLEAVE = "INTERLEAVE"


class MotorType(Enum):
    """Motor type identifier."""
    VERTICAL = "V-Motor"
    HORIZONTAL = "H-Motor"
    FOCUS = "F-Motor"


# =============================================================================
# Abstract Motor Base Class
# =============================================================================

class StepMotor(ABC):
    """
    Abstract base class for stepper motors.
    
    Defines the interface that all motor implementations must follow.
    """
    
    def __init__(self, config: TelescopeConfig):
        self.config = config
        self.logger = logging.getLogger('telescope.motor')
    
    @abstractmethod
    def step(self, steps: int, direction: str, style: str) -> None:
        """Execute motor steps."""
        pass
    
    @abstractmethod
    def set_sensor(self, forward_pin: int, backward_pin: int) -> None:
        """Set limit sensor pins."""
        pass
    
    @abstractmethod
    def set_port(self, port: str) -> None:
        """Set motor port identifier."""
        pass
    
    @abstractmethod
    def set_speed(self, rpm: int, adjustment: int = 0) -> None:
        """Set motor speed."""
        pass
    
    @abstractmethod
    def release(self) -> None:
        """Release motor (disable holding torque)."""
        pass


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class MotorCommand:
    """Command for motor execution."""
    direction: str
    speed: int
    adjustment: int
    steps: int


@dataclass
class TrackingPoint:
    """Single tracking measurement."""
    timestamp: time.struct_time
    delta_ra: float
    delta_dec: float


@dataclass
class CameraSettings:
    """Camera configuration state."""
    width: int = 700
    height: int = 524
    roi_left: float = 0.0
    brightness: int = 10
    sharpness: int = 20
    contrast: int = 20
    saturation: int = 100
    shutter_speed: int = 4000  # microseconds
    iso: int = 400
    video_length: int = 20
    timelapse_count: int = 1
    horizontal_flip: bool = True
    vertical_flip: bool = True
    color_mode: str = "day"
    raw_mode: bool = False
    
    # Sequence counters
    image_seq: int = 0
    snapshot_seq: int = 0
    video_seq: int = 0
    
    # Storage limits
    max_keep_snapshots: int = 100
    max_keep_videoshots: int = 5


@dataclass
class MotorSettings:
    """Motor configuration state."""
    speed: int
    steps: int
    adjustment: int


@dataclass  
class TrackingSettings:
    """Tracking configuration state."""
    # Current position
    current_az: float = 0.0
    current_alt: float = 0.0
    
    # Target position
    target_az: float = 0.0
    target_alt: float = 0.0
    target_ra_h: float = 0.0
    target_ra_m: float = 0.0
    target_ra_s: float = 0.0
    target_dec_d: float = 0.0
    target_dec_m: float = 0.0
    target_dec_s: float = 0.0
    
    # Location
    latitude: float = 42.27
    longitude: float = -83.04
    
    # Adjustments
    az_adjustment: float = 0.0
    alt_adjustment: float = 0.0
    
    # Reference points
    ref0_x: float = 0.0
    ref0_y: float = 0.0
    ref1_x: float = 0.0
    ref1_y: float = 0.0
    delta_ra: float = 0.0
    delta_dec: float = 0.0
    
    # Processing params
    blur_limit: int = 13
    thresh_limit: int = 45
    positive_direction: str = "UP"
    negative_direction: str = "DOWN"
    
    # Mode
    mode: str = "ALTAZ"  # ALTAZ or RADEC


# =============================================================================
# Control Package - Refactored
# =============================================================================

class ControlPackageV2:
    """
    Central control state manager for telescope.
    
    Replaces the old class-variable based ControlPackage with
    instance-based state management using configuration files.
    
    Features:
    - Configuration-driven initialization
    - Thread-safe state access
    - Proper resource cleanup
    - Backward-compatible property interface
    """
    
    _instance: Optional['ControlPackageV2'] = None
    _lock = threading.Lock()
    
    def __new__(cls, config: Optional[TelescopeConfig] = None):
        """Singleton pattern for global state."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance
    
    def __init__(self, config: Optional[TelescopeConfig] = None):
        """Initialize control package."""
        if self._initialized:
            return
        
        self.logger = logging.getLogger('telescope.control')
        self.config = config or get_config()
        
        # Threading primitives
        self.exit_flag = threading.Event()
        self.is_tracking = threading.Event()
        self.in_progress_tracking = threading.Event()
        self.thread_lock = threading.Lock()
        
        # Command queues
        self.v_cmdqueue: queue.Queue[MotorCommand] = queue.Queue()
        self.h_cmdqueue: queue.Queue[MotorCommand] = queue.Queue()
        self.f_cmdqueue: queue.Queue[MotorCommand] = queue.Queue()
        
        # Tracking queue
        self.tk_queue: Deque[TrackingPoint] = deque(maxlen=20)
        self.ref_pattern: list = []
        
        # Initialize state from config
        self._init_gpio()
        self._init_serial()
        self._init_camera_settings()
        self._init_motor_settings()
        self._init_tracking_settings()
        
        # Motor threads (lazy init)
        self._motor_v: Optional['MotorControlThreadV2'] = None
        self._motor_h: Optional['MotorControlThreadV2'] = None
        self._motor_f: Optional['MotorControlThreadV2'] = None
        
        # Camera reference (set externally)
        self.camera = None
        
        # Network
        self.ip = ""
        self.camera_only = False
        
        # Move method
        self.move_method = self.config.motors.movement.method
        
        self._initialized = True
        self.logger.info("ControlPackage initialized from config")
    
    def _init_gpio(self) -> None:
        """Initialize GPIO pins."""
        if not HAS_GPIO:
            self.logger.warning("GPIO not available, running in simulation mode")
            return
        
        limits = self.config.motors.limit_switches
        
        # Store pin numbers
        self.VL_pin = limits.vertical_low
        self.VH_pin = limits.vertical_high
        self.HL_pin = limits.horizontal_left
        self.HR_pin = limits.horizontal_right
        
        # Setup GPIO
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        
        for pin in [self.VL_pin, self.VH_pin, self.HL_pin, self.HR_pin]:
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        
        self.logger.debug("GPIO initialized")
    
    def _init_serial(self) -> None:
        """Initialize serial connection."""
        if not HAS_SERIAL:
            self.logger.warning("Serial not available")
            self.serial_data = None
            return
        
        try:
            self.serial_data = serial.Serial(
                port=self.config.serial.port,
                baudrate=self.config.serial.baudrate,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS,
                timeout=self.config.serial.timeout
            )
            self.logger.debug(f"Serial connected on {self.config.serial.port}")
        except serial.SerialException as e:
            self.logger.warning(f"Serial connection failed: {e}")
            self.serial_data = None
    
    def _init_camera_settings(self) -> None:
        """Initialize camera settings from config."""
        cam_cfg = self.config.camera
        
        self.camera_settings = CameraSettings(
            width=cam_cfg.resolution.width,
            height=cam_cfg.resolution.height,
            roi_left=cam_cfg.roi_left,
            brightness=cam_cfg.defaults.brightness,
            sharpness=cam_cfg.defaults.sharpness,
            contrast=cam_cfg.defaults.contrast,
            saturation=cam_cfg.defaults.saturation,
            shutter_speed=cam_cfg.defaults.shutter_speed,
            iso=cam_cfg.defaults.iso,
            video_length=cam_cfg.video_length,
            timelapse_count=cam_cfg.timelapse_count,
            horizontal_flip=cam_cfg.horizontal_flip,
            vertical_flip=cam_cfg.vertical_flip,
            color_mode=cam_cfg.color_mode,
            raw_mode=cam_cfg.raw_mode,
            max_keep_snapshots=cam_cfg.max_keep_snapshots,
            max_keep_videoshots=cam_cfg.max_keep_videoshots
        )
    
    def _init_motor_settings(self) -> None:
        """Initialize motor settings from config."""
        self.v_settings = MotorSettings(
            speed=self.config.motors.vertical.speed,
            steps=self.config.motors.vertical.steps,
            adjustment=self.config.motors.vertical.adjustment
        )
        
        self.h_settings = MotorSettings(
            speed=self.config.motors.horizontal.speed,
            steps=self.config.motors.horizontal.steps,
            adjustment=self.config.motors.horizontal.adjustment
        )
        
        self.f_settings = MotorSettings(
            speed=self.config.motors.focus.speed,
            steps=self.config.motors.focus.steps,
            adjustment=self.config.motors.focus.adjustment
        )
    
    def _init_tracking_settings(self) -> None:
        """Initialize tracking settings from config."""
        self.tracking = TrackingSettings(
            latitude=self.config.location.latitude,
            longitude=self.config.location.longitude,
            blur_limit=self.config.tracking.blur_limit,
            thresh_limit=self.config.tracking.thresh_limit,
            positive_direction=self.config.tracking.eq_mode.positive_direction,
            negative_direction=self.config.tracking.eq_mode.negative_direction
        )
    
    # =========================================================================
    # Motor Management
    # =========================================================================
    
    def start_motors(self) -> None:
        """Start motor control threads."""
        self.exit_flag.set()
        
        self._motor_v = MotorControlThreadV2(MotorType.VERTICAL, self)
        self._motor_h = MotorControlThreadV2(MotorType.HORIZONTAL, self)
        self._motor_f = MotorControlThreadV2(MotorType.FOCUS, self)
        
        self._motor_v.daemon = True
        self._motor_h.daemon = True
        self._motor_f.daemon = True
        
        self._motor_v.start()
        self._motor_h.start()
        self._motor_f.start()
        
        self.logger.info("Motor threads started")
    
    def stop_motors(self) -> None:
        """Stop motor control threads."""
        self.exit_flag.clear()
        self.logger.info("Motor threads stopping")
    
    @property
    def motorV(self) -> Optional['MotorControlThreadV2']:
        """Get vertical motor thread."""
        return self._motor_v
    
    @property
    def motorH(self) -> Optional['MotorControlThreadV2']:
        """Get horizontal motor thread."""
        return self._motor_h
    
    @property
    def motorF(self) -> Optional['MotorControlThreadV2']:
        """Get focus motor thread."""
        return self._motor_f
    
    # =========================================================================
    # Backward-Compatible Properties (Legacy Interface)
    # =========================================================================
    
    # Camera settings aliases
    @property
    def width(self) -> int:
        return self.camera_settings.width
    
    @property
    def height(self) -> int:
        return self.camera_settings.height
    
    @property
    def brightness(self) -> int:
        return self.camera_settings.brightness
    
    @brightness.setter
    def brightness(self, value: int) -> None:
        self.camera_settings.brightness = max(0, min(100, value))
    
    @property
    def sharpness(self) -> int:
        return self.camera_settings.sharpness
    
    @sharpness.setter
    def sharpness(self, value: int) -> None:
        self.camera_settings.sharpness = max(-100, min(100, value))
    
    @property
    def contrast(self) -> int:
        return self.camera_settings.contrast
    
    @contrast.setter
    def contrast(self, value: int) -> None:
        self.camera_settings.contrast = max(-100, min(100, value))
    
    @property
    def saturation(self) -> int:
        return self.camera_settings.saturation
    
    @saturation.setter
    def saturation(self, value: int) -> None:
        self.camera_settings.saturation = max(-100, min(100, value))
    
    @property
    def ss(self) -> int:
        return self.camera_settings.shutter_speed
    
    @ss.setter
    def ss(self, value: int) -> None:
        self.camera_settings.shutter_speed = max(100, value)
    
    @property
    def iso(self) -> int:
        return self.camera_settings.iso
    
    @iso.setter
    def iso(self, value: int) -> None:
        self.camera_settings.iso = max(60, min(1600, value))
    
    @property
    def imageseq(self) -> int:
        return self.camera_settings.image_seq
    
    @imageseq.setter
    def imageseq(self, value: int) -> None:
        self.camera_settings.image_seq = value
    
    @property
    def rawmode(self) -> str:
        return 'true' if self.camera_settings.raw_mode else 'false'
    
    @rawmode.setter
    def rawmode(self, value: str) -> None:
        self.camera_settings.raw_mode = value.lower() == 'true'
    
    @property
    def cmode(self) -> str:
        return self.camera_settings.color_mode
    
    @cmode.setter
    def cmode(self, value: str) -> None:
        self.camera_settings.color_mode = value
    
    @property
    def hflip(self) -> str:
        return 'true' if self.camera_settings.horizontal_flip else 'false'
    
    @hflip.setter
    def hflip(self, value: str) -> None:
        self.camera_settings.horizontal_flip = value.lower() == 'true'
    
    @property
    def vflip(self) -> str:
        return 'true' if self.camera_settings.vertical_flip else 'false'
    
    @vflip.setter
    def vflip(self, value: str) -> None:
        self.camera_settings.vertical_flip = value.lower() == 'true'
    
    # Motor settings aliases
    @property
    def vspeed(self) -> int:
        return self.v_settings.speed
    
    @vspeed.setter
    def vspeed(self, value: int) -> None:
        self.v_settings.speed = max(1, value)
    
    @property
    def vsteps(self) -> int:
        return self.v_settings.steps
    
    @vsteps.setter
    def vsteps(self, value: int) -> None:
        self.v_settings.steps = max(1, value)
    
    @property
    def vadj(self) -> int:
        return self.v_settings.adjustment
    
    @vadj.setter
    def vadj(self, value: int) -> None:
        self.v_settings.adjustment = value
    
    @property
    def hspeed(self) -> int:
        return self.h_settings.speed
    
    @hspeed.setter
    def hspeed(self, value: int) -> None:
        self.h_settings.speed = max(1, value)
    
    @property
    def hsteps(self) -> int:
        return self.h_settings.steps
    
    @hsteps.setter
    def hsteps(self, value: int) -> None:
        self.h_settings.steps = max(1, value)
    
    @property
    def hadj(self) -> int:
        return self.h_settings.adjustment
    
    @hadj.setter
    def hadj(self, value: int) -> None:
        self.h_settings.adjustment = value
    
    @property
    def fspeed(self) -> int:
        return self.f_settings.speed
    
    @fspeed.setter
    def fspeed(self, value: int) -> None:
        self.f_settings.speed = max(1, value)
    
    @property
    def fsteps(self) -> int:
        return self.f_settings.steps
    
    @fsteps.setter
    def fsteps(self, value: int) -> None:
        self.f_settings.steps = max(1, value)
    
    @property
    def fadj(self) -> int:
        return self.f_settings.adjustment
    
    @fadj.setter
    def fadj(self, value: int) -> None:
        self.f_settings.adjustment = value
    
    # Tracking settings aliases
    @property
    def curaz(self) -> float:
        return self.tracking.current_az
    
    @curaz.setter
    def curaz(self, value: float) -> None:
        self.tracking.current_az = value
    
    @property
    def curalt(self) -> float:
        return self.tracking.current_alt
    
    @curalt.setter
    def curalt(self, value: float) -> None:
        self.tracking.current_alt = value
    
    @property
    def tgaz(self) -> float:
        return self.tracking.target_az
    
    @tgaz.setter
    def tgaz(self, value: float) -> None:
        self.tracking.target_az = value
    
    @property
    def tgalt(self) -> float:
        return self.tracking.target_alt
    
    @tgalt.setter
    def tgalt(self, value: float) -> None:
        self.tracking.target_alt = value
    
    @property
    def tgrah(self) -> float:
        return self.tracking.target_ra_h
    
    @tgrah.setter
    def tgrah(self, value: float) -> None:
        self.tracking.target_ra_h = value
    
    @property
    def tgram(self) -> float:
        return self.tracking.target_ra_m
    
    @tgram.setter
    def tgram(self, value: float) -> None:
        self.tracking.target_ra_m = value
    
    @property
    def tgras(self) -> float:
        return self.tracking.target_ra_s
    
    @tgras.setter
    def tgras(self, value: float) -> None:
        self.tracking.target_ra_s = value
    
    @property
    def tgdecdg(self) -> float:
        return self.tracking.target_dec_d
    
    @tgdecdg.setter
    def tgdecdg(self, value: float) -> None:
        self.tracking.target_dec_d = value
    
    @property
    def tgdecm(self) -> float:
        return self.tracking.target_dec_m
    
    @tgdecm.setter
    def tgdecm(self, value: float) -> None:
        self.tracking.target_dec_m = value
    
    @property
    def tgdecs(self) -> float:
        return self.tracking.target_dec_s
    
    @tgdecs.setter
    def tgdecs(self, value: float) -> None:
        self.tracking.target_dec_s = value
    
    @property
    def myloclat(self) -> float:
        return self.tracking.latitude
    
    @myloclat.setter
    def myloclat(self, value: float) -> None:
        self.tracking.latitude = value
    
    @property
    def myloclong(self) -> float:
        return self.tracking.longitude
    
    @myloclong.setter
    def myloclong(self, value: float) -> None:
        self.tracking.longitude = value
    
    @property
    def tgazadj(self) -> float:
        return self.tracking.az_adjustment
    
    @tgazadj.setter
    def tgazadj(self, value: float) -> None:
        self.tracking.az_adjustment = value
    
    @property
    def tgaltadj(self) -> float:
        return self.tracking.alt_adjustment
    
    @tgaltadj.setter
    def tgaltadj(self, value: float) -> None:
        self.tracking.alt_adjustment = value
    
    @property
    def ref0_x(self) -> float:
        return self.tracking.ref0_x
    
    @ref0_x.setter
    def ref0_x(self, value: float) -> None:
        self.tracking.ref0_x = value
    
    @property
    def ref0_y(self) -> float:
        return self.tracking.ref0_y
    
    @ref0_y.setter
    def ref0_y(self, value: float) -> None:
        self.tracking.ref0_y = value
    
    @property
    def ref1_x(self) -> float:
        return self.tracking.ref1_x
    
    @ref1_x.setter
    def ref1_x(self, value: float) -> None:
        self.tracking.ref1_x = value
    
    @property
    def ref1_y(self) -> float:
        return self.tracking.ref1_y
    
    @ref1_y.setter
    def ref1_y(self, value: float) -> None:
        self.tracking.ref1_y = value
    
    @property
    def tk_blur_limit(self) -> int:
        return self.tracking.blur_limit
    
    @tk_blur_limit.setter
    def tk_blur_limit(self, value: int) -> None:
        self.tracking.blur_limit = value
    
    @property
    def tk_thresh_limit(self) -> int:
        return self.tracking.thresh_limit
    
    @tk_thresh_limit.setter
    def tk_thresh_limit(self, value: int) -> None:
        self.tracking.thresh_limit = value
    
    @property
    def tk_pos_dir(self) -> str:
        return self.tracking.positive_direction
    
    @tk_pos_dir.setter
    def tk_pos_dir(self, value: str) -> None:
        self.tracking.positive_direction = value
    
    @property
    def tk_neg_dir(self) -> str:
        return self.tracking.negative_direction
    
    @tk_neg_dir.setter
    def tk_neg_dir(self, value: str) -> None:
        self.tracking.negative_direction = value
    
    @property
    def altazradec(self) -> str:
        return self.tracking.mode
    
    @altazradec.setter
    def altazradec(self, value: str) -> None:
        self.tracking.mode = value
    
    # Threading aliases (for backward compatibility)
    @property
    def exitFlag(self) -> threading.Event:
        return self.exit_flag
    
    @property
    def isTracking(self) -> threading.Event:
        return self.is_tracking
    
    @property
    def ipTracking(self) -> threading.Event:
        return self.in_progress_tracking
    
    @property
    def threadLock(self) -> threading.Lock:
        return self.thread_lock
    
    # Serial alias
    @property
    def SerialData(self):
        return self.serial_data
    
    # =========================================================================
    # Methods
    # =========================================================================
    
    def validate(self) -> None:
        """Validate all settings are within bounds."""
        # Camera validation is done via property setters
        # This method exists for backward compatibility
        pass
    
    # Alias for backward compatibility
    Validate = validate
    
    def newadj(self) -> Tuple[float, float]:
        """Calculate new adjustments based on current error."""
        self.tracking.az_adjustment = (
            self.tracking.target_az - 
            self.tracking.current_az + 
            self.tracking.az_adjustment
        )
        self.tracking.alt_adjustment = (
            self.tracking.target_alt - 
            self.tracking.current_alt + 
            self.tracking.alt_adjustment
        )
        return (self.tracking.az_adjustment, self.tracking.alt_adjustment)
    
    def release(self) -> None:
        """Release all resources."""
        self.logger.info("Releasing ControlPackage resources")
        
        # Stop motors
        self.stop_motors()
        
        # Release motor hardware
        if self._motor_v:
            self._motor_v.release()
        if self._motor_h:
            self._motor_h.release()
        if self._motor_f:
            self._motor_f.release()
        
        # Release camera
        if self.camera:
            try:
                self.camera.release()
            except Exception as e:
                self.logger.warning(f"Camera release failed: {e}")
        
        # Close serial
        if self.serial_data:
            try:
                self.serial_data.close()
            except Exception as e:
                self.logger.warning(f"Serial close failed: {e}")
        
        # Cleanup GPIO
        if HAS_GPIO:
            try:
                GPIO.cleanup()
            except Exception:
                pass
        
        self.logger.info("ControlPackage resources released")
    
    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton instance (for testing)."""
        with cls._lock:
            if cls._instance:
                cls._instance.release()
            cls._instance = None


# =============================================================================
# Motor Control Thread
# =============================================================================

class MotorControlThreadV2(threading.Thread):
    """
    Motor control thread.
    
    Processes commands from queue and executes motor movements.
    """
    
    def __init__(self, motor_type: MotorType, control_package: ControlPackageV2):
        super().__init__()
        self.logger = logging.getLogger(f'telescope.motor.{motor_type.value}')
        self.motor_type = motor_type
        self.cp = control_package
        self.name = motor_type.value
        
        # Select queue and pins based on motor type
        if motor_type == MotorType.HORIZONTAL:
            self.queue = control_package.h_cmdqueue
            self.fwd_pin = control_package.HL_pin
            self.bwd_pin = control_package.HR_pin
            self.port = "M1M2"
        elif motor_type == MotorType.VERTICAL:
            self.queue = control_package.v_cmdqueue
            self.fwd_pin = control_package.VH_pin
            self.bwd_pin = control_package.VL_pin
            self.port = "M3M4"
        else:  # FOCUS
            self.queue = control_package.f_cmdqueue
            self.fwd_pin = 0
            self.bwd_pin = 0
            self.port = "M5M6"
        
        # Initialize motor driver
        self.motor = self._create_motor_driver()
    
    def _create_motor_driver(self) -> Optional[StepMotor]:
        """Create appropriate motor driver."""
        try:
            if self.motor_type == MotorType.FOCUS:
                from EDStepMotor import EDStepMotor
                motor = EDStepMotor(0x60, debug=False)
            else:
                from ArduinoSerialStepMotor import ArduinoSerialStepMotor
                motor = ArduinoSerialStepMotor(0x60, debug=False)
            
            motor.setPort(self.port)
            motor.setSensor(self.fwd_pin, self.bwd_pin)
            
            if self.motor_type == MotorType.VERTICAL:
                motor.setFreq(1600)
            
            return motor
            
        except ImportError as e:
            self.logger.warning(f"Motor driver not available: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Motor initialization failed: {e}")
            return None
    
    def release(self) -> None:
        """Release motor hardware."""
        if self.motor:
            try:
                self.motor.release()
            except Exception as e:
                self.logger.warning(f"Motor release failed: {e}")
    
    @handle_errors(severity=ErrorSeverity.WARNING)
    def _process_command(self, direction: str, speed: int, adj: int, steps: int) -> None:
        """Process a single motor command."""
        if not self.motor:
            self.logger.warning("No motor driver available")
            return
        
        self.logger.info(f"{direction} Speed:{speed} Adj:{adj} Steps:{steps}")
        
        self.motor.setSpeed(speed, adj)
        
        # Map directions
        if self.motor_type == MotorType.HORIZONTAL:
            # LEFT = BACKWARD, RIGHT = FORWARD
            motor_dir = "BACKWARD" if direction == "LEFT" else "FORWARD"
            style = "MICROSTEP"
        elif self.motor_type == MotorType.VERTICAL:
            # UP = FORWARD, DOWN = BACKWARD
            motor_dir = "FORWARD" if direction == "UP" else "BACKWARD"
            style = self.cp.move_method
        else:  # FOCUS
            # IN = FORWARD, OUT = BACKWARD
            motor_dir = "FORWARD" if direction == "IN" else "BACKWARD"
            style = "MICROSTEP"
        
        # Execute
        self.motor.step(steps, motor_dir, style)
        
        # Check limits
        self._check_limits(direction)
        
        # Release focus motor after move
        if self.motor_type == MotorType.FOCUS:
            self.motor.release()
    
    def _check_limits(self, direction: str) -> None:
        """Check and log limit switch states."""
        if not HAS_GPIO:
            return
        
        if self.motor_type == MotorType.HORIZONTAL:
            if direction == "LEFT" and GPIO.input(self.fwd_pin):
                self.logger.warning("Horizontal leftmost limit reached!")
            if direction == "RIGHT" and GPIO.input(self.bwd_pin):
                self.logger.warning("Horizontal rightmost limit reached!")
        
        elif self.motor_type == MotorType.VERTICAL:
            if direction == "UP" and GPIO.input(self.fwd_pin):
                self.logger.warning("Vertical highest limit reached!")
            if direction == "DOWN" and GPIO.input(self.bwd_pin):
                self.logger.warning("Vertical lowest limit reached!")
    
    def run(self) -> None:
        """Main thread loop."""
        self.logger.info(f"Starting {self.name}")
        
        while self.cp.exit_flag.is_set():
            direction = ""
            speed = 0
            adj = 0
            steps = 0
            
            # Get command from queue
            self.cp.thread_lock.acquire()
            try:
                if not self.queue.empty():
                    direction, speed, adj, steps = self.queue.get()
            finally:
                self.cp.thread_lock.release()
            
            # Process if we have a command
            if direction:
                self._process_command(direction, speed, adj, steps)
            
            time.sleep(0.1)
        
        self.logger.info(f"Exiting {self.name}")


# =============================================================================
# Legacy Compatibility Layer
# =============================================================================

# Create a module-level instance that mimics the old class-variable behavior
_control_package: Optional[ControlPackageV2] = None


def get_control_package(config: Optional[TelescopeConfig] = None) -> ControlPackageV2:
    """Get or create the global ControlPackage instance."""
    global _control_package
    if _control_package is None:
        _control_package = ControlPackageV2(config)
    return _control_package


# For backward compatibility: create a class that proxies to ControlPackageV2
class ControlPackage:
    """
    Backward-compatible wrapper for ControlPackageV2.
    
    Provides class-level attribute access that maps to the singleton instance.
    """
    
    _instance: Optional[ControlPackageV2] = None
    
    @classmethod
    def _get_instance(cls) -> ControlPackageV2:
        if cls._instance is None:
            cls._instance = get_control_package()
        return cls._instance
    
    def __class_getattr__(cls, name: str) -> Any:
        """Proxy attribute access to singleton instance."""
        return getattr(cls._get_instance(), name)
    
    def __class_setattr__(cls, name: str, value: Any) -> None:
        """Proxy attribute setting to singleton instance."""
        if name == '_instance':
            super().__setattr__(name, value)
        else:
            setattr(cls._get_instance(), name, value)
    
    # Explicit class-level properties for common attributes
    @classmethod
    def release(cls) -> None:
        cls._get_instance().release()
    
    @classmethod  
    def Validate(cls) -> None:
        cls._get_instance().validate()
    
    @classmethod
    def newadj(cls) -> Tuple[float, float]:
        return cls._get_instance().newadj()


# =============================================================================
# Module Initialization
# =============================================================================

def initialize_motors(config: Optional[TelescopeConfig] = None) -> ControlPackageV2:
    """
    Initialize the motor control system.
    
    Call this once at startup to set up motors and start control threads.
    """
    cp = get_control_package(config)
    cp.start_motors()
    return cp


# =============================================================================
# Main / Demo
# =============================================================================

if __name__ == '__main__':
    from config import setup_logging
    
    setup_logging()
    logger = logging.getLogger('telescope')
    
    # Create control package (won't start motors without hardware)
    cp = get_control_package()
    
    print("ControlPackage V2 Demo")
    print("=" * 50)
    print(f"Vertical motor: speed={cp.vspeed}, steps={cp.vsteps}")
    print(f"Horizontal motor: speed={cp.hspeed}, steps={cp.hsteps}")
    print(f"Focus motor: speed={cp.fspeed}, steps={cp.fsteps}")
    print(f"Location: lat={cp.myloclat}, long={cp.myloclong}")
    print(f"Camera: {cp.width}x{cp.height}, ISO={cp.iso}")
    
    # Test validation through property setters
    cp.brightness = 150  # Should clamp to 100
    print(f"Brightness after setting 150: {cp.brightness}")  # Should be 100
    
    cp.iso = 50  # Should clamp to 60
    print(f"ISO after setting 50: {cp.iso}")  # Should be 60
    
    print("\nControlPackage V2 initialized successfully!")

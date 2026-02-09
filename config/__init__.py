"""
Telescope Configuration Module

Centralized configuration management with validation and error handling.
"""

import os
import yaml
import logging
from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path

# =============================================================================
# Logging Setup
# =============================================================================

def setup_logging(config: dict = None) -> logging.Logger:
    """Setup logging with configuration from config dict or defaults."""
    
    log_config = config.get('logging', {}) if config else {}
    
    level_str = log_config.get('level', 'INFO')
    level = getattr(logging, level_str.upper(), logging.INFO)
    
    log_format = log_config.get(
        'format', 
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create logs directory if needed
    log_file = log_config.get('file', 'logs/telescope.log')
    log_dir = os.path.dirname(log_file)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
    
    # Configure root logger
    handlers = [logging.StreamHandler()]
    
    try:
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=log_config.get('max_bytes', 10485760),
            backupCount=log_config.get('backup_count', 5)
        )
        handlers.append(file_handler)
    except Exception as e:
        print(f"Warning: Could not setup file logging: {e}")
    
    logging.basicConfig(
        level=level,
        format=log_format,
        handlers=handlers
    )
    
    return logging.getLogger('telescope')


# =============================================================================
# Configuration Data Classes
# =============================================================================

@dataclass
class LocationConfig:
    latitude: float = 42.27069402
    longitude: float = -83.04411196
    timezone: str = "America/Detroit"


@dataclass
class MotorPinConfig:
    pins: List[int] = field(default_factory=lambda: [0, 0, 0, 0])
    speed: int = 100
    steps: int = 100
    adjustment: int = 5


@dataclass
class LimitSwitchConfig:
    vertical_low: int = 24
    vertical_high: int = 23
    horizontal_left: int = 25
    horizontal_right: int = 8


@dataclass
class MovementConfig:
    method: str = "DOUBLE"
    refined_method: str = "MICROSTEP"


@dataclass
class MotorsConfig:
    vertical: MotorPinConfig = field(default_factory=lambda: MotorPinConfig(
        pins=[12, 16, 20, 21], speed=120, steps=200, adjustment=5
    ))
    horizontal: MotorPinConfig = field(default_factory=lambda: MotorPinConfig(
        pins=[6, 13, 19, 26], speed=50, steps=10, adjustment=3
    ))
    focus: MotorPinConfig = field(default_factory=lambda: MotorPinConfig(
        pins=[4, 17, 27, 22], speed=100, steps=50, adjustment=3
    ))
    limit_switches: LimitSwitchConfig = field(default_factory=LimitSwitchConfig)
    movement: MovementConfig = field(default_factory=MovementConfig)


@dataclass
class EQModeConfig:
    positive_direction: str = "UP"
    negative_direction: str = "DOWN"
    ra_speed_multiplier: int = 15
    ra_speed_divisor: int = 5


@dataclass
class TrackingConfig:
    threshold_limit: float = 5.0
    trace_reference_count: int = 3
    min_vertical_offset: float = 0.2
    min_horizontal_offset: float = 0.5
    max_vertical_steps: int = 300
    max_horizontal_steps: int = 20
    min_vertical_steps: int = 10
    min_horizontal_steps: int = 2
    tracking_interval: float = 1.0
    vertical_sleep: float = 2.0
    horizontal_sleep: float = 2.0
    default_ra_sleep: float = 20.0
    blur_limit: int = 13
    thresh_limit: int = 45
    eq_mode: EQModeConfig = field(default_factory=EQModeConfig)


@dataclass
class ResolutionConfig:
    width: int = 700
    height: int = 524


@dataclass
class CameraDefaultsConfig:
    brightness: int = 10
    sharpness: int = 20
    contrast: int = 20
    saturation: int = 100
    shutter_speed: int = 4000
    iso: int = 400


@dataclass 
class CameraConfig:
    resolution: ResolutionConfig = field(default_factory=ResolutionConfig)
    defaults: CameraDefaultsConfig = field(default_factory=CameraDefaultsConfig)
    roi_left: float = 0.0
    video_length: int = 20
    timelapse_count: int = 1
    horizontal_flip: bool = True
    vertical_flip: bool = True
    color_mode: str = "day"
    raw_mode: bool = False
    max_keep_snapshots: int = 100
    max_keep_videoshots: int = 5


@dataclass
class SerialConfig:
    port: str = "/dev/ttyAMA0"
    baudrate: int = 9600
    parity: str = "none"
    stopbits: int = 1
    bytesize: int = 8
    timeout: int = 1


@dataclass
class MagnetometerConfig:
    x_min: int = -652
    x_max: int = 538
    y_min: int = -656
    y_max: int = 643
    z_min: int = -563
    z_max: int = 641
    samples_per_read: int = 5
    sample_interval: float = 0.1


@dataclass
class WebServerConfig:
    host: str = "0.0.0.0"
    port: int = 8080
    content_dir: str = "content"


@dataclass
class TelescopeConfig:
    """Main configuration container."""
    location: LocationConfig = field(default_factory=LocationConfig)
    motors: MotorsConfig = field(default_factory=MotorsConfig)
    tracking: TrackingConfig = field(default_factory=TrackingConfig)
    camera: CameraConfig = field(default_factory=CameraConfig)
    serial: SerialConfig = field(default_factory=SerialConfig)
    magnetometer: MagnetometerConfig = field(default_factory=MagnetometerConfig)
    web_server: WebServerConfig = field(default_factory=WebServerConfig)


# =============================================================================
# Configuration Loader
# =============================================================================

class ConfigLoader:
    """Load and validate telescope configuration."""
    
    DEFAULT_CONFIG_PATHS = [
        'telescope_config.yaml',
        'config/telescope_config.yaml',
        '../config/telescope_config.yaml',
        os.path.expanduser('~/.telescope/config.yaml'),
    ]
    
    def __init__(self, config_path: Optional[str] = None):
        self.logger = logging.getLogger('telescope.config')
        self.config_path = config_path
        self._raw_config = {}
        self._config: Optional[TelescopeConfig] = None
    
    def find_config_file(self) -> Optional[str]:
        """Find configuration file from default paths."""
        if self.config_path and os.path.exists(self.config_path):
            return self.config_path
        
        # Get the base directory (projects folder)
        base_dir = Path(__file__).parent.parent
        
        for path in self.DEFAULT_CONFIG_PATHS:
            full_path = base_dir / path
            if full_path.exists():
                return str(full_path)
            if os.path.exists(path):
                return path
        
        return None
    
    def load(self) -> TelescopeConfig:
        """Load configuration from YAML file."""
        config_file = self.find_config_file()
        
        if not config_file:
            self.logger.warning(
                "No config file found, using defaults. "
                "Create telescope_config.yaml to customize."
            )
            self._config = TelescopeConfig()
            return self._config
        
        try:
            self.logger.info(f"Loading configuration from: {config_file}")
            with open(config_file, 'r') as f:
                self._raw_config = yaml.safe_load(f) or {}
            
            self._config = self._parse_config(self._raw_config)
            self.logger.info("Configuration loaded successfully")
            return self._config
            
        except yaml.YAMLError as e:
            self.logger.error(f"YAML parsing error: {e}")
            raise ConfigurationError(f"Invalid YAML in config file: {e}")
        except Exception as e:
            self.logger.error(f"Error loading config: {e}")
            raise ConfigurationError(f"Failed to load configuration: {e}")
    
    def _parse_config(self, raw: dict) -> TelescopeConfig:
        """Parse raw dictionary into TelescopeConfig."""
        config = TelescopeConfig()
        
        # Location
        if 'location' in raw:
            loc = raw['location']
            config.location = LocationConfig(
                latitude=loc.get('latitude', config.location.latitude),
                longitude=loc.get('longitude', config.location.longitude),
                timezone=loc.get('timezone', config.location.timezone),
            )
        
        # Motors
        if 'motors' in raw:
            motors = raw['motors']
            
            if 'vertical' in motors:
                v = motors['vertical']
                config.motors.vertical = MotorPinConfig(
                    pins=v.get('pins', config.motors.vertical.pins),
                    speed=v.get('speed', config.motors.vertical.speed),
                    steps=v.get('steps', config.motors.vertical.steps),
                    adjustment=v.get('adjustment', config.motors.vertical.adjustment),
                )
            
            if 'horizontal' in motors:
                h = motors['horizontal']
                config.motors.horizontal = MotorPinConfig(
                    pins=h.get('pins', config.motors.horizontal.pins),
                    speed=h.get('speed', config.motors.horizontal.speed),
                    steps=h.get('steps', config.motors.horizontal.steps),
                    adjustment=h.get('adjustment', config.motors.horizontal.adjustment),
                )
            
            if 'focus' in motors:
                f = motors['focus']
                config.motors.focus = MotorPinConfig(
                    pins=f.get('pins', config.motors.focus.pins),
                    speed=f.get('speed', config.motors.focus.speed),
                    steps=f.get('steps', config.motors.focus.steps),
                    adjustment=f.get('adjustment', config.motors.focus.adjustment),
                )
            
            if 'limit_switches' in motors:
                ls = motors['limit_switches']
                config.motors.limit_switches = LimitSwitchConfig(
                    vertical_low=ls.get('vertical_low', 24),
                    vertical_high=ls.get('vertical_high', 23),
                    horizontal_left=ls.get('horizontal_left', 25),
                    horizontal_right=ls.get('horizontal_right', 8),
                )
            
            if 'movement' in motors:
                mv = motors['movement']
                config.motors.movement = MovementConfig(
                    method=mv.get('method', 'DOUBLE'),
                    refined_method=mv.get('refined_method', 'MICROSTEP')
                )
        
        # Tracking
        if 'tracking' in raw:
            tr = raw['tracking']
            
            # EQ mode config
            eq_mode = EQModeConfig()
            if 'eq_mode' in tr:
                eq = tr['eq_mode']
                eq_mode = EQModeConfig(
                    positive_direction=eq.get('positive_direction', 'UP'),
                    negative_direction=eq.get('negative_direction', 'DOWN'),
                    ra_speed_multiplier=eq.get('ra_speed_multiplier', 15),
                    ra_speed_divisor=eq.get('ra_speed_divisor', 5)
                )
            
            config.tracking = TrackingConfig(
                threshold_limit=tr.get('threshold_limit', 5.0),
                trace_reference_count=tr.get('trace_reference_count', 3),
                min_vertical_offset=tr.get('min_vertical_offset', 0.2),
                min_horizontal_offset=tr.get('min_horizontal_offset', 0.5),
                max_vertical_steps=tr.get('max_vertical_steps', 300),
                max_horizontal_steps=tr.get('max_horizontal_steps', 20),
                min_vertical_steps=tr.get('min_vertical_steps', 10),
                min_horizontal_steps=tr.get('min_horizontal_steps', 2),
                tracking_interval=tr.get('tracking_interval', 1.0),
                vertical_sleep=tr.get('vertical_sleep', 2.0),
                horizontal_sleep=tr.get('horizontal_sleep', 2.0),
                default_ra_sleep=tr.get('default_ra_sleep', 20.0),
                blur_limit=tr.get('blur_limit', 13),
                thresh_limit=tr.get('thresh_limit', 45),
                eq_mode=eq_mode
            )
        
        # Camera
        if 'camera' in raw:
            cam = raw['camera']
            res = cam.get('resolution', {})
            defaults = cam.get('defaults', {})
            
            resolution = ResolutionConfig(
                width=res.get('width', 700),
                height=res.get('height', 524)
            )
            
            camera_defaults = CameraDefaultsConfig(
                brightness=defaults.get('brightness', 10),
                sharpness=defaults.get('sharpness', 20),
                contrast=defaults.get('contrast', 20),
                saturation=defaults.get('saturation', 100),
                shutter_speed=defaults.get('shutter_speed', 4000),
                iso=defaults.get('iso', 400)
            )
            
            config.camera = CameraConfig(
                resolution=resolution,
                defaults=camera_defaults,
                roi_left=cam.get('roi_left', 0.0),
                video_length=cam.get('video_length', 20),
                timelapse_count=cam.get('timelapse_count', 1),
                horizontal_flip=cam.get('horizontal_flip', True),
                vertical_flip=cam.get('vertical_flip', True),
                color_mode=cam.get('color_mode', 'day'),
                raw_mode=cam.get('raw_mode', False),
                max_keep_snapshots=cam.get('max_keep_snapshots', 100),
                max_keep_videoshots=cam.get('max_keep_videoshots', 5)
            )
        
        # Serial
        if 'serial' in raw:
            ser = raw['serial']
            config.serial = SerialConfig(
                port=ser.get('port', '/dev/ttyAMA0'),
                baudrate=ser.get('baudrate', 9600),
                parity=ser.get('parity', 'none'),
                stopbits=ser.get('stopbits', 1),
                bytesize=ser.get('bytesize', 8),
                timeout=ser.get('timeout', 1),
            )
        
        # Magnetometer
        if 'magnetometer' in raw:
            mag = raw['magnetometer']
            cal = mag.get('calibration', {})
            config.magnetometer = MagnetometerConfig(
                x_min=cal.get('x_min', -652),
                x_max=cal.get('x_max', 538),
                y_min=cal.get('y_min', -656),
                y_max=cal.get('y_max', 643),
                z_min=cal.get('z_min', -563),
                z_max=cal.get('z_max', 641),
                samples_per_read=mag.get('samples_per_read', 5),
                sample_interval=mag.get('sample_interval', 0.1),
            )
        
        # Web Server
        if 'web_server' in raw:
            web = raw['web_server']
            config.web_server = WebServerConfig(
                host=web.get('host', '0.0.0.0'),
                port=web.get('port', 8080),
                content_dir=web.get('content_dir', 'content'),
            )
        
        return config
    
    def get_raw(self) -> dict:
        """Get raw configuration dictionary."""
        return self._raw_config
    
    @property
    def config(self) -> TelescopeConfig:
        """Get parsed configuration, loading if necessary."""
        if self._config is None:
            self.load()
        return self._config


class ConfigurationError(Exception):
    """Configuration related errors."""
    pass


# =============================================================================
# Global Config Instance
# =============================================================================

_config_loader: Optional[ConfigLoader] = None
_config: Optional[TelescopeConfig] = None


def get_config(config_path: Optional[str] = None) -> TelescopeConfig:
    """Get global configuration instance."""
    global _config_loader, _config
    
    if _config is None:
        _config_loader = ConfigLoader(config_path)
        _config = _config_loader.load()
    
    return _config


def reload_config(config_path: Optional[str] = None) -> TelescopeConfig:
    """Force reload configuration."""
    global _config_loader, _config
    _config = None
    _config_loader = None
    return get_config(config_path)

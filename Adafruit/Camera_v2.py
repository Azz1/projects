#!/usr/bin/python
"""
Camera Module - Refactored with Config System

Provides camera control decoupled from ControlPackage.
"""

import os
import sys
import time
import glob
import logging
import threading
import traceback
import base64
from io import BytesIO
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Tuple, Any, Deque, List
from collections import deque

# Add project path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import get_config, TelescopeConfig
from config.errors import (
    CameraError,
    handle_errors,
    ErrorSeverity
)

# Optional imports - may not be available on all systems
try:
    import cv2
    import numpy as np
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False
    cv2 = None
    np = None

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    Image = None

try:
    import libcamera
    from picamera2 import Picamera2
    from libcamera import Transform
    from picamera2.encoders import H264Encoder, Quality
    HAS_PICAMERA2 = True
except ImportError:
    HAS_PICAMERA2 = False
    libcamera = None
    Picamera2 = None
    Transform = None
    H264Encoder = None
    Quality = None

# CV2 helper for star tracking
cv2lib_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'cv2'))
sys.path.append(cv2lib_path)
try:
    from detect_bright_spots import CV2Helper
    HAS_CV2HELPER = True
except ImportError:
    HAS_CV2HELPER = False
    CV2Helper = None


# =============================================================================
# Camera State (Decoupled from ControlPackage)
# =============================================================================

@dataclass
class CameraState:
    """
    Camera state container - replaces direct ControlPackage access.
    
    Can be linked to ControlPackage or used standalone.
    """
    # Image settings
    width: int = 700
    height: int = 524
    roi_left: float = 0.0
    roi_width: float = 1.0
    
    # Exposure settings
    shutter_speed: int = 4000  # microseconds
    iso: int = 400
    brightness: int = 10
    sharpness: int = 20
    contrast: int = 20
    saturation: int = 100
    
    # Mode settings
    color_mode: str = "day"  # day/night
    raw_mode: bool = False
    vertical_flip: bool = True
    horizontal_flip: bool = True
    
    # Video settings
    video_length: int = 20  # seconds
    timelapse_count: int = 1
    
    # Storage limits
    max_keep_snapshots: int = 100
    max_keep_videoshots: int = 5
    
    # Sequence counters
    image_seq: int = 0
    snapshot_seq: int = 0
    video_seq: int = 0
    
    # Tracking reference points
    ref0_x: float = 0.0
    ref0_y: float = 0.0
    ref1_x: float = 0.0
    ref1_y: float = 0.0
    
    # Tracking parameters
    blur_limit: int = 13
    thresh_limit: int = 45
    delta_ra: float = 0.0
    delta_dec: float = 0.0
    
    # Tracking queue (for storing tracking history)
    tracking_queue: Deque = field(default_factory=lambda: deque(maxlen=20))
    
    @classmethod
    def from_config(cls, config: TelescopeConfig) -> 'CameraState':
        """Create CameraState from TelescopeConfig."""
        cam = config.camera
        tracking = config.tracking
        
        return cls(
            width=cam.resolution.width,
            height=cam.resolution.height,
            roi_left=cam.roi_left,
            roi_width=(1 - cam.roi_left) ** 2,
            shutter_speed=cam.defaults.shutter_speed,
            iso=cam.defaults.iso,
            brightness=cam.defaults.brightness,
            sharpness=cam.defaults.sharpness,
            contrast=cam.defaults.contrast,
            saturation=cam.defaults.saturation,
            color_mode=cam.color_mode,
            raw_mode=cam.raw_mode,
            vertical_flip=cam.vertical_flip,
            horizontal_flip=cam.horizontal_flip,
            video_length=cam.video_length,
            timelapse_count=cam.timelapse_count,
            max_keep_snapshots=cam.max_keep_snapshots,
            max_keep_videoshots=cam.max_keep_videoshots,
            blur_limit=tracking.blur_limit,
            thresh_limit=tracking.thresh_limit,
        )
    
    @classmethod
    def from_control_package(cls, cp: Any) -> 'CameraState':
        """Create CameraState that proxies to ControlPackage."""
        return ControlPackageProxy(cp)
    
    def has_ref_points(self) -> bool:
        """Check if tracking reference points are defined."""
        return (self.ref0_x != self.ref1_x or self.ref0_y != self.ref1_y)


class ControlPackageProxy(CameraState):
    """
    Proxy that reads/writes to ControlPackage for backward compatibility.
    """
    
    def __init__(self, cp: Any):
        self._cp = cp
    
    # Properties that proxy to ControlPackage
    @property
    def width(self) -> int:
        return self._cp.width
    
    @property
    def height(self) -> int:
        return self._cp.height
    
    @property
    def roi_left(self) -> float:
        return getattr(self._cp, 'roi_l', 0.0)
    
    @property
    def roi_width(self) -> float:
        return getattr(self._cp, 'roi_w', 1.0)
    
    @property
    def shutter_speed(self) -> int:
        return self._cp.ss
    
    @property
    def iso(self) -> int:
        return self._cp.iso
    
    @property
    def brightness(self) -> int:
        return self._cp.brightness
    
    @property
    def sharpness(self) -> int:
        return self._cp.sharpness
    
    @property
    def contrast(self) -> int:
        return self._cp.contrast
    
    @property
    def saturation(self) -> int:
        return self._cp.saturation
    
    @property
    def color_mode(self) -> str:
        return self._cp.cmode
    
    @property
    def raw_mode(self) -> bool:
        return self._cp.rawmode == 'true'
    
    @property
    def vertical_flip(self) -> bool:
        return self._cp.vflip == 'true'
    
    @property
    def horizontal_flip(self) -> bool:
        return self._cp.hflip == 'true'
    
    @property
    def video_length(self) -> int:
        return getattr(self._cp, 'videolen', 20)
    
    @property
    def timelapse_count(self) -> int:
        return getattr(self._cp, 'timelapse', 1)
    
    @property
    def max_keep_snapshots(self) -> int:
        return getattr(self._cp, 'max_keep_snapshots', 100)
    
    @property
    def max_keep_videoshots(self) -> int:
        return getattr(self._cp, 'max_keep_videoshots', 5)
    
    @property
    def image_seq(self) -> int:
        return self._cp.imageseq
    
    @image_seq.setter
    def image_seq(self, value: int):
        self._cp.imageseq = value
    
    @property
    def snapshot_seq(self) -> int:
        return getattr(self._cp, 'simageseq', 0)
    
    @snapshot_seq.setter
    def snapshot_seq(self, value: int):
        self._cp.simageseq = value
    
    @property
    def video_seq(self) -> int:
        return getattr(self._cp, 'videoseq', 0)
    
    @video_seq.setter
    def video_seq(self, value: int):
        self._cp.videoseq = value
    
    @property
    def ref0_x(self) -> float:
        return self._cp.ref0_x
    
    @property
    def ref0_y(self) -> float:
        return self._cp.ref0_y
    
    @property
    def ref1_x(self) -> float:
        return self._cp.ref1_x
    
    @property
    def ref1_y(self) -> float:
        return self._cp.ref1_y
    
    @property
    def blur_limit(self) -> int:
        return self._cp.tk_blur_limit
    
    @property
    def thresh_limit(self) -> int:
        return self._cp.tk_thresh_limit
    
    @property
    def delta_ra(self) -> float:
        return self._cp.tk_delta_ra
    
    @delta_ra.setter
    def delta_ra(self, value: float):
        self._cp.tk_delta_ra = value
    
    @property
    def delta_dec(self) -> float:
        return self._cp.tk_delta_dec
    
    @delta_dec.setter
    def delta_dec(self, value: float):
        self._cp.tk_delta_dec = value
    
    @property
    def tracking_queue(self) -> Deque:
        return self._cp.tk_queue
    
    def has_ref_points(self) -> bool:
        return (self._cp.ref0_x != self._cp.ref1_x or 
                self._cp.ref0_y != self._cp.ref1_y)


# =============================================================================
# Abstract Camera Base
# =============================================================================

class Camera(ABC):
    """Abstract base class for camera implementations."""
    
    @abstractmethod
    def snapshot(self) -> Tuple[time.struct_time, str, bool]:
        """Take a snapshot, return (localtime, base64_image, error_flag)."""
        pass
    
    @abstractmethod
    def snapshot_full(self) -> str:
        """Take a full resolution snapshot, return filename."""
        pass
    
    @abstractmethod
    def videoshot(self) -> str:
        """Record a video clip, return filename."""
        pass
    
    @abstractmethod
    def startvideo(self) -> None:
        """Start video streaming."""
        pass
    
    @abstractmethod
    def stopvideo(self) -> None:
        """Stop video streaming."""
        pass
    
    @abstractmethod
    def release(self) -> None:
        """Release camera resources."""
        pass
    
    def haltsys(self) -> None:
        """Halt the system."""
        os.system('sudo halt')


# =============================================================================
# Shell Camera (uses rpicam-still/rpicam-vid CLI)
# =============================================================================

class ShellCamera(Camera):
    """
    Camera implementation using rpicam-still and rpicam-vid CLI tools.
    
    This is the most compatible option for Raspberry Pi cameras.
    """
    
    def __init__(self, state: CameraState, temp_dir: str = 'temp'):
        self.logger = logging.getLogger('telescope.camera.shell')
        self.state = state
        self.temp_dir = temp_dir
        self._lock = threading.Lock()
        self._video_started = False
        
        # Ensure temp directory exists
        os.makedirs(temp_dir, exist_ok=True)
    
    def _build_common_args(self) -> str:
        """Build common CLI arguments."""
        s = self.state
        
        args = []
        if s.vertical_flip:
            args.append('--vflip')
        if s.horizontal_flip:
            args.append('--hflip')
        
        # ROI
        roi = s.roi_left
        roi_w = s.roi_width
        args.append(f'--roi {roi},{roi},{roi_w},{roi_w}')
        
        # Brightness/Gain
        args.append(f'--brightness {s.brightness/100:.2f}')
        args.append(f'--analoggain {s.iso/100:.0f}')
        args.append(f'--sharpness {s.sharpness/20:.2f}')
        args.append(f'--contrast {s.contrast/20:.2f}')
        args.append(f'--saturation {s.saturation/100:.2f}')
        
        return ' '.join(args)
    
    def _process_tracking(
        self,
        fname: str,
        localtime: time.struct_time,
        img: Any = None
    ) -> Tuple[str, bool]:
        """Process image for star tracking, return (base64_image, error_flag)."""
        track_err = False
        imgstr = ""
        
        if not HAS_CV2HELPER or not HAS_CV2:
            # No tracking support, just return image
            if img is None and HAS_PIL:
                img = Image.open(fname)
            
            if img:
                output = BytesIO()
                if hasattr(img, 'save'):
                    img.save(output, format='JPEG')
                    imgstr = base64.b64encode(output.getvalue()).decode('utf-8')
            return imgstr, True
        
        try:
            self.logger.debug(
                f"Blur Limit: {self.state.blur_limit}, "
                f"Thresh Limit: {self.state.thresh_limit}"
            )
            
            cvhelper = CV2Helper(
                blur_limit=self.state.blur_limit,
                thresh_limit=self.state.thresh_limit
            )
            
            if img is None:
                img = cvhelper.loadimage(fname)
            else:
                cvhelper.setimage(img)
            
            centers, radius, img = cvhelper.processimage(mark=True)
            cvhelper.printcenters()
            cvhelper.setref(
                self.state.ref0_x, self.state.ref0_y,
                self.state.ref1_x, self.state.ref1_y
            )
            
            idx, cntr, img = cvhelper.find_tracking_point()
            
            if idx >= 0:
                self.logger.info(
                    f"Tracking Point #{idx+1} - ({int(cntr[0])}, {int(cntr[1])})"
                )
                
                delta_ra, delta_dec = cvhelper.calc_offset(cntr[0], cntr[1])
                self.state.delta_ra = delta_ra
                self.state.delta_dec = delta_dec
                
                self.logger.info(f"Delta-RA: {delta_ra}, Delta-Dec: {delta_dec}")
                
                # Add to tracking queue
                queue = self.state.tracking_queue
                if len(queue) >= queue.maxlen:
                    queue.popleft()
                queue.append([localtime, delta_ra, delta_dec, cntr[0], cntr[1]])
            else:
                track_err = True
            
            ret, buf = cv2.imencode('.jpg', img)
            imgstr = base64.b64encode(np.array(buf)).decode('utf-8')
            
        except Exception as e:
            self.logger.error(f"Tracking processing failed: {e}")
            traceback.print_exc()
            track_err = True
            
            # Fallback to simple image
            if HAS_PIL:
                try:
                    if img is None:
                        img = Image.open(fname)
                    output = BytesIO()
                    if hasattr(img, 'save'):
                        img.save(output, format='JPEG')
                    else:
                        # CV2 image
                        ret, buf = cv2.imencode('.jpg', img)
                        output.write(buf)
                    imgstr = base64.b64encode(output.getvalue()).decode('utf-8')
                except:
                    pass
        
        return imgstr, track_err
    
    @handle_errors(severity=ErrorSeverity.ERROR)
    def snapshot(self) -> Tuple[time.struct_time, str, bool]:
        """Take a snapshot for preview/tracking."""
        if self._video_started:
            return time.localtime(), "", True
        
        track_err = False
        localtime = time.localtime()
        s = self.state
        
        # Increment sequence
        s.image_seq += 1
        
        fname = os.path.join(
            self.temp_dir,
            f'image-{s.image_seq}-{time.strftime("%Y%m%d-%H%M%S", localtime)}.jpg'
        )
        
        with self._lock:
            # Build command
            ss = min(s.shutter_speed, 4000000)
            
            night_args = ''
            if s.color_mode == 'night':
                night_args = '--ev 10 --awb custom --awbgains 2.63,1.62 --exposure normal'
            
            cmd = (
                f'rpicam-still -o {fname} '
                f'--width {s.width} --height {s.height} '
                f'{self._build_common_args()} '
                f'{night_args} --shutter {ss} '
                f'--immediate --nopreview'
            )
            
            self.logger.debug(f"Running: {cmd}")
            os.system(cmd)
        
        # Process image
        if s.has_ref_points():
            imgstr, track_err = self._process_tracking(fname, localtime)
        else:
            # No tracking, just encode image
            if HAS_PIL:
                img = Image.open(fname)
                output = BytesIO()
                img.save(output, format='JPEG')
                imgstr = base64.b64encode(output.getvalue()).decode('utf-8')
                del img
            else:
                imgstr = ""
        
        # Cleanup old images
        if s.image_seq > s.max_keep_snapshots:
            old_seq = s.image_seq - s.max_keep_snapshots
            for f in glob.glob(os.path.join(self.temp_dir, f'image-{old_seq}-*.jpg')):
                try:
                    os.remove(f)
                except:
                    pass
        
        return localtime, imgstr, track_err
    
    @handle_errors(severity=ErrorSeverity.ERROR)
    def snapshot_full(self) -> str:
        """Take full resolution snapshot."""
        if self._video_started:
            return ""
        
        s = self.state
        s.snapshot_seq += 1
        localtime = time.localtime()
        
        fname = os.path.join(
            self.temp_dir,
            f'snapshot-{s.snapshot_seq}-{time.strftime("%Y%m%d-%H%M%S", localtime)}'
        )
        if s.raw_mode:
            fname += '-raw'
        
        with self._lock:
            # Timelapse settings
            ts = ''
            if s.timelapse_count > 1:
                tl = s.shutter_speed / 1000 + 2000
                tt = tl * (s.timelapse_count + 1)
                ts = f'--timelapse {int(tl)} --timeout {int(tt)}'
                fname += '-%02d'
            
            fname_jpg = fname + '.jpg'
            
            night_args = ''
            if s.color_mode == 'night':
                night_args = '--ev 10 --awb custom --awbgains 2.63,1.62 --exposure normal'
            
            raw_arg = '--raw' if s.raw_mode else ''
            immediate = '--immediate' if s.timelapse_count <= 1 else ts
            
            cmd = (
                f'rpicam-still {raw_arg} -o {fname_jpg} '
                f'{self._build_common_args()} '
                f'{night_args} --shutter {s.shutter_speed} '
                f'--nopreview {immediate}'
            )
            
            self.logger.debug(f"Running: {cmd}")
            os.system(cmd)
        
        # Cleanup old snapshots
        if s.snapshot_seq > s.max_keep_snapshots:
            old_seq = s.snapshot_seq - s.max_keep_snapshots
            for f in glob.glob(os.path.join(self.temp_dir, f'snapshot-{old_seq}-*')):
                try:
                    os.remove(f)
                except:
                    pass
        
        return fname_jpg.replace('-%02d', '-00')
    
    @handle_errors(severity=ErrorSeverity.ERROR)
    def videoshot(self) -> str:
        """Record a video clip."""
        s = self.state
        s.video_seq += 1
        localtime = time.localtime()
        
        fname = os.path.join(
            self.temp_dir,
            f'videoshot-{s.video_seq}-{time.strftime("%Y%m%d-%H%M%S", localtime)}.mp4'
        )
        
        with self._lock:
            cmd = (
                f'rpicam-vid --codec libav -o {fname} '
                f'{self._build_common_args()} '
                f'--shutter {s.shutter_speed} '
                f'-t {s.video_length * 1000}'
            )
            
            self.logger.debug(f"Running: {cmd}")
            os.system(cmd)
        
        # Cleanup old videos
        if s.video_seq > s.max_keep_videoshots:
            old_seq = s.video_seq - s.max_keep_videoshots
            for f in glob.glob(os.path.join(self.temp_dir, f'videoshot-{old_seq}-*')):
                try:
                    os.remove(f)
                except:
                    pass
        
        return fname
    
    def startvideo(self) -> None:
        """Start video streaming."""
        if self._video_started:
            return
        
        s = self.state
        
        with self._lock:
            time.sleep(5)
            
            cmd = (
                f'sh runvideo.sh '
                f'{int(s.width/2.1875)*2} {int(s.height/2.1875)*2} '
                f'{s.shutter_speed} {s.iso/100} '
                f'{s.brightness/100:.2f} '
                f'{s.sharpness/20:.2f} {s.contrast/20:.2f} '
                f'{s.saturation/100:.2f} '
                f'{s.roi_left} {s.roi_width} '
                f'{"--vflip" if s.vertical_flip else ""} '
                f'{"--hflip" if s.horizontal_flip else ""}'
            )
            
            self.logger.debug(f"Running: {cmd}")
            os.system(cmd)
            self._video_started = True
            time.sleep(8)
    
    def stopvideo(self) -> None:
        """Stop video streaming."""
        self._video_started = False
        os.system('sh stopvideo.sh')
    
    def release(self) -> None:
        """Release resources."""
        if self._video_started:
            self.stopvideo()


# =============================================================================
# PiCamera2 Implementation
# =============================================================================

class PiCamera2Camera(Camera):
    """
    Camera implementation using Picamera2 library.
    
    Provides more control but requires picamera2 to be installed.
    """
    
    def __init__(self, state: CameraState, temp_dir: str = 'temp'):
        if not HAS_PICAMERA2:
            raise CameraError("Picamera2 not available")
        
        self.logger = logging.getLogger('telescope.camera.picamera2')
        self.state = state
        self.temp_dir = temp_dir
        self._lock = threading.Lock()
        self._video_started = False
        self._picam2: Optional[Picamera2] = None
        
        os.makedirs(temp_dir, exist_ok=True)
    
    def _get_transform(self) -> Transform:
        """Get libcamera Transform from state."""
        return Transform(
            vflip=self.state.vertical_flip,
            hflip=self.state.horizontal_flip
        )
    
    def _apply_controls(self, picam2: Picamera2) -> None:
        """Apply camera controls from state."""
        s = self.state
        
        with picam2.controls as controls:
            controls.AeEnable = False
            controls.ExposureTime = min(int(s.shutter_speed), 4000000)
            controls.AnalogueGain = int(s.iso / 100)
            controls.Brightness = s.brightness / 100
            controls.Contrast = s.contrast / 20
            controls.Sharpness = s.sharpness / 20
            controls.Saturation = s.saturation / 100
            
            if s.color_mode == 'night':
                controls.AwbMode = libcamera.controls.AwbModeEnum.Custom
                controls.ColourGains = (2.63, 1.62)
                controls.ExposureValue = 10
    
    def _process_tracking(
        self,
        img: Any,
        localtime: time.struct_time
    ) -> Tuple[str, bool]:
        """Process PIL image for tracking."""
        track_err = False
        imgstr = ""
        
        if not HAS_CV2HELPER or not HAS_CV2:
            output = BytesIO()
            img.save(output, format='JPEG')
            return base64.b64encode(output.getvalue()).decode('utf-8'), True
        
        try:
            cvhelper = CV2Helper(
                blur_limit=self.state.blur_limit,
                thresh_limit=self.state.thresh_limit
            )
            cvhelper.setimage(img)
            
            centers, radius, cv_img = cvhelper.processimage(mark=True)
            cvhelper.printcenters()
            cvhelper.setref(
                self.state.ref0_x, self.state.ref0_y,
                self.state.ref1_x, self.state.ref1_y
            )
            
            idx, cntr, cv_img = cvhelper.find_tracking_point()
            
            if idx >= 0:
                delta_ra, delta_dec = cvhelper.calc_offset(cntr[0], cntr[1])
                self.state.delta_ra = delta_ra
                self.state.delta_dec = delta_dec
                
                queue = self.state.tracking_queue
                if len(queue) >= queue.maxlen:
                    queue.popleft()
                queue.append([localtime, delta_ra, delta_dec, cntr[0], cntr[1]])
            else:
                track_err = True
            
            ret, buf = cv2.imencode('.jpg', cv_img)
            imgstr = base64.b64encode(np.array(buf)).decode('utf-8')
            
        except Exception as e:
            self.logger.error(f"Tracking failed: {e}")
            traceback.print_exc()
            track_err = True
            
            output = BytesIO()
            img.save(output, format='JPEG')
            imgstr = base64.b64encode(output.getvalue()).decode('utf-8')
        
        return imgstr, track_err
    
    @handle_errors(severity=ErrorSeverity.ERROR)
    def snapshot(self) -> Tuple[time.struct_time, str, bool]:
        """Take a snapshot using Picamera2."""
        if self._video_started:
            return time.localtime(), "", True
        
        s = self.state
        s.image_seq += 1
        localtime = time.localtime()
        
        img = Image.new(mode="RGB", size=(s.width, s.height))
        
        with self._lock:
            try:
                if self._picam2 is None:
                    self._picam2 = Picamera2()
                
                config = self._picam2.create_still_configuration(
                    {"size": (s.width, s.height)},
                    transform=self._get_transform()
                )
                self._picam2.configure(config)
                self._apply_controls(self._picam2)
                
                self._picam2.start(show_preview=False)
                time.sleep(1)
                img = self._picam2.capture_image('main')
                self._picam2.stop()
                self._picam2.stop_encoder()
                
            except Exception as e:
                self.logger.error(f"Capture failed: {e}")
                traceback.print_exc()
            finally:
                if self._picam2:
                    self._picam2.close()
                    self._picam2 = None
        
        # Process for tracking or simple encode
        if s.has_ref_points():
            imgstr, track_err = self._process_tracking(img, localtime)
        else:
            output = BytesIO()
            img.save(output, format='JPEG')
            imgstr = base64.b64encode(output.getvalue()).decode('utf-8')
            track_err = False
        
        return localtime, imgstr, track_err
    
    @handle_errors(severity=ErrorSeverity.ERROR)
    def snapshot_full(self) -> str:
        """Take full resolution snapshot."""
        if self._video_started:
            return ""
        
        s = self.state
        s.snapshot_seq += 1
        localtime = time.localtime()
        
        fname = os.path.join(
            self.temp_dir,
            f'snapshot-{s.snapshot_seq}-{time.strftime("%Y%m%d-%H%M%S", localtime)}'
        )
        if s.raw_mode:
            fname += '-raw'
        
        fname_ret = fname + '.jpg'
        
        with self._lock:
            try:
                if self._picam2 is None:
                    self._picam2 = Picamera2()
                
                capture_config = self._picam2.create_still_configuration(
                    raw={}, display=None,
                    transform=self._get_transform()
                )
                self._picam2.configure(capture_config)
                self._apply_controls(self._picam2)
                
                self._picam2.start()
                time.sleep(2)
                
                for i in range(s.timelapse_count):
                    fnamedng = f"{fname}-{i:02d}.dng" if s.timelapse_count > 1 else f"{fname}.dng"
                    fnamejpg = f"{fname}-{i:02d}.jpg" if s.timelapse_count > 1 else f"{fname}.jpg"
                    
                    if i == 0:
                        fname_ret = fnamejpg
                    
                    buffers, metadata = self._picam2.switch_mode_and_capture_buffers(
                        capture_config, ["main", "raw"]
                    )
                    self._picam2.helpers.save(
                        self._picam2.helpers.make_image(buffers[0], capture_config["main"]),
                        metadata, fnamejpg
                    )
                    if s.raw_mode:
                        self._picam2.helpers.save_dng(
                            buffers[1], metadata, capture_config["raw"], fnamedng
                        )
                    
                    if s.timelapse_count > 1:
                        time.sleep(2)
                
                self._picam2.stop()
                self._picam2.stop_encoder()
                
            finally:
                if self._picam2:
                    self._picam2.close()
                    self._picam2 = None
        
        # Cleanup old snapshots
        if s.snapshot_seq > s.max_keep_snapshots:
            old_seq = s.snapshot_seq - s.max_keep_snapshots
            for f in glob.glob(os.path.join(self.temp_dir, f'snapshot-{old_seq}-*')):
                try:
                    os.remove(f)
                except:
                    pass
        
        return fname_ret
    
    @handle_errors(severity=ErrorSeverity.ERROR)
    def videoshot(self) -> str:
        """Record video using Picamera2."""
        s = self.state
        s.video_seq += 1
        localtime = time.localtime()
        
        fname = os.path.join(
            self.temp_dir,
            f'videoshot-{s.video_seq}-{time.strftime("%Y%m%d-%H%M%S", localtime)}.h264'
        )
        
        with self._lock:
            try:
                if self._picam2 is None:
                    self._picam2 = Picamera2()
                
                capture_config = self._picam2.create_video_configuration(
                    display=None,
                    transform=self._get_transform()
                )
                encoder = H264Encoder()
                
                self._picam2.configure(capture_config)
                self._apply_controls(self._picam2)
                
                self._picam2.start_recording(encoder, fname, quality=Quality.HIGH)
                time.sleep(s.video_length)
                self._picam2.stop_recording()
                
            finally:
                if self._picam2:
                    self._picam2.close()
                    self._picam2 = None
        
        # Cleanup
        if s.video_seq > s.max_keep_videoshots:
            old_seq = s.video_seq - s.max_keep_videoshots
            for f in glob.glob(os.path.join(self.temp_dir, f'videoshot-{old_seq}-*')):
                try:
                    os.remove(f)
                except:
                    pass
        
        return fname
    
    def startvideo(self) -> None:
        """Start video streaming (uses shell script)."""
        if self._video_started:
            return
        
        s = self.state
        
        with self._lock:
            if self._picam2:
                self._picam2.close()
                self._picam2 = None
            
            time.sleep(5)
            
            cmd = (
                f'sh runvideo.sh '
                f'{int(s.width/2.1875)*2} {int(s.height/2.1875)*2} '
                f'{s.shutter_speed} {s.iso/100} '
                f'{s.brightness/100:.2f} '
                f'{s.sharpness/20:.2f} {s.contrast/20:.2f} '
                f'{s.saturation/100:.2f} '
                f'{s.roi_left} {s.roi_width} '
                f'{"--vflip" if s.vertical_flip else ""} '
                f'{"--hflip" if s.horizontal_flip else ""}'
            )
            
            self.logger.debug(f"Running: {cmd}")
            os.system(cmd)
            self._video_started = True
            time.sleep(8)
    
    def stopvideo(self) -> None:
        """Stop video streaming."""
        self._video_started = False
        os.system('sh stopvideo.sh')
    
    def release(self) -> None:
        """Release resources."""
        if self._video_started:
            self.stopvideo()
        
        if self._picam2:
            try:
                self._picam2.close()
            except:
                pass
            self._picam2 = None


# =============================================================================
# Factory Function
# =============================================================================

def create_camera(
    state: Optional[CameraState] = None,
    control_package: Any = None,
    config: Optional[TelescopeConfig] = None,
    prefer_shell: bool = True,
    temp_dir: str = 'temp'
) -> Camera:
    """
    Create appropriate camera instance.
    
    Args:
        state: CameraState instance (optional)
        control_package: Legacy ControlPackage for backward compatibility
        config: TelescopeConfig for creating state
        prefer_shell: Prefer shell camera over Picamera2
        temp_dir: Directory for temporary files
        
    Returns:
        Camera instance
    """
    logger = logging.getLogger('telescope.camera')
    
    # Determine state
    if state is None:
        if control_package is not None:
            state = ControlPackageProxy(control_package)
            logger.info("Using ControlPackage proxy for camera state")
        elif config is not None:
            state = CameraState.from_config(config)
            logger.info("Using config-based camera state")
        else:
            config = get_config()
            state = CameraState.from_config(config)
            logger.info("Using default config for camera state")
    
    # Create camera
    if prefer_shell or not HAS_PICAMERA2:
        logger.info("Using ShellCamera (rpicam-still/rpicam-vid)")
        return ShellCamera(state, temp_dir)
    else:
        logger.info("Using PiCamera2Camera")
        return PiCamera2Camera(state, temp_dir)


# =============================================================================
# Backward Compatibility
# =============================================================================

def init_camera_for_control_package(control_package: Any) -> Camera:
    """
    Initialize camera and attach to ControlPackage.
    
    This provides backward compatibility with code expecting:
        ControlPackage.camera = ...
    """
    camera = create_camera(control_package=control_package)
    control_package.camera = camera
    return camera


# =============================================================================
# Main / Demo
# =============================================================================

if __name__ == '__main__':
    from config import setup_logging
    
    setup_logging()
    logger = logging.getLogger('telescope')
    
    # Create camera with config
    config = get_config()
    state = CameraState.from_config(config)
    
    print("Camera_v2 Demo")
    print("=" * 50)
    print(f"Resolution: {state.width}x{state.height}")
    print(f"ISO: {state.iso}, Shutter: {state.shutter_speed}µs")
    print(f"Brightness: {state.brightness}, Contrast: {state.contrast}")
    print(f"Has Picamera2: {HAS_PICAMERA2}")
    print(f"Has CV2: {HAS_CV2}")
    print(f"Has CV2Helper: {HAS_CV2HELPER}")
    
    # Try creating camera (may fail without hardware)
    try:
        camera = create_camera(state=state, prefer_shell=True)
        print(f"\nCamera created: {type(camera).__name__}")
    except Exception as e:
        print(f"\nCamera creation failed (expected without hardware): {e}")
    
    print("\nCamera_v2 module loaded successfully!")

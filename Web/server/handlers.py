"""
Request Handlers Module

Implements the business logic for each API endpoint.
"""

import os
import sys
import time
import json
import logging
import datetime
import threading
from typing import Dict, Any, Optional
from http import HTTPStatus
from dataclasses import dataclass

# Add project paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
# Add server directory for direct script execution
sys.path.insert(0, os.path.dirname(__file__))

from config import get_config, TelescopeConfig
from config.errors import (
    TelescopeError,
    CameraError,
    MotorError,
    MotorLimitError,
    TrackingError,
    handle_errors,
    ErrorSeverity
)

# Handle both direct execution and module import
try:
    from .routes import (
        APIResponse,
        json_response,
        error_response,
        success_response,
        file_response,
        ParameterParser,
        RouteMatch
    )
except ImportError:
    from routes import (
        APIResponse,
        json_response,
        error_response,
        success_response,
        file_response,
        ParameterParser,
        RouteMatch
    )


# =============================================================================
# Handler State
# =============================================================================

@dataclass
class ServerState:
    """Shared server state."""
    camera_only: bool = False
    ip_address: str = ""
    content_dir: str = "content"
    
    # Will be set by the server
    control_package: Any = None
    camera: Any = None
    tracking_manager: Any = None


# =============================================================================
# Request Handler
# =============================================================================

class RequestHandler:
    """
    Handles API requests and delegates to appropriate methods.
    
    Each public method corresponds to a route handler.
    """
    
    def __init__(self, state: ServerState, config: Optional[TelescopeConfig] = None):
        self.logger = logging.getLogger('telescope.handlers')
        self.config = config or get_config()
        self.state = state
        self.parser = ParameterParser()
    
    # =========================================================================
    # GET Handlers
    # =========================================================================
    
    @handle_errors(severity=ErrorSeverity.ERROR)
    def get_time(
        self,
        match: RouteMatch,
        headers: Dict[str, str],
        body: bytes
    ) -> APIResponse:
        """GET /api/gettime - Get server time and current position."""
        # Get timezone offset
        tz_offset = time.timezone // -36  # Convert to HHMM format
        dt = datetime.datetime.now()
        now_string = f"{dt.strftime('%Y-%m-%d %H:%M:%S')}{tz_offset:+05d}"
        
        # Update adjustments if provided
        params = match.params
        if 'group_0' in params and params['group_0']:
            try:
                az_adj = float(params['group_0'])
                self._update_state('tgazadj', az_adj)
            except ValueError:
                pass
        
        if 'group_1' in params and params['group_1']:
            try:
                alt_adj = float(params['group_1'])
                self._update_state('tgaltadj', alt_adj)
            except ValueError:
                pass
        
        # Get current position (if tracking is set up)
        cur_az = self._get_state('curaz', 0.0)
        cur_alt = self._get_state('curalt', 0.0)
        tg_az = self._get_state('tgaz', 0.0)
        tg_alt = self._get_state('tgalt', 0.0)
        
        return json_response({
            'time': now_string,
            'curaz': f'{cur_az:.4f}',
            'curalt': f'{cur_alt:.4f}',
            'tgaz': f'{tg_az:.4f}',
            'tgalt': f'{tg_alt:.4f}',
        })
    
    @handle_errors(severity=ErrorSeverity.ERROR)
    def get_init_params(
        self,
        match: RouteMatch,
        headers: Dict[str, str],
        body: bytes
    ) -> APIResponse:
        """GET /api/init - Get initial parameters."""
        cp = self.state.control_package
        
        return json_response({
            'vspeed': str(self._get_state('vspeed', self.config.motors.vertical.speed)),
            'vsteps': str(self._get_state('vsteps', self.config.motors.vertical.steps)),
            'hspeed': str(self._get_state('hspeed', self.config.motors.horizontal.speed)),
            'hsteps': str(self._get_state('hsteps', self.config.motors.horizontal.steps)),
            'fspeed': str(self._get_state('fspeed', self.config.motors.focus.speed)),
            'fsteps': str(self._get_state('fsteps', self.config.motors.focus.steps)),
            'ss': str(self._get_state('ss', self.config.camera.defaults.shutter_speed) / 1000.0),
            'iso': str(self._get_state('iso', self.config.camera.defaults.iso)),
            'br': str(self._get_state('brightness', self.config.camera.defaults.brightness)),
            'sh': str(self._get_state('sharpness', self.config.camera.defaults.sharpness)),
            'co': str(self._get_state('contrast', self.config.camera.defaults.contrast)),
            'sa': str(self._get_state('saturation', self.config.camera.defaults.saturation)),
            'tgaz': str(self._get_state('tgaz', 0.0)),
            'tgalt': str(self._get_state('tgalt', 0.0)),
            'tgrah': str(self._get_state('tgrah', 0.0)),
            'tgram': str(self._get_state('tgram', 0.0)),
            'tgras': str(self._get_state('tgras', 0.0)),
            'tgdecdg': str(self._get_state('tgdecdg', 0.0)),
            'tgdecm': str(self._get_state('tgdecm', 0.0)),
            'tgdecs': str(self._get_state('tgdecs', 0.0)),
            'tgazadj': str(self._get_state('tgazadj', 0.0)),
            'tgaltadj': str(self._get_state('tgaltadj', 0.0)),
            'myloclat': str(self._get_state('myloclat', self.config.location.latitude)),
            'myloclong': str(self._get_state('myloclong', self.config.location.longitude)),
        })
    
    @handle_errors(severity=ErrorSeverity.ERROR)
    def stop_tracking(
        self,
        match: RouteMatch,
        headers: Dict[str, str],
        body: bytes
    ) -> APIResponse:
        """GET /api/stoptracking - Stop star tracking."""
        self.logger.info("Stopping tracking")
        
        if self.state.tracking_manager:
            self.state.tracking_manager.stop_tracking()
        
        if self.state.control_package:
            self.state.control_package.isTracking.clear()
        
        return success_response()
    
    def _get_camera(self):
        """Get camera from state or control_package."""
        camera = self.state.camera
        if not camera and self.state.control_package:
            camera = getattr(self.state.control_package, 'camera', None)
        return camera
    
    @handle_errors(severity=ErrorSeverity.ERROR)
    def start_video(
        self,
        match: RouteMatch,
        headers: Dict[str, str],
        body: bytes
    ) -> APIResponse:
        """GET /api/startvideo - Start video streaming."""
        camera = self._get_camera()
        if camera:
            camera.startvideo()
        
        return success_response()
    
    @handle_errors(severity=ErrorSeverity.ERROR)
    def stop_video(
        self,
        match: RouteMatch,
        headers: Dict[str, str],
        body: bytes
    ) -> APIResponse:
        """GET /api/stopvideo - Stop video streaming."""
        camera = self._get_camera()
        if camera:
            camera.stopvideo()
        
        return success_response()
    
    @handle_errors(severity=ErrorSeverity.ERROR)
    def take_snapshot(
        self,
        match: RouteMatch,
        headers: Dict[str, str],
        body: bytes
    ) -> APIResponse:
        """GET /api/snapshot - Take a snapshot image."""
        camera = self._get_camera()
        if not camera:
            return error_response("Camera not available", HTTPStatus.SERVICE_UNAVAILABLE)
        
        try:
            filename = camera.snapshot_full()
            
            with open(filename, 'rb') as f:
                content = f.read()
            
            return file_response(
                content=content,
                content_type='image/jpeg',
                filename=os.path.basename(filename)
            )
        except Exception as e:
            self.logger.error(f"Snapshot failed: {e}")
            return error_response(str(e), HTTPStatus.INTERNAL_SERVER_ERROR)
    
    @handle_errors(severity=ErrorSeverity.ERROR)
    def take_videoshot(
        self,
        match: RouteMatch,
        headers: Dict[str, str],
        body: bytes
    ) -> APIResponse:
        """GET /api/videoshot - Record a video clip."""
        camera = self._get_camera()
        if not camera:
            return error_response("Camera not available", HTTPStatus.SERVICE_UNAVAILABLE)
        
        # Parse camera params from URL path: /api/videoshot/ss/iso/br/sh/co/sa/len
        try:
            path_params = match.params.get('group_0', '').split('/')
            if len(path_params) >= 7:
                self._update_state('ss', int(float(path_params[0]) * 1000))
                self._update_state('iso', int(path_params[1]))
                self._update_state('brightness', int(path_params[2]))
                self._update_state('sharpness', int(path_params[3]))
                self._update_state('contrast', int(path_params[4]))
                self._update_state('saturation', int(path_params[5]))
                self._update_state('videolen', int(path_params[6]))
        except (ValueError, IndexError) as e:
            self.logger.warning(f"Failed to parse videoshot params: {e}")
        
        # Validate and record
        if self.state.control_package:
            self.state.control_package.Validate()
        
        try:
            filename = camera.videoshot()
            
            with open(filename, 'rb') as f:
                content = f.read()
            
            return file_response(
                content=content,
                content_type='application/octet-stream',
                filename=os.path.basename(filename)
            )
        except Exception as e:
            self.logger.error(f"Videoshot failed: {e}")
            return error_response(str(e), HTTPStatus.INTERNAL_SERVER_ERROR)
    
    # =========================================================================
    # POST Handlers
    # =========================================================================
    
    @handle_errors(severity=ErrorSeverity.ERROR)
    def handle_refresh(
        self,
        match: RouteMatch,
        headers: Dict[str, str],
        body: bytes
    ) -> APIResponse:
        """POST /api/refresh - Refresh camera and get new frame."""
        params = self.parser.parse_form_data(body)
        
        # Update camera settings
        camera_params = self.parser.validate_camera_params(params)
        for key, value in camera_params.items():
            self._update_state(key, value)
        
        # Update other settings
        self._update_state('cmode', self.parser.get_string(params, 'cmode', 'day'))
        self._update_state('rawmode', self.parser.get_string(params, 'rawmode', 'false'))
        self._update_state('vflip', self.parser.get_string(params, 'vflip', 'true'))
        self._update_state('hflip', self.parser.get_string(params, 'hflip', 'true'))
        self._update_state('tk_pos_dir', self.parser.get_string(params, 'eqposdir', 'UP'))
        
        # Parse reference points
        refpoints = self.parser.parse_refpoints(
            self.parser.get_string(params, 'refpoints')
        )
        if refpoints:
            self._update_refpoints(*refpoints)
        
        # Update tracking parameters
        blur_limit = self.parser.get_string(params, 'tk_blur_limit')
        if blur_limit:
            self._update_state('tk_blur_limit', int(blur_limit))
        
        thresh_limit = self.parser.get_string(params, 'tk_thresh_limit')
        if thresh_limit:
            self._update_state('tk_thresh_limit', int(thresh_limit))
        
        # Take snapshot
        camera = self._get_camera()
        if camera:
            try:
                # Validate settings before snapshot
                if self.state.control_package:
                    self.state.control_package.Validate()
                localtime, imgstr, err = camera.snapshot()
            except Exception as e:
                self.logger.error(f"Camera snapshot failed: {e}")
                localtime = time.localtime()
                imgstr = ""
                err = True
        else:
            self.logger.warning("No camera available for snapshot")
            localtime = time.localtime()
            imgstr = ""
            err = True
        
        # Build tracking history
        history = self._build_tracking_history()
        
        # Trigger tracking if active
        self._trigger_tracking_if_needed(err)
        
        return json_response({
            'seq': self._get_state('imageseq', 0),
            'timestamp': time.strftime('%Y%m%d-%H%M%S', localtime),
            'trackinghistory': history,
            'image': imgstr
        })
    
    @handle_errors(severity=ErrorSeverity.ERROR)
    def handle_motor(
        self,
        match: RouteMatch,
        headers: Dict[str, str],
        body: bytes
    ) -> APIResponse:
        """POST /api/motor/{motorid}/{direction} - Control motor movement."""
        # Stop tracking when manually controlling motors
        if self.state.control_package:
            self.state.control_package.isTracking.clear()
        
        params = self.parser.parse_form_data(body)
        motor_params = self.parser.validate_motor_params(params)
        
        # Extract motor ID and direction from path
        motor_id = match.params.get('group_0', '').lower()
        direction = match.params.get('group_1', '').upper()
        
        status = True
        status_msg = 'Motor move complete.'
        
        try:
            if motor_id == 'v':
                status, status_msg = self._move_vertical_motor(
                    direction, motor_params
                )
            elif motor_id == 'h':
                status, status_msg = self._move_horizontal_motor(
                    direction, motor_params
                )
            elif motor_id == 'f':
                status, status_msg = self._move_focus_motor(
                    direction, motor_params
                )
            else:
                status = False
                status_msg = f'Unknown motor: {motor_id}'
                
        except MotorLimitError as e:
            status = False
            status_msg = str(e)
        except MotorError as e:
            status = False
            status_msg = f'Motor error: {e}'
        
        return json_response({
            'status': str(status).lower(),
            'detail': status_msg
        })
    
    @handle_errors(severity=ErrorSeverity.ERROR)
    def start_tracking(
        self,
        match: RouteMatch,
        headers: Dict[str, str],
        body: bytes
    ) -> APIResponse:
        """POST /api/starttracking - Start star tracking."""
        params = self.parser.parse_form_data(body)
        
        # Clear reference pattern
        if self.state.control_package:
            self.state.control_package.ref_pattern.clear()
        
        # Parse and validate reference points
        refpoints = self.parser.parse_refpoints(
            self.parser.get_string(params, 'refpoints')
        )
        if refpoints:
            self._update_refpoints(*refpoints)
        
        # Validate tracking parameters
        valid, tracking_params = self.parser.validate_tracking_params(params)
        
        if not valid:
            return json_response({
                'status': 'false',
                'detail': 'Star Tracking not started, check parameters!'
            })
        
        # Apply tracking parameters
        for key, value in tracking_params.items():
            self._update_state(key, value)
        
        # Calculate negative direction
        pos_dir = tracking_params['eqposdir']
        neg_dir = 'DOWN' if pos_dir == 'UP' else 'UP'
        self._update_state('tk_neg_dir', neg_dir)
        
        # Start tracking
        self.logger.info('Starting star tracking...')
        if self.state.control_package:
            self.state.control_package.isTracking.set()
        
        if self.state.tracking_manager:
            # Use new tracking manager
            from StarLocator.StarTracking_v2 import MountMode
            mode = MountMode.EQUATORIAL if tracking_params['altazradec'] == 'RADEC' else MountMode.ALTAZ
            self.state.tracking_manager.set_target(
                mode=mode,
                az=tracking_params.get('tgaz', 0),
                alt=tracking_params.get('tgalt', 0),
                ra_h=tracking_params.get('tgrah', 0),
                ra_m=tracking_params.get('tgram', 0),
                ra_s=tracking_params.get('tgras', 0),
                dec_d=tracking_params.get('tgdecdg', 0),
                dec_m=tracking_params.get('tgdecm', 0),
                dec_s=tracking_params.get('tgdecs', 0),
                az_adj=tracking_params['tgazadj'],
                alt_adj=tracking_params['tgaltadj']
            )
            self.state.tracking_manager.start_tracking()
        
        return json_response({
            'status': 'true',
            'detail': 'Star Tracking Started.'
        })
    
    @handle_errors(severity=ErrorSeverity.ERROR)
    def adjust_offset(
        self,
        match: RouteMatch,
        headers: Dict[str, str],
        body: bytes
    ) -> APIResponse:
        """POST /api/adjoffset - Adjust direction offset."""
        if self.state.control_package:
            az_adj, alt_adj = self.state.control_package.newadj()
        elif self.state.tracking_manager:
            az_adj, alt_adj = self.state.tracking_manager.update_adjustments()
        else:
            az_adj, alt_adj = 0.0, 0.0
        
        return json_response({
            'azadj': f'{az_adj:.2f}',
            'altadj': f'{alt_adj:.2f}'
        })
    
    @handle_errors(severity=ErrorSeverity.ERROR)
    def halt_system(
        self,
        match: RouteMatch,
        headers: Dict[str, str],
        body: bytes,
        client_address: tuple = None
    ) -> APIResponse:
        """POST /api/halt - Halt the system (local IPs only)."""
        # Security check: only allow from local IPs
        if client_address:
            client_ip = client_address[0]
            if not client_ip.startswith('192.') and not client_ip.startswith('10.'):
                self.logger.warning(f"Halt rejected from {client_ip}")
                return error_response("Forbidden", HTTPStatus.FORBIDDEN)
        
        self.logger.info("System halt requested")
        camera = self._get_camera()
        if camera:
            camera.haltsys()
        
        return success_response()
    
    # =========================================================================
    # Static File Handlers
    # =========================================================================
    
    def serve_index(
        self,
        match: RouteMatch,
        headers: Dict[str, str],
        body: bytes
    ) -> APIResponse:
        """Serve index.html."""
        return self._serve_file('index.html', 'text/html')
    
    def serve_html(
        self,
        match: RouteMatch,
        headers: Dict[str, str],
        body: bytes
    ) -> APIResponse:
        """Serve HTML files."""
        filename = match.params.get('group_0', 'index.html')
        return self._serve_file(filename, 'text/html')
    
    def serve_javascript(
        self,
        match: RouteMatch,
        headers: Dict[str, str],
        body: bytes
    ) -> APIResponse:
        """Serve JavaScript files."""
        filename = match.params.get('group_0', '')
        return self._serve_file(filename, 'application/javascript')
    
    def serve_css(
        self,
        match: RouteMatch,
        headers: Dict[str, str],
        body: bytes
    ) -> APIResponse:
        """Serve CSS files."""
        filename = match.params.get('group_0', '')
        return self._serve_file(filename, 'text/css')
    
    def serve_icon(
        self,
        match: RouteMatch,
        headers: Dict[str, str],
        body: bytes
    ) -> APIResponse:
        """Serve icon files."""
        filename = match.params.get('group_0', '')
        return self._serve_file(filename, 'image/x-icon', binary=True)
    
    def serve_image(
        self,
        match: RouteMatch,
        headers: Dict[str, str],
        body: bytes
    ) -> APIResponse:
        """Serve image files."""
        filename = match.params.get('group_0', '')
        ext = filename.rsplit('.', 1)[-1].lower()
        content_type = {
            'gif': 'image/gif',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png'
        }.get(ext, 'application/octet-stream')
        return self._serve_file(filename, content_type, binary=True)
    
    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    def _serve_file(
        self,
        filename: str,
        content_type: str,
        binary: bool = False
    ) -> APIResponse:
        """Serve a static file from content directory."""
        filepath = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            self.state.content_dir,
            filename
        )
        
        if not os.path.isfile(filepath):
            return error_response(f"File not found: {filename}", HTTPStatus.NOT_FOUND)
        
        try:
            mode = 'rb' if binary else 'r'
            with open(filepath, mode) as f:
                content = f.read()
            
            # Replace IP placeholder in HTML/JS
            if not binary and self.state.ip_address:
                if isinstance(content, str):
                    content = content.replace('[IPADDRESS]', self.state.ip_address)
            
            if isinstance(content, str):
                content = content.encode('utf-8')
            
            return APIResponse(
                status=HTTPStatus.OK,
                content_type=content_type,
                body=content
            )
        except Exception as e:
            self.logger.error(f"Error serving file {filename}: {e}")
            return error_response(str(e), HTTPStatus.INTERNAL_SERVER_ERROR)
    
    def _get_state(self, key: str, default: Any = None) -> Any:
        """Get value from control package state."""
        if self.state.control_package:
            return getattr(self.state.control_package, key, default)
        return default
    
    def _update_state(self, key: str, value: Any) -> None:
        """Update control package state."""
        if self.state.control_package:
            setattr(self.state.control_package, key, value)
    
    def _update_refpoints(self, x0: float, y0: float, x1: float, y1: float) -> None:
        """Update reference points and clear tracking queue."""
        cp = self.state.control_package
        if not cp:
            return
        
        # Check if changed
        if (x0 != cp.ref0_x or y0 != cp.ref0_y or 
            x1 != cp.ref1_x or y1 != cp.ref1_y):
            cp.tk_queue.clear()
            cp.ref0_x = x0
            cp.ref0_y = y0
            cp.ref1_x = x1
            cp.ref1_y = y1
            cp.ref_pattern.clear()
    
    def _build_tracking_history(self) -> list:
        """Build tracking history for response."""
        history = []
        cp = self.state.control_package
        
        if cp and hasattr(cp, 'tk_queue'):
            for point in cp.tk_queue:
                history.append({
                    'timestamp': time.strftime('%Y%m%d-%H%M%S', point[0]),
                    'd_ra': f'{point[1]:.2f}',
                    'd_dec': f'{point[2]:.2f}'
                })
        
        return history
    
    def _trigger_tracking_if_needed(self, camera_error: bool) -> None:
        """Trigger tracking correction if conditions are met."""
        cp = self.state.control_package
        if not cp:
            return
        
        if camera_error:
            return
        
        if not cp.isTracking.is_set():
            return
        
        if cp.ipTracking.is_set():
            return
        
        # Start tracking in background thread
        self.logger.debug("Triggering tracking correction")
        if self.state.tracking_manager:
            self.state.tracking_manager.trigger_eq_correction()
        else:
            # Legacy: use old tracking
            try:
                from StarLocator.StarTracking import EQStarTracking
                tr = EQStarTracking()
                t = threading.Thread(target=tr.Track, daemon=True)
                t.start()
                cp.ipTracking.set()
            except Exception as e:
                self.logger.error(f"Failed to start tracking: {e}")
    
    def _move_vertical_motor(
        self,
        direction: str,
        params: Dict[str, Any]
    ) -> tuple:
        """Move vertical motor."""
        cp = self.state.control_package
        if not cp:
            return False, "Control package not initialized"
        
        # Determine actual direction
        v_dir = 'UP' if direction == 'FORWARD' else 'DOWN'
        
        # Check limits
        try:
            import RPi.GPIO as GPIO
            if v_dir == 'UP' and GPIO.input(cp.VH_pin):
                raise MotorLimitError("vertical", "highest")
            if v_dir == 'DOWN' and GPIO.input(cp.VL_pin):
                raise MotorLimitError("vertical", "lowest")
        except ImportError:
            pass  # No GPIO on this system
        
        # Update settings
        cp.vspeed = params['speed']
        cp.vadj = params['adj']
        cp.vsteps = params['steps']
        cp.move_method = 'MICROSTEP'  # Use refined method
        
        # Queue command
        cp.threadLock.acquire()
        cp.v_cmdqueue.put((v_dir, params['speed'], params['adj'], params['steps']))
        cp.threadLock.release()
        
        return True, 'Motor move complete.'
    
    def _move_horizontal_motor(
        self,
        direction: str,
        params: Dict[str, Any]
    ) -> tuple:
        """Move horizontal motor."""
        cp = self.state.control_package
        if not cp:
            return False, "Control package not initialized"
        
        h_dir = 'LEFT' if direction == 'FORWARD' else 'RIGHT'
        
        # Check limits
        try:
            import RPi.GPIO as GPIO
            if h_dir == 'LEFT' and GPIO.input(cp.HL_pin):
                raise MotorLimitError("horizontal", "leftmost")
            if h_dir == 'RIGHT' and GPIO.input(cp.HR_pin):
                raise MotorLimitError("horizontal", "rightmost")
        except ImportError:
            pass
        
        cp.hspeed = params['speed']
        cp.hadj = params['adj']
        cp.hsteps = params['steps']
        
        cp.threadLock.acquire()
        cp.h_cmdqueue.put((h_dir, params['speed'], params['adj'], params['steps']))
        cp.threadLock.release()
        
        return True, 'Motor move complete.'
    
    def _move_focus_motor(
        self,
        direction: str,
        params: Dict[str, Any]
    ) -> tuple:
        """Move focus motor."""
        cp = self.state.control_package
        if not cp:
            return False, "Control package not initialized"
        
        f_dir = 'IN' if direction == 'FORWARD' else 'OUT'
        
        cp.fspeed = params['speed']
        cp.fadj = params['adj']
        cp.fsteps = params['steps']
        
        cp.threadLock.acquire()
        cp.f_cmdqueue.put((f_dir, params['speed'], params['adj'], params['steps']))
        cp.threadLock.release()
        
        return True, 'Motor move complete.'

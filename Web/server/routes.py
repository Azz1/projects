"""
API Routes Module

Defines all API endpoints and their handlers.
"""

import os
import re
import json
import time
import logging
import datetime
from typing import Dict, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field
from urllib.parse import parse_qs
from http import HTTPStatus


# =============================================================================
# Route Definitions
# =============================================================================

@dataclass
class Route:
    """API route definition."""
    pattern: str
    method: str
    handler: str  # Handler method name
    description: str = ""


@dataclass
class RouteMatch:
    """Result of route matching."""
    route: Route
    params: Dict[str, str] = field(default_factory=dict)


class APIRoutes:
    """
    API route registry and matcher.
    
    Separates route definitions from handler implementations.
    """
    
    # GET routes
    GET_ROUTES = [
        Route(r'/api/gettime(?:/([^/]*)/([^/]*))?$', 'GET', 'get_time', 
              'Get server time and position'),
        Route(r'/api/startvideo/(.+)$', 'GET', 'start_video',
              'Start video streaming'),
        Route(r'/api/stopvideo$', 'GET', 'stop_video',
              'Stop video streaming'),
        Route(r'/api/stoptracking$', 'GET', 'stop_tracking',
              'Stop star tracking'),
        Route(r'/api/init$', 'GET', 'get_init_params',
              'Get initial parameters'),
        Route(r'/api/snapshot/(.+)$', 'GET', 'take_snapshot',
              'Take a snapshot image'),
        Route(r'/api/videoshot/(.+)$', 'GET', 'take_videoshot',
              'Record video clip'),
        Route(r'/$', 'GET', 'serve_index',
              'Serve index.html'),
        Route(r'/(.+\.html?)$', 'GET', 'serve_html',
              'Serve HTML files'),
        Route(r'/(.+\.js)$', 'GET', 'serve_javascript',
              'Serve JavaScript files'),
        Route(r'/(.+\.css)$', 'GET', 'serve_css',
              'Serve CSS files'),
        Route(r'/(.+\.ico)$', 'GET', 'serve_icon',
              'Serve icon files'),
        Route(r'/(.+\.(gif|jpg|jpeg|png))$', 'GET', 'serve_image',
              'Serve image files'),
    ]
    
    # POST routes
    POST_ROUTES = [
        Route(r'/api/refresh$', 'POST', 'handle_refresh',
              'Refresh camera and get new frame'),
        Route(r'/api/motor/([^/]+)/([^/]+)$', 'POST', 'handle_motor',
              'Control motor movement'),
        Route(r'/api/starttracking$', 'POST', 'start_tracking',
              'Start star tracking'),
        Route(r'/api/adjoffset$', 'POST', 'adjust_offset',
              'Adjust direction offset'),
        Route(r'/api/halt$', 'POST', 'halt_system',
              'Halt the system'),
    ]
    
    def __init__(self):
        self.logger = logging.getLogger('telescope.routes')
        self._compiled_get = [(re.compile(r.pattern), r) for r in self.GET_ROUTES]
        self._compiled_post = [(re.compile(r.pattern), r) for r in self.POST_ROUTES]
    
    def match(self, method: str, path: str) -> Optional[RouteMatch]:
        """
        Match a request to a route.
        
        Args:
            method: HTTP method (GET, POST)
            path: Request path
            
        Returns:
            RouteMatch if found, None otherwise
        """
        routes = self._compiled_get if method == 'GET' else self._compiled_post
        
        for pattern, route in routes:
            match = pattern.match(path)
            if match:
                params = {f'group_{i}': g for i, g in enumerate(match.groups()) if g}
                self.logger.debug(f"Matched route: {route.handler}")
                return RouteMatch(route=route, params=params)
        
        return None


# =============================================================================
# Request/Response Helpers
# =============================================================================

@dataclass
class APIResponse:
    """Standardized API response."""
    status: HTTPStatus = HTTPStatus.OK
    content_type: str = 'application/json'
    body: Any = None
    headers: Dict[str, str] = field(default_factory=dict)
    
    def to_json(self) -> bytes:
        """Convert body to JSON bytes."""
        if isinstance(self.body, bytes):
            return self.body
        if isinstance(self.body, str):
            return self.body.encode('utf-8')
        return json.dumps(self.body).encode('utf-8')


def json_response(data: Dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> APIResponse:
    """Create a JSON response."""
    return APIResponse(
        status=status,
        content_type='application/json',
        body=data
    )


def error_response(message: str, status: HTTPStatus = HTTPStatus.BAD_REQUEST) -> APIResponse:
    """Create an error response."""
    return json_response(
        {'status': 'false', 'error': message},
        status=status
    )


def success_response(data: Optional[Dict[str, Any]] = None) -> APIResponse:
    """Create a success response."""
    body = {'status': 'true'}
    if data:
        body.update(data)
    return json_response(body)


def file_response(
    content: bytes,
    content_type: str,
    filename: Optional[str] = None
) -> APIResponse:
    """Create a file download response."""
    response = APIResponse(
        status=HTTPStatus.OK,
        content_type=content_type,
        body=content
    )
    if filename:
        response.headers['Content-Disposition'] = f'inline;filename="{filename}"'
    return response


# =============================================================================
# Parameter Parser
# =============================================================================

class ParameterParser:
    """Parse and validate request parameters."""
    
    def __init__(self):
        self.logger = logging.getLogger('telescope.params')
    
    def parse_form_data(self, data: bytes) -> Dict[str, Any]:
        """Parse URL-encoded form data."""
        try:
            return parse_qs(data.decode('utf-8'), keep_blank_values=True)
        except Exception as e:
            self.logger.error(f"Failed to parse form data: {e}")
            return {}
    
    def get_string(
        self,
        params: Dict[str, Any],
        key: str,
        default: str = ""
    ) -> str:
        """Get string parameter."""
        values = params.get(key, [default])
        return values[0] if values else default
    
    def get_int(
        self,
        params: Dict[str, Any],
        key: str,
        default: int = 0
    ) -> int:
        """Get integer parameter."""
        try:
            value = self.get_string(params, key)
            return int(value) if value else default
        except ValueError:
            return default
    
    def get_float(
        self,
        params: Dict[str, Any],
        key: str,
        default: float = 0.0
    ) -> float:
        """Get float parameter."""
        try:
            value = self.get_string(params, key)
            return float(value) if value else default
        except ValueError:
            return default
    
    def parse_path_params(self, path: str, count: int) -> list:
        """Parse parameters from URL path."""
        parts = path.rstrip('/').split('/')
        return parts[-count:] if len(parts) >= count else []
    
    def validate_camera_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and extract camera parameters."""
        return {
            'ss': max(100, int(self.get_float(params, 'ss', 4.0) * 1000)),
            'iso': self._clamp(self.get_int(params, 'iso', 400), 60, 1600),
            'brightness': self._clamp(self.get_int(params, 'br', 10), 0, 100),
            'sharpness': self._clamp(self.get_int(params, 'sh', 20), -100, 100),
            'contrast': self._clamp(self.get_int(params, 'co', 20), -100, 100),
            'saturation': self._clamp(self.get_int(params, 'sa', 100), -100, 100),
        }
    
    def validate_motor_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and extract motor parameters."""
        return {
            'speed': max(1, self.get_int(params, 'speed', 100)),
            'adj': self.get_int(params, 'adj', 0),
            'steps': max(1, self.get_int(params, 'steps', 50)),
        }
    
    def validate_tracking_params(self, params: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """Validate tracking parameters."""
        result = {
            'myloclat': self.get_float(params, 'myloclat'),
            'myloclong': self.get_float(params, 'myloclong'),
            'tgazadj': self.get_float(params, 'tgazadj'),
            'tgaltadj': self.get_float(params, 'tgaltadj'),
            'altazradec': self.get_string(params, 'altazradec', 'ALTAZ'),
            'vspeed': self.get_int(params, 'vspeed', 120),
            'vsteps': self.get_int(params, 'vsteps', 200),
            'vadj': self.get_int(params, 'vadj', 5),
            'hspeed': self.get_int(params, 'hspeed', 50),
            'hsteps': self.get_int(params, 'hsteps', 10),
            'hadj': self.get_int(params, 'hadj', 3),
            'eqposdir': self.get_string(params, 'eqposdir', 'UP'),
        }
        
        # Add mode-specific params
        if result['altazradec'] == 'ALTAZ':
            result['tgaz'] = self.get_float(params, 'tgaz')
            result['tgalt'] = self.get_float(params, 'tgalt')
            valid = result['tgaz'] != 0 or result['tgalt'] != 0
        else:
            result['tgrah'] = self.get_float(params, 'tgrah')
            result['tgram'] = self.get_float(params, 'tgram')
            result['tgras'] = self.get_float(params, 'tgras')
            result['tgdecdg'] = self.get_float(params, 'tgdecdg')
            result['tgdecm'] = self.get_float(params, 'tgdecm')
            result['tgdecs'] = self.get_float(params, 'tgdecs')
            valid = True  # RADEC params can be zero
        
        # Check required params
        if not result['myloclat'] and not result['myloclong']:
            valid = False
        
        return valid, result
    
    def parse_refpoints(self, refpoints_str: str) -> Optional[Tuple[float, float, float, float]]:
        """Parse reference points string."""
        if not refpoints_str:
            return None
        
        try:
            parts = refpoints_str.split(',')
            if len(parts) != 4:
                return None
            
            x0, y0, x1, y1 = map(float, parts)
            
            # Validate minimum distance
            if abs(x0 - x1) <= 1.0 and abs(y0 - y1) <= 1.0:
                return None
            
            return (x0, y0, x1, y1)
        except (ValueError, IndexError):
            return None
    
    @staticmethod
    def _clamp(value: int, min_val: int, max_val: int) -> int:
        """Clamp value to range."""
        return max(min_val, min(max_val, value))

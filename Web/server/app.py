"""
Telescope Web Server Application

Main server application with threading support.
"""

import os
import sys
import time
import logging
import argparse
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from http import HTTPStatus
from typing import Optional
import http.cookies

# Add project paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
# Add server directory for direct script execution
sys.path.insert(0, os.path.dirname(__file__))

from config import get_config, setup_logging, TelescopeConfig
from config.errors import handle_errors, ErrorSeverity

# Handle both direct execution and module import
try:
    from .routes import APIRoutes, RouteMatch
    from .handlers import RequestHandler, ServerState
except ImportError:
    from routes import APIRoutes, RouteMatch
    from handlers import RequestHandler, ServerState


# =============================================================================
# HTTP Request Handler
# =============================================================================

class TelescopeHTTPHandler(BaseHTTPRequestHandler):
    """
    HTTP request handler for telescope control server.
    
    Delegates to RequestHandler for business logic.
    """
    
    # Class-level shared state (set by server)
    routes: APIRoutes = None
    handler: RequestHandler = None
    state: ServerState = None
    
    def __init__(self, *args, **kwargs):
        self.logger = logging.getLogger('telescope.http')
        self.cookie = http.cookies.SimpleCookie()
        super().__init__(*args, **kwargs)
    
    def _get_cookie(self) -> None:
        """Parse cookie from request headers."""
        if "Cookie" in self.headers:
            self.cookie = http.cookies.SimpleCookie(self.headers["Cookie"])
        else:
            # Set defaults
            self.cookie = http.cookies.SimpleCookie()
            self.cookie['refined'] = 'true'
            self.cookie['norefresh'] = 'false'
            self.cookie['cmode'] = 'day'
            self.cookie['rawmode'] = 'false'
            self.cookie['vflip'] = 'true'
            self.cookie['hflip'] = 'true'
    
    def _send_cookie(self) -> None:
        """Send cookie in response headers."""
        for c in self.cookie.values():
            self.send_header('Set-Cookie', c.output(header='').lstrip())
    
    def _send_response(self, response) -> None:
        """Send APIResponse to client."""
        self.send_response(response.status.value)
        self.send_header('Content-Type', response.content_type)
        
        for key, value in response.headers.items():
            self.send_header(key, value)
        
        self._send_cookie()
        self.end_headers()
        
        body = response.to_json()
        self.wfile.write(body)
    
    def _handle_request(self, method: str) -> None:
        """Handle HTTP request."""
        self._get_cookie()
        
        # Match route
        match = self.routes.match(method, self.path)
        
        if not match:
            self.send_error(HTTPStatus.FORBIDDEN.value)
            return
        
        # Read body for POST
        body = b''
        if method == 'POST':
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                body = self.rfile.read(content_length)
        
        # Get handler method
        handler_method = getattr(self.handler, match.route.handler, None)
        if not handler_method:
            self.logger.error(f"Handler not found: {match.route.handler}")
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR.value)
            return
        
        # Execute handler
        try:
            # Add client address for security checks
            if match.route.handler == 'halt_system':
                response = handler_method(
                    match, 
                    dict(self.headers), 
                    body,
                    client_address=self.client_address
                )
            else:
                response = handler_method(match, dict(self.headers), body)
            
            self._send_response(response)
            
        except Exception as e:
            self.logger.exception(f"Handler error: {e}")
            self.send_error(
                HTTPStatus.INTERNAL_SERVER_ERROR.value,
                str(e)
            )
    
    def do_GET(self):
        """Handle GET request."""
        self._handle_request('GET')
    
    def do_POST(self):
        """Handle POST request."""
        self._handle_request('POST')
    
    def log_message(self, format, *args):
        """Override to use logging module."""
        self.logger.info("%s - %s", self.client_address[0], format % args)


# =============================================================================
# Threaded HTTP Server
# =============================================================================

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """HTTP server with threading support."""
    
    daemon_threads = True
    allow_reuse_address = True
    
    def shutdown(self):
        """Clean shutdown."""
        self.socket.close()
        HTTPServer.shutdown(self)


# =============================================================================
# Main Server Class
# =============================================================================

class TelescopeServer:
    """
    Main telescope control web server.
    
    Usage:
        server = TelescopeServer(ip='0.0.0.0', port=8080)
        server.start()
        # ... server runs ...
        server.stop()
    """
    
    def __init__(
        self,
        ip: str = '0.0.0.0',
        port: int = 8080,
        camera_only: bool = False,
        config: Optional[TelescopeConfig] = None
    ):
        self.logger = logging.getLogger('telescope.server')
        self.config = config or get_config()
        
        self.ip = ip
        self.port = port
        self.camera_only = camera_only
        
        # Initialize state
        self.state = ServerState(
            camera_only=camera_only,
            ip_address=ip,
            content_dir=self.config.web_server.content_dir
        )
        
        # Initialize routes and handler
        self.routes = APIRoutes()
        self.handler = RequestHandler(self.state, self.config)
        
        # Set class-level references for HTTP handler
        TelescopeHTTPHandler.routes = self.routes
        TelescopeHTTPHandler.handler = self.handler
        TelescopeHTTPHandler.state = self.state
        
        # Server instance
        self._server: Optional[ThreadedHTTPServer] = None
        self._server_thread: Optional[threading.Thread] = None
        
        self.logger.info(f"Telescope server initialized on {ip}:{port}")
        if camera_only:
            self.logger.info("Running in CAMERA ONLY mode")
    
    def set_control_package(self, control_package) -> None:
        """Set the control package reference."""
        self.state.control_package = control_package
        self.logger.debug("Control package connected")
    
    def set_camera(self, camera) -> None:
        """Set the camera reference."""
        self.state.camera = camera
        self.logger.debug("Camera connected")
    
    def set_tracking_manager(self, tracking_manager) -> None:
        """Set the tracking manager reference."""
        self.state.tracking_manager = tracking_manager
        self.logger.debug("Tracking manager connected")
    
    def start(self) -> None:
        """Start the server in a background thread."""
        self._server = ThreadedHTTPServer(
            (self.ip, self.port),
            TelescopeHTTPHandler
        )
        
        self._server_thread = threading.Thread(
            target=self._server.serve_forever,
            daemon=True
        )
        self._server_thread.start()
        
        self.logger.info(f"Server started on http://{self.ip}:{self.port}")
    
    def serve_forever(self) -> None:
        """Start server and block until shutdown."""
        self.start()
        self._server_thread.join()
    
    def stop(self) -> None:
        """Stop the server."""
        if self._server:
            self.logger.info("Stopping server...")
            self._server.shutdown()
            
            if self._server_thread:
                self._server_thread.join(timeout=5)
            
            self._server = None
            self._server_thread = None
            self.logger.info("Server stopped")
    
    def wait(self) -> None:
        """Wait for server to stop."""
        if self._server_thread:
            self._server_thread.join()


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    """Main entry point for standalone server."""
    parser = argparse.ArgumentParser(description='Telescope Control HTTP Server')
    parser.add_argument('port', type=int, nargs='?', default=8080,
                        help='Listening port (default: 8080)')
    parser.add_argument('ip', nargs='?', default='0.0.0.0',
                        help='Server IP address (default: 0.0.0.0)')
    parser.add_argument('--camera-only', '-c', action='store_true',
                        help='Run in camera-only mode')
    parser.add_argument('--config', '-f', type=str,
                        help='Configuration file path')
    args = parser.parse_args()
    
    # Setup logging
    setup_logging()
    logger = logging.getLogger('telescope')
    
    # Load config
    config = get_config(args.config)
    
    # Create server
    server = TelescopeServer(
        ip=args.ip,
        port=args.port,
        camera_only=args.camera_only,
        config=config
    )
    
    # Connect to hardware
    try:
        # Import hardware modules
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'Adafruit'))
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'StarLocator'))
        
        # Always need ControlPackage for camera settings (even in camera-only mode)
        # Use legacy StepMotor since Camera.py imports from it directly
        from StepMotor import ControlPackage
        server.set_control_package(ControlPackage)
        logger.info("Using legacy StepMotor (required for Camera)")
        
        # Set IP in control package
        ControlPackage.ip = args.ip
        
        # Initialize camera (needed for both modes)
        try:
            # Try new Camera_v2 first
            try:
                from Camera_v2 import create_camera, ControlPackageProxy
                camera = create_camera(control_package=ControlPackage, prefer_shell=True)
                ControlPackage.camera = camera
                server.set_camera(camera)
                logger.info("Camera initialized (Camera_v2)")
            except ImportError:
                # Fall back to legacy Camera module
                import Camera
                if hasattr(ControlPackage, 'camera') and ControlPackage.camera:
                    server.set_camera(ControlPackage.camera)
                    logger.info("Camera initialized (legacy)")
                else:
                    logger.warning("Camera not initialized in control package")
        except ImportError as e:
            logger.warning(f"Camera module not available: {e}")
        except Exception as e:
            logger.error(f"Camera initialization failed: {e}")
        
        # Start motors only if not camera-only mode
        if not args.camera_only:
            # Motors are started automatically when StepMotor is imported
            logger.info("Motor control enabled")
            
            # Try to use new tracking manager
            try:
                from StarTracking_v2 import TrackingManager
                tracking_manager = TrackingManager(config)
                server.set_tracking_manager(tracking_manager)
            except ImportError:
                logger.info("Using legacy tracking system")
        else:
            # In camera-only mode, stop motor threads
            ControlPackage.exitFlag.clear()
            logger.info("Camera-only mode: motors disabled")
        
    except ImportError as e:
        logger.warning(f"Hardware modules not available: {e}")
        logger.info("Running without hardware control")
    
    # Start server
    logger.info("Starting HTTP server...")
    server.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutdown requested")
    finally:
        server.stop()
        
        # Release hardware
        if not args.camera_only and server.state.control_package:
            try:
                cp = server.state.control_package
                cp.exit_flag.clear()
                cp.release()
            except Exception as e:
                logger.warning(f"Error releasing hardware: {e}")
    
    logger.info("Server shutdown complete")


if __name__ == '__main__':
    main()

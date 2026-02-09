"""
Telescope Error Handling Module

Custom exceptions and error handling utilities.
"""

import logging
import functools
import traceback
from typing import Callable, Optional, Any, Type
from enum import Enum


# =============================================================================
# Custom Exceptions
# =============================================================================

class TelescopeError(Exception):
    """Base exception for telescope operations."""
    
    def __init__(self, message: str, cause: Optional[Exception] = None):
        super().__init__(message)
        self.message = message
        self.cause = cause
    
    def __str__(self):
        if self.cause:
            return f"{self.message} (caused by: {self.cause})"
        return self.message


class MotorError(TelescopeError):
    """Motor operation errors."""
    pass


class MotorLimitError(MotorError):
    """Motor has reached its limit switch."""
    
    def __init__(self, motor: str, direction: str):
        super().__init__(f"{motor} motor reached {direction} limit")
        self.motor = motor
        self.direction = direction


class MotorTimeoutError(MotorError):
    """Motor operation timed out."""
    pass


class SensorError(TelescopeError):
    """Sensor reading errors."""
    pass


class MagnetometerError(SensorError):
    """Magnetometer specific errors."""
    pass


class CameraError(TelescopeError):
    """Camera operation errors."""
    pass


class CameraNotReadyError(CameraError):
    """Camera is not ready or initialized."""
    pass


class TrackingError(TelescopeError):
    """Star tracking errors."""
    pass


class TrackingLostError(TrackingError):
    """Lost tracking of target."""
    pass


class CommunicationError(TelescopeError):
    """Serial/network communication errors."""
    pass


class ConfigurationError(TelescopeError):
    """Configuration errors."""
    pass


# =============================================================================
# Error Severity Levels
# =============================================================================

class ErrorSeverity(Enum):
    """Error severity levels for handling decisions."""
    DEBUG = 1       # Log only, continue
    INFO = 2        # Log, maybe notify, continue
    WARNING = 3     # Log, notify, continue with caution
    ERROR = 4       # Log, notify, try to recover
    CRITICAL = 5    # Log, notify, stop operations


# =============================================================================
# Error Handler Class
# =============================================================================

class ErrorHandler:
    """Centralized error handling with recovery strategies."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger('telescope.errors')
        self._error_counts = {}
        self._max_retries = 3
        self._recovery_callbacks = {}
    
    def register_recovery(
        self, 
        error_type: Type[TelescopeError], 
        callback: Callable
    ):
        """Register a recovery callback for an error type."""
        self._recovery_callbacks[error_type] = callback
    
    def handle(
        self, 
        error: Exception, 
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: Optional[str] = None
    ) -> bool:
        """
        Handle an error with appropriate logging and recovery.
        
        Returns True if recovered, False if not.
        """
        error_key = f"{type(error).__name__}:{context or 'default'}"
        self._error_counts[error_key] = self._error_counts.get(error_key, 0) + 1
        
        # Log based on severity
        log_msg = f"[{context}] {error}" if context else str(error)
        
        if severity == ErrorSeverity.DEBUG:
            self.logger.debug(log_msg)
        elif severity == ErrorSeverity.INFO:
            self.logger.info(log_msg)
        elif severity == ErrorSeverity.WARNING:
            self.logger.warning(log_msg)
        elif severity == ErrorSeverity.ERROR:
            self.logger.error(log_msg)
            self.logger.debug(traceback.format_exc())
        elif severity == ErrorSeverity.CRITICAL:
            self.logger.critical(log_msg)
            self.logger.error(traceback.format_exc())
        
        # Try recovery if available
        for error_type, callback in self._recovery_callbacks.items():
            if isinstance(error, error_type):
                try:
                    self.logger.info(f"Attempting recovery for {type(error).__name__}")
                    callback(error)
                    self.logger.info("Recovery successful")
                    return True
                except Exception as recovery_error:
                    self.logger.error(f"Recovery failed: {recovery_error}")
                    return False
        
        return False
    
    def get_error_count(self, error_type: str, context: str = 'default') -> int:
        """Get count of errors of a specific type."""
        key = f"{error_type}:{context}"
        return self._error_counts.get(key, 0)
    
    def reset_counts(self):
        """Reset all error counts."""
        self._error_counts = {}


# =============================================================================
# Decorators for Error Handling
# =============================================================================

def handle_errors(
    logger: Optional[logging.Logger] = None,
    default_return: Any = None,
    reraise: bool = False,
    severity: ErrorSeverity = ErrorSeverity.ERROR,
    error_types: tuple = (Exception,)
):
    """
    Decorator for automatic error handling.
    
    Usage:
        @handle_errors(logger=my_logger, default_return=0)
        def risky_function():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            _logger = logger or logging.getLogger('telescope')
            try:
                return func(*args, **kwargs)
            except error_types as e:
                context = f"{func.__module__}.{func.__name__}"
                
                if severity == ErrorSeverity.DEBUG:
                    _logger.debug(f"[{context}] {e}")
                elif severity == ErrorSeverity.INFO:
                    _logger.info(f"[{context}] {e}")
                elif severity == ErrorSeverity.WARNING:
                    _logger.warning(f"[{context}] {e}")
                elif severity == ErrorSeverity.ERROR:
                    _logger.error(f"[{context}] {e}")
                else:
                    _logger.critical(f"[{context}] {e}")
                    _logger.error(traceback.format_exc())
                
                if reraise:
                    raise
                return default_return
        return wrapper
    return decorator


def retry_on_error(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    error_types: tuple = (Exception,),
    logger: Optional[logging.Logger] = None
):
    """
    Decorator for automatic retry on errors.
    
    Usage:
        @retry_on_error(max_retries=3, delay=1.0)
        def flaky_function():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            _logger = logger or logging.getLogger('telescope')
            last_error = None
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except error_types as e:
                    last_error = e
                    if attempt < max_retries:
                        _logger.warning(
                            f"{func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                            f"Retrying in {current_delay:.1f}s..."
                        )
                        import time
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        _logger.error(
                            f"{func.__name__} failed after {max_retries + 1} attempts: {e}"
                        )
            
            raise last_error
        return wrapper
    return decorator


def validate_args(**validators):
    """
    Decorator for argument validation.
    
    Usage:
        @validate_args(
            speed=lambda x: 0 < x <= 1000,
            steps=lambda x: x > 0
        )
        def move_motor(speed, steps):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            import inspect
            sig = inspect.signature(func)
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            
            for param_name, validator in validators.items():
                if param_name in bound.arguments:
                    value = bound.arguments[param_name]
                    if not validator(value):
                        raise ValueError(
                            f"Invalid value for '{param_name}': {value}"
                        )
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


# =============================================================================
# Global Error Handler Instance
# =============================================================================

_error_handler: Optional[ErrorHandler] = None


def get_error_handler() -> ErrorHandler:
    """Get global error handler instance."""
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler()
    return _error_handler

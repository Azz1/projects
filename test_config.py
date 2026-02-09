#!/usr/bin/env python3
"""
Test script for the new configuration and error handling system.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

def test_config_loading():
    """Test configuration loading."""
    print("\n" + "=" * 60)
    print("Testing Configuration Loading")
    print("=" * 60)
    
    from config import get_config, setup_logging
    
    # Setup logging first
    logger = setup_logging()
    
    # Load config
    config = get_config()
    
    print(f"\n✓ Location: {config.location.latitude}, {config.location.longitude}")
    print(f"✓ Timezone: {config.location.timezone}")
    print(f"✓ Motor V pins: {config.motors.vertical.pins}")
    print(f"✓ Motor H pins: {config.motors.horizontal.pins}")
    print(f"✓ Tracking threshold: {config.tracking.threshold_limit}")
    print(f"✓ Camera resolution: {config.camera.resolution.width}x{config.camera.resolution.height}")
    print(f"✓ Web server: {config.web_server.host}:{config.web_server.port}")
    
    return True


def test_error_handling():
    """Test error handling decorators."""
    print("\n" + "=" * 60)
    print("Testing Error Handling")
    print("=" * 60)
    
    from config.errors import (
        handle_errors, 
        retry_on_error, 
        validate_args,
        MotorError,
        MotorLimitError,
        ErrorSeverity
    )
    import logging
    
    logger = logging.getLogger('test')
    
    # Test @handle_errors decorator
    @handle_errors(logger=logger, default_return=-1, severity=ErrorSeverity.WARNING)
    def risky_division(a, b):
        return a / b
    
    result = risky_division(10, 2)
    print(f"✓ Normal division: 10/2 = {result}")
    
    result = risky_division(10, 0)
    print(f"✓ Division by zero handled, returned: {result}")
    
    # Test @validate_args decorator
    @validate_args(speed=lambda x: 0 < x <= 1000)
    def set_speed(speed):
        return f"Speed set to {speed}"
    
    result = set_speed(500)
    print(f"✓ Valid speed: {result}")
    
    try:
        set_speed(-10)
        print("✗ Should have raised ValueError")
    except ValueError as e:
        print(f"✓ Invalid speed caught: {e}")
    
    # Test custom exceptions
    error = MotorLimitError("vertical", "upper")
    print(f"✓ Custom exception: {error}")
    
    # Test @retry_on_error decorator
    attempt_count = [0]
    
    @retry_on_error(max_retries=2, delay=0.1, error_types=(ValueError,))
    def flaky_operation():
        attempt_count[0] += 1
        if attempt_count[0] < 3:
            raise ValueError("Not ready yet")
        return "Success!"
    
    result = flaky_operation()
    print(f"✓ Retry decorator: {result} (after {attempt_count[0]} attempts)")
    
    return True


def test_star_locator():
    """Test refactored StarLocator."""
    print("\n" + "=" * 60)
    print("Testing StarLocator")
    print("=" * 60)
    
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'StarLocator'))
    
    from StarLocator_v2 import StarLocator, CelestialCoords, HorizontalCoords
    from datetime import datetime
    
    # Create locator
    locator = StarLocator()
    
    print(f"✓ StarLocator created for ({locator.latitude}, {locator.longitude})")
    
    # Test with known coordinates
    # Polaris: RA 02h 31m 49s, DEC +89° 15′ 51″
    polaris = CelestialCoords(
        ra_hours=2, ra_minutes=31, ra_seconds=49,
        dec_degrees=89, dec_minutes=15, dec_seconds=51
    )
    
    print(f"✓ Polaris RA: {polaris.ra_decimal:.4f}°, DEC: {polaris.dec_decimal:.4f}°")
    
    result = locator.celestial_to_horizontal(polaris)
    print(f"✓ Polaris position: {result}")
    
    # Test legacy interface
    az, alt = locator.RaDec2AltAz1(2, 31, 49, 89, 15, 51, datetime.utcnow())
    print(f"✓ Legacy interface: AZ={az:.4f}°, ALT={alt:.4f}°")
    
    # Test validation
    try:
        locator.ra_dec_to_alt_az(400, 0)  # Invalid RA
        print("✗ Should have raised error for invalid RA")
    except ValueError as e:
        print(f"✓ Validation caught invalid RA: {e}")
    
    return True


def main():
    """Run all tests."""
    print("\n" + "#" * 60)
    print("# Telescope Configuration & Error Handling Tests")
    print("#" * 60)
    
    tests = [
        ("Config Loading", test_config_loading),
        ("Error Handling", test_error_handling),
        ("Star Locator", test_star_locator),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"\n✗ {name} failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    all_passed = True
    for name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"  {status}: {name}")
        if not success:
            all_passed = False
    
    print()
    if all_passed:
        print("All tests passed! 🎉")
        return 0
    else:
        print("Some tests failed. 😞")
        return 1


if __name__ == '__main__':
    sys.exit(main())

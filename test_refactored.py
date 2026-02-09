#!/usr/bin/env python3
"""
Test script for refactored StarTracking and Web Server modules.
"""

import sys
import os

# Add project paths
sys.path.insert(0, os.path.dirname(__file__))


def test_star_tracking_v2():
    """Test the refactored StarTracking module."""
    print("\n" + "=" * 60)
    print("Testing StarTracking_v2")
    print("=" * 60)
    
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'StarLocator'))
    
    from StarTracking_v2 import (
        TrackingManager,
        TrackingState,
        MountMode,
        Target,
        TrackingPoint,
        WeightedAverageCalculator
    )
    from config import get_config
    from datetime import datetime
    
    # Test TrackingState
    state = TrackingState()
    print(f"✓ TrackingState created")
    print(f"  - exit_flag set: {state.exit_flag.is_set()}")
    print(f"  - is_tracking: {state.is_tracking.is_set()}")
    
    # Test Target dataclass
    target = Target(
        azimuth=180.0,
        altitude=45.0,
        ra_hours=5, ra_minutes=30, ra_seconds=0,
        dec_degrees=22, dec_minutes=0, dec_seconds=0
    )
    print(f"✓ Target created: AZ={target.azimuth}°, ALT={target.altitude}°")
    
    # Test WeightedAverageCalculator
    calculator = WeightedAverageCalculator(reference_count=3)
    
    from collections import deque
    history = deque(maxlen=20)
    history.append(TrackingPoint(datetime.now(), delta_ra=1.0))
    history.append(TrackingPoint(datetime.now(), delta_ra=2.0))
    history.append(TrackingPoint(datetime.now(), delta_ra=3.0))
    
    avg = calculator.calculate(history, lambda p: p.delta_ra)
    # Expected: (3*3 + 2*2 + 1*1) / (3+2+1) = 14/6 = 2.33
    print(f"✓ WeightedAverageCalculator: avg_ra = {avg:.2f} (expected ~2.33)")
    
    # Test TrackingManager
    config = get_config()
    manager = TrackingManager(config)
    print(f"✓ TrackingManager created")
    
    manager.set_target(
        mode=MountMode.ALTAZ,
        az=270.0,
        alt=30.0
    )
    print(f"✓ Target set: mode={manager.state.mode.value}")
    
    # Test tracking point addition
    manager.add_tracking_point(TrackingPoint(
        timestamp=datetime.now(),
        delta_ra=0.5,
        delta_dec=0.3
    ))
    print(f"✓ Tracking point added, history size: {len(manager.state.history)}")
    
    return True


def test_web_server_routes():
    """Test the web server routes module."""
    print("\n" + "=" * 60)
    print("Testing Web Server Routes")
    print("=" * 60)
    
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'Web'))
    
    from server.routes import (
        APIRoutes,
        ParameterParser,
        json_response,
        error_response,
        success_response
    )
    from http import HTTPStatus
    
    # Test route matching
    routes = APIRoutes()
    
    # Test GET routes
    match = routes.match('GET', '/api/init')
    assert match is not None
    print(f"✓ Route matched: /api/init -> {match.route.handler}")
    
    match = routes.match('GET', '/api/gettime/1.5/2.5')
    assert match is not None
    print(f"✓ Route matched with params: /api/gettime/1.5/2.5 -> {match.route.handler}")
    print(f"  Params: {match.params}")
    
    match = routes.match('GET', '/')
    assert match is not None
    print(f"✓ Route matched: / -> {match.route.handler}")
    
    # Test POST routes
    match = routes.match('POST', '/api/motor/v/FORWARD')
    assert match is not None
    print(f"✓ Route matched: /api/motor/v/FORWARD -> {match.route.handler}")
    print(f"  Params: {match.params}")
    
    # Test no match
    match = routes.match('GET', '/nonexistent')
    assert match is None
    print(f"✓ No match for invalid route")
    
    # Test ParameterParser
    parser = ParameterParser()
    
    # Test form data parsing
    form_data = b'speed=100&adj=5&steps=50'
    params = parser.parse_form_data(form_data)
    print(f"✓ Form data parsed: {params}")
    
    motor_params = parser.validate_motor_params(params)
    print(f"✓ Motor params validated: {motor_params}")
    
    # Test response helpers
    resp = json_response({'test': 'value'})
    assert resp.status == HTTPStatus.OK
    print(f"✓ json_response created")
    
    resp = error_response('Test error')
    assert resp.status == HTTPStatus.BAD_REQUEST
    print(f"✓ error_response created")
    
    resp = success_response({'extra': 'data'})
    assert resp.status == HTTPStatus.OK
    print(f"✓ success_response created")
    
    # Test refpoints parsing
    refpoints = parser.parse_refpoints("100.5,200.3,150.8,250.6")
    assert refpoints == (100.5, 200.3, 150.8, 250.6)
    print(f"✓ Reference points parsed: {refpoints}")
    
    # Invalid refpoints (too close)
    refpoints = parser.parse_refpoints("100,100,100.5,100.5")
    assert refpoints is None
    print(f"✓ Invalid reference points rejected")
    
    return True


def test_web_server_handlers():
    """Test the web server handlers module."""
    print("\n" + "=" * 60)
    print("Testing Web Server Handlers")
    print("=" * 60)
    
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'Web'))
    
    from server.handlers import RequestHandler, ServerState
    from server.routes import APIRoutes, RouteMatch
    from config import get_config
    
    # Create handler
    state = ServerState(
        camera_only=True,
        ip_address='127.0.0.1'
    )
    config = get_config()
    handler = RequestHandler(state, config)
    
    print(f"✓ RequestHandler created")
    
    # Test get_time handler
    routes = APIRoutes()
    match = routes.match('GET', '/api/gettime')
    
    response = handler.get_time(match, {}, b'')
    assert response.status.value == 200
    print(f"✓ get_time handler works")
    
    import json
    body = json.loads(response.to_json())
    assert 'time' in body
    print(f"  Time: {body['time']}")
    
    # Test get_init_params handler
    match = routes.match('GET', '/api/init')
    response = handler.get_init_params(match, {}, b'')
    assert response.status.value == 200
    print(f"✓ get_init_params handler works")
    
    # Test stop_tracking handler
    match = routes.match('GET', '/api/stoptracking')
    response = handler.stop_tracking(match, {}, b'')
    assert response.status.value == 200
    print(f"✓ stop_tracking handler works")
    
    return True


def test_step_motor_v2():
    """Test the refactored StepMotor module."""
    print("\n" + "=" * 60)
    print("Testing StepMotor_v2 (ControlPackage)")
    print("=" * 60)
    
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'Adafruit'))
    
    from StepMotor_v2 import (
        ControlPackageV2,
        get_control_package,
        MotorType,
        MotorCommand,
        CameraSettings,
        MotorSettings,
        TrackingSettings
    )
    from config import get_config
    
    # Reset singleton for clean test
    ControlPackageV2.reset_instance()
    
    # Get control package
    config = get_config()
    cp = get_control_package(config)
    print(f"✓ ControlPackageV2 singleton created")
    
    # Test that it's truly a singleton
    cp2 = get_control_package()
    assert cp is cp2
    print(f"✓ Singleton pattern verified")
    
    # Test camera settings (backward compatible)
    assert cp.width == 700
    assert cp.height == 524
    print(f"✓ Camera settings: {cp.width}x{cp.height}")
    
    # Test camera property setters with validation
    cp.brightness = 150  # Should clamp to 100
    assert cp.brightness == 100
    print(f"✓ Brightness clamped: 150 -> {cp.brightness}")
    
    cp.iso = 50  # Should clamp to 60
    assert cp.iso == 60
    print(f"✓ ISO clamped: 50 -> {cp.iso}")
    
    cp.shutter_speed = 50  # Should clamp to 100
    cp.ss = 50  # Alias
    assert cp.ss == 100
    print(f"✓ Shutter speed clamped: 50 -> {cp.ss}")
    
    # Test motor settings
    assert cp.vspeed > 0
    assert cp.vsteps > 0
    print(f"✓ Vertical motor: speed={cp.vspeed}, steps={cp.vsteps}")
    
    assert cp.hspeed > 0
    assert cp.hsteps > 0
    print(f"✓ Horizontal motor: speed={cp.hspeed}, steps={cp.hsteps}")
    
    # Test motor setters with validation
    cp.vspeed = -10  # Should clamp to 1
    assert cp.vspeed == 1
    print(f"✓ Motor speed clamped: -10 -> {cp.vspeed}")
    
    # Reset to valid value
    cp.vspeed = 200
    
    # Test tracking settings
    assert cp.myloclat != 0
    assert cp.myloclong != 0
    print(f"✓ Location: lat={cp.myloclat}, long={cp.myloclong}")
    
    # Test tracking setters
    cp.tgaz = 180.0
    cp.tgalt = 45.0
    assert cp.tgaz == 180.0
    assert cp.tgalt == 45.0
    print(f"✓ Target set: AZ={cp.tgaz}, ALT={cp.tgalt}")
    
    # Test newadj calculation
    cp.curaz = 175.0
    cp.curalt = 44.0
    cp.tgazadj = 0.0
    cp.tgaltadj = 0.0
    
    az_adj, alt_adj = cp.newadj()
    assert az_adj == 5.0  # 180 - 175
    assert alt_adj == 1.0  # 45 - 44
    print(f"✓ newadj calculation: AZ={az_adj}, ALT={alt_adj}")
    
    # Test threading events (backward compatible aliases)
    assert cp.exitFlag is cp.exit_flag
    assert cp.isTracking is cp.is_tracking
    assert cp.threadLock is cp.thread_lock
    print(f"✓ Threading aliases work correctly")
    
    # Test command queues exist
    assert cp.v_cmdqueue is not None
    assert cp.h_cmdqueue is not None
    assert cp.f_cmdqueue is not None
    print(f"✓ Command queues initialized")
    
    # Test tracking queue
    from datetime import datetime
    from collections import deque
    assert isinstance(cp.tk_queue, deque)
    assert cp.tk_queue.maxlen == 20
    print(f"✓ Tracking queue: maxlen={cp.tk_queue.maxlen}")
    
    # Test GPIO pin attributes (if available)
    if hasattr(cp, 'VL_pin'):
        print(f"✓ GPIO pins: VL={cp.VL_pin}, VH={cp.VH_pin}, HL={cp.HL_pin}, HR={cp.HR_pin}")
    
    # Cleanup
    ControlPackageV2.reset_instance()
    print(f"✓ Singleton reset for clean state")
    
    return True


def test_server_creation():
    """Test server creation without starting."""
    print("\n" + "=" * 60)
    print("Testing Server Creation")
    print("=" * 60)
    
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'Web'))
    
    from server.app import TelescopeServer
    from config import get_config
    
    config = get_config()
    
    # Create server (don't start)
    server = TelescopeServer(
        ip='127.0.0.1',
        port=9999,
        camera_only=True,
        config=config
    )
    
    print(f"✓ TelescopeServer created")
    print(f"  IP: {server.ip}")
    print(f"  Port: {server.port}")
    print(f"  Camera only: {server.camera_only}")
    
    return True


def main():
    """Run all tests."""
    print("\n" + "#" * 60)
    print("# Refactored Modules Tests")
    print("#" * 60)
    
    # Setup logging
    from config import setup_logging
    setup_logging()
    
    tests = [
        ("StarTracking_v2", test_star_tracking_v2),
        ("StepMotor_v2", test_step_motor_v2),
        ("Web Server Routes", test_web_server_routes),
        ("Web Server Handlers", test_web_server_handlers),
        ("Server Creation", test_server_creation),
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

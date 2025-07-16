
#!/usr/bin/env python3
"""
Multi-drone test to verify multiple mock drones work simultaneously
"""
import sys
import os
import time
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add djitellopy to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from djitellopy import Tello
    print("✓ djitellopy imported successfully")
except ImportError as e:
    print(f"✗ Failed to import djitellopy: {e}")
    sys.exit(1)

def test_single_drone(drone_id, drone_ip, port):
    """Test a single drone with specific movements"""
    print(f"\n{'='*60}")
    print(f"Testing Drone {drone_id} at {drone_ip}:{port}")
    print(f"{'='*60}")
    
    results = {
        'drone_id': drone_id,
        'success': False,
        'errors': [],
        'completed_actions': []
    }

    try:
        # Create Tello instance with custom IP and port
        print(f"[{drone_id}] Connecting to drone at {drone_ip}:{port}")
        tello = Tello(host=drone_ip, control_udp=port)
        results['completed_actions'].append('instance_created')

        # Try to connect
        print(f"[{drone_id}] Attempting to connect...")
        try:
            tello.connect()
            print(f"[{drone_id}] ✓ Connected to drone")
            results['completed_actions'].append('connected')

            # Get battery level
            try:
                battery = tello.get_battery()
                print(f"[{drone_id}] ✓ Battery level: {battery}%")
                results['completed_actions'].append('battery_check')
            except Exception as e:
                print(f"[{drone_id}] ⚠ Could not get battery: {e}")
                results['errors'].append(f'battery_error: {e}')

            # Get current state
            try:
                state = tello.get_current_state()
                if state:
                    print(f"[{drone_id}] ✓ State received: Battery {state.get('bat', 'N/A')}%, Height {state.get('h', 'N/A')}cm")
                    results['completed_actions'].append('state_check')
                else:
                    print(f"[{drone_id}] ⚠ No state data received")
            except Exception as e:
                print(f"[{drone_id}] ⚠ Could not get state: {e}")
                results['errors'].append(f'state_error: {e}')
            
            # Test movements if connected
            if tello.get_current_state():
                print(f"\n[{drone_id}] {'-'*40}")
                print(f"[{drone_id}] Testing Flight Sequence")
                print(f"[{drone_id}] {'-'*40}")
                
                try:
                    # Takeoff
                    print(f"[{drone_id}] 🚁 Taking off...")
                    tello.takeoff()
                    time.sleep(2)
                    print(f"[{drone_id}] ✓ Takeoff completed")
                    results['completed_actions'].append('takeoff')
                    
                    # Different movement pattern for each drone
                    drone_num = int(drone_id.split('_')[-1]) if '_' in drone_id else 1
                    
                    if drone_num % 3 == 1:
                        # Square pattern
                        print(f"[{drone_id}] 📐 Executing square pattern...")
                        tello.move_forward(80)
                        time.sleep(2)
                        tello.rotate_clockwise(90)
                        time.sleep(1)
                        tello.move_forward(80)
                        time.sleep(2)
                        tello.rotate_clockwise(90)
                        time.sleep(1)
                        tello.move_forward(80)
                        time.sleep(2)
                        tello.rotate_clockwise(90)
                        time.sleep(1)
                        tello.move_forward(80)
                        time.sleep(2)
                        tello.rotate_clockwise(90)
                        time.sleep(1)
                        results['completed_actions'].append('square_pattern')
                        
                    elif drone_num % 3 == 2:
                        # Triangle pattern
                        print(f"[{drone_id}] 🔺 Executing triangle pattern...")
                        tello.move_forward(100)
                        time.sleep(2)
                        tello.rotate_clockwise(120)
                        time.sleep(1)
                        tello.move_forward(100)
                        time.sleep(2)
                        tello.rotate_clockwise(120)
                        time.sleep(1)
                        tello.move_forward(100)
                        time.sleep(2)
                        tello.rotate_clockwise(120)
                        time.sleep(1)
                        results['completed_actions'].append('triangle_pattern')
                        
                    else:
                        # Up-down pattern
                        print(f"[{drone_id}] ⬆️⬇️ Executing vertical pattern...")
                        tello.move_up(60)
                        time.sleep(2)
                        tello.move_forward(50)
                        time.sleep(2)
                        tello.move_down(60)
                        time.sleep(2)
                        tello.move_back(50)
                        time.sleep(2)
                        results['completed_actions'].append('vertical_pattern')
                    
                    # Get final state
                    state = tello.get_current_state()
                    if state:
                        print(f"[{drone_id}] Final - Height: {state.get('h', 'N/A')}cm, Battery: {state.get('bat', 'N/A')}%")
                    
                    # Land
                    print(f"[{drone_id}] 🛬 Landing...")
                    tello.land()
                    time.sleep(2)
                    print(f"[{drone_id}] ✓ Landing completed")
                    results['completed_actions'].append('landing')
                    
                    print(f"[{drone_id}] ✅ All flight tests completed successfully!")
                    results['success'] = True
                    
                except Exception as e:
                    print(f"[{drone_id}] ❌ Flight test failed: {e}")
                    results['errors'].append(f'flight_error: {e}')
                    try:
                        print(f"[{drone_id}] 🚨 Emergency landing...")
                        tello.emergency()
                        results['completed_actions'].append('emergency_landing')
                    except:
                        pass

        except Exception as e:
            print(f"[{drone_id}] ✗ Connection failed: {e}")
            results['errors'].append(f'connection_error: {e}')

    except Exception as e:
        print(f"[{drone_id}] ✗ Test setup failed: {e}")
        results['errors'].append(f'setup_error: {e}')
    
    return results


def test_multiple_drones(base_ip='127.0.0.1', start_port=8889, drone_count=3):
    """Test multiple drones sequentially (djitellopy limitation prevents true parallel testing)"""
    print(f"\n{'='*80}")
    print(f"MULTI-DRONE TEST - Testing {drone_count} drones sequentially")
    print(f"{'='*80}")
    print("⚠️  Note: Testing sequentially due to djitellopy port binding limitations")
    
    # Create drone configurations
    drone_configs = []
    for i in range(drone_count):
        drone_configs.append({
            'drone_id': f'drone_{i+1}',
            'ip': base_ip,
            'port': start_port + i
        })
    
    print(f"Drone configurations:")
    for config in drone_configs:
        print(f"  - {config['drone_id']}: {config['ip']}:{config['port']}")
    
    # Test drones sequentially to avoid port conflicts
    print(f"\n🚀 Starting sequential drone tests...")
    start_time = time.time()
    
    results = []
    for i, config in enumerate(drone_configs):
        print(f"\n📍 Testing drone {i+1}/{drone_count}: {config['drone_id']}")
        try:
            result = test_single_drone(config['drone_id'], config['ip'], config['port'])
            results.append(result)
            print(f"✓ {config['drone_id']} test completed")
            
            # Small delay between drone tests to ensure clean disconnection
            if i < len(drone_configs) - 1:
                print(f"⏳ Waiting 2 seconds before next drone test...")
                time.sleep(2)
                
        except Exception as e:
            print(f"✗ {config['drone_id']} test failed with exception: {e}")
            results.append({
                'drone_id': config['drone_id'],
                'success': False,
                'errors': [f'execution_error: {e}'],
                'completed_actions': []
            })
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # Print summary
    print(f"\n{'='*80}")
    print(f"MULTI-DRONE TEST SUMMARY")
    print(f"{'='*80}")
    print(f"Total test time: {total_time:.2f} seconds")
    print(f"Drones tested: {len(results)}")
    
    successful_drones = [r for r in results if r['success']]
    failed_drones = [r for r in results if not r['success']]
    
    print(f"Successful: {len(successful_drones)}")
    print(f"Failed: {len(failed_drones)}")
    
    if successful_drones:
        print(f"\n✅ Successful drones:")
        for result in successful_drones:
            actions = ', '.join(result['completed_actions'])
            print(f"  - {result['drone_id']}: {actions}")
    
    if failed_drones:
        print(f"\n❌ Failed drones:")
        for result in failed_drones:
            actions = ', '.join(result['completed_actions']) if result['completed_actions'] else 'none'
            errors = '; '.join(result['errors']) if result['errors'] else 'unknown'
            print(f"  - {result['drone_id']}: completed={actions}, errors={errors}")
    
    return results


def test_swarm_coordination(base_ip='127.0.0.1', start_port=8889, drone_count=3):
    """Test coordinated swarm movements"""
    print(f"\n{'='*80}")
    print(f"SWARM COORDINATION TEST - {drone_count} drones in formation")
    print(f"{'='*80}")
    
    # Create drone instances
    drones = []
    for i in range(drone_count):
        try:
            drone_id = f'swarm_{i+1}'
            tello = Tello(host=base_ip, control_udp=start_port + i)
            tello.connect()
            drones.append({'id': drone_id, 'tello': tello, 'index': i})
            print(f"✓ {drone_id} connected on port {start_port + i}")
        except Exception as e:
            print(f"✗ Failed to connect {drone_id}: {e}")
    
    if not drones:
        print("❌ No drones connected for swarm test")
        return
    
    print(f"\n🎯 Starting coordinated swarm maneuvers with {len(drones)} drones...")
    
    try:
        # Synchronized takeoff
        print("🚁 Synchronized takeoff...")
        for drone in drones:
            drone['tello'].takeoff()
        time.sleep(4)  # Wait for all to complete takeoff
        
        # Formation flying - spread out
        print("📐 Formation spread...")
        for i, drone in enumerate(drones):
            if i == 0:
                drone['tello'].move_left(100)
            elif i == 1:
                pass  # Center drone stays
            else:
                drone['tello'].move_right(100)
        time.sleep(3)
        
        # Synchronized forward movement
        print("➡️ Synchronized forward movement...")
        for drone in drones:
            drone['tello'].move_forward(150)
        time.sleep(4)
        
        # Coordinated rotation
        print("🔄 Coordinated rotation...")
        for drone in drones:
            drone['tello'].rotate_clockwise(180)
        time.sleep(3)
        
        # Return to formation
        print("🔙 Return movement...")
        for drone in drones:
            drone['tello'].move_forward(150)
        time.sleep(4)
        
        # Synchronized landing
        print("🛬 Synchronized landing...")
        for drone in drones:
            drone['tello'].land()
        time.sleep(4)
        
        print("✅ Swarm coordination test completed successfully!")
        
    except Exception as e:
        print(f"❌ Swarm test failed: {e}")
        # Emergency landing for all drones
        print("🚨 Emergency landing all drones...")
        for drone in drones:
            try:
                drone['tello'].emergency()
            except:
                pass

def main():
    """Main test function with multi-drone support"""
    import argparse
    
    parser = argparse.ArgumentParser(description='RoboMaster TT Multi-Drone Test Suite')
    parser.add_argument('--mode', choices=['single', 'multi', 'swarm'], default='multi',
                       help='Test mode: single drone, multiple independent drones, or coordinated swarm')
    parser.add_argument('--ip', default='127.0.0.1', 
                       help='Base IP address for drones (default: 127.0.0.1 for local mock drones)')
    parser.add_argument('--port', type=int, default=8889,
                       help='Starting port number (default: 8889)')
    parser.add_argument('--count', type=int, default=3,
                       help='Number of drones to test (default: 3)')
    parser.add_argument('--single-port', type=int,
                       help='Port for single drone test (overrides --port)')
    
    args = parser.parse_args()
    
    print("RoboMaster TT Multi-Drone Test Suite")
    print("====================================")
    print(f"Mode: {args.mode}")
    print(f"Base IP: {args.ip}")
    print(f"Starting Port: {args.port}")
    if args.mode != 'single':
        print(f"Drone Count: {args.count}")
    
    if args.mode == 'single':
        # Single drone test (legacy mode)
        port = args.single_port if args.single_port else args.port
        print(f"\n🎯 Testing single drone at {args.ip}:{port}")
        result = test_single_drone('single_drone', args.ip, port)
        
        if result['success']:
            print(f"\n✅ Single drone test completed successfully!")
            print(f"Completed actions: {', '.join(result['completed_actions'])}")
        else:
            print(f"\n❌ Single drone test failed!")
            if result['errors']:
                print(f"Errors: {'; '.join(result['errors'])}")
    
    elif args.mode == 'multi':
        # Multiple independent drones test
        print(f"\n🎯 Testing {args.count} independent drones")
        results = test_multiple_drones(args.ip, args.port, args.count)
        
        success_rate = len([r for r in results if r['success']]) / len(results) * 100
        print(f"\n📊 Overall success rate: {success_rate:.1f}%")
    
    elif args.mode == 'swarm':
        # Coordinated swarm test
        print(f"\n🎯 Testing {args.count} drones in coordinated swarm")
        test_swarm_coordination(args.ip, args.port, args.count)
    
    print(f"\n{'='*80}")
    print("SETUP INSTRUCTIONS FOR MOCK DRONES:")
    print("="*80)
    
    if args.mode == 'single':
        port = args.single_port if args.single_port else args.port
        print(f"For single drone test:")
        print(f"  python -m mock_drone.mock_drone --drone-id test_drone --port {port}")
    else:
        print(f"For {args.count} mock drones, run these commands in separate terminals:")
        for i in range(args.count):
            drone_port = args.port + i
            print(f"  python -m mock_drone.mock_drone --drone-id drone_{i+1} --port {drone_port}")
        
        print(f"\nOr use the drone manager to start all at once:")
        print(f"  python -m mock_drone.drone_manager --count {args.count} --prefix drone")
    
    print(f"\nFor remote testing (different machines):")
    print(f"  1. On drone machine: Start mock drones with --host 0.0.0.0")
    print(f"  2. On test machine: python test_simple_drone.py --ip <DRONE_MACHINE_IP>")
    print("="*80)

if __name__ == "__main__":
    main()

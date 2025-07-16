#!/usr/bin/env python3
"""
Debug script to troubleshoot drone connection issues
"""
import socket
import sys
import time

def test_udp_connection(host, port, timeout=5):
    """Test basic UDP connectivity to a host:port"""
    print(f"Testing UDP connection to {host}:{port}")
    
    try:
        # Create UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        
        # Send a test command (Tello command format)
        test_command = b"command"
        print(f"Sending test command: {test_command.decode()}")
        
        sock.sendto(test_command, (host, port))
        
        # Try to receive response
        try:
            response, addr = sock.recvfrom(1024)
            print(f"✓ Received response: {response.decode()} from {addr}")
            return True
        except socket.timeout:
            print(f"✗ No response received within {timeout} seconds")
            return False
        except Exception as e:
            print(f"✗ Error receiving response: {e}")
            return False
            
    except Exception as e:
        print(f"✗ Connection error: {e}")
        return False
    finally:
        sock.close()

def test_multiple_ports(host, start_port, count):
    """Test multiple consecutive ports"""
    print(f"\n{'='*60}")
    print(f"Testing {count} ports starting from {host}:{start_port}")
    print(f"{'='*60}")
    
    results = []
    for i in range(count):
        port = start_port + i
        print(f"\n[Port {port}] Testing connection...")
        success = test_udp_connection(host, port)
        results.append({'port': port, 'success': success})
        
        if i < count - 1:
            time.sleep(1)  # Small delay between tests
    
    # Summary
    print(f"\n{'='*60}")
    print("CONNECTION TEST SUMMARY")
    print(f"{'='*60}")
    
    successful_ports = [r for r in results if r['success']]
    failed_ports = [r for r in results if not r['success']]
    
    print(f"Successful connections: {len(successful_ports)}")
    print(f"Failed connections: {len(failed_ports)}")
    
    if successful_ports:
        print(f"\n✅ Working ports:")
        for result in successful_ports:
            print(f"  - Port {result['port']}: OK")
    
    if failed_ports:
        print(f"\n❌ Failed ports:")
        for result in failed_ports:
            print(f"  - Port {result['port']}: No response")
    
    return results

def check_network_connectivity(host):
    """Check basic network connectivity using ping-like approach"""
    print(f"\n{'='*60}")
    print(f"Checking network connectivity to {host}")
    print(f"{'='*60}")
    
    try:
        # Try to create a connection to a common port to test reachability
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        
        # Test if host is reachable (try connecting to any port)
        # We'll use a high port that's unlikely to be in use
        test_port = 65432
        result = sock.connect_ex((host, test_port))
        sock.close()
        
        if result == 0:
            print(f"✓ Host {host} is reachable (port {test_port} responded)")
        else:
            print(f"⚠ Host {host} connectivity test - Connection refused (expected for unused port)")
            print(f"  This usually means the host is reachable but port {test_port} is not in use")
        
        return True
        
    except socket.gaierror as e:
        print(f"✗ DNS/Host resolution error: {e}")
        print(f"  Check if {host} is a valid IP address or hostname")
        return False
    except Exception as e:
        print(f"✗ Network connectivity error: {e}")
        return False

def main():
    """Main diagnostic function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Debug drone connection issues')
    parser.add_argument('--host', default='127.0.0.1', help='Host IP address')
    parser.add_argument('--port', type=int, default=8889, help='Starting port number')
    parser.add_argument('--count', type=int, default=3, help='Number of ports to test')
    parser.add_argument('--timeout', type=int, default=5, help='Timeout in seconds')
    
    args = parser.parse_args()
    
    print("Drone Connection Debug Tool")
    print("==========================")
    print(f"Target: {args.host}")
    print(f"Port range: {args.port}-{args.port + args.count - 1}")
    print(f"Timeout: {args.timeout}s")
    
    # Step 1: Check basic network connectivity
    network_ok = check_network_connectivity(args.host)
    
    if not network_ok:
        print(f"\n❌ Network connectivity issues detected!")
        print(f"Recommendations:")
        print(f"1. Check if {args.host} is the correct IP address")
        print(f"2. Verify both machines are on the same network")
        print(f"3. Check firewall settings on both machines")
        return
    
    # Step 2: Test UDP ports
    results = test_multiple_ports(args.host, args.port, args.count)
    
    # Step 3: Provide recommendations
    print(f"\n{'='*60}")
    print("TROUBLESHOOTING RECOMMENDATIONS")
    print(f"{'='*60}")
    
    successful_count = len([r for r in results if r['success']])
    
    if successful_count == 0:
        print("❌ No mock drones are responding!")
        print("\nPossible issues:")
        print("1. Mock drones are not running on the target machine")
        print("2. Mock drones are not bound to 0.0.0.0 (all interfaces)")
        print("3. Firewall is blocking UDP traffic")
        print("4. Wrong IP address or port numbers")
        print("\nSolutions:")
        print(f"1. On PC1 ({args.host}), run:")
        print(f"   python -m mock_drone.drone_manager --count {args.count} --prefix drone")
        print("2. Make sure mock drones use --host 0.0.0.0 for remote access")
        print("3. Check Windows Firewall settings on both machines")
        
    elif successful_count < args.count:
        print(f"⚠ Only {successful_count}/{args.count} mock drones are responding")
        print("\nPartial success - some drones may not be running or accessible")
        
    else:
        print(f"✅ All {successful_count} mock drones are responding correctly!")
        print("Connection test passed - the issue may be with djitellopy library")

if __name__ == "__main__":
    main()
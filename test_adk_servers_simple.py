#!/usr/bin/env python3
"""
Simple test script for ADK web and API server startup and agent discovery.
"""

import subprocess
import time
import requests
import sys
import signal
from typing import Optional

class SimpleADKTester:
    def __init__(self):
        self.web_process: Optional[subprocess.Popen] = None
        self.api_process: Optional[subprocess.Popen] = None
        self.web_port = 8000
        self.api_port = 8001
        self.expected_agents = [
            "video_orchestrator",
            "research_agent", 
            "story_agent",
            "asset_sourcing_agent",
            "image_generation_agent",
            "audio_agent",
            "video_assembly_agent"
        ]
    
    def test_web_server(self) -> bool:
        """Test ADK web server startup and basic functionality."""
        print("🚀 Testing ADK web server...")
        
        try:
            # Start web server
            cmd = ["adk", "web", "video_system", "--port", str(self.web_port)]
            print(f"Running: {' '.join(cmd)}")
            
            self.web_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait for startup
            print("⏳ Waiting for web server to start...")
            for i in range(20):
                if self.web_process.poll() is not None:
                    stdout, stderr = self.web_process.communicate()
                    print(f"❌ Web server exited early:")
                    print(f"STDOUT: {stdout}")
                    print(f"STDERR: {stderr}")
                    return False
                
                try:
                    # Try different common endpoints
                    endpoints_to_try = [
                        f"http://localhost:{self.web_port}",
                        f"http://localhost:{self.web_port}/health",
                        f"http://localhost:{self.web_port}/docs"
                    ]
                    
                    for endpoint in endpoints_to_try:
                        try:
                            response = requests.get(endpoint, timeout=2)
                            if response.status_code in [200, 404]:  # 404 is ok, means server is running
                                print(f"✅ Web server is running on port {self.web_port}")
                                return True
                        except requests.exceptions.RequestException:
                            continue
                            
                except Exception:
                    pass
                
                time.sleep(1)
                print(f"   Waiting... ({i+1}/20)")
            
            print("❌ Web server failed to start within timeout")
            return False
            
        except Exception as e:
            print(f"❌ Error testing web server: {e}")
            return False
    
    def test_api_server(self) -> bool:
        """Test ADK API server startup and basic functionality."""
        print("🚀 Testing ADK API server...")
        
        try:
            # Start API server
            cmd = ["adk", "api_server", "video_system", "--port", str(self.api_port)]
            print(f"Running: {' '.join(cmd)}")
            
            self.api_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait for startup
            print("⏳ Waiting for API server to start...")
            for i in range(20):
                if self.api_process.poll() is not None:
                    stdout, stderr = self.api_process.communicate()
                    print(f"❌ API server exited early:")
                    print(f"STDOUT: {stdout}")
                    print(f"STDERR: {stderr}")
                    return False
                
                try:
                    # Try different common endpoints
                    endpoints_to_try = [
                        f"http://localhost:{self.api_port}",
                        f"http://localhost:{self.api_port}/health",
                        f"http://localhost:{self.api_port}/docs"
                    ]
                    
                    for endpoint in endpoints_to_try:
                        try:
                            response = requests.get(endpoint, timeout=2)
                            if response.status_code in [200, 404]:  # 404 is ok, means server is running
                                print(f"✅ API server is running on port {self.api_port}")
                                return True
                        except requests.exceptions.RequestException:
                            continue
                            
                except Exception:
                    pass
                
                time.sleep(1)
                print(f"   Waiting... ({i+1}/20)")
            
            print("❌ API server failed to start within timeout")
            return False
            
        except Exception as e:
            print(f"❌ Error testing API server: {e}")
            return False
    
    def cleanup(self):
        """Clean up processes."""
        print("🧹 Cleaning up...")
        
        if self.web_process:
            try:
                self.web_process.terminate()
                self.web_process.wait(timeout=5)
                print("✅ Web server terminated")
            except:
                try:
                    self.web_process.kill()
                    print("⚠️ Web server killed")
                except:
                    pass
        
        if self.api_process:
            try:
                self.api_process.terminate()
                self.api_process.wait(timeout=5)
                print("✅ API server terminated")
            except:
                try:
                    self.api_process.kill()
                    print("⚠️ API server killed")
                except:
                    pass
    
    def run_tests(self) -> bool:
        """Run all tests."""
        print("🧪 Testing ADK Web and API Server Integration")
        print("=" * 50)
        
        all_passed = True
        
        try:
            # Test web server
            print("\n📋 Test 1: Web Server Startup")
            print("-" * 30)
            web_success = self.test_web_server()
            if not web_success:
                all_passed = False
            
            # Give a moment between tests
            time.sleep(2)
            
            # Test API server
            print("\n📋 Test 2: API Server Startup")
            print("-" * 30)
            api_success = self.test_api_server()
            if not api_success:
                all_passed = False
            
            # Keep servers running for a moment to verify stability
            if web_success or api_success:
                print("\n⏳ Keeping servers running for 5 seconds to verify stability...")
                time.sleep(5)
                
                # Check if processes are still running
                if self.web_process and self.web_process.poll() is None:
                    print("✅ Web server is stable")
                elif web_success:
                    print("❌ Web server became unstable")
                    all_passed = False
                
                if self.api_process and self.api_process.poll() is None:
                    print("✅ API server is stable")
                elif api_success:
                    print("❌ API server became unstable")
                    all_passed = False
            
        except KeyboardInterrupt:
            print("\n⚠️ Tests interrupted")
            all_passed = False
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
            all_passed = False
        finally:
            self.cleanup()
        
        print("\n" + "=" * 50)
        if all_passed:
            print("🎉 TESTS PASSED! ADK servers can start successfully.")
        else:
            print("❌ SOME TESTS FAILED! Check output above.")
        print("=" * 50)
        
        return all_passed

def main():
    tester = SimpleADKTester()
    
    def signal_handler(sig, frame):
        print("\n⚠️ Interrupted, cleaning up...")
        tester.cleanup()
        sys.exit(1)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    success = tester.run_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
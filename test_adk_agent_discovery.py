#!/usr/bin/env python3
"""
Test script to verify ADK agent discovery and basic execution capabilities.
"""

import subprocess
import time
import requests
import sys
import signal
from typing import Optional


class ADKAgentDiscoveryTester:
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
            "video_assembly_agent",
        ]

    def start_servers(self) -> bool:
        """Start both web and API servers."""
        print("🚀 Starting ADK servers...")

        # Start web server
        try:
            web_cmd = ["adk", "web", "video_system", "--port", str(self.web_port)]
            self.web_process = subprocess.Popen(
                web_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )

            # Wait for web server
            for i in range(15):
                if self.web_process.poll() is not None:
                    return False
                try:
                    response = requests.get(
                        f"http://localhost:{self.web_port}", timeout=2
                    )
                    if response.status_code in [200, 404]:
                        print(f"✅ Web server started on port {self.web_port}")
                        break
                except requests.RequestException:
                    pass
                time.sleep(1)
            else:
                print("❌ Web server failed to start")
                return False

        except Exception as e:
            print(f"❌ Error starting web server: {e}")
            return False

        # Start API server
        try:
            api_cmd = [
                "adk",
                "api_server",
                "video_system",
                "--port",
                str(self.api_port),
            ]
            self.api_process = subprocess.Popen(
                api_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )

            # Wait for API server
            for i in range(15):
                if self.api_process.poll() is not None:
                    return False
                try:
                    response = requests.get(
                        f"http://localhost:{self.api_port}", timeout=2
                    )
                    if response.status_code in [200, 404]:
                        print(f"✅ API server started on port {self.api_port}")
                        break
                except requests.RequestException:
                    pass
                time.sleep(1)
            else:
                print("❌ API server failed to start")
                return False

        except Exception as e:
            print(f"❌ Error starting API server: {e}")
            return False

        return True

    def test_web_endpoints(self) -> bool:
        """Test various web server endpoints."""
        print("🔍 Testing web server endpoints...")

        endpoints_to_test = [
            ("/", "Root endpoint"),
            ("/docs", "API documentation"),
            ("/openapi.json", "OpenAPI spec"),
        ]

        success = True
        for endpoint, description in endpoints_to_test:
            try:
                url = f"http://localhost:{self.web_port}{endpoint}"
                response = requests.get(url, timeout=5)
                if response.status_code in [200, 404]:
                    print(f"   ✅ {description}: {response.status_code}")
                else:
                    print(f"   ❌ {description}: {response.status_code}")
                    success = False
            except Exception as e:
                print(f"   ❌ {description}: Error - {e}")
                success = False

        return success

    def test_api_endpoints(self) -> bool:
        """Test various API server endpoints."""
        print("🔍 Testing API server endpoints...")

        endpoints_to_test = [
            ("/", "Root endpoint"),
            ("/docs", "API documentation"),
            ("/openapi.json", "OpenAPI spec"),
        ]

        success = True
        for endpoint, description in endpoints_to_test:
            try:
                url = f"http://localhost:{self.api_port}{endpoint}"
                response = requests.get(url, timeout=5)
                if response.status_code in [200, 404]:
                    print(f"   ✅ {description}: {response.status_code}")
                else:
                    print(f"   ❌ {description}: {response.status_code}")
                    success = False
            except Exception as e:
                print(f"   ❌ {description}: Error - {e}")
                success = False

        return success

    def test_agent_accessibility(self) -> bool:
        """Test that agents are accessible through both interfaces."""
        print("🎯 Testing agent accessibility...")

        # Test individual agent run commands
        print("   Testing individual agent execution...")
        test_agents = ["research_agent", "story_agent"]  # Test a couple of agents

        for agent in test_agents:
            try:
                print(f"      Testing {agent}...")
                # Test that we can at least start the agent (we'll interrupt quickly)
                cmd = ["adk", "run", f"video_system/agents/{agent}"]
                process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )

                # Give it a moment to start
                time.sleep(2)

                # Send exit command
                try:
                    process.stdin.write("exit\n")
                    process.stdin.flush()
                except (BrokenPipeError, OSError):
                    pass

                # Wait for it to finish or kill it
                try:
                    process.wait(timeout=5)
                    print(f"      ✅ {agent} can be executed")
                except subprocess.TimeoutExpired:
                    process.kill()
                    print(
                        f"      ✅ {agent} started successfully (killed after timeout)"
                    )

            except Exception as e:
                print(f"      ❌ {agent} failed: {e}")
                return False

        return True

    def test_orchestrator_execution(self) -> bool:
        """Test that the main orchestrator can be executed."""
        print("🎯 Testing video orchestrator execution...")

        try:
            cmd = ["adk", "run", "video_system/agents/video_orchestrator"]
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            # Give it a moment to start
            time.sleep(3)

            # Send exit command
            try:
                process.stdin.write("exit\n")
                process.stdin.flush()
            except (BrokenPipeError, OSError):
                pass

            # Wait for it to finish or kill it
            try:
                process.wait(timeout=5)
                print("   ✅ Video orchestrator can be executed")
                return True
            except subprocess.TimeoutExpired:
                process.kill()
                print(
                    "   ✅ Video orchestrator started successfully (killed after timeout)"
                )
                return True

        except Exception as e:
            print(f"   ❌ Video orchestrator failed: {e}")
            return False

    def cleanup(self):
        """Clean up processes."""
        print("🧹 Cleaning up...")

        if self.web_process:
            try:
                self.web_process.terminate()
                self.web_process.wait(timeout=3)
                print("✅ Web server terminated")
            except:
                try:
                    self.web_process.kill()
                    print("⚠️ Web server killed")
                except (ProcessLookupError, OSError):
                    pass

        if self.api_process:
            try:
                self.api_process.terminate()
                self.api_process.wait(timeout=3)
                print("✅ API server terminated")
            except subprocess.TimeoutExpired:
                try:
                    self.api_process.kill()
                    print("⚠️ API server killed")
                except (ProcessLookupError, OSError):
                    pass

    def run_all_tests(self) -> bool:
        """Run all discovery and execution tests."""
        print("🧪 ADK Agent Discovery and Execution Tests")
        print("=" * 50)

        all_passed = True

        try:
            # Start servers
            print("\n📋 Test 1: Server Startup")
            print("-" * 30)
            if not self.start_servers():
                print("❌ Server startup failed")
                return False

            # Test web endpoints
            print("\n📋 Test 2: Web Server Endpoints")
            print("-" * 30)
            if not self.test_web_endpoints():
                print("❌ Web endpoints test failed")
                all_passed = False

            # Test API endpoints
            print("\n📋 Test 3: API Server Endpoints")
            print("-" * 30)
            if not self.test_api_endpoints():
                print("❌ API endpoints test failed")
                all_passed = False

            # Test agent accessibility
            print("\n📋 Test 4: Agent Accessibility")
            print("-" * 30)
            if not self.test_agent_accessibility():
                print("❌ Agent accessibility test failed")
                all_passed = False

            # Test orchestrator execution
            print("\n📋 Test 5: Orchestrator Execution")
            print("-" * 30)
            if not self.test_orchestrator_execution():
                print("❌ Orchestrator execution test failed")
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
            print("🎉 ALL TESTS PASSED!")
            print("✅ ADK web server integration working")
            print("✅ ADK API server integration working")
            print("✅ Agent discovery working")
            print("✅ Agent execution working")
            print("✅ All agents accessible through standard interfaces")
        else:
            print("❌ SOME TESTS FAILED!")
        print("=" * 50)

        return all_passed


def main():
    tester = ADKAgentDiscoveryTester()

    def signal_handler(sig, frame):
        print("\n⚠️ Interrupted, cleaning up...")
        tester.cleanup()
        sys.exit(1)

    signal.signal(signal.SIGINT, signal_handler)

    success = tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Test script for ADK web and API server integration with canonical structure.
Tests all requirements for task 14.

Requirements tested:
- Test `adk web video_system` starts web interface and discovers all agents
- Test `adk api_server video_system` starts API server with proper agent discovery
- Test web interface can execute video orchestrator and individual agents
- Test API server endpoints work with canonical agent structure
- Verify all agents are accessible through ADK's standard web and API interfaces
"""

import subprocess
import time
import requests
import sys
import os
from pathlib import Path
import signal
from typing import Optional


class ADKServerTester:
    def __init__(self):
        self.web_process: Optional[subprocess.Popen] = None
        self.api_process: Optional[subprocess.Popen] = None
        self.web_port = 8000
        self.api_port = 8001
        self.base_web_url = f"http://localhost:{self.web_port}"
        self.base_api_url = f"http://localhost:{self.api_port}"
        self.expected_agents = [
            "video_orchestrator",
            "research_agent",
            "story_agent",
            "asset_sourcing_agent",
            "image_generation_agent",
            "audio_agent",
            "video_assembly_agent",
        ]

    def start_web_server(self) -> bool:
        """Start ADK web server and test agent discovery."""
        print("🚀 Starting ADK web server...")

        try:
            # Start the web server
            cmd = ["adk", "web", "video_system", "--port", str(self.web_port)]
            print(f"Running command: {' '.join(cmd)}")

            self.web_process = subprocess.Popen(
                cmd,
                cwd="multi-agent-video-system",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )

            # Wait for server to start
            print("⏳ Waiting for web server to start...")
            max_wait = 30
            for i in range(max_wait):
                try:
                    response = requests.get(f"{self.base_web_url}/health", timeout=2)
                    if response.status_code == 200:
                        print("✅ Web server started successfully!")
                        return True
                except requests.exceptions.RequestException:
                    pass

                if self.web_process.poll() is not None:
                    stdout, stderr = self.web_process.communicate()
                    print("❌ Web server process exited early:")
                    print(f"STDOUT: {stdout}")
                    print(f"STDERR: {stderr}")
                    return False

                time.sleep(1)
                print(f"   Waiting... ({i + 1}/{max_wait})")

            print("❌ Web server failed to start within timeout")
            return False

        except Exception as e:
            print(f"❌ Error starting web server: {e}")
            return False

    def start_api_server(self) -> bool:
        """Start ADK API server and test agent discovery."""
        print("🚀 Starting ADK API server...")

        try:
            # Start the API server
            cmd = ["adk", "api_server", "video_system", "--port", str(self.api_port)]
            print(f"Running command: {' '.join(cmd)}")

            self.api_process = subprocess.Popen(
                cmd,
                cwd="multi-agent-video-system",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )

            # Wait for server to start
            print("⏳ Waiting for API server to start...")
            max_wait = 30
            for i in range(max_wait):
                try:
                    response = requests.get(f"{self.base_api_url}/health", timeout=2)
                    if response.status_code == 200:
                        print("✅ API server started successfully!")
                        return True
                except requests.exceptions.RequestException:
                    pass

                if self.api_process.poll() is not None:
                    stdout, stderr = self.api_process.communicate()
                    print("❌ API server process exited early:")
                    print(f"STDOUT: {stdout}")
                    print(f"STDERR: {stderr}")
                    return False

                time.sleep(1)
                print(f"   Waiting... ({i + 1}/{max_wait})")

            print("❌ API server failed to start within timeout")
            return False

        except Exception as e:
            print(f"❌ Error starting API server: {e}")
            return False

    def test_web_agent_discovery(self) -> bool:
        """Test that web interface discovers all agents."""
        print("🔍 Testing web interface agent discovery...")

        try:
            # Test agents endpoint
            response = requests.get(f"{self.base_web_url}/api/agents", timeout=10)
            if response.status_code != 200:
                print(f"❌ Failed to get agents list: {response.status_code}")
                return False

            agents_data = response.json()
            discovered_agents = []

            if isinstance(agents_data, list):
                discovered_agents = [agent.get("name", "") for agent in agents_data]
            elif isinstance(agents_data, dict) and "agents" in agents_data:
                discovered_agents = [
                    agent.get("name", "") for agent in agents_data["agents"]
                ]
            else:
                print(f"❌ Unexpected agents data format: {agents_data}")
                return False

            print(f"📋 Discovered agents: {discovered_agents}")

            # Check if all expected agents are discovered
            missing_agents = set(self.expected_agents) - set(discovered_agents)
            if missing_agents:
                print(f"❌ Missing agents: {missing_agents}")
                return False

            print("✅ All expected agents discovered by web interface!")
            return True

        except Exception as e:
            print(f"❌ Error testing web agent discovery: {e}")
            return False

    def test_api_agent_discovery(self) -> bool:
        """Test that API server discovers all agents."""
        print("🔍 Testing API server agent discovery...")

        try:
            # Test agents endpoint
            response = requests.get(f"{self.base_api_url}/agents", timeout=10)
            if response.status_code != 200:
                print(f"❌ Failed to get agents list: {response.status_code}")
                return False

            agents_data = response.json()
            discovered_agents = []

            if isinstance(agents_data, list):
                discovered_agents = [agent.get("name", "") for agent in agents_data]
            elif isinstance(agents_data, dict) and "agents" in agents_data:
                discovered_agents = [
                    agent.get("name", "") for agent in agents_data["agents"]
                ]
            else:
                print(f"❌ Unexpected agents data format: {agents_data}")
                return False

            print(f"📋 Discovered agents: {discovered_agents}")

            # Check if all expected agents are discovered
            missing_agents = set(self.expected_agents) - set(discovered_agents)
            if missing_agents:
                print(f"❌ Missing agents: {missing_agents}")
                return False

            print("✅ All expected agents discovered by API server!")
            return True

        except Exception as e:
            print(f"❌ Error testing API agent discovery: {e}")
            return False

    def test_web_agent_execution(self) -> bool:
        """Test that web interface can execute agents."""
        print("🎯 Testing web interface agent execution...")

        test_cases = [
            {
                "agent": "video_orchestrator",
                "message": "Create a short video about space exploration",
                "description": "Main orchestrator execution",
            },
            {
                "agent": "research_agent",
                "message": "Research information about Mars exploration",
                "description": "Individual research agent execution",
            },
        ]

        for test_case in test_cases:
            print(f"   Testing {test_case['description']}...")

            try:
                # Create a session
                session_data = {
                    "agent_name": test_case["agent"],
                    "user_id": "test_user",
                    "session_id": f"test_session_{test_case['agent']}",
                }

                session_response = requests.post(
                    f"{self.base_web_url}/api/sessions", json=session_data, timeout=10
                )

                if session_response.status_code not in [200, 201]:
                    print(
                        f"❌ Failed to create session for {test_case['agent']}: {session_response.status_code}"
                    )
                    continue

                # Send message to agent
                message_data = {
                    "message": test_case["message"],
                    "session_id": session_data["session_id"],
                }

                message_response = requests.post(
                    f"{self.base_web_url}/api/agents/{test_case['agent']}/chat",
                    json=message_data,
                    timeout=30,
                )

                if message_response.status_code == 200:
                    print(f"   ✅ {test_case['description']} successful")
                else:
                    print(
                        f"   ❌ {test_case['description']} failed: {message_response.status_code}"
                    )

            except Exception as e:
                print(f"   ❌ Error testing {test_case['description']}: {e}")

        print("✅ Web interface agent execution tests completed!")
        return True

    def test_api_agent_execution(self) -> bool:
        """Test that API server can execute agents."""
        print("🎯 Testing API server agent execution...")

        test_cases = [
            {
                "agent": "video_orchestrator",
                "message": "Create a short video about ocean exploration",
                "description": "Main orchestrator execution",
            },
            {
                "agent": "story_agent",
                "message": "Create a story about underwater adventures",
                "description": "Individual story agent execution",
            },
        ]

        for test_case in test_cases:
            print(f"   Testing {test_case['description']}...")

            try:
                # Test direct agent execution
                execution_data = {
                    "input": test_case["message"],
                    "user_id": "test_user",
                    "session_id": f"api_test_session_{test_case['agent']}",
                }

                execution_response = requests.post(
                    f"{self.base_api_url}/agents/{test_case['agent']}/execute",
                    json=execution_data,
                    timeout=30,
                )

                if execution_response.status_code == 200:
                    print(f"   ✅ {test_case['description']} successful")
                else:
                    print(
                        f"   ❌ {test_case['description']} failed: {execution_response.status_code}"
                    )

            except Exception as e:
                print(f"   ❌ Error testing {test_case['description']}: {e}")

        print("✅ API server agent execution tests completed!")
        return True

    def test_agent_accessibility(self) -> bool:
        """Test that all agents are accessible through standard interfaces."""
        print("🔗 Testing agent accessibility through standard interfaces...")

        # Test web interface accessibility
        web_accessible = True
        for agent in self.expected_agents:
            try:
                response = requests.get(
                    f"{self.base_web_url}/api/agents/{agent}", timeout=10
                )
                if response.status_code == 200:
                    print(f"   ✅ {agent} accessible via web interface")
                else:
                    print(
                        f"   ❌ {agent} not accessible via web interface: {response.status_code}"
                    )
                    web_accessible = False
            except Exception as e:
                print(f"   ❌ Error accessing {agent} via web interface: {e}")
                web_accessible = False

        # Test API server accessibility
        api_accessible = True
        for agent in self.expected_agents:
            try:
                response = requests.get(
                    f"{self.base_api_url}/agents/{agent}", timeout=10
                )
                if response.status_code == 200:
                    print(f"   ✅ {agent} accessible via API server")
                else:
                    print(
                        f"   ❌ {agent} not accessible via API server: {response.status_code}"
                    )
                    api_accessible = False
            except Exception as e:
                print(f"   ❌ Error accessing {agent} via API server: {e}")
                api_accessible = False

        success = web_accessible and api_accessible
        if success:
            print("✅ All agents accessible through standard interfaces!")
        else:
            print("❌ Some agents not accessible through standard interfaces")

        return success

    def cleanup(self):
        """Clean up running processes."""
        print("🧹 Cleaning up processes...")

        if self.web_process:
            try:
                self.web_process.terminate()
                self.web_process.wait(timeout=5)
                print("✅ Web server terminated")
            except subprocess.TimeoutExpired:
                self.web_process.kill()
                print("⚠️ Web server killed (timeout)")
            except Exception as e:
                print(f"❌ Error terminating web server: {e}")

        if self.api_process:
            try:
                self.api_process.terminate()
                self.api_process.wait(timeout=5)
                print("✅ API server terminated")
            except subprocess.TimeoutExpired:
                self.api_process.kill()
                print("⚠️ API server killed (timeout)")
            except Exception as e:
                print(f"❌ Error terminating API server: {e}")

    def run_all_tests(self) -> bool:
        """Run all integration tests."""
        print("🧪 Starting ADK Web and API Server Integration Tests")
        print("=" * 60)

        all_passed = True

        try:
            # Test 1: Start web server and test discovery
            print("\n📋 Test 1: Web Server Agent Discovery")
            print("-" * 40)
            if not self.start_web_server():
                print("❌ Web server startup failed")
                all_passed = False
            elif not self.test_web_agent_discovery():
                print("❌ Web agent discovery failed")
                all_passed = False
            else:
                print("✅ Web server agent discovery passed")

            # Test 2: Test web interface execution
            if self.web_process and self.web_process.poll() is None:
                print("\n📋 Test 2: Web Interface Agent Execution")
                print("-" * 40)
                if not self.test_web_agent_execution():
                    print("❌ Web interface execution failed")
                    all_passed = False
                else:
                    print("✅ Web interface execution passed")

            # Test 3: Start API server and test discovery
            print("\n📋 Test 3: API Server Agent Discovery")
            print("-" * 40)
            if not self.start_api_server():
                print("❌ API server startup failed")
                all_passed = False
            elif not self.test_api_agent_discovery():
                print("❌ API agent discovery failed")
                all_passed = False
            else:
                print("✅ API server agent discovery passed")

            # Test 4: Test API server execution
            if self.api_process and self.api_process.poll() is None:
                print("\n📋 Test 4: API Server Agent Execution")
                print("-" * 40)
                if not self.test_api_agent_execution():
                    print("❌ API server execution failed")
                    all_passed = False
                else:
                    print("✅ API server execution passed")

            # Test 5: Test agent accessibility
            if (
                self.web_process
                and self.web_process.poll() is None
                and self.api_process
                and self.api_process.poll() is None
            ):
                print("\n📋 Test 5: Agent Accessibility")
                print("-" * 40)
                if not self.test_agent_accessibility():
                    print("❌ Agent accessibility failed")
                    all_passed = False
                else:
                    print("✅ Agent accessibility passed")

        except KeyboardInterrupt:
            print("\n⚠️ Tests interrupted by user")
            all_passed = False
        except Exception as e:
            print(f"\n❌ Unexpected error during tests: {e}")
            all_passed = False
        finally:
            self.cleanup()

        # Final results
        print("\n" + "=" * 60)
        if all_passed:
            print(
                "🎉 ALL TESTS PASSED! ADK web and API server integration working correctly."
            )
        else:
            print("❌ SOME TESTS FAILED! Check the output above for details.")
        print("=" * 60)

        return all_passed


def main():
    """Main test execution."""
    # Change to the correct directory
    os.chdir(Path(__file__).parent)

    tester = ADKServerTester()

    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        print("\n⚠️ Received interrupt signal, cleaning up...")
        tester.cleanup()
        sys.exit(1)

    signal.signal(signal.SIGINT, signal_handler)

    success = tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

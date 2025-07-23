# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Test script for the video assembly agent in canonical structure."""

import os
import sys
import unittest
from unittest.mock import MagicMock

# Add src directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

# Mock the problematic modules
sys.modules["video_system.tools.audio_tools"] = MagicMock()
sys.modules["video_system.tools.video_tools"] = MagicMock()
sys.modules["video_system.utils.error_handling"] = MagicMock()
sys.modules["video_system.utils.resilience"] = MagicMock()

# Create mock functions
mock_check_ffmpeg_health = MagicMock()
mock_check_ffmpeg_health.return_value = {
    "status": "healthy",
    "details": {"message": "FFmpeg is installed and operational"},
}

mock_ffmpeg_composition_tool = MagicMock()
mock_ffmpeg_composition_tool.__name__ = "ffmpeg_composition_tool"

mock_video_synchronization_tool = MagicMock()
mock_video_synchronization_tool.__name__ = "video_synchronization_tool"

mock_transition_effects_tool = MagicMock()
mock_transition_effects_tool.__name__ = "transition_effects_tool"

mock_video_encoding_tool = MagicMock()
mock_video_encoding_tool.__name__ = "video_encoding_tool"

# Assign mock functions to the mock modules
sys.modules[
    "video_system.tools.video_tools"
].check_ffmpeg_health = mock_check_ffmpeg_health
sys.modules[
    "video_system.tools.video_tools"
].ffmpeg_composition_tool = mock_ffmpeg_composition_tool
sys.modules[
    "video_system.tools.video_tools"
].video_synchronization_tool = mock_video_synchronization_tool
sys.modules[
    "video_system.tools.video_tools"
].transition_effects_tool = mock_transition_effects_tool
sys.modules[
    "video_system.tools.video_tools"
].video_encoding_tool = mock_video_encoding_tool

# Mock logger and health monitor
mock_logger = MagicMock()
mock_health_monitor = MagicMock()
mock_health_monitor.service_registry = MagicMock()

sys.modules["video_system.utils.error_handling"].get_logger = MagicMock(
    return_value=mock_logger
)
sys.modules["video_system.utils.resilience"].get_health_monitor = MagicMock(
    return_value=mock_health_monitor
)


class TestVideoAssemblyAgent(unittest.TestCase):
    """Test cases for the video assembly agent."""

    def test_agent_import(self):
        """Test that the video assembly agent can be imported."""
        try:
            from video_system.agents.video_assembly_agent.agent import root_agent

            self.assertIsNotNone(root_agent)
            self.assertEqual(root_agent.name, "video_assembly_agent")
            self.assertEqual(root_agent.model, "gemini-2.5-pro")
            self.assertGreater(len(root_agent.tools), 0)
        except ImportError as e:
            self.fail(f"Failed to import video assembly agent: {e}")

    def test_health_check(self):
        """Test the health check function."""
        # Import the health check function
        from video_system.agents.video_assembly_agent.agent import (
            check_video_assembly_health,
        )

        # Call the health check function
        result = check_video_assembly_health()

        # Verify the result
        self.assertEqual(result["status"], "healthy")
        self.assertIn("message", result["details"])
        self.assertEqual(
            result["details"]["message"], "Video assembly services are operational"
        )

    def test_ffmpeg_composition_tool_imported(self):
        """Test that the FFmpeg composition tool is imported correctly."""
        # Import the agent
        from video_system.agents.video_assembly_agent.agent import root_agent

        # Check that the tool is in the agent's tools
        tool_names = [tool.__name__ for tool in root_agent.tools]
        self.assertIn("ffmpeg_composition_tool", tool_names)


if __name__ == "__main__":
    unittest.main()

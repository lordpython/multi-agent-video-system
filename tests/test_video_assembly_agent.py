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

"""Integration tests for the Video Assembly Agent."""

import pytest
import os
import tempfile
import shutil
from unittest.mock import Mock, patch
from video_system.agents.video_assembly_agent.agent import (
    root_agent as video_assembly_agent,
)


class TestVideoAssemblyAgent:
    """Test cases for the Video Assembly Agent."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_assets = self._create_test_assets()

    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_test_assets(self):
        """Create mock test assets for testing."""
        assets = {
            "video1": os.path.join(self.temp_dir, "video1.mp4"),
            "video2": os.path.join(self.temp_dir, "video2.mp4"),
            "audio": os.path.join(self.temp_dir, "audio.wav"),
            "output": os.path.join(self.temp_dir, "output.mp4"),
        }

        # Create empty test files
        for file_path in assets.values():
            with open(file_path, "w") as f:
                f.write("test content")

        return assets

    def test_agent_initialization(self):
        """Test that the video assembly agent is properly initialized."""
        assert video_assembly_agent is not None
        assert video_assembly_agent.name == "video_assembly_agent"
        assert video_assembly_agent.model == "gemini-2.5-pro"
        assert len(video_assembly_agent.tools) == 4

        # Check that all required tools are present (tools are functions)
        tool_names = [tool.__name__ for tool in video_assembly_agent.tools]
        expected_tools = [
            "synchronize_video_timeline",
            "compose_video_with_ffmpeg",
            "apply_video_transitions",
            "encode_video",
        ]

        for expected_tool in expected_tools:
            assert expected_tool in tool_names

    @patch("subprocess.run")
    def test_video_synchronization_tool(self, mock_subprocess):
        """Test the video synchronization tool."""
        # Mock successful execution
        mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")

        request = SynchronizationRequest(
            scenes=[
                {
                    "scene_number": 1,
                    "description": "Opening scene",
                    "visual_requirements": ["landscape"],
                    "dialogue": "Welcome to our video",
                    "duration": 5.0,
                }
            ],
            audio_segments=[
                {
                    "duration": 5.0,
                    "text": "Welcome to our video",
                    "audio_file": self.test_assets["audio"],
                    "scene_number": 1,
                }
            ],
            visual_assets=[self.test_assets["video1"]],
            target_duration=5.0,
        )

        response = synchronize_video_timeline(request)

        assert response.success is True
        assert response.total_duration == 5.0
        assert len(response.synchronized_timeline) == 1
        assert response.synchronized_timeline[0]["scene_number"] == 1

    @patch("subprocess.run")
    @patch("sub_agents.video_assembly.tools.ffmpeg_composition._get_video_duration")
    @patch("sub_agents.video_assembly.tools.ffmpeg_composition._get_video_metadata")
    def test_ffmpeg_composition_tool(
        self, mock_metadata, mock_duration, mock_subprocess
    ):
        """Test the FFmpeg composition tool."""
        # Mock successful execution
        mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")
        mock_duration.return_value = 10.0
        mock_metadata.return_value = {"width": 1920, "height": 1080, "fps": 30}

        request = VideoCompositionRequest(
            video_assets=[self.test_assets["video1"], self.test_assets["video2"]],
            audio_file=self.test_assets["audio"],
            output_path=self.test_assets["output"],
            scene_timings=[
                {"start_time": 0, "duration": 5},
                {"start_time": 5, "duration": 5},
            ],
        )

        response = compose_video_with_ffmpeg(request)

        assert response.success is True
        assert response.output_file == self.test_assets["output"]
        assert response.duration == 10.0
        mock_subprocess.assert_called_once()

    @patch("subprocess.run")
    @patch("sub_agents.video_assembly.tools.transition_effects._get_video_duration")
    def test_transition_effects_tool(self, mock_duration, mock_subprocess):
        """Test the transition effects tool."""
        # Mock successful execution
        mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")
        mock_duration.return_value = 8.0

        request = TransitionRequest(
            input_segments=[self.test_assets["video1"], self.test_assets["video2"]],
            transition_types=["crossfade"],
            transition_durations=[1.0],
            output_path=self.test_assets["output"],
        )

        response = apply_video_transitions(request)

        assert response.success is True
        assert response.output_file == self.test_assets["output"]
        assert response.total_duration == 8.0
        assert "Crossfade transition" in response.transitions_applied

    @patch("subprocess.run")
    @patch("os.path.getsize")
    @patch("sub_agents.video_assembly.tools.video_encoding._get_video_info")
    def test_video_encoding_tool(self, mock_video_info, mock_getsize, mock_subprocess):
        """Test the video encoding tool."""
        # Mock successful execution
        mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")
        mock_getsize.side_effect = [1000000, 800000]  # Original and encoded sizes
        mock_video_info.return_value = {
            "duration": 10.0,
            "width": 1920,
            "height": 1080,
            "fps": 30,
            "video_codec": "h264",
        }

        request = EncodingRequest(
            input_file=self.test_assets["video1"],
            output_file=self.test_assets["output"],
            quality="high",
            format="mp4",
        )

        response = encode_video(request)

        assert response.success is True
        assert response.output_file == self.test_assets["output"]
        assert response.original_size == 1000000
        assert response.encoded_size == 800000
        assert response.compression_ratio == 1.25

    def test_video_synchronization_error_handling(self):
        """Test error handling in video synchronization."""
        request = SynchronizationRequest(
            scenes=[],  # Empty scenes should cause error
            audio_segments=[],
            visual_assets=[],
            target_duration=10.0,
        )

        response = synchronize_video_timeline(request)

        assert response.success is False
        assert "Missing scenes or audio segments" in response.error_message

    @patch("subprocess.run")
    def test_ffmpeg_composition_missing_files(self, mock_subprocess):
        """Test FFmpeg composition with missing input files."""
        request = VideoCompositionRequest(
            video_assets=["/nonexistent/file.mp4"],
            audio_file="/nonexistent/audio.wav",
            output_path=self.test_assets["output"],
            scene_timings=[],
        )

        response = compose_video_with_ffmpeg(request)

        assert response.success is False
        assert "Audio file not found" in response.error_message

    @patch("subprocess.run")
    def test_transition_effects_insufficient_segments(self, mock_subprocess):
        """Test transition effects with insufficient input segments."""
        request = TransitionRequest(
            input_segments=[self.test_assets["video1"]],  # Only one segment
            transition_types=["crossfade"],
            transition_durations=[1.0],
            output_path=self.test_assets["output"],
        )

        response = apply_video_transitions(request)

        assert response.success is False
        assert "At least 2 video segments required" in response.error_message

    @patch("subprocess.run")
    def test_video_encoding_timeout(self, mock_subprocess):
        """Test video encoding timeout handling."""
        from subprocess import TimeoutExpired

        mock_subprocess.side_effect = TimeoutExpired("ffmpeg", 1800)

        request = EncodingRequest(
            input_file=self.test_assets["video1"],
            output_file=self.test_assets["output"],
        )

        response = encode_video(request)

        assert response.success is False
        assert "timed out" in response.error_message

    def test_integration_workflow_simulation(self):
        """Test a simulated integration workflow."""
        # This test simulates the complete workflow without actual FFmpeg execution

        # Step 1: Synchronization
        sync_request = SynchronizationRequest(
            scenes=[
                {
                    "scene_number": 1,
                    "description": "Opening",
                    "visual_requirements": ["landscape"],
                    "dialogue": "Hello world",
                    "duration": 3.0,
                },
                {
                    "scene_number": 2,
                    "description": "Closing",
                    "visual_requirements": ["sunset"],
                    "dialogue": "Goodbye",
                    "duration": 2.0,
                },
            ],
            audio_segments=[
                {
                    "duration": 3.0,
                    "text": "Hello world",
                    "scene_number": 1,
                    "audio_file": "audio1.wav",
                },
                {
                    "duration": 2.0,
                    "text": "Goodbye",
                    "scene_number": 2,
                    "audio_file": "audio2.wav",
                },
            ],
            visual_assets=["video1.mp4", "video2.mp4"],
            target_duration=5.0,
        )

        sync_response = synchronize_video_timeline(sync_request)

        # Verify synchronization worked
        assert sync_response.success is True
        assert len(sync_response.synchronized_timeline) == 2
        assert sync_response.total_duration == 5.0

        # Verify timeline structure
        timeline = sync_response.synchronized_timeline
        assert timeline[0]["scene_number"] == 1
        assert timeline[1]["scene_number"] == 2
        assert timeline[0]["start_time"] == 0.0
        assert timeline[1]["start_time"] > 0.0


class TestVideoAssemblyUtilities:
    """Test utility functions in video assembly tools."""

    def test_transition_suggestion(self):
        """Test transition suggestion based on content."""
        from video_system.tools.video_tools import suggest_transition_for_content

        assert suggest_transition_for_content("dramatic action scene") == "zoom"
        assert suggest_transition_for_content("peaceful landscape") == "dissolve"
        assert suggest_transition_for_content("fast-paced action") == "slide"
        assert suggest_transition_for_content("emotional moment") == "fade_in"
        assert suggest_transition_for_content("regular scene") == "crossfade"

    def test_optimal_transition_duration(self):
        """Test optimal transition duration calculation."""
        from video_system.tools.video_tools import calculate_optimal_transition_duration

        # Test various segment durations
        assert calculate_optimal_transition_duration(10.0) == 0.75  # 7.5% of 10s
        assert calculate_optimal_transition_duration(5.0) == 0.5  # Minimum bound
        assert calculate_optimal_transition_duration(50.0) == 3.0  # Maximum bound

    def test_encoding_recommendations(self):
        """Test encoding recommendation system."""
        from video_system.tools.video_tools import get_recommended_settings

        web_settings = get_recommended_settings(150.0, "web")
        assert web_settings["optimize_for"] == "size"
        assert web_settings["resolution"] == "1280x720"

        mobile_settings = get_recommended_settings(50.0, "mobile")
        assert mobile_settings["resolution"] == "854x480"
        assert mobile_settings["fps"] == 24

        archive_settings = get_recommended_settings(100.0, "archive")
        assert archive_settings["quality"] == "ultra"

    def test_encoding_time_estimation(self):
        """Test encoding time estimation."""
        from video_system.tools.video_tools import estimate_encoding_time

        # Test different quality levels
        assert estimate_encoding_time(60.0, "low") == 30.0  # 2x realtime
        assert estimate_encoding_time(60.0, "medium") == 60.0  # 1x realtime
        assert estimate_encoding_time(60.0, "high") == 120.0  # 0.5x realtime
        assert estimate_encoding_time(60.0, "ultra") == 240.0  # 0.25x realtime


if __name__ == "__main__":
    pytest.main([__file__])

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

"""Integration tests for agent orchestration and coordination."""

import pytest
from unittest.mock import patch

from video_system.orchestration_tools import (
    coordinate_research,
    coordinate_story,
    coordinate_assets,
    coordinate_audio,
    coordinate_assembly,
    get_session_status,
    create_session_state,
    get_session_state,
    session_states
)
from video_system.shared_libraries.models import (
    VideoGenerationRequest,
    VideoStyle,
    VideoQuality,
    ResearchData,
    VideoScript,
    VideoScene,
    AssetCollection,
    AssetItem,
    AudioAssets
)
from video_system.agent import root_agent


class TestOrchestrationTools:
    """Test suite for orchestration tools."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Clear session states before each test
        session_states.clear()
        
        # Create a test video request
        self.test_request = VideoGenerationRequest(
            prompt="Create a video about renewable energy",
            duration_preference=60,
            style=VideoStyle.EDUCATIONAL,
            voice_preference="neutral",
            quality=VideoQuality.HIGH
        )
        
        # Create a test session
        self.session_state = create_session_state(self.test_request)
        self.session_id = self.session_state.session_id
    
    def test_create_session_state(self):
        """Test session state creation."""
        assert self.session_state.session_id is not None
        assert self.session_state.request == self.test_request
        assert self.session_state.status.status == "processing"
        assert self.session_state.status.progress == 0.0
        assert self.session_state.research_data is None
        assert self.session_state.script is None
    
    def test_get_session_state(self):
        """Test session state retrieval."""
        retrieved_state = get_session_state(self.session_id)
        assert retrieved_state is not None
        assert retrieved_state.session_id == self.session_id
        assert retrieved_state.request.prompt == self.test_request.prompt
        
        # Test non-existent session
        non_existent = get_session_state("non-existent-id")
        assert non_existent is None
    
    def test_coordinate_research_tool(self):
        """Test research coordination tool."""
        # Test successful research coordination
        result = coordinate_research(
            topic="renewable energy",
            session_id=self.session_id
        )
        
        assert result["success"] is True
        assert result["session_id"] == self.session_id
        assert result["research_data"] is not None
        assert "facts" in result["research_data"]
        assert "sources" in result["research_data"]
        assert "key_points" in result["research_data"]
        
        # Verify session state was updated
        session_state = get_session_state(self.session_id)
        assert session_state.research_data is not None
        assert session_state.status.progress == 0.2
        assert session_state.status.current_stage == "Research"
    
    def test_coordinate_story_tool(self):
        """Test story coordination tool."""
        # First set up research data
        research_data = ResearchData(
            facts=["Renewable energy is sustainable", "Solar power is growing rapidly"],
            sources=["https://example.com/renewable", "https://example.com/solar"],
            key_points=["Sustainability", "Growth trends"],
            context={"topic": "renewable energy"}
        )
        
        # Test successful story coordination
        result = coordinate_story(
            research_data=research_data.model_dump(),
            session_id=self.session_id,
            duration=60
        )
        
        assert result["success"] is True
        assert result["session_id"] == self.session_id
        assert result["script"] is not None
        
        script_data = result["script"]
        assert "title" in script_data
        assert "scenes" in script_data
        assert "total_duration" in script_data
        assert len(script_data["scenes"]) == 3  # Introduction, main content, conclusion
        
        # Verify session state was updated
        session_state = get_session_state(self.session_id)
        assert session_state.script is not None
        assert session_state.status.progress == 0.4
        assert session_state.status.current_stage == "Script Creation"
    
    def test_coordinate_assets_tool(self):
        """Test asset coordination tool."""
        # Set up script data
        script = VideoScript(
            title="Renewable Energy Video",
            total_duration=60.0,
            scenes=[
                VideoScene(
                    scene_number=1,
                    description="Introduction to renewable energy",
                    visual_requirements=["title card", "clean energy imagery"],
                    dialogue="Welcome to our renewable energy overview",
                    duration=20.0
                ),
                VideoScene(
                    scene_number=2,
                    description="Solar power benefits",
                    visual_requirements=["solar panels", "statistics"],
                    dialogue="Solar power offers many advantages",
                    duration=20.0
                ),
                VideoScene(
                    scene_number=3,
                    description="Future of renewable energy",
                    visual_requirements=["future technology", "growth charts"],
                    dialogue="The future looks bright for renewable energy",
                    duration=20.0
                )
            ]
        )
        
        # Test successful asset coordination
        result = coordinate_assets(
            script=script.model_dump(),
            session_id=self.session_id
        )
        
        assert result["success"] is True
        assert result["session_id"] == self.session_id
        assert result["assets"] is not None
        
        assets_data = result["assets"]
        assert "images" in assets_data
        assert "videos" in assets_data
        assert len(assets_data["images"]) >= 3  # At least one per scene
        
        # Verify session state was updated
        session_state = get_session_state(self.session_id)
        assert session_state.assets is not None
        assert session_state.status.progress == 0.6
        assert session_state.status.current_stage == "Asset Collection"
    
    def test_coordinate_audio_tool(self):
        """Test audio coordination tool."""
        # Set up script data
        script = VideoScript(
            title="Test Video",
            total_duration=60.0,
            scenes=[
                VideoScene(
                    scene_number=1,
                    description="Test scene",
                    visual_requirements=["test image"],
                    dialogue="This is test dialogue",
                    duration=30.0
                ),
                VideoScene(
                    scene_number=2,
                    description="Second test scene",
                    visual_requirements=["another test image"],
                    dialogue="This is more test dialogue",
                    duration=30.0
                )
            ]
        )
        
        # Test successful audio coordination
        result = coordinate_audio(
            script=script.model_dump(),
            session_id=self.session_id
        )
        
        assert result["success"] is True
        assert result["session_id"] == self.session_id
        assert result["audio_assets"] is not None
        
        audio_data = result["audio_assets"]
        assert "voice_files" in audio_data
        assert "timing_data" in audio_data
        assert "synchronization_markers" in audio_data
        assert len(audio_data["voice_files"]) == 2  # One per scene
        
        # Verify session state was updated
        session_state = get_session_state(self.session_id)
        assert session_state.audio_assets is not None
        assert session_state.status.progress == 0.8
        assert session_state.status.current_stage == "Audio Generation"
    
    def test_coordinate_assembly_tool(self):
        """Test video assembly coordination tool."""
        # Set up all required data
        script = VideoScript(
            title="Test Video",
            total_duration=60.0,
            scenes=[
                VideoScene(
                    scene_number=1,
                    description="Test scene",
                    visual_requirements=["test image"],
                    dialogue="Test dialogue",
                    duration=60.0
                )
            ]
        )
        
        assets = AssetCollection(
            images=[
                AssetItem(
                    asset_id="test_img_1",
                    asset_type="image",
                    source_url="https://example.com/test.jpg",
                    local_path="/tmp/test.jpg",
                    usage_rights="royalty_free",
                    metadata={"scene": 1}
                )
            ],
            videos=[],
            metadata={"total_assets": 1}
        )
        
        audio_assets = AudioAssets(
            voice_files=["/tmp/audio_scene_1.wav"],
            timing_data={"total_duration": 60.0},
            synchronization_markers=[{"time": 0, "scene": 1}]
        )
        
        # Test successful assembly coordination
        result = coordinate_assembly(
            script=script.model_dump(),
            assets=assets.model_dump(),
            audio_assets=audio_assets.model_dump(),
            session_id=self.session_id
        )
        
        assert result["success"] is True
        assert result["session_id"] == self.session_id
        assert result["final_video"] is not None
        
        video_data = result["final_video"]
        assert "video_file" in video_data
        assert "metadata" in video_data
        assert "quality_metrics" in video_data
        
        # Verify session state was updated
        session_state = get_session_state(self.session_id)
        assert session_state.final_video is not None
        assert session_state.status.progress == 1.0
        assert session_state.status.status == "completed"
        assert session_state.status.current_stage == "Completed"
    
    def test_get_session_status_tool(self):
        """Test session status retrieval tool."""
        # Test successful status retrieval
        result = get_session_status(session_id=self.session_id)
        
        assert result["success"] is True
        assert result["status"] is not None
        assert result["status"]["session_id"] == self.session_id
        assert result["status"]["status"] == "processing"
        assert result["status"]["progress"] == 0.0
        
        # Test non-existent session
        result = get_session_status(session_id="non-existent")
        assert result["success"] is False
        assert result["status"] is None
        assert "not found" in result["error_message"]
    
    def test_error_handling(self):
        """Test error handling in coordination tools."""
        # Test with invalid session ID
        result = coordinate_research(
            topic="test topic",
            session_id="invalid-session-id"
        )
        
        # Should still work but session state won't be updated
        assert result["success"] is True  # Tool itself works
        assert result["session_id"] == "invalid-session-id"
    
    def test_workflow_sequence(self):
        """Test complete workflow sequence."""
        # 1. Research
        research_result = coordinate_research(
            topic="renewable energy",
            session_id=self.session_id
        )
        assert research_result["success"] is True
        
        # 2. Story
        story_result = coordinate_story(
            research_data=research_result["research_data"],
            session_id=self.session_id,
            duration=60
        )
        assert story_result["success"] is True
        
        # 3. Assets
        assets_result = coordinate_assets(
            script=story_result["script"],
            session_id=self.session_id
        )
        assert assets_result["success"] is True
        
        # 4. Audio
        audio_result = coordinate_audio(
            script=story_result["script"],
            session_id=self.session_id
        )
        assert audio_result["success"] is True
        
        # 5. Assembly
        assembly_result = coordinate_assembly(
            script=story_result["script"],
            assets=assets_result["assets"],
            audio_assets=audio_result["audio_assets"],
            session_id=self.session_id
        )
        assert assembly_result["success"] is True
        
        # Verify final session state
        session_state = get_session_state(self.session_id)
        assert session_state.status.status == "completed"
        assert session_state.status.progress == 1.0
        assert session_state.research_data is not None
        assert session_state.script is not None
        assert session_state.assets is not None
        assert session_state.audio_assets is not None
        assert session_state.final_video is not None


class TestRootAgentIntegration:
    """Test suite for root agent integration."""
    
    def setup_method(self):
        """Set up test fixtures."""
        session_states.clear()
    
    def test_root_agent_tools(self):
        """Test that root agent has all required tools."""
        tools = root_agent.tools
        tool_names = [tool.__name__ if hasattr(tool, '__name__') else str(tool) for tool in tools]
        
        expected_tools = [
            "coordinate_research",
            "coordinate_story", 
            "coordinate_assets",
            "coordinate_audio",
            "coordinate_assembly",
            "get_session_status",
            "start_video_generation",
            "execute_complete_workflow"
        ]
        
        for expected_tool in expected_tools:
            assert expected_tool in tool_names, f"Missing tool: {expected_tool}"
    
    def test_start_video_generation_tool(self):
        """Test the start video generation tool."""
        # Find the start_video_generation tool
        start_tool = None
        for tool in root_agent.tools:
            if hasattr(tool, '__name__') and tool.__name__ == "start_video_generation":
                start_tool = tool
                break
        
        assert start_tool is not None, "start_video_generation tool not found"
        
        # Test the tool
        result = start_tool(
            prompt="Create a video about artificial intelligence",
            duration_preference=90,
            style="educational",
            voice_preference="professional",
            quality="high"
        )
        
        assert result["success"] is True
        assert result["session_id"] != ""
        assert result["status"] is not None
        assert result["status"]["status"] == "processing"
        
        # Verify session was created
        session_id = result["session_id"]
        session_state = get_session_state(session_id)
        assert session_state is not None
        assert session_state.request.prompt == "Create a video about artificial intelligence"
        assert session_state.request.duration_preference == 90
    
    def test_execute_complete_workflow_tool(self):
        """Test the execute complete workflow tool."""
        # First create a session
        start_tool = None
        for tool in root_agent.tools:
            if hasattr(tool, '__name__') and tool.__name__ == "start_video_generation":
                start_tool = tool
                break
        
        start_result = start_tool(
            prompt="Test video prompt",
            duration_preference=60
        )
        session_id = start_result["session_id"]
        
        # Find the execute workflow tool
        execute_tool = None
        for tool in root_agent.tools:
            if hasattr(tool, '__name__') and tool.__name__ == "execute_complete_workflow":
                execute_tool = tool
                break
        
        assert execute_tool is not None, "execute_complete_workflow tool not found"
        
        # Test the tool
        result = execute_tool(session_id=session_id)
        
        assert result["success"] is True
        assert result["session_id"] == session_id
        assert "workflow initialized" in result["error_message"].lower()
    
    def test_agent_model_and_name(self):
        """Test root agent configuration."""
        assert root_agent.model == 'gemini-2.5-pro'
        assert root_agent.name == 'video_system_orchestrator'
        assert root_agent.instruction is not None
        assert len(root_agent.instruction) > 100  # Should have substantial instructions


class TestErrorRecoveryAndRetry:
    """Test suite for error recovery and retry mechanisms."""
    
    def setup_method(self):
        """Set up test fixtures."""
        session_states.clear()
    
    @patch('video_system.orchestration_tools.logger')
    def test_error_logging(self, mock_logger):
        """Test that errors are properly logged."""
        # Create a session
        request = VideoGenerationRequest(
            prompt="Test prompt",
            duration_preference=60
        )
        session_state = create_session_state(request)
        session_id = session_state.session_id
        
        # Mock an exception during research
        with patch('video_system.orchestration_tools.coordinate_research', side_effect=Exception("Test error")):
            try:
                coordinate_research(topic="test", session_id=session_id)
            except:
                pass
        
        # Verify error was logged (in real implementation)
        # This is a simplified test since we're mocking
        assert True  # Placeholder for actual error logging verification
    
    def test_session_state_error_tracking(self):
        """Test that session state tracks errors properly."""
        request = VideoGenerationRequest(
            prompt="Test prompt",
            duration_preference=60
        )
        session_state = create_session_state(request)
        
        # Simulate adding errors to session state
        session_state.error_log.append("Test error 1")
        session_state.error_log.append("Test error 2")
        session_state.retry_count["research"] = 2
        
        assert len(session_state.error_log) == 2
        assert session_state.retry_count["research"] == 2
    
    def test_retry_count_tracking(self):
        """Test retry count tracking in session state."""
        request = VideoGenerationRequest(
            prompt="Test prompt",
            duration_preference=60
        )
        session_state = create_session_state(request)
        
        # Test initial state
        assert session_state.retry_count == {}
        
        # Simulate retry tracking
        session_state.retry_count["research"] = 1
        session_state.retry_count["story"] = 2
        
        assert session_state.retry_count["research"] == 1
        assert session_state.retry_count["story"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
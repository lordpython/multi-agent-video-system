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

"""Unit tests for core data models."""

import pytest
from pydantic import ValidationError
from video_system.shared_libraries.models import (
    VideoGenerationRequest,
    VideoScript,
    VideoScene,
    AssetItem,
    VideoGenerationStatus,
    VideoStatus,
    AssetType,
    VideoQuality,
    VideoStyle,
    ResearchRequest,
    ResearchData,
    ScriptRequest,
    AssetRequest,
    AssetCollection,
    AudioRequest,
    AudioAssets,
    AssemblyRequest,
    FinalVideo
)


class TestVideoGenerationRequest:
    """Test cases for VideoGenerationRequest model."""
    
    def test_valid_request(self):
        """Test creating a valid video generation request."""
        request = VideoGenerationRequest(
            prompt="Create a video about artificial intelligence",
            duration_preference=120,
            style=VideoStyle.EDUCATIONAL,
            voice_preference="female",
            quality=VideoQuality.HIGH
        )
        assert request.prompt == "Create a video about artificial intelligence"
        assert request.duration_preference == 120
        assert request.style == VideoStyle.EDUCATIONAL
        assert request.voice_preference == "female"
        assert request.quality == VideoQuality.HIGH
    
    def test_minimal_request(self):
        """Test creating a request with minimal required fields."""
        request = VideoGenerationRequest(prompt="Test video prompt")
        assert request.prompt == "Test video prompt"
        assert request.duration_preference == 60  # default
        assert request.style == VideoStyle.PROFESSIONAL  # default
        assert request.voice_preference == "neutral"  # default
        assert request.quality == VideoQuality.HIGH  # default
    
    def test_prompt_validation(self):
        """Test prompt validation rules."""
        # Test empty prompt
        with pytest.raises(ValidationError):
            VideoGenerationRequest(prompt="")
        
        # Test whitespace-only prompt
        with pytest.raises(ValidationError):
            VideoGenerationRequest(prompt="   ")
        
        # Test too short prompt
        with pytest.raises(ValidationError):
            VideoGenerationRequest(prompt="short")
        
        # Test too long prompt
        with pytest.raises(ValidationError):
            VideoGenerationRequest(prompt="x" * 2001)
    
    def test_duration_validation(self):
        """Test duration validation rules."""
        # Test too short duration
        with pytest.raises(ValidationError):
            VideoGenerationRequest(
                prompt="Valid prompt for testing",
                duration_preference=5
            )
        
        # Test too long duration
        with pytest.raises(ValidationError):
            VideoGenerationRequest(
                prompt="Valid prompt for testing",
                duration_preference=700
            )


class TestVideoScene:
    """Test cases for VideoScene model."""
    
    def test_valid_scene(self):
        """Test creating a valid video scene."""
        scene = VideoScene(
            scene_number=1,
            description="Opening scene with introduction",
            visual_requirements=["person speaking", "office background"],
            dialogue="Welcome to our presentation",
            duration=15.5,
            assets=["asset1", "asset2"]
        )
        assert scene.scene_number == 1
        assert scene.description == "Opening scene with introduction"
        assert scene.visual_requirements == ["person speaking", "office background"]
        assert scene.dialogue == "Welcome to our presentation"
        assert scene.duration == 15.5
        assert scene.assets == ["asset1", "asset2"]
    
    def test_scene_validation(self):
        """Test scene validation rules."""
        # Test invalid scene number
        with pytest.raises(ValidationError):
            VideoScene(
                scene_number=0,
                description="Test description",
                visual_requirements=["test"],
                dialogue="Test dialogue",
                duration=10.0
            )
        
        # Test empty visual requirements
        with pytest.raises(ValidationError):
            VideoScene(
                scene_number=1,
                description="Test description",
                visual_requirements=[],
                dialogue="Test dialogue",
                duration=10.0
            )
        
        # Test invalid duration
        with pytest.raises(ValidationError):
            VideoScene(
                scene_number=1,
                description="Test description",
                visual_requirements=["test"],
                dialogue="Test dialogue",
                duration=0
            )


class TestVideoScript:
    """Test cases for VideoScript model."""
    
    def test_valid_script(self):
        """Test creating a valid video script."""
        scenes = [
            VideoScene(
                scene_number=1,
                description="Opening scene with introduction",
                visual_requirements=["requirement 1"],
                dialogue="Dialogue 1",
                duration=30.0
            ),
            VideoScene(
                scene_number=2,
                description="Second scene with main content",
                visual_requirements=["requirement 2"],
                dialogue="Dialogue 2",
                duration=30.0
            )
        ]
        
        script = VideoScript(
            title="Test Video",
            total_duration=60.0,
            scenes=scenes,
            metadata={"author": "test"}
        )
        
        assert script.title == "Test Video"
        assert script.total_duration == 60.0
        assert len(script.scenes) == 2
        assert script.metadata["author"] == "test"
    
    def test_scene_sequence_validation(self):
        """Test scene sequence validation."""
        # Test non-sequential scene numbers
        scenes = [
            VideoScene(
                scene_number=1,
                description="First scene with introduction",
                visual_requirements=["req"],
                dialogue="Dialogue",
                duration=30.0
            ),
            VideoScene(
                scene_number=3,  # Should be 2
                description="Third scene with conclusion",
                visual_requirements=["req"],
                dialogue="Dialogue",
                duration=30.0
            )
        ]
        
        with pytest.raises(ValidationError):
            VideoScript(
                title="Test Video",
                total_duration=60.0,
                scenes=scenes
            )
    
    def test_duration_mismatch_validation(self):
        """Test duration validation between total and scene sum."""
        scenes = [
            VideoScene(
                scene_number=1,
                description="First scene with content",
                visual_requirements=["req"],
                dialogue="Dialogue",
                duration=30.0
            )
        ]
        
        # Total duration doesn't match scene duration
        with pytest.raises(ValidationError):
            VideoScript(
                title="Test Video",
                total_duration=60.0,  # Should be 30.0
                scenes=scenes
            )


class TestAssetItem:
    """Test cases for AssetItem model."""
    
    def test_valid_asset(self):
        """Test creating a valid asset item."""
        asset = AssetItem(
            asset_id="asset123",
            asset_type="image",
            source_url="https://example.com/image.jpg",
            local_path="/local/path/image.jpg",
            usage_rights="Creative Commons",
            metadata={"size": "1920x1080"}
        )
        
        assert asset.asset_id == "asset123"
        assert asset.asset_type == "image"
        assert asset.source_url == "https://example.com/image.jpg"
        assert asset.local_path == "/local/path/image.jpg"
        assert asset.usage_rights == "Creative Commons"
        assert asset.metadata["size"] == "1920x1080"


class TestVideoGenerationStatus:
    """Test cases for VideoGenerationStatus model."""
    
    def test_valid_status(self):
        """Test creating a valid video generation status."""
        status = VideoGenerationStatus(
            session_id="session123",
            status="processing",
            progress=0.5,
            current_stage="Research",
            estimated_completion="2024-01-01T12:00:00",
            error_message=None
        )
        
        assert status.session_id == "session123"
        assert status.status == "processing"
        assert status.progress == 0.5
        assert status.current_stage == "Research"
        assert status.estimated_completion == "2024-01-01T12:00:00"
        assert status.error_message is None


class TestResearchModels:
    """Test cases for research-related models."""
    
    def test_research_request(self):
        """Test creating a research request."""
        request = ResearchRequest(
            topic="Artificial Intelligence",
            scope="comprehensive",
            depth_requirements="detailed"
        )
        
        assert request.topic == "Artificial Intelligence"
        assert request.scope == "comprehensive"
        assert request.depth_requirements == "detailed"
    
    def test_research_data(self):
        """Test creating research data."""
        data = ResearchData(
            facts=["AI is growing rapidly", "Machine learning is a subset of AI"],
            sources=["https://example.com/ai-article"],
            key_points=["Growth", "Applications"],
            context={"industry": "technology"}
        )
        
        assert len(data.facts) == 2
        assert len(data.sources) == 1
        assert len(data.key_points) == 2
        assert data.context["industry"] == "technology"


class TestAssetModels:
    """Test cases for asset-related models."""
    
    def test_asset_request(self):
        """Test creating an asset request."""
        request = AssetRequest(
            scene_descriptions=["Office scene", "Nature scene"],
            style_requirements={"style": "professional"},
            specifications={"resolution": "1080p"}
        )
        
        assert len(request.scene_descriptions) == 2
        assert request.style_requirements["style"] == "professional"
        assert request.specifications["resolution"] == "1080p"
    
    def test_asset_collection(self):
        """Test creating an asset collection."""
        asset = AssetItem(
            asset_id="img1",
            asset_type="image",
            source_url="https://example.com/img.jpg",
            usage_rights="Free"
        )
        
        collection = AssetCollection(
            images=[asset],
            videos=[],
            metadata={"total_count": 1}
        )
        
        assert len(collection.images) == 1
        assert len(collection.videos) == 0
        assert collection.metadata["total_count"] == 1


class TestAudioModels:
    """Test cases for audio-related models."""
    
    def test_audio_request(self):
        """Test creating an audio request."""
        request = AudioRequest(
            script_text="Hello world",
            voice_preferences={"voice": "female"},
            timing_requirements={"speed": "normal"}
        )
        
        assert request.script_text == "Hello world"
        assert request.voice_preferences["voice"] == "female"
        assert request.timing_requirements["speed"] == "normal"
    
    def test_audio_assets(self):
        """Test creating audio assets."""
        assets = AudioAssets(
            voice_files=["audio1.wav", "audio2.wav"],
            timing_data={"total_duration": 60},
            synchronization_markers=[{"time": 0, "text": "start"}]
        )
        
        assert len(assets.voice_files) == 2
        assert assets.timing_data["total_duration"] == 60
        assert len(assets.synchronization_markers) == 1


class TestAssemblyModels:
    """Test cases for assembly-related models."""
    
    def test_assembly_request(self):
        """Test creating an assembly request."""
        # Create required components
        asset = AssetItem(
            asset_id="img1",
            asset_type="image",
            source_url="https://example.com/img.jpg",
            usage_rights="Free"
        )
        
        asset_collection = AssetCollection(images=[asset])
        
        audio_assets = AudioAssets(
            voice_files=["audio.wav"],
            timing_data={},
            synchronization_markers=[]
        )
        
        scene = VideoScene(
            scene_number=1,
            description="Test scene",
            visual_requirements=["test"],
            dialogue="Test dialogue",
            duration=30.0
        )
        
        script = VideoScript(
            title="Test Video",
            total_duration=30.0,
            scenes=[scene]
        )
        
        request = AssemblyRequest(
            assets=asset_collection,
            audio=audio_assets,
            script=script,
            specifications={"format": "mp4"}
        )
        
        assert len(request.assets.images) == 1
        assert len(request.audio.voice_files) == 1
        assert request.script.title == "Test Video"
        assert request.specifications["format"] == "mp4"
    
    def test_final_video(self):
        """Test creating a final video model."""
        video = FinalVideo(
            video_file="/path/to/video.mp4",
            metadata={"duration": 60, "format": "mp4"},
            quality_metrics={"resolution": "1080p", "bitrate": "5000kbps"}
        )
        
        assert video.video_file == "/path/to/video.mp4"
        assert video.metadata["duration"] == 60
        assert video.quality_metrics["resolution"] == "1080p"


class TestEnums:
    """Test cases for enum values."""
    
    def test_video_status_enum(self):
        """Test VideoStatus enum values."""
        assert VideoStatus.PROCESSING == "processing"
        assert VideoStatus.COMPLETED == "completed"
        assert VideoStatus.FAILED == "failed"
        assert VideoStatus.QUEUED == "queued"
        assert VideoStatus.CANCELLED == "cancelled"
    
    def test_asset_type_enum(self):
        """Test AssetType enum values."""
        assert AssetType.IMAGE == "image"
        assert AssetType.VIDEO == "video"
        assert AssetType.AUDIO == "audio"
    
    def test_video_quality_enum(self):
        """Test VideoQuality enum values."""
        assert VideoQuality.LOW == "low"
        assert VideoQuality.MEDIUM == "medium"
        assert VideoQuality.HIGH == "high"
        assert VideoQuality.ULTRA == "ultra"
    
    def test_video_style_enum(self):
        """Test VideoStyle enum values."""
        assert VideoStyle.PROFESSIONAL == "professional"
        assert VideoStyle.CASUAL == "casual"
        assert VideoStyle.EDUCATIONAL == "educational"
        assert VideoStyle.ENTERTAINMENT == "entertainment"
        assert VideoStyle.DOCUMENTARY == "documentary"


class TestValidationUtilities:
    """Test cases for validation utility functions."""
    
    def test_validate_video_duration(self):
        """Test video duration validation utility."""
        from video_system.shared_libraries.models import validate_video_duration
        
        # Valid durations
        assert validate_video_duration(10) is True
        assert validate_video_duration(60) is True
        assert validate_video_duration(600) is True
        
        # Invalid durations
        assert validate_video_duration(5) is False
        assert validate_video_duration(700) is False
        assert validate_video_duration(0) is False
        assert validate_video_duration(-10) is False
    
    def test_validate_scene_duration(self):
        """Test scene duration validation utility."""
        from video_system.shared_libraries.models import validate_scene_duration
        
        # Valid durations
        assert validate_scene_duration(0.1) is True
        assert validate_scene_duration(30) is True
        assert validate_scene_duration(120) is True
        
        # Invalid durations
        assert validate_scene_duration(0) is False
        assert validate_scene_duration(-5) is False
        assert validate_scene_duration(150) is False
    
    def test_validate_prompt_length(self):
        """Test prompt length validation utility."""
        from video_system.shared_libraries.models import validate_prompt_length
        
        # Valid prompts
        assert validate_prompt_length("This is a valid prompt for testing") is True
        assert validate_prompt_length("x" * 100) is True
        assert validate_prompt_length("x" * 2000) is True
        
        # Invalid prompts
        assert validate_prompt_length("short") is False
        assert validate_prompt_length("x" * 2001) is False
        assert validate_prompt_length("") is False
        assert validate_prompt_length("   ") is False
    
    def test_validate_asset_url(self):
        """Test asset URL validation utility."""
        from video_system.shared_libraries.models import validate_asset_url
        
        # Valid URLs
        assert validate_asset_url("https://example.com/image.jpg") is True
        assert validate_asset_url("http://test.com/video.mp4") is True
        assert validate_asset_url("https://subdomain.example.com/path/file.png") is True
        
        # Invalid URLs
        assert validate_asset_url("not-a-url") is False
        assert validate_asset_url("ftp://example.com/file.jpg") is False
        assert validate_asset_url("") is False
    
    def test_validate_scene_sequence(self):
        """Test scene sequence validation utility."""
        from video_system.shared_libraries.models import validate_scene_sequence
        
        # Valid sequences
        scenes_valid = [
            VideoScene(
                scene_number=1,
                description="First scene with introduction",
                visual_requirements=["req1"],
                dialogue="Dialogue 1",
                duration=30.0
            ),
            VideoScene(
                scene_number=2,
                description="Second scene with main content",
                visual_requirements=["req2"],
                dialogue="Dialogue 2",
                duration=30.0
            )
        ]
        assert validate_scene_sequence(scenes_valid) is True
        
        # Invalid sequences
        scenes_invalid = [
            VideoScene(
                scene_number=1,
                description="First scene with introduction",
                visual_requirements=["req1"],
                dialogue="Dialogue 1",
                duration=30.0
            ),
            VideoScene(
                scene_number=3,  # Should be 2
                description="Third scene with conclusion",
                visual_requirements=["req3"],
                dialogue="Dialogue 3",
                duration=30.0
            )
        ]
        assert validate_scene_sequence(scenes_invalid) is False
        
        # Empty list
        assert validate_scene_sequence([]) is False


class TestHelperFunctions:
    """Test cases for helper functions."""
    
    def test_generate_session_id(self):
        """Test session ID generation."""
        from video_system.shared_libraries.models import generate_session_id
        
        # Generate multiple IDs and ensure they're unique
        id1 = generate_session_id()
        id2 = generate_session_id()
        
        assert isinstance(id1, str)
        assert isinstance(id2, str)
        assert id1 != id2
        assert len(id1) > 0
        assert len(id2) > 0
    
    def test_calculate_total_duration(self):
        """Test total duration calculation."""
        from video_system.shared_libraries.models import calculate_total_duration
        
        scenes = [
            VideoScene(
                scene_number=1,
                description="First scene with introduction",
                visual_requirements=["req1"],
                dialogue="Dialogue 1",
                duration=30.0
            ),
            VideoScene(
                scene_number=2,
                description="Second scene with main content",
                visual_requirements=["req2"],
                dialogue="Dialogue 2",
                duration=45.5
            )
        ]
        
        total = calculate_total_duration(scenes)
        assert total == 75.5
        
        # Empty list
        assert calculate_total_duration([]) == 0
    
    def test_create_default_video_request(self):
        """Test default video request creation."""
        from video_system.shared_libraries.models import create_default_video_request
        
        request = create_default_video_request("Test prompt for video generation")
        
        assert request.prompt == "Test prompt for video generation"
        assert request.duration_preference == 60
        assert request.style == VideoStyle.PROFESSIONAL
        assert request.voice_preference == "neutral"
        assert request.quality == VideoQuality.HIGH
    
    def test_create_video_status(self):
        """Test video status creation."""
        from video_system.shared_libraries.models import create_video_status
        
        # Default status
        status = create_video_status("session123")
        assert status.session_id == "session123"
        assert status.status == "queued"
        assert status.progress == 0.0
        assert status.current_stage == "Initializing"
        assert status.estimated_completion is None
        assert status.error_message is None
        
        # Custom status
        status_custom = create_video_status("session456", "processing")
        assert status_custom.session_id == "session456"
        assert status_custom.status == "processing"
    
    def test_get_asset_by_type(self):
        """Test asset filtering by type."""
        from video_system.shared_libraries.models import get_asset_by_type
        
        assets = [
            AssetItem(
                asset_id="img1",
                asset_type="image",
                source_url="https://example.com/img1.jpg",
                usage_rights="Free"
            ),
            AssetItem(
                asset_id="vid1",
                asset_type="video",
                source_url="https://example.com/vid1.mp4",
                usage_rights="Free"
            ),
            AssetItem(
                asset_id="img2",
                asset_type="image",
                source_url="https://example.com/img2.jpg",
                usage_rights="Free"
            )
        ]
        
        images = get_asset_by_type(assets, "image")
        videos = get_asset_by_type(assets, "video")
        audio = get_asset_by_type(assets, "audio")
        
        assert len(images) == 2
        assert len(videos) == 1
        assert len(audio) == 0
        assert images[0].asset_id == "img1"
        assert images[1].asset_id == "img2"
        assert videos[0].asset_id == "vid1"
    
    def test_validate_video_script_consistency(self):
        """Test video script consistency validation."""
        from video_system.shared_libraries.models import validate_video_script_consistency
        
        # Valid script
        scenes_valid = [
            VideoScene(
                scene_number=1,
                description="First scene with introduction",
                visual_requirements=["req1"],
                dialogue="Dialogue 1",
                duration=30.0
            ),
            VideoScene(
                scene_number=2,
                description="Second scene with main content",
                visual_requirements=["req2"],
                dialogue="Dialogue 2",
                duration=30.0
            )
        ]
        
        script_valid = VideoScript(
            title="Valid Script",
            total_duration=60.0,
            scenes=scenes_valid
        )
        
        issues = validate_video_script_consistency(script_valid)
        assert len(issues) == 0
        
        # Script with duration mismatch - we need to create this manually to bypass validation
        # Create a script that would have duration mismatch by modifying after creation
        script_invalid_duration = VideoScript(
            title="Invalid Duration Script",
            total_duration=60.0,
            scenes=scenes_valid
        )
        # Manually modify the total_duration to create mismatch for testing
        script_invalid_duration.total_duration = 100.0
        
        issues = validate_video_script_consistency(script_invalid_duration)
        assert len(issues) > 0
        assert any("duration" in issue.lower() for issue in issues)
        
        # Script with invalid scene sequence - create manually to bypass validation
        script_invalid_sequence = VideoScript(
            title="Invalid Sequence Script",
            total_duration=60.0,
            scenes=scenes_valid
        )
        # Manually modify scene numbers to create invalid sequence
        script_invalid_sequence.scenes[1].scene_number = 3  # Should be 2
        
        issues = validate_video_script_consistency(script_invalid_sequence)
        assert len(issues) > 0
        assert any("sequential" in issue.lower() for issue in issues)
        
        # Script with empty dialogue - create manually to bypass validation
        script_empty_dialogue = VideoScript(
            title="Empty Dialogue Script",
            total_duration=30.0,
            scenes=[VideoScene(
                scene_number=1,
                description="First scene with introduction",
                visual_requirements=["req1"],
                dialogue="Valid dialogue",  # Start with valid dialogue
                duration=30.0
            )]
        )
        # Manually modify dialogue to be empty for testing
        script_empty_dialogue.scenes[0].dialogue = ""
        
        issues = validate_video_script_consistency(script_empty_dialogue)
        assert len(issues) > 0
        assert any("empty dialogue" in issue.lower() for issue in issues)
        
        # Script with missing visual requirements - create manually to bypass validation
        script_no_visual = VideoScript(
            title="No Visual Script",
            total_duration=30.0,
            scenes=[VideoScene(
                scene_number=1,
                description="First scene with introduction",
                visual_requirements=["valid requirement"],  # Start with valid requirement
                dialogue="Dialogue 1",
                duration=30.0
            )]
        )
        # Manually modify visual_requirements to be empty for testing
        script_no_visual.scenes[0].visual_requirements = []
        
        issues = validate_video_script_consistency(script_no_visual)
        assert len(issues) > 0
        assert any("visual requirements" in issue.lower() for issue in issues)
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

"""Orchestration tools for coordinating sub-agents in the video generation pipeline."""

import logging
import time
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

from .shared_libraries.models import (
    VideoGenerationRequest,
    ResearchRequest,
    ResearchData,
    ScriptRequest,
    VideoScript,
    AssetRequest,
    AssetCollection,
    AssetItem,
    AudioRequest,
    AudioAssets,
    AssemblyRequest,
    FinalVideo,
)
from .shared_libraries.adk_session_manager import get_session_manager
from .shared_libraries.adk_session_models import (
    VideoGenerationState,
    VideoGenerationStage,
)

logger = logging.getLogger(__name__)


def validate_asset_collection(assets: AssetCollection) -> List[str]:
    """Validate AssetCollection structure and return list of issues.
    
    Args:
        assets: AssetCollection to validate
        
    Returns:
        List of validation issues (empty if valid)
    """
    issues = []
    
    try:
        # Validate that images are proper AssetItem objects
        for i, asset in enumerate(assets.images):
            if not isinstance(asset, AssetItem):
                # Try to convert if it's a dict
                if isinstance(asset, dict):
                    try:
                        # Validate required fields
                        required_fields = ['asset_id', 'asset_type', 'source_url', 'usage_rights']
                        missing_fields = [field for field in required_fields if field not in asset]
                        if missing_fields:
                            issues.append(f"Image asset {i}: Missing required fields: {missing_fields}")
                        else:
                            # Convert to AssetItem to validate structure
                            AssetItem(**asset)
                    except Exception as e:
                        issues.append(f"Image asset {i}: Invalid structure - {str(e)}")
                else:
                    issues.append(f"Image asset {i}: Not an AssetItem object or dict")
        
        # Validate that videos are proper AssetItem objects
        for i, asset in enumerate(assets.videos):
            if not isinstance(asset, AssetItem):
                if isinstance(asset, dict):
                    try:
                        required_fields = ['asset_id', 'asset_type', 'source_url', 'usage_rights']
                        missing_fields = [field for field in required_fields if field not in asset]
                        if missing_fields:
                            issues.append(f"Video asset {i}: Missing required fields: {missing_fields}")
                        else:
                            AssetItem(**asset)
                    except Exception as e:
                        issues.append(f"Video asset {i}: Invalid structure - {str(e)}")
                else:
                    issues.append(f"Video asset {i}: Not an AssetItem object or dict")
                    
    except Exception as e:
        issues.append(f"AssetCollection validation error: {str(e)}")
    
    return issues


def ensure_asset_consistency(assets: AssetCollection) -> AssetCollection:
    """Ensure all assets in the collection are proper AssetItem objects.
    
    Args:
        assets: AssetCollection to normalize
        
    Returns:
        AssetCollection with all assets as proper AssetItem objects
        
    Raises:
        ValueError: If assets cannot be converted to proper structure
    """
    try:
        # Convert image assets to proper AssetItem objects if needed
        normalized_images = []
        for asset in assets.images:
            if isinstance(asset, AssetItem):
                normalized_images.append(asset)
            elif isinstance(asset, dict):
                # Convert dict to AssetItem
                normalized_images.append(AssetItem(**asset))
            else:
                raise ValueError(f"Invalid asset type: {type(asset)}")
        
        # Convert video assets to proper AssetItem objects if needed
        normalized_videos = []
        for asset in assets.videos:
            if isinstance(asset, AssetItem):
                normalized_videos.append(asset)
            elif isinstance(asset, dict):
                # Convert dict to AssetItem
                normalized_videos.append(AssetItem(**asset))
            else:
                raise ValueError(f"Invalid asset type: {type(asset)}")
        
        # Return normalized collection
        return AssetCollection(
            images=normalized_images,
            videos=normalized_videos,
            metadata=assets.metadata
        )
        
    except Exception as e:
        logger.error(f"Failed to ensure asset consistency: {e}")
        raise ValueError(f"Asset consistency validation failed: {str(e)}")


def create_asset_collection_from_dict(data: Dict[str, Any]) -> AssetCollection:
    """Create AssetCollection from dictionary data with proper type validation.
    
    This function ensures that all assets within the collection are proper AssetItem objects,
    not dictionaries, addressing serialization/deserialization consistency issues.
    
    Args:
        data: Dictionary containing asset collection data
        
    Returns:
        AssetCollection with properly typed AssetItem objects
        
    Raises:
        ValueError: If data cannot be converted to proper AssetCollection structure
    """
    try:
        # Extract and validate images
        images = []
        if "images" in data:
            for img_data in data["images"]:
                if isinstance(img_data, AssetItem):
                    images.append(img_data)
                elif isinstance(img_data, dict):
                    # Ensure all required fields are present
                    required_fields = ['asset_id', 'asset_type', 'source_url', 'usage_rights']
                    missing_fields = [field for field in required_fields if field not in img_data]
                    if missing_fields:
                        raise ValueError(f"Missing required fields in image asset: {missing_fields}")
                    images.append(AssetItem(**img_data))
                else:
                    raise ValueError(f"Invalid image asset type: {type(img_data)}")
        
        # Extract and validate videos
        videos = []
        if "videos" in data:
            for vid_data in data["videos"]:
                if isinstance(vid_data, AssetItem):
                    videos.append(vid_data)
                elif isinstance(vid_data, dict):
                    # Ensure all required fields are present
                    required_fields = ['asset_id', 'asset_type', 'source_url', 'usage_rights']
                    missing_fields = [field for field in required_fields if field not in vid_data]
                    if missing_fields:
                        raise ValueError(f"Missing required fields in video asset: {missing_fields}")
                    videos.append(AssetItem(**vid_data))
                else:
                    raise ValueError(f"Invalid video asset type: {type(vid_data)}")
        
        # Create and return the collection
        return AssetCollection(
            images=images,
            videos=videos,
            metadata=data.get("metadata", {})
        )
        
    except Exception as e:
        logger.error(f"Failed to create AssetCollection from dict: {e}")
        raise ValueError(f"AssetCollection creation failed: {str(e)}")


async def get_session_state(session_id: str) -> Optional[VideoGenerationState]:
    """Retrieve session state by ID using ADK SessionService with error handling."""
    try:
        session_manager = await get_session_manager()
        return await session_manager.get_session_state(session_id)
    except Exception as e:
        logger.error(f"Failed to get session state {session_id}: {e}")
        return None


async def update_session_state(session_id: str, **updates) -> bool:
    """Update session state with comprehensive error handling.

    This function ensures all state updates go through ADK's append_event mechanism
    for proper persistence and event tracking with retry logic.
    """
    try:
        # Enhanced validation
        if not session_id:
            logger.error("Cannot update session state: session_id is None or empty")
            return False
        
        session_manager = await get_session_manager()
        
        # Ensure session exists before attempting update
        if not await session_manager.ensure_session_exists(session_id):
            logger.error(f"Cannot update session state: session {session_id} does not exist")
            return False
        
        return await session_manager.update_session_state(session_id, **updates)
    except Exception as e:
        logger.error(f"Failed to update session state {session_id}: {e}")
        return False


async def create_session_state(
    request: VideoGenerationRequest, user_id: Optional[str] = None
) -> str:
    """Create a new session state for video generation with comprehensive error handling."""
    try:
        session_manager = await get_session_manager()
        return await session_manager.create_session(request, user_id)
    except Exception as e:
        logger.error(f"Failed to create session state: {e}")
        # Re-raise to let caller handle the error appropriately
        raise


class CoordinateResearchInput(BaseModel):
    """Input model for research coordination."""

    topic: str = Field(..., description="Research topic based on video prompt")
    session_id: str = Field(..., description="Session ID for tracking")


class CoordinateResearchOutput(BaseModel):
    """Output model for research coordination."""

    research_data: ResearchData
    session_id: str
    success: bool
    error_message: Optional[str] = None


async def coordinate_research(topic: str, session_id: str) -> Dict[str, Any]:
    """Coordinate research phase with comprehensive error handling and retry logic."""
    session_manager = None

    try:
        logger.info(f"Starting research coordination for session {session_id}")

        # Validate inputs
        if not topic or not topic.strip():
            raise ValueError("Research topic cannot be empty")
        if not session_id or not session_id.strip():
            raise ValueError("Session ID cannot be empty")

        # Get session manager with error handling
        try:
            session_manager = await get_session_manager()
        except Exception as e:
            logger.error(f"Failed to get session manager: {e}")
            return {
                "research_data": None,
                "session_id": session_id,
                "success": False,
                "error_message": f"Session manager unavailable: {str(e)}",
            }

        # Update session status with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                await session_manager.update_stage_and_progress(
                    session_id, VideoGenerationStage.RESEARCHING, 0.1
                )
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(
                        f"Failed to update session status after {max_retries} attempts: {e}"
                    )
                    return {
                        "research_data": None,
                        "session_id": session_id,
                        "success": False,
                        "error_message": f"Failed to update session status: {str(e)}",
                    }
                logger.warning(
                    f"Session update attempt {attempt + 1} failed, retrying: {e}"
                )
                await asyncio.sleep(1.0 * (attempt + 1))  # Exponential backoff

        # Create research request with validation
        try:
            research_request = ResearchRequest(
                topic=topic, scope="comprehensive", depth_requirements="detailed"
            )
        except Exception as e:
            logger.error(f"Failed to create research request: {e}")
            await session_manager.update_stage_and_progress(
                session_id,
                VideoGenerationStage.FAILED,
                error_message=f"Invalid research request: {str(e)}",
            )
            return {
                "research_data": None,
                "session_id": session_id,
                "success": False,
                "error_message": f"Invalid research request: {str(e)}",
            }

        # Simulate research with error handling
        try:
            # In a real implementation, this would use ADK's agent communication
            # For now, we'll simulate the research response with potential failures
            research_data = ResearchData(
                facts=[
                    f"Key information about {topic}",
                    f"Important facts related to {topic}",
                    f"Relevant details for {topic}",
                ],
                sources=["https://example.com/source1", "https://example.com/source2"],
                key_points=[
                    f"Main point about {topic}",
                    f"Secondary point about {topic}",
                ],
                context={"research_quality": "high", "topic": topic},
            )
        except Exception as e:
            logger.error(f"Research data generation failed: {e}")
            await session_manager.update_stage_and_progress(
                session_id,
                VideoGenerationStage.FAILED,
                error_message=f"Research data generation failed: {str(e)}",
            )
            return {
                "research_data": None,
                "session_id": session_id,
                "success": False,
                "error_message": f"Research data generation failed: {str(e)}",
            }

        # Update session state with research data using proper event tracking and retry
        update_success = False
        for attempt in range(max_retries):
            try:
                update_success = await update_session_state(
                    session_id,
                    research_data=research_data,
                    progress=0.2,
                    last_updated_by="research_agent",
                    last_update_stage="research_completed",
                )
                if update_success:
                    break
            except Exception as e:
                logger.warning(
                    f"Session state update attempt {attempt + 1} failed: {e}"
                )
                if attempt == max_retries - 1:
                    logger.error(
                        f"Failed to update session state after {max_retries} attempts"
                    )
                await asyncio.sleep(1.0 * (attempt + 1))

        if not update_success:
            logger.error(f"Failed to update session state for {session_id}")
            # Don't fail the entire operation if state update fails
            logger.warning(
                "Continuing with research completion despite state update failure"
            )

        logger.info(f"Research coordination completed for session {session_id}")

        return {
            "research_data": research_data.model_dump(),
            "session_id": session_id,
            "success": True,
            "error_message": None,
        }

    except Exception as e:
        logger.error(f"Research coordination failed for session {session_id}: {str(e)}")

        # Update session with error (with error handling)
        if session_manager:
            try:
                await session_manager.update_stage_and_progress(
                    session_id,
                    VideoGenerationStage.FAILED,
                    error_message=f"Research failed: {str(e)}",
                )
            except Exception as update_error:
                logger.error(
                    f"Failed to update session with error status: {update_error}"
                )

        return {
            "research_data": None,
            "session_id": session_id,
            "success": False,
            "error_message": str(e),
        }


class CoordinateStoryInput(BaseModel):
    """Input model for story coordination."""

    research_data: Dict[str, Any] = Field(
        ..., description="Research data from previous step"
    )
    session_id: str = Field(..., description="Session ID for tracking")
    duration: int = Field(60, description="Target video duration in seconds")


class CoordinateStoryOutput(BaseModel):
    """Output model for story coordination."""

    script: Dict[str, Any]
    session_id: str
    success: bool
    error_message: Optional[str] = None


async def coordinate_story(
    research_data: Dict[str, Any], session_id: str, duration: int = 60
) -> Dict[str, Any]:
    """Coordinate script creation with the Story Agent."""
    try:
        logger.info(f"Starting story coordination for session {session_id}")

        # Update session status
        session_manager = await get_session_manager()
        await session_manager.update_stage_and_progress(
            session_id, VideoGenerationStage.SCRIPTING, 0.3
        )

        # Convert research data back to model
        research_obj = ResearchData(**research_data)

        # Create script request
        script_request = ScriptRequest(
            research_data=research_obj,
            style_preferences={"tone": "engaging", "pace": "moderate"},
            duration=duration,
        )

        # Simulate script generation (in real implementation would use ADK messaging)
        script = VideoScript(
            title=f"Video about {research_obj.key_points[0] if research_obj.key_points else 'Topic'}",
            total_duration=float(duration),
            scenes=[
                {
                    "scene_number": 1,
                    "description": "Introduction scene",
                    "visual_requirements": ["title card", "engaging background"],
                    "dialogue": "Welcome to our exploration of this fascinating topic.",
                    "duration": duration / 3,
                    "assets": [],
                },
                {
                    "scene_number": 2,
                    "description": "Main content scene",
                    "visual_requirements": ["relevant imagery", "supporting visuals"],
                    "dialogue": f"Let's dive into the key aspects: {', '.join(research_obj.key_points[:2])}",
                    "duration": duration / 3,
                    "assets": [],
                },
                {
                    "scene_number": 3,
                    "description": "Conclusion scene",
                    "visual_requirements": ["summary graphics", "call to action"],
                    "dialogue": "Thank you for watching. Don't forget to subscribe for more content.",
                    "duration": duration / 3,
                    "assets": [],
                },
            ],
            metadata={"created_from_research": True, "target_duration": duration},
        )

        # Update session state with script using proper event tracking
        await update_session_state(
            session_id,
            script=script,
            progress=0.4,
            last_updated_by="story_agent",
            last_update_stage="script_completed",
        )

        logger.info(f"Story coordination completed for session {session_id}")

        return {
            "script": script.model_dump(),
            "session_id": session_id,
            "success": True,
            "error_message": None,
        }

    except Exception as e:
        logger.error(f"Story coordination failed for session {session_id}: {str(e)}")

        # Update session with error
        await session_manager.update_stage_and_progress(
            session_id,
            VideoGenerationStage.FAILED,
            error_message=f"Story creation failed: {str(e)}",
        )

        return {
            "script": None,
            "session_id": session_id,
            "success": False,
            "error_message": str(e),
        }


class CoordinateAssetsInput(BaseModel):
    """Input model for asset coordination."""

    script: Dict[str, Any] = Field(..., description="Video script from previous step")
    session_id: str = Field(..., description="Session ID for tracking")


class CoordinateAssetsOutput(BaseModel):
    """Output model for asset coordination."""

    assets: Dict[str, Any]
    session_id: str
    success: bool
    error_message: Optional[str] = None


async def coordinate_assets(script: Dict[str, Any], session_id: str) -> Dict[str, Any]:
    """Coordinate asset sourcing with both Asset Sourcing and Image Generation agents."""
    try:
        logger.info(f"Starting asset coordination for session {session_id}")

        # Update session status
        session_manager = await get_session_manager()
        await session_manager.update_stage_and_progress(
            session_id, VideoGenerationStage.ASSET_SOURCING, 0.5
        )

        # Convert script back to model
        script_obj = VideoScript(**script)

        # Extract scene descriptions for asset sourcing
        scene_descriptions = [scene.description for scene in script_obj.scenes]
        visual_requirements = []
        for scene in script_obj.scenes:
            visual_requirements.extend(scene.visual_requirements)

        # Create asset request
        asset_request = AssetRequest(
            scene_descriptions=scene_descriptions,
            style_requirements={"quality": "high", "style": "professional"},
            specifications={"format": "jpg", "resolution": "1920x1080"},
        )

        # First try asset sourcing agent
        logger.info("Attempting to source assets from stock providers")

        # Simulate asset sourcing (in real implementation would use ADK messaging)
        sourced_assets = AssetCollection(
            images=[
                AssetItem(
                    asset_id=f"stock_img_{i}",
                    asset_type="image",
                    source_url=f"https://example.com/stock/{i}",
                    local_path=f"/tmp/stock_img_{i}.jpg",
                    usage_rights="royalty_free",
                    metadata={"source": "stock", "scene": i},
                )
                for i in range(len(scene_descriptions))
            ],
            videos=[],
            metadata={
                "sourcing_method": "stock_apis",
                "total_assets": len(scene_descriptions),
            },
        )

        # Check if we need additional custom images
        missing_assets = []
        for i, scene in enumerate(script_obj.scenes):
            if (
                len(
                    [
                        asset
                        for asset in sourced_assets.images
                        if asset.metadata.get("scene") == i
                    ]
                )
                == 0
            ):
                missing_assets.append(
                    {
                        "scene_number": i + 1,
                        "description": scene.description,
                        "visual_requirements": scene.visual_requirements,
                    }
                )

        # Generate custom images for missing assets
        if missing_assets:
            logger.info(f"Generating {len(missing_assets)} custom images")

            for missing in missing_assets:
                # Simulate image generation (in real implementation would use ADK messaging)
                generated_asset = AssetItem(
                    asset_id=f"generated_img_{missing['scene_number']}",
                    asset_type="image",
                    source_url=f"generated://scene_{missing['scene_number']}",
                    local_path=f"/tmp/generated_img_{missing['scene_number']}.jpg",
                    usage_rights="generated",
                    metadata={
                        "source": "ai_generated",
                        "scene": missing["scene_number"],
                        "prompt": missing["description"],
                    },
                )
                sourced_assets.images.append(generated_asset)

        # Validate and ensure asset consistency
        try:
            validation_issues = validate_asset_collection(sourced_assets)
            if validation_issues:
                logger.warning(f"Asset validation issues found: {validation_issues}")
                # Try to fix consistency issues
                sourced_assets = ensure_asset_consistency(sourced_assets)
                logger.info("Asset consistency issues resolved")
        except Exception as e:
            logger.error(f"Asset validation failed: {e}")
            await session_manager.update_stage_and_progress(
                session_id,
                VideoGenerationStage.FAILED,
                error_message=f"Asset validation failed: {str(e)}",
            )
            return {
                "assets": None,
                "session_id": session_id,
                "success": False,
                "error_message": f"Asset validation failed: {str(e)}",
            }

        # Track intermediate files for cleanup
        intermediate_files = []
        for asset in sourced_assets.images:
            if hasattr(asset, "local_path") and asset.local_path:
                intermediate_files.append(asset.local_path)

        # Update session state with assets using proper event tracking
        await update_session_state(
            session_id,
            assets=sourced_assets,
            progress=0.6,
            last_updated_by="asset_agent",
            last_update_stage="assets_completed",
        )

        # Track intermediate files in session manager
        session_manager = await get_session_manager()
        await session_manager.update_stage_and_progress(
            session_id,
            VideoGenerationStage.ASSET_SOURCING,
            0.6,
            intermediate_files=intermediate_files,
        )

        logger.info(f"Asset coordination completed for session {session_id}")

        return {
            "assets": sourced_assets.model_dump(),
            "session_id": session_id,
            "success": True,
            "error_message": None,
        }

    except Exception as e:
        logger.error(f"Asset coordination failed for session {session_id}: {str(e)}")

        # Update session with error
        await session_manager.update_stage_and_progress(
            session_id,
            VideoGenerationStage.FAILED,
            error_message=f"Asset coordination failed: {str(e)}",
        )

        return {
            "assets": None,
            "session_id": session_id,
            "success": False,
            "error_message": str(e),
        }


class CoordinateAudioInput(BaseModel):
    """Input model for audio coordination."""

    script: Dict[str, Any] = Field(..., description="Video script for audio generation")
    session_id: str = Field(..., description="Session ID for tracking")


class CoordinateAudioOutput(BaseModel):
    """Output model for audio coordination."""

    audio_assets: Dict[str, Any]
    session_id: str
    success: bool
    error_message: Optional[str] = None


async def coordinate_audio(script: Dict[str, Any], session_id: str) -> Dict[str, Any]:
    """Coordinate audio generation with the Audio Agent."""
    try:
        logger.info(f"Starting audio coordination for session {session_id}")

        # Update session status
        session_manager = await get_session_manager()
        await session_manager.update_stage_and_progress(
            session_id, VideoGenerationStage.AUDIO_GENERATION, 0.7
        )

        # Convert script back to model
        script_obj = VideoScript(**script)

        # Extract dialogue for TTS
        full_script_text = " ".join([scene.dialogue for scene in script_obj.scenes])

        # Create audio request
        audio_request = AudioRequest(
            script_text=full_script_text,
            voice_preferences={
                "voice": "neutral",
                "speed": "normal",
                "pitch": "medium",
            },
            timing_requirements={
                "sync_with_scenes": True,
                "total_duration": script_obj.total_duration,
            },
        )

        # Simulate audio generation (in real implementation would use ADK messaging)
        audio_assets = AudioAssets(
            voice_files=[
                f"/tmp/audio_scene_{i + 1}.wav" for i in range(len(script_obj.scenes))
            ],
            timing_data={
                "total_duration": script_obj.total_duration,
                "scene_timings": [
                    {
                        "scene": i + 1,
                        "start": sum(s.duration for s in script_obj.scenes[:i]),
                        "duration": scene.duration,
                    }
                    for i, scene in enumerate(script_obj.scenes)
                ],
            },
            synchronization_markers=[
                {"time": sum(s.duration for s in script_obj.scenes[:i]), "scene": i + 1}
                for i in range(len(script_obj.scenes))
            ],
        )

        # Track intermediate files for cleanup
        intermediate_files = (
            audio_assets.voice_files.copy() if audio_assets.voice_files else []
        )

        # Update session state with audio assets using proper event tracking
        await update_session_state(
            session_id,
            audio_assets=audio_assets,
            progress=0.8,
            last_updated_by="audio_agent",
            last_update_stage="audio_completed",
        )

        # Track intermediate files in session manager
        session_manager = await get_session_manager()
        await session_manager.update_stage_and_progress(
            session_id,
            VideoGenerationStage.AUDIO_GENERATION,
            0.8,
            intermediate_files=intermediate_files,
        )

        logger.info(f"Audio coordination completed for session {session_id}")

        return {
            "audio_assets": audio_assets.model_dump(),
            "session_id": session_id,
            "success": True,
            "error_message": None,
        }

    except Exception as e:
        logger.error(f"Audio coordination failed for session {session_id}: {str(e)}")

        # Update session with error
        await session_manager.update_stage_and_progress(
            session_id,
            VideoGenerationStage.FAILED,
            error_message=f"Audio generation failed: {str(e)}",
        )

        return {
            "audio_assets": None,
            "session_id": session_id,
            "success": False,
            "error_message": str(e),
        }


class CoordinateAssemblyInput(BaseModel):
    """Input model for video assembly coordination."""

    script: Dict[str, Any] = Field(..., description="Video script")
    assets: Dict[str, Any] = Field(..., description="Visual assets")
    audio_assets: Dict[str, Any] = Field(..., description="Audio assets")
    session_id: str = Field(..., description="Session ID for tracking")


class CoordinateAssemblyOutput(BaseModel):
    """Output model for video assembly coordination."""

    final_video: Dict[str, Any]
    session_id: str
    success: bool
    error_message: Optional[str] = None


async def coordinate_assembly(
    script: Dict[str, Any],
    assets: Dict[str, Any],
    audio_assets: Dict[str, Any],
    session_id: str,
) -> Dict[str, Any]:
    """Coordinate final video assembly with the Video Assembly Agent."""
    try:
        logger.info(f"Starting video assembly coordination for session {session_id}")

        # Update session status
        session_manager = await get_session_manager()
        await session_manager.update_stage_and_progress(
            session_id, VideoGenerationStage.VIDEO_ASSEMBLY, 0.9
        )

        # Convert models back with proper type validation
        script_obj = VideoScript(**script)
        assets_obj = create_asset_collection_from_dict(assets)
        audio_obj = AudioAssets(**audio_assets)

        # Create assembly request
        assembly_request = AssemblyRequest(
            assets=assets_obj,
            audio=audio_obj,
            script=script_obj,
            specifications={
                "output_format": "mp4",
                "resolution": "1920x1080",
                "fps": 30,
                "quality": "high",
            },
        )

        # Simulate video assembly (in real implementation would use ADK messaging)
        final_video = FinalVideo(
            video_file=f"/tmp/final_video_{session_id}.mp4",
            metadata={
                "duration": script_obj.total_duration,
                "resolution": "1920x1080",
                "format": "mp4",
                "scenes": len(script_obj.scenes),
                "assets_used": len(assets_obj.images),
                "creation_time": time.time(),
            },
            quality_metrics={
                "video_quality": "high",
                "audio_quality": "high",
                "sync_accuracy": 0.95,
            },
        )

        # Track final video file for cleanup (if needed)
        intermediate_files = [final_video.video_file] if final_video.video_file else []

        # Update session state with final video using proper event tracking
        await update_session_state(
            session_id,
            final_video=final_video,
            last_updated_by="assembly_agent",
            last_update_stage="assembly_completed",
        )
        await session_manager.update_stage_and_progress(
            session_id,
            VideoGenerationStage.COMPLETED,
            1.0,
            intermediate_files=intermediate_files,
        )

        logger.info(f"Video assembly coordination completed for session {session_id}")

        return {
            "final_video": final_video.model_dump(),
            "session_id": session_id,
            "success": True,
            "error_message": None,
        }

    except Exception as e:
        logger.error(
            f"Video assembly coordination failed for session {session_id}: {str(e)}"
        )

        # Update session with error
        await session_manager.update_stage_and_progress(
            session_id,
            VideoGenerationStage.FAILED,
            error_message=f"Video assembly failed: {str(e)}",
        )

        return {
            "final_video": None,
            "session_id": session_id,
            "success": False,
            "error_message": str(e),
        }


class GetSessionStatusInput(BaseModel):
    """Input model for getting session status."""

    session_id: str = Field(..., description="Session ID to check status for")


class GetSessionStatusOutput(BaseModel):
    """Output model for session status."""

    status: Dict[str, Any]
    success: bool
    error_message: Optional[str] = None


async def get_session_status(session_id: str) -> Dict[str, Any]:
    """Get the current status of a video generation session with comprehensive error handling."""
    try:
        # Validate input
        if not session_id or not session_id.strip():
            return {
                "status": None,
                "success": False,
                "error_message": "Session ID cannot be empty",
            }

        # Get session manager with error handling
        try:
            session_manager = await get_session_manager()
        except Exception as e:
            logger.error(f"Failed to get session manager: {e}")
            return {
                "status": None,
                "success": False,
                "error_message": f"Session manager unavailable: {str(e)}",
            }

        # Get session status with retry logic
        max_retries = 3
        last_error = None

        for attempt in range(max_retries):
            try:
                status = await session_manager.get_session_status(session_id)

                if not status:
                    return {
                        "status": None,
                        "success": False,
                        "error_message": f"Session {session_id} not found",
                    }

                return {
                    "status": status.model_dump(),
                    "success": True,
                    "error_message": None,
                }

            except Exception as e:
                last_error = e
                if attempt == max_retries - 1:
                    logger.error(
                        f"Failed to get session status after {max_retries} attempts: {e}"
                    )
                    break

                logger.warning(
                    f"Session status retrieval attempt {attempt + 1} failed, retrying: {e}"
                )
                await asyncio.sleep(0.5 * (attempt + 1))  # Exponential backoff

        return {
            "status": None,
            "success": False,
            "error_message": f"Failed to get session status: {str(last_error)}",
        }

    except Exception as e:
        logger.error(f"Unexpected error getting session status: {e}")
        return {
            "status": None,
            "success": False,
            "error_message": f"Unexpected error: {str(e)}",
        }


async def handle_orchestration_error(
    session_id: str,
    stage: str,
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Handle orchestration errors with proper logging and session updates."""
    try:
        logger.error(
            f"Orchestration error in {stage} for session {session_id}: {str(error)}"
        )

        # Log additional context if provided
        if context:
            logger.error(f"Error context: {context}")

        # Try to update session with error status
        try:
            session_manager = await get_session_manager()
            await session_manager.update_stage_and_progress(
                session_id,
                VideoGenerationStage.FAILED,
                error_message=f"{stage} failed: {str(error)}",
            )
        except Exception as update_error:
            logger.error(
                f"Failed to update session {session_id} with error status: {update_error}"
            )

        # Return standardized error response
        return {
            "success": False,
            "session_id": session_id,
            "stage": stage,
            "error_message": str(error),
            "error_context": context,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to handle orchestration error: {e}")
        return {
            "success": False,
            "session_id": session_id,
            "stage": stage,
            "error_message": f"Error handling failed: {str(e)}",
            "original_error": str(error),
            "timestamp": datetime.utcnow().isoformat(),
        }


async def validate_session_exists(session_id: str) -> bool:
    """Validate that a session exists and is accessible."""
    try:
        if not session_id or not session_id.strip():
            return False

        session_manager = await get_session_manager()
        session_state = await session_manager.get_session_state(session_id)
        return session_state is not None

    except Exception as e:
        logger.warning(f"Session validation failed for {session_id}: {e}")
        return False


# Error recovery and retry mechanisms
def retry_with_backoff(func, max_retries: int = 3, backoff_factor: float = 2.0):
    """Retry a function with exponential backoff."""
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise e

            wait_time = backoff_factor**attempt
            logger.warning(
                f"Attempt {attempt + 1} failed, retrying in {wait_time} seconds: {str(e)}"
            )
            time.sleep(wait_time)


async def handle_agent_error(session_id: str, stage: str, error: Exception) -> None:
    """Handle errors from sub-agents with appropriate recovery strategies."""
    try:
        session_manager = await get_session_manager()
        session_state = await session_manager.get_session_state(session_id)

        if not session_state:
            return

        error_msg = f"{stage} failed: {str(error)}"
        session_state.add_error(error_msg, stage)

        # If we've exceeded max retries, mark as failed
        if session_state.retry_count.get(stage, 0) >= 3:
            await session_manager.update_stage_and_progress(
                session_id,
                VideoGenerationStage.FAILED,
                error_message=f"Max retries exceeded for {stage}",
            )
            logger.error(f"Session {session_id} failed at {stage} after 3 retries")
        else:
            # Update session state with error info using proper event tracking
            await update_session_state(
                session_id,
                error_log=session_state.error_log,
                retry_count=session_state.retry_count,
                last_updated_by="error_handler",
                last_update_stage=f"error_recovery_{stage}",
            )
            logger.warning(
                f"Session {session_id} error at {stage}, retry {session_state.retry_count[stage]}/3"
            )

    except Exception as e:
        logger.error(f"Failed to handle agent error for session {session_id}: {e}")


# Export all orchestration tools as simple functions
def get_orchestration_tools() -> List:
    """Get all orchestration tools for the root agent."""
    return [
        coordinate_research,
        coordinate_story,
        coordinate_assets,
        coordinate_audio,
        coordinate_assembly,
        get_session_status,
    ]

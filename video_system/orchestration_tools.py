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

import json
import logging
import time
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

from .shared_libraries.models import (
    VideoGenerationRequest,
    VideoGenerationStatus,
    ResearchRequest,
    ResearchData,
    ScriptRequest,
    VideoScript,
    AssetRequest,
    AssetCollection,
    AudioRequest,
    AudioAssets,
    AssemblyRequest,
    FinalVideo,
    generate_session_id,
    create_video_status
)

logger = logging.getLogger(__name__)

# Session state management
session_states: Dict[str, Dict[str, Any]] = {}


class SessionState(BaseModel):
    """Model for managing session state throughout the video generation process."""
    session_id: str
    status: VideoGenerationStatus
    request: VideoGenerationRequest
    research_data: Optional[ResearchData] = None
    script: Optional[VideoScript] = None
    assets: Optional[AssetCollection] = None
    audio_assets: Optional[AudioAssets] = None
    final_video: Optional[FinalVideo] = None
    error_log: List[str] = Field(default_factory=list)
    retry_count: Dict[str, int] = Field(default_factory=dict)


def get_session_state(session_id: str) -> Optional[SessionState]:
    """Retrieve session state by ID."""
    return session_states.get(session_id)


def update_session_state(session_id: str, **updates) -> None:
    """Update session state with new data."""
    if session_id in session_states:
        for key, value in updates.items():
            if hasattr(session_states[session_id], key):
                setattr(session_states[session_id], key, value)


def create_session_state(request: VideoGenerationRequest) -> SessionState:
    """Create a new session state for video generation."""
    session_id = generate_session_id()
    status = create_video_status(session_id, "processing")
    
    state = SessionState(
        session_id=session_id,
        status=status,
        request=request
    )
    
    session_states[session_id] = state
    return state


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


def coordinate_research(topic: str, session_id: str) -> Dict[str, Any]:
    """Coordinate research phase with the Research Agent."""
    try:
        logger.info(f"Starting research coordination for session {session_id}")
        
        # Update session status
        session_state = get_session_state(session_id)
        if session_state:
            session_state.status.current_stage = "Research"
            session_state.status.progress = 0.1
        
        # Create research request
        research_request = ResearchRequest(
            topic=topic,
            scope="comprehensive",
            depth_requirements="detailed"
        )
        
        # Call research agent (simulated - in real implementation would use ADK messaging)
        research_prompt = f"""
        Research the following topic for video content creation: {topic}
        
        Please provide:
        1. Key facts and information
        2. Reliable sources
        3. Important points to highlight
        4. Relevant context for video creation
        
        Focus on accurate, engaging information suitable for video content.
        """
        
        # In a real implementation, this would use ADK's agent communication
        # For now, we'll simulate the research response
        research_data = ResearchData(
            facts=[
                f"Key information about {topic}",
                f"Important facts related to {topic}",
                f"Relevant details for {topic}"
            ],
            sources=[
                "https://example.com/source1",
                "https://example.com/source2"
            ],
            key_points=[
                f"Main point about {topic}",
                f"Secondary point about {topic}"
            ],
            context={"research_quality": "high", "topic": topic}
        )
        
        # Update session state
        if session_state:
            session_state.research_data = research_data
            session_state.status.progress = 0.2
        
        logger.info(f"Research coordination completed for session {session_id}")
        
        return {
            "research_data": research_data.model_dump(),
            "session_id": session_id,
            "success": True,
            "error_message": None
        }
        
    except Exception as e:
        logger.error(f"Research coordination failed for session {session_id}: {str(e)}")
        
        # Update session with error
        session_state = get_session_state(session_id)
        if session_state:
            session_state.error_log.append(f"Research failed: {str(e)}")
            session_state.status.status = "failed"
            session_state.status.error_message = str(e)
        
        return {
            "research_data": None,
            "session_id": session_id,
            "success": False,
            "error_message": str(e)
        }


class CoordinateStoryInput(BaseModel):
    """Input model for story coordination."""
    research_data: Dict[str, Any] = Field(..., description="Research data from previous step")
    session_id: str = Field(..., description="Session ID for tracking")
    duration: int = Field(60, description="Target video duration in seconds")


class CoordinateStoryOutput(BaseModel):
    """Output model for story coordination."""
    script: Dict[str, Any]
    session_id: str
    success: bool
    error_message: Optional[str] = None


def coordinate_story(research_data: Dict[str, Any], session_id: str, duration: int = 60) -> Dict[str, Any]:
    """Coordinate script creation with the Story Agent."""
    try:
        logger.info(f"Starting story coordination for session {session_id}")
        
        # Update session status
        session_state = get_session_state(session_id)
        if session_state:
            session_state.status.current_stage = "Script Creation"
            session_state.status.progress = 0.3
        
        # Convert research data back to model
        research_obj = ResearchData(**research_data)
        
        # Create script request
        script_request = ScriptRequest(
            research_data=research_obj,
            style_preferences={"tone": "engaging", "pace": "moderate"},
            duration=duration
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
                    "assets": []
                },
                {
                    "scene_number": 2,
                    "description": "Main content scene",
                    "visual_requirements": ["relevant imagery", "supporting visuals"],
                    "dialogue": f"Let's dive into the key aspects: {', '.join(research_obj.key_points[:2])}",
                    "duration": duration / 3,
                    "assets": []
                },
                {
                    "scene_number": 3,
                    "description": "Conclusion scene",
                    "visual_requirements": ["summary graphics", "call to action"],
                    "dialogue": "Thank you for watching. Don't forget to subscribe for more content.",
                    "duration": duration / 3,
                    "assets": []
                }
            ],
            metadata={"created_from_research": True, "target_duration": duration}
        )
        
        # Update session state
        if session_state:
            session_state.script = script
            session_state.status.progress = 0.4
        
        logger.info(f"Story coordination completed for session {session_id}")
        
        return {
            "script": script.model_dump(),
            "session_id": session_id,
            "success": True,
            "error_message": None
        }
        
    except Exception as e:
        logger.error(f"Story coordination failed for session {session_id}: {str(e)}")
        
        # Update session with error
        session_state = get_session_state(session_id)
        if session_state:
            session_state.error_log.append(f"Story creation failed: {str(e)}")
            session_state.status.status = "failed"
            session_state.status.error_message = str(e)
        
        return {
            "script": None,
            "session_id": session_id,
            "success": False,
            "error_message": str(e)
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


def coordinate_assets(script: Dict[str, Any], session_id: str) -> Dict[str, Any]:
    """Coordinate asset sourcing with both Asset Sourcing and Image Generation agents."""
    try:
        logger.info(f"Starting asset coordination for session {session_id}")
        
        # Update session status
        session_state = get_session_state(session_id)
        if session_state:
            session_state.status.current_stage = "Asset Collection"
            session_state.status.progress = 0.5
        
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
            specifications={"format": "jpg", "resolution": "1920x1080"}
        )
        
        # First try asset sourcing agent
        logger.info("Attempting to source assets from stock providers")
        
        # Simulate asset sourcing (in real implementation would use ADK messaging)
        sourced_assets = AssetCollection(
            images=[
                {
                    "asset_id": f"stock_img_{i}",
                    "asset_type": "image",
                    "source_url": f"https://example.com/stock/{i}",
                    "local_path": f"/tmp/stock_img_{i}.jpg",
                    "usage_rights": "royalty_free",
                    "metadata": {"source": "stock", "scene": i}
                }
                for i in range(len(scene_descriptions))
            ],
            videos=[],
            metadata={"sourcing_method": "stock_apis", "total_assets": len(scene_descriptions)}
        )
        
        # Check if we need additional custom images
        missing_assets = []
        for i, scene in enumerate(script_obj.scenes):
            if len([asset for asset in sourced_assets.images if asset.metadata.get("scene") == i]) == 0:
                missing_assets.append({
                    "scene_number": i + 1,
                    "description": scene.description,
                    "visual_requirements": scene.visual_requirements
                })
        
        # Generate custom images for missing assets
        if missing_assets:
            logger.info(f"Generating {len(missing_assets)} custom images")
            
            for missing in missing_assets:
                # Simulate image generation (in real implementation would use ADK messaging)
                generated_asset = {
                    "asset_id": f"generated_img_{missing['scene_number']}",
                    "asset_type": "image",
                    "source_url": f"generated://scene_{missing['scene_number']}",
                    "local_path": f"/tmp/generated_img_{missing['scene_number']}.jpg",
                    "usage_rights": "generated",
                    "metadata": {
                        "source": "ai_generated",
                        "scene": missing['scene_number'],
                        "prompt": missing['description']
                    }
                }
                sourced_assets.images.append(generated_asset)
        
        # Update session state
        if session_state:
            session_state.assets = sourced_assets
            session_state.status.progress = 0.6
        
        logger.info(f"Asset coordination completed for session {session_id}")
        
        return {
            "assets": sourced_assets.model_dump(),
            "session_id": session_id,
            "success": True,
            "error_message": None
        }
        
    except Exception as e:
        logger.error(f"Asset coordination failed for session {session_id}: {str(e)}")
        
        # Update session with error
        session_state = get_session_state(session_id)
        if session_state:
            session_state.error_log.append(f"Asset coordination failed: {str(e)}")
            session_state.status.status = "failed"
            session_state.status.error_message = str(e)
        
        return {
            "assets": None,
            "session_id": session_id,
            "success": False,
            "error_message": str(e)
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


def coordinate_audio(script: Dict[str, Any], session_id: str) -> Dict[str, Any]:
    """Coordinate audio generation with the Audio Agent."""
    try:
        logger.info(f"Starting audio coordination for session {session_id}")
        
        # Update session status
        session_state = get_session_state(session_id)
        if session_state:
            session_state.status.current_stage = "Audio Generation"
            session_state.status.progress = 0.7
        
        # Convert script back to model
        script_obj = VideoScript(**script)
        
        # Extract dialogue for TTS
        full_script_text = " ".join([scene.dialogue for scene in script_obj.scenes])
        
        # Create audio request
        audio_request = AudioRequest(
            script_text=full_script_text,
            voice_preferences={"voice": "neutral", "speed": "normal", "pitch": "medium"},
            timing_requirements={"sync_with_scenes": True, "total_duration": script_obj.total_duration}
        )
        
        # Simulate audio generation (in real implementation would use ADK messaging)
        audio_assets = AudioAssets(
            voice_files=[f"/tmp/audio_scene_{i+1}.wav" for i in range(len(script_obj.scenes))],
            timing_data={
                "total_duration": script_obj.total_duration,
                "scene_timings": [
                    {"scene": i+1, "start": sum(s.duration for s in script_obj.scenes[:i]), 
                     "duration": scene.duration}
                    for i, scene in enumerate(script_obj.scenes)
                ]
            },
            synchronization_markers=[
                {"time": sum(s.duration for s in script_obj.scenes[:i]), "scene": i+1}
                for i in range(len(script_obj.scenes))
            ]
        )
        
        # Update session state
        if session_state:
            session_state.audio_assets = audio_assets
            session_state.status.progress = 0.8
        
        logger.info(f"Audio coordination completed for session {session_id}")
        
        return {
            "audio_assets": audio_assets.model_dump(),
            "session_id": session_id,
            "success": True,
            "error_message": None
        }
        
    except Exception as e:
        logger.error(f"Audio coordination failed for session {session_id}: {str(e)}")
        
        # Update session with error
        session_state = get_session_state(session_id)
        if session_state:
            session_state.error_log.append(f"Audio generation failed: {str(e)}")
            session_state.status.status = "failed"
            session_state.status.error_message = str(e)
        
        return {
            "audio_assets": None,
            "session_id": session_id,
            "success": False,
            "error_message": str(e)
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


def coordinate_assembly(script: Dict[str, Any], assets: Dict[str, Any], 
                      audio_assets: Dict[str, Any], session_id: str) -> Dict[str, Any]:
    """Coordinate final video assembly with the Video Assembly Agent."""
    try:
        logger.info(f"Starting video assembly coordination for session {session_id}")
        
        # Update session status
        session_state = get_session_state(session_id)
        if session_state:
            session_state.status.current_stage = "Video Assembly"
            session_state.status.progress = 0.9
        
        # Convert models back
        script_obj = VideoScript(**script)
        assets_obj = AssetCollection(**assets)
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
                "quality": "high"
            }
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
                "creation_time": time.time()
            },
            quality_metrics={
                "video_quality": "high",
                "audio_quality": "high",
                "sync_accuracy": 0.95
            }
        )
        
        # Update session state
        if session_state:
            session_state.final_video = final_video
            session_state.status.progress = 1.0
            session_state.status.status = "completed"
            session_state.status.current_stage = "Completed"
        
        logger.info(f"Video assembly coordination completed for session {session_id}")
        
        return {
            "final_video": final_video.model_dump(),
            "session_id": session_id,
            "success": True,
            "error_message": None
        }
        
    except Exception as e:
        logger.error(f"Video assembly coordination failed for session {session_id}: {str(e)}")
        
        # Update session with error
        session_state = get_session_state(session_id)
        if session_state:
            session_state.error_log.append(f"Video assembly failed: {str(e)}")
            session_state.status.status = "failed"
            session_state.status.error_message = str(e)
        
        return {
            "final_video": None,
            "session_id": session_id,
            "success": False,
            "error_message": str(e)
        }


class GetSessionStatusInput(BaseModel):
    """Input model for getting session status."""
    session_id: str = Field(..., description="Session ID to check status for")


class GetSessionStatusOutput(BaseModel):
    """Output model for session status."""
    status: Dict[str, Any]
    success: bool
    error_message: Optional[str] = None


def get_session_status(session_id: str) -> Dict[str, Any]:
    """Get the current status of a video generation session."""
    try:
        session_state = get_session_state(session_id)
        if not session_state:
            return {
                "status": None,
                "success": False,
                "error_message": f"Session {session_id} not found"
            }
        
        return {
            "status": session_state.status.model_dump(),
            "success": True,
            "error_message": None
        }
        
    except Exception as e:
        return {
            "status": None,
            "success": False,
            "error_message": str(e)
        }


# Error recovery and retry mechanisms
def retry_with_backoff(func, max_retries: int = 3, backoff_factor: float = 2.0):
    """Retry a function with exponential backoff."""
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            
            wait_time = backoff_factor ** attempt
            logger.warning(f"Attempt {attempt + 1} failed, retrying in {wait_time} seconds: {str(e)}")
            time.sleep(wait_time)


def handle_agent_error(session_id: str, stage: str, error: Exception) -> None:
    """Handle errors from sub-agents with appropriate recovery strategies."""
    session_state = get_session_state(session_id)
    if not session_state:
        return
    
    error_msg = f"{stage} failed: {str(error)}"
    session_state.error_log.append(error_msg)
    
    # Increment retry count for this stage
    if stage not in session_state.retry_count:
        session_state.retry_count[stage] = 0
    session_state.retry_count[stage] += 1
    
    # If we've exceeded max retries, mark as failed
    if session_state.retry_count[stage] >= 3:
        session_state.status.status = "failed"
        session_state.status.error_message = f"Max retries exceeded for {stage}"
        logger.error(f"Session {session_id} failed at {stage} after 3 retries")
    else:
        logger.warning(f"Session {session_id} error at {stage}, retry {session_state.retry_count[stage]}/3")


# Export all orchestration tools as simple functions
def get_orchestration_tools() -> List:
    """Get all orchestration tools for the root agent."""
    return [
        coordinate_research,
        coordinate_story,
        coordinate_assets,
        coordinate_audio,
        coordinate_assembly,
        get_session_status
    ]
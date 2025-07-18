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

"""Root orchestrator agent for the multi-agent video system."""

import os
import logging
from typing import Dict, Any, Optional
from google.adk.agents import Agent
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from .prompts import return_instructions_root
from .orchestration_tools import (
    get_orchestration_tools,
    create_session_state,
    get_session_state
)
from .shared_libraries.models import (
    VideoGenerationRequest as VideoRequest,
    create_default_video_request
)

load_dotenv()
logger = logging.getLogger(__name__)


class StartVideoGenerationInput(BaseModel):
    """Input model for starting video generation."""
    prompt: str = Field(..., description="Text prompt for video generation", min_length=10, max_length=2000)
    duration_preference: Optional[int] = Field(60, description="Preferred video duration in seconds", ge=10, le=600)
    style: Optional[str] = Field("professional", description="Video style preference")
    voice_preference: Optional[str] = Field("neutral", description="Voice preference for narration")
    quality: Optional[str] = Field("high", description="Video quality setting")


class StartVideoGenerationOutput(BaseModel):
    """Output model for starting video generation."""
    session_id: str
    status: Dict[str, Any]
    success: bool
    error_message: Optional[str] = None


def start_video_generation(
    prompt: str,
    duration_preference: int = 60,
    style: str = "professional",
    voice_preference: str = "neutral",
    quality: str = "high"
) -> Dict[str, Any]:
    """Start the complete video generation workflow."""
    try:
        logger.info(f"Starting video generation for prompt: {prompt[:50]}...")
        
        # Create video generation request
        request = VideoRequest(
            prompt=prompt,
            duration_preference=duration_preference,
            style=style,
            voice_preference=voice_preference,
            quality=quality
        )
        
        # Create session state
        session_state = create_session_state(request)
        session_id = session_state.session_id
        
        logger.info(f"Created session {session_id} for video generation")
        
        return {
            "session_id": session_id,
            "status": session_state.status.model_dump(),
            "success": True,
            "error_message": None
        }
        
    except Exception as e:
        logger.error(f"Failed to start video generation: {str(e)}")
        return {
            "session_id": "",
            "status": {},
            "success": False,
            "error_message": str(e)
        }


class ExecuteWorkflowInput(BaseModel):
    """Input model for executing the complete workflow."""
    session_id: str = Field(..., description="Session ID for the video generation")


class ExecuteWorkflowOutput(BaseModel):
    """Output model for workflow execution."""
    final_video_path: Optional[str]
    session_id: str
    success: bool
    error_message: Optional[str] = None


def execute_complete_workflow(session_id: str) -> Dict[str, Any]:
    """Execute the complete video generation workflow for a session."""
    try:
        logger.info(f"Executing complete workflow for session {session_id}")
        
        session_state = get_session_state(session_id)
        if not session_state:
            return {
                "final_video_path": None,
                "session_id": session_id,
                "success": False,
                "error_message": f"Session {session_id} not found"
            }
        
        # This would typically be handled by the orchestrator calling each tool in sequence
        # For now, we'll return a success message indicating the workflow is ready
        logger.info(f"Workflow ready for session {session_id}. Use individual coordination tools to proceed.")
        
        return {
            "final_video_path": None,
            "session_id": session_id,
            "success": True,
            "error_message": "Workflow initialized. Use coordinate_research, coordinate_story, coordinate_assets, coordinate_audio, and coordinate_assembly tools in sequence."
        }
        
    except Exception as e:
        logger.error(f"Workflow execution failed for session {session_id}: {str(e)}")
        return {
            "final_video_path": None,
            "session_id": session_id,
            "success": False,
            "error_message": str(e)
        }


# Get all tools for the root agent
def get_root_agent_tools():
    """Get all tools for the root orchestrator agent."""
    orchestration_tools = get_orchestration_tools()
    workflow_tools = [
        start_video_generation,
        execute_complete_workflow
    ]
    
    return orchestration_tools + workflow_tools


# Root orchestrator agent with full coordination capabilities
root_agent = Agent(
    model='gemini-2.5-flash',
    name='video_system_orchestrator',
    instruction=return_instructions_root(),
    tools=get_root_agent_tools()
)
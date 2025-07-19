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

"""Root orchestrator agent for the multi-agent video system with comprehensive error handling."""

import os
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
from .shared_libraries import (
    get_health_monitor,
    get_logger,
    ProcessingError,
    ValidationError,
    log_error,
    create_error_response,
    with_resource_check
)

load_dotenv()
logger = get_logger("root_orchestrator")


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


@with_resource_check
def start_video_generation(
    prompt: str,
    duration_preference: int = 60,
    style: str = "professional",
    voice_preference: str = "neutral",
    quality: str = "high"
) -> Dict[str, Any]:
    """Start the complete video generation workflow with comprehensive error handling."""
    try:
        # Input validation
        if not isinstance(prompt, str) or not prompt.strip():
            error = ValidationError("Prompt cannot be empty", field="prompt")
            log_error(logger, error)
            return create_error_response(error)
        
        if not (10 <= duration_preference <= 600):
            error = ValidationError("Duration must be between 10 and 600 seconds", field="duration_preference")
            log_error(logger, error)
            return create_error_response(error)
        
        valid_styles = ["professional", "casual", "educational", "entertainment", "documentary"]
        if style not in valid_styles:
            error = ValidationError(f"Style must be one of: {', '.join(valid_styles)}", field="style")
            log_error(logger, error)
            return create_error_response(error)
        
        valid_qualities = ["low", "medium", "high", "ultra"]
        if quality not in valid_qualities:
            error = ValidationError(f"Quality must be one of: {', '.join(valid_qualities)}", field="quality")
            log_error(logger, error)
            return create_error_response(error)
        
        logger.info(f"Starting video generation for prompt: {prompt[:50]}...")
        
        # Create video generation request
        request = VideoRequest(
            prompt=prompt.strip(),
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
        
    except (ValidationError, ProcessingError) as e:
        log_error(logger, e, {"prompt_length": len(prompt) if prompt else 0})
        return create_error_response(e)
    
    except Exception as e:
        error = ProcessingError(f"Unexpected error starting video generation: {str(e)}", original_exception=e)
        log_error(logger, error, {"prompt_length": len(prompt) if prompt else 0})
        return create_error_response(error)


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


# Initialize health monitoring system
def initialize_video_system():
    """Initialize the video system with health monitoring and logging."""
    from .shared_libraries import (
        initialize_logging,
        log_system_startup,
        get_health_monitor
    )
    
    # Initialize logging
    initialize_logging()
    
    # Log system startup
    log_system_startup()
    
    # Start health monitoring
    health_monitor = get_health_monitor()
    health_monitor.start_monitoring(check_interval=60)  # Check every minute
    
    logger.info("Video system initialized with comprehensive error handling and resilience")


# Health check function for the root orchestrator
def check_orchestrator_health() -> Dict[str, Any]:
    """Perform a health check on the root orchestrator."""
    try:
        # Check if all sub-agents are healthy
        health_monitor = get_health_monitor()
        all_services = health_monitor.service_registry.get_all_service_health()
        
        critical_services = [
            "serper_api", "story_generation", "pexels_api", 
            "gemini_tts", "ffmpeg", "asset_sourcing", 
            "audio_services", "video_assembly"
        ]
        
        unhealthy_critical = [
            name for name, health in all_services.items()
            if name in critical_services and health.status.value != "healthy"
        ]
        
        if not unhealthy_critical:
            return {
                "status": "healthy",
                "details": {"message": "All critical services are operational"}
            }
        elif len(unhealthy_critical) < len(critical_services) / 2:
            return {
                "status": "degraded",
                "details": {"unhealthy_services": unhealthy_critical}
            }
        else:
            return {
                "status": "unhealthy",
                "details": {"unhealthy_services": unhealthy_critical}
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "details": {"error": str(e)}
        }


# Register orchestrator health check
try:
    health_monitor = get_health_monitor()
    health_monitor.service_registry.register_service(
        service_name="root_orchestrator",
        health_check_func=check_orchestrator_health,
        health_check_interval=120,  # Check every 2 minutes
        critical=True
    )
except Exception as e:
    logger.warning(f"Failed to register orchestrator health check: {str(e)}")


# Root orchestrator agent with full coordination capabilities and error handling
root_agent = Agent(
    model='gemini-2.5-flash',
    name='video_system_orchestrator',
    instruction=return_instructions_root(),
    tools=get_root_agent_tools()
)
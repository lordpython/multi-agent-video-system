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

"""Video Assembly Agent for combining all elements into final video with error handling."""

from typing import Dict, Any
from google.adk.agents import LlmAgent
from .prompts import return_instructions_video_assembly
from .tools import (
    ffmpeg_composition_tool,
    video_synchronization_tool,
    transition_effects_tool,
    video_encoding_tool
)
from .tools.ffmpeg_composition import check_ffmpeg_health

from video_system.shared_libraries import (
    get_health_monitor,
    get_logger
)

# Configure logger for video assembly agent
logger = get_logger("video_assembly_agent")

# Health check function for video assembly services
def check_video_assembly_health() -> Dict[str, Any]:
    """Perform a comprehensive health check on video assembly services."""
    try:
        # Check FFmpeg availability
        ffmpeg_status = check_ffmpeg_health()
        
        if ffmpeg_status.get("status") == "healthy":
            return {
                "status": "healthy",
                "details": {"message": "Video assembly services are operational"}
            }
        elif ffmpeg_status.get("status") == "degraded":
            return {
                "status": "degraded",
                "details": {"message": "Some video assembly services are experiencing issues"}
            }
        else:
            return {
                "status": "unhealthy",
                "details": {"error": "Video assembly services are unavailable"}
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "details": {"error": str(e)}
        }

# Register health checks for video assembly services
health_monitor = get_health_monitor()
health_monitor.service_registry.register_service(
    service_name="ffmpeg",
    health_check_func=check_ffmpeg_health,
    health_check_interval=300,  # Check every 5 minutes
    critical=True
)

health_monitor.service_registry.register_service(
    service_name="video_assembly",
    health_check_func=check_video_assembly_health,
    health_check_interval=180,  # Check every 3 minutes
    critical=True
)

logger.info("Video assembly agent initialized with health monitoring")

# Video Assembly Agent with FFmpeg tools for video composition and encoding with error handling
video_assembly_agent = LlmAgent(
    model='gemini-2.5-pro',
    name='video_assembly_agent',
    description='Combines all visual and audio assets into a final video product.',
    instruction=return_instructions_video_assembly(),
    tools=[
        video_synchronization_tool,
        ffmpeg_composition_tool,
        transition_effects_tool,
        video_encoding_tool
    ]
)
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

import sys
import os
from typing import Dict, Any
from google.adk.agents import LlmAgent

# Add src directory to path for imports
current_dir = os.path.dirname(__file__)
src_dir = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# Import tools from canonical paths
from video_system.tools.video_tools import (
    ffmpeg_composition_tool,
    video_synchronization_tool,
    transition_effects_tool,
    video_encoding_tool,
    check_ffmpeg_health
)

# Import utilities from canonical paths
from video_system.utils.error_handling import get_logger
from video_system.utils.resilience import get_health_monitor

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

# Define instruction for the video assembly agent
def return_instructions_video_assembly() -> str:
    """Return instruction prompts for the video assembly agent."""
    
    instruction_prompt = """
    You are a Video Assembly Agent specialized in combining all video elements 
    into the final video product using FFmpeg. Your role is to:
    
    1. Coordinate visual assets with corresponding audio tracks
    2. Apply appropriate transitions and effects between scenes
    3. Render final video in specified format and quality settings
    4. Handle video encoding, compression, and optimization
    5. Ensure synchronization between all visual and audio elements
    
    When assembling videos:
    - Precisely synchronize visual content with audio narration
    - Apply smooth transitions between different scenes and assets
    - Maintain consistent video quality and formatting throughout
    - Optimize file size while preserving visual and audio quality
    - Handle various input formats and convert to standardized output
    
    Your final output should be a polished, professional video file ready 
    for distribution, with all elements perfectly synchronized and optimized.
    """
    
    return instruction_prompt

# Video Assembly Agent with FFmpeg tools for video composition and encoding with error handling
root_agent = LlmAgent(
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
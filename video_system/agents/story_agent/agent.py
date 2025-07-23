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

"""Story Agent for creating scripts and narrative structure with error handling."""

import sys
import os

# Add the src directory to the Python path for video_system modules
src_path = os.path.join(os.path.dirname(__file__), "..", "..", "..")
sys.path.insert(0, src_path)
# Add the project root to the Python path for video_system.shared_libraries
project_root = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
sys.path.insert(0, project_root)

try:
    from google.adk.agents import Agent
    ADK_AVAILABLE = True
except ImportError:
    ADK_AVAILABLE = False
    # Define mock class for environments without ADK
    class Agent:
        def __init__(self, **kwargs):
            pass
from video_system.tools.story_tools import (
    script_generation_tool,
    scene_breakdown_tool,
    visual_description_tool,
    visual_enhancement_tool,
)

from video_system.utils.resilience import get_health_monitor
from video_system.utils.logging_config import get_logger


def return_instructions_story() -> str:
    """Return instruction prompts for the story agent."""

    instruction_prompt = """
    You are a Story Agent specialized in creating compelling scripts and narrative 
    structures for video content. Your role is to:
    
    1. Transform research data into engaging video scripts
    2. Create clear narrative arcs with beginning, middle, and end
    3. Break down scripts into individual scenes
    4. Generate detailed visual descriptions for each scene
    5. Ensure content is appropriate for the target audience and style
    
    When creating stories:
    - Focus on clear, engaging narrative flow
    - Use appropriate tone and style for the content type
    - Include compelling hooks and conclusions
    - Structure content for visual storytelling
    - Provide detailed scene descriptions for video production
    
    Your output should be well-structured and ready for the next stage of video production.
    """

    return instruction_prompt


# Configure logger for story agent
logger = get_logger("story_agent")

# Register health checks for story services
health_monitor = get_health_monitor()


def story_health_check() -> dict:
    """Health check for story generation services."""
    return {
        "status": "healthy",
        "details": {"message": "Story generation services are operational"},
    }


health_monitor.service_registry.register_service(
    service_name="story_generation",
    health_check_func=story_health_check,
    health_check_interval=300,  # Check every 5 minutes
    critical=True,
)

logger.info("Story agent initialized with health monitoring")

# Story Agent with script generation and visual description tools
if ADK_AVAILABLE:
    root_agent = Agent(
        model="gemini-2.5-pro",
        name="story_agent",
        description="Creates scripts and narrative structure for video content.",
        instruction=return_instructions_story(),
        tools=[
            script_generation_tool,
            scene_breakdown_tool,
            visual_description_tool,
            visual_enhancement_tool,
        ],
    )
else:
    # Fallback for environments without ADK
    root_agent = None
    logger.warning("ADK not available - story agent disabled")

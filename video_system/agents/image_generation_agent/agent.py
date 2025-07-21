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

"""Image Generation Agent for creating custom visual assets."""

import sys
import os
# Add the src directory to the Python path for video_system modules
src_path = os.path.join(os.path.dirname(__file__), '..', '..', '..')
sys.path.insert(0, src_path)
# Add the project root to the Python path for video_system.shared_libraries
project_root = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..')
sys.path.insert(0, project_root)

from google.adk.agents import LlmAgent
from video_system.tools.image_tools import (
    imagen_generation_tool,
    stable_diffusion_tool,
    prompt_optimizer_tool,
    style_variations_tool
)

def return_instructions_image_generation() -> str:
    """Return instruction prompts for the image generation agent."""
    
    instruction_prompt = """
    You are an Image Generation Agent specialized in creating custom visual 
    assets for video content using AI image generation models. Your role is to:
    
    1. Generate high-quality images based on scene descriptions
    2. Optimize prompts for different AI image generation models
    3. Create style variations and visual consistency across scenes
    4. Handle fallbacks when primary generation services are unavailable
    5. Ensure generated images meet video production requirements
    
    When generating images:
    - Create visually compelling and relevant images for each scene
    - Maintain consistent style and quality across all generated assets
    - Optimize prompts for the best results from each AI model
    - Provide multiple variations when requested
    - Ensure images are suitable for video production workflows
    
    Your output should provide the Video Assembly agent with custom visual 
    assets that perfectly match the video's narrative and style requirements.
    """
    
    return instruction_prompt

def image_health_check() -> dict:
    """Health check for image generation services."""
    return {
        "status": "healthy",
        "details": {"message": "Image generation services are operational"}
    }

from video_system.utils.resilience import get_health_monitor
from video_system.utils.logging_config import get_logger

# Configure logger for image generation agent
logger = get_logger("image_generation_agent")

# Register health checks for image generation services
health_monitor = get_health_monitor()
health_monitor.service_registry.register_service(
    service_name="image_generation",
    health_check_func=image_health_check,
    health_check_interval=300,  # Check every 5 minutes
    critical=False  # Not critical since we have fallbacks
)

logger.info("Image generation agent initialized with health monitoring")

# Image Generation Agent with AI image generation tools
root_agent = LlmAgent(
    model='gemini-2.5-pro',
    name='image_generation_agent',
    description='Creates custom visual assets for video content using various AI image generation models.',
    instruction=return_instructions_image_generation(),
    tools=[
        imagen_generation_tool,
        stable_diffusion_tool,
        prompt_optimizer_tool,
        style_variations_tool
    ]
)
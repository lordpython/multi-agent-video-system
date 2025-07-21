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
from src.video_system.utils.prompts import return_instructions_image_generation
from src.video_system.tools.image_tools import (
    imagen_generation_tool,
    stable_diffusion_tool,
    prompt_optimizer_tool,
    style_variations_tool,
    image_health_check_tool
)

from video_system.shared_libraries import (
    get_health_monitor,
    get_logger
)

# Configure logger for image generation agent
logger = get_logger("image_generation_agent")

# Register health checks for image generation services
health_monitor = get_health_monitor()
health_monitor.service_registry.register_service(
    service_name="image_generation",
    health_check_func=image_health_check_tool.func,  # Access the underlying function
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
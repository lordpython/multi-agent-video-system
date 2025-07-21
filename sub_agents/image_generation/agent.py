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

from google.adk.agents import Agent
from .prompts import return_instructions_image_generation
from .tools import (
    imagen_generation_tool,
    stable_diffusion_tool,
    prompt_optimizer_tool,
    style_variations_tool
)

# Image Generation Agent with AI image generation tools
image_generation_agent = Agent(
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
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

"""Story Agent for creating scripts and narrative structure."""

from google.adk.agents import Agent
from .prompts import return_instructions_story
from .tools import (
    script_generation_tool,
    scene_breakdown_tool,
    visual_description_tool,
    visual_enhancement_tool
)

# Story Agent with script generation and visual description tools
story_agent = Agent(
    model='gemini-2.5-flash',
    name='story_agent',
    instruction=return_instructions_story(),
    tools=[
        script_generation_tool,
        scene_breakdown_tool,
        visual_description_tool,
        visual_enhancement_tool
    ]
)
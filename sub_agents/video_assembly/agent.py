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

"""Video Assembly Agent for combining all elements into final video."""

from google.adk.agents import Agent
from .prompts import return_instructions_video_assembly
from .tools import (
    ffmpeg_composition_tool,
    video_synchronization_tool,
    transition_effects_tool,
    video_encoding_tool
)

# Video Assembly Agent with FFmpeg tools for video composition and encoding
video_assembly_agent = Agent(
    model='gemini-2.5-flash',
    name='video_assembly_agent',
    instruction=return_instructions_video_assembly(),
    tools=[
        video_synchronization_tool,
        ffmpeg_composition_tool,
        transition_effects_tool,
        video_encoding_tool
    ]
)
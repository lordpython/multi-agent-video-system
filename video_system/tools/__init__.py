# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Tools package for the video system.

This package contains all shared tools organized by functional area.
"""

# Import asset tools
from .asset_tools import (
    pexels_search_tool,
    unsplash_search_tool,
    pixabay_search_tool,
    check_pexels_health
)

# Import audio tools
from .audio_tools import (
    gemini_tts_tool,
    audio_timing_tool,
    audio_format_tool,
    check_gemini_tts_health
)

# Import image tools
from .image_tools import (
    imagen_generation_tool,
    stable_diffusion_tool,
    prompt_optimizer_tool,
    style_variations_tool
)

# Import research tools
from .research_tools import (
    serper_web_search_tool,
)

# Import story tools
from .story_tools import (
    script_generation_tool,
    scene_breakdown_tool,
    visual_description_tool,
    visual_enhancement_tool
)

# Import video tools
from .video_tools import (
    ffmpeg_composition_tool,
    video_synchronization_tool,
    transition_effects_tool,
    video_encoding_tool,
    check_ffmpeg_health
)

__all__ = [
    # Asset tools
    'pexels_search_tool',
    'unsplash_search_tool',
    'pixabay_search_tool',
    'check_pexels_health',
    # Audio tools
    'gemini_tts_tool',
    'audio_timing_tool',
    'audio_format_tool',
    'check_gemini_tts_health',
    # Image tools
    'imagen_generation_tool',
    'stable_diffusion_tool',
    'prompt_optimizer_tool',
    'style_variations_tool',
    # Research tools
    'serper_web_search_tool',
    # Story tools
    'script_generation_tool',
    'scene_breakdown_tool',
    'visual_description_tool',
    'visual_enhancement_tool',
    # Video tools
    'ffmpeg_composition_tool',
    'video_synchronization_tool',
    'transition_effects_tool',
    'video_encoding_tool',
    'check_ffmpeg_health'
]
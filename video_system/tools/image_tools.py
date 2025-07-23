"""Image generation tools module.

This module exposes the image generation tools for the image generation agent
under the canonical import path ``src.video_system.tools.image_tools``.

Currently the actual implementations reside in the legacy package
``sub_agents.image_generation.tools``.  To avoid duplicating large amounts of code
we simply re-export the existing tool callables.  Future refactors can migrate
the implementations here without changing the public interface.
"""

# Re-export FunctionTool objects from legacy implementation
from sub_agents.image_generation.tools import (
    imagen_generation_tool,
    stable_diffusion_tool,
    prompt_optimizer_tool,
    style_variations_tool,
)

__all__ = [
    "imagen_generation_tool",
    "stable_diffusion_tool",
    "prompt_optimizer_tool",
    "style_variations_tool",
]

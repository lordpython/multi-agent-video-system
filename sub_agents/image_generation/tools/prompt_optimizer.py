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

"""Prompt optimization tool for consistent image generation."""

from typing import Dict, Any, List
from pydantic import BaseModel, Field


class PromptOptimizerInput(BaseModel):
    """Input schema for prompt optimization tool."""
    scene_description: str = Field(description="The original scene description")
    video_style: str = Field(default="professional", description="Overall video style (professional, cinematic, documentary, etc.)")
    consistency_elements: List[str] = Field(default=[], description="Elements to maintain consistency across images")
    target_service: str = Field(default="imagen4", description="Target image generation service (imagen4, stable_diffusion)")


def optimize_image_prompt(
    scene_description: str, 
    video_style: str = "professional", 
    consistency_elements: List[str] = None, 
    target_service: str = "imagen4"
) -> Dict[str, Any]:
    """
    Optimize prompts for consistent image generation across different AI services.
    
    Args:
        scene_description: The original scene description
        video_style: Overall video style preference
        consistency_elements: Elements to maintain consistency
        target_service: Target image generation service
        
    Returns:
        Dict containing optimized prompts and generation parameters
    """
    if consistency_elements is None:
        consistency_elements = []
    
    try:
        # Base style mappings for different video styles
        style_mappings = {
            "professional": {
                "quality_terms": ["high quality", "professional", "clean", "polished"],
                "lighting": "soft professional lighting",
                "composition": "well-composed, balanced framing"
            },
            "cinematic": {
                "quality_terms": ["cinematic", "dramatic", "film-like", "high production value"],
                "lighting": "dramatic cinematic lighting",
                "composition": "cinematic composition, rule of thirds"
            },
            "documentary": {
                "quality_terms": ["realistic", "authentic", "natural", "documentary style"],
                "lighting": "natural lighting",
                "composition": "documentary photography style"
            },
            "corporate": {
                "quality_terms": ["corporate", "business", "professional", "clean"],
                "lighting": "bright, even lighting",
                "composition": "corporate photography style"
            },
            "artistic": {
                "quality_terms": ["artistic", "creative", "stylized", "visually striking"],
                "lighting": "artistic lighting",
                "composition": "creative composition"
            }
        }
        
        # Get style configuration
        style_config = style_mappings.get(video_style.lower(), style_mappings["professional"])
        
        # Build optimized prompt components
        prompt_parts = []
        
        # Add the core scene description
        prompt_parts.append(scene_description)
        
        # Add consistency elements
        if consistency_elements:
            consistency_str = ", ".join(consistency_elements)
            prompt_parts.append(f"maintaining visual consistency with: {consistency_str}")
        
        # Add style-specific quality terms
        quality_terms = ", ".join(style_config["quality_terms"])
        prompt_parts.append(quality_terms)
        
        # Add lighting and composition guidance
        prompt_parts.append(style_config["lighting"])
        prompt_parts.append(style_config["composition"])
        
        # Service-specific optimizations
        if target_service.lower() == "imagen4":
            # Imagen 4 specific optimizations
            prompt_parts.append("detailed, sharp focus, high resolution")
            negative_prompt = ""
        elif target_service.lower() == "stable_diffusion":
            # Stable Diffusion specific optimizations
            prompt_parts.append("masterpiece, best quality, ultra detailed, sharp focus")
            negative_prompt = "blurry, low quality, distorted, deformed, ugly, bad anatomy, bad proportions"
        elif target_service.lower() == "dalle":
            # DALL-E specific optimizations (kept for backward compatibility)
            prompt_parts.append("detailed, sharp focus, 8K resolution")
            negative_prompt = ""
        else:
            # Generic optimizations (defaults to Imagen 4 style)
            prompt_parts.append("high quality, detailed")
            negative_prompt = ""
        
        # Combine all parts
        optimized_prompt = ", ".join(prompt_parts)
        
        # Generate recommended parameters based on service
        if target_service.lower() == "imagen4":
            recommended_params = {
                "aspect_ratio": "16:9" if video_style == "cinematic" else "1:1",
                "number_of_images": 1,
                "person_generation": "ALLOW_ADULT",
                "output_mime_type": "image/jpeg"
            }
        elif target_service.lower() == "stable_diffusion":
            recommended_params = {
                "width": 1024,
                "height": 1024,
                "steps": 30,
                "cfg_scale": 7.5,
                "negative_prompt": negative_prompt
            }
        elif target_service.lower() == "dalle":
            recommended_params = {
                "size": "1024x1024",
                "quality": "hd",
                "style": "vivid" if video_style in ["cinematic", "artistic"] else "natural"
            }
        else:
            recommended_params = {}
        
        return {
            "optimized_prompt": optimized_prompt,
            "negative_prompt": negative_prompt,
            "original_description": scene_description,
            "video_style": video_style,
            "consistency_elements": consistency_elements,
            "target_service": target_service,
            "recommended_params": recommended_params,
            "prompt_components": {
                "scene": scene_description,
                "style_terms": quality_terms,
                "lighting": style_config["lighting"],
                "composition": style_config["composition"],
                "consistency": consistency_elements
            },
            "status": "success"
        }
        
    except Exception as e:
        return {
            "optimized_prompt": scene_description,  # Fallback to original
            "negative_prompt": "",
            "original_description": scene_description,
            "video_style": video_style,
            "consistency_elements": consistency_elements or [],
            "target_service": target_service,
            "recommended_params": {},
            "error": f"Failed to optimize prompt: {str(e)}",
            "status": "error"
        }


def generate_style_variations(base_prompt: str, num_variations: int = 3) -> Dict[str, Any]:
    """
    Generate multiple style variations of a base prompt for diverse image options.
    
    Args:
        base_prompt: The base prompt to create variations from
        num_variations: Number of variations to generate
        
    Returns:
        Dict containing multiple prompt variations
    """
    try:
        style_modifiers = [
            "photorealistic, detailed",
            "artistic interpretation, stylized",
            "documentary style, natural",
            "cinematic, dramatic lighting",
            "minimalist, clean composition",
            "vibrant colors, high contrast",
            "soft lighting, warm tones",
            "professional photography style"
        ]
        
        variations = []
        for i in range(min(num_variations, len(style_modifiers))):
            variation = {
                "prompt": f"{base_prompt}, {style_modifiers[i]}",
                "style_modifier": style_modifiers[i],
                "variation_id": i + 1
            }
            variations.append(variation)
        
        return {
            "base_prompt": base_prompt,
            "variations": variations,
            "total_variations": len(variations),
            "status": "success"
        }
        
    except Exception as e:
        return {
            "base_prompt": base_prompt,
            "variations": [{"prompt": base_prompt, "style_modifier": "none", "variation_id": 1}],
            "total_variations": 1,
            "error": f"Failed to generate variations: {str(e)}",
            "status": "error"
        }


# Create the tool functions for ADK
prompt_optimizer_tool = optimize_image_prompt
style_variations_tool = generate_style_variations
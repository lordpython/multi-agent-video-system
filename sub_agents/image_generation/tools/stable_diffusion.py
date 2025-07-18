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

"""Stable Diffusion API integration tool for image generation agent."""

import os
import requests
import base64
import time
from typing import Dict, Any, List
from pydantic import BaseModel, Field


class StableDiffusionInput(BaseModel):
    """Input schema for Stable Diffusion image generation tool."""
    prompt: str = Field(description="The text prompt for image generation")
    negative_prompt: str = Field(default="", description="Negative prompt to avoid certain elements")
    width: int = Field(default=1024, description="Image width in pixels")
    height: int = Field(default=1024, description="Image height in pixels")
    steps: int = Field(default=30, description="Number of inference steps (10-50)")
    cfg_scale: float = Field(default=7.0, description="Classifier-free guidance scale (1.0-20.0)")
    samples: int = Field(default=1, description="Number of images to generate (1-4)")


def generate_stable_diffusion_image(
    prompt: str, 
    negative_prompt: str = "", 
    width: int = 1024, 
    height: int = 1024, 
    steps: int = 30, 
    cfg_scale: float = 7.0, 
    samples: int = 1
) -> Dict[str, Any]:
    """
    Generate images using Stability AI's Stable Diffusion API.
    
    Args:
        prompt: The text prompt for image generation
        negative_prompt: Negative prompt to avoid certain elements
        width: Image width in pixels
        height: Image height in pixels
        steps: Number of inference steps
        cfg_scale: Classifier-free guidance scale
        samples: Number of images to generate
        
    Returns:
        Dict containing generated image data and metadata
    """
    api_key = os.getenv("STABILITY_API_KEY")
    if not api_key:
        return {
            "images": [{
                "base64": "",
                "seed": 0,
                "error": "STABILITY_API_KEY environment variable is not set",
                "source": "stable_diffusion",
                "status": "error"
            }],
            "prompt": prompt,
            "total_images": 0,
            "source": "stable_diffusion"
        }
    
    base_url = "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image"
    
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # Validate and clamp parameters
        width = max(512, min(width, 2048))
        height = max(512, min(height, 2048))
        steps = max(10, min(steps, 50))
        cfg_scale = max(1.0, min(cfg_scale, 20.0))
        samples = max(1, min(samples, 4))
        
        payload = {
            "text_prompts": [
                {
                    "text": prompt,
                    "weight": 1.0
                }
            ],
            "cfg_scale": cfg_scale,
            "height": height,
            "width": width,
            "samples": samples,
            "steps": steps,
            "style_preset": "photographic"  # Good default for video content
        }
        
        # Add negative prompt if provided
        if negative_prompt.strip():
            payload["text_prompts"].append({
                "text": negative_prompt,
                "weight": -1.0
            })
        
        response = requests.post(
            base_url,
            headers=headers,
            json=payload,
            timeout=120  # Stable Diffusion can take time
        )
        response.raise_for_status()
        
        data = response.json()
        
        # Extract and format generated images
        images = []
        for i, artifact in enumerate(data.get("artifacts", [])):
            if artifact.get("finishReason") == "SUCCESS":
                formatted_image = {
                    "base64": artifact.get("base64", ""),
                    "seed": artifact.get("seed", 0),
                    "width": width,
                    "height": height,
                    "steps": steps,
                    "cfg_scale": cfg_scale,
                    "source": "stable_diffusion",
                    "model": "stable-diffusion-xl-1024-v1-0",
                    "status": "success",
                    "usage_rights": "Generated content - check Stability AI usage policies",
                    "media_type": "image",
                    "prompt": prompt,
                    "negative_prompt": negative_prompt
                }
                images.append(formatted_image)
        
        return {
            "images": images,
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "total_images": len(images),
            "source": "stable_diffusion",
            "model": "stable-diffusion-xl-1024-v1-0"
        }
        
    except requests.exceptions.RequestException as e:
        error_image = {
            "base64": "",
            "seed": 0,
            "error": f"Failed to generate image with Stable Diffusion: {str(e)}",
            "source": "stable_diffusion",
            "status": "error"
        }
        
        return {
            "images": [error_image],
            "prompt": prompt,
            "total_images": 0,
            "source": "stable_diffusion"
        }
    
    except Exception as e:
        error_image = {
            "base64": "",
            "seed": 0,
            "error": f"An unexpected error occurred: {str(e)}",
            "source": "stable_diffusion",
            "status": "error"
        }
        
        return {
            "images": [error_image],
            "prompt": prompt,
            "total_images": 0,
            "source": "stable_diffusion"
        }


# Create the tool function for ADK
stable_diffusion_tool = generate_stable_diffusion_image
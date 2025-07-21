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

"""Image generation tools for creating custom visual assets with comprehensive error handling."""

import os
import base64
import requests
import sys
import re
from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from google.adk.tools import FunctionTool

# Add the project root to the Python path to access video_system.shared_libraries
project_root = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..')
sys.path.insert(0, project_root)

from video_system.shared_libraries import (
    APIError,
    NetworkError,
    ValidationError,
    ProcessingError,
    get_logger,
    log_error,
    create_error_response
)

try:
    from google import genai
    from PIL import Image
    from io import BytesIO
    IMAGEN_AVAILABLE = True
except ImportError:
    IMAGEN_AVAILABLE = False

# Configure logger for image tools
logger = get_logger("image.tools")

# Default directory for saving generated images
DEFAULT_IMAGES_DIR = "generated_images"


def extract_keywords_from_prompt(prompt: str, max_keywords: int = 3) -> List[str]:
    """Extract meaningful keywords from a prompt for file naming."""
    # Remove common words and punctuation
    stop_words = {
        'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from', 'has', 'he', 'in', 'is', 'it',
        'its', 'of', 'on', 'that', 'the', 'to', 'was', 'will', 'with', 'high', 'quality', 'detailed',
        'professional', 'photorealistic', 'realistic', 'image', 'picture', 'photo'
    }
    
    # Clean and split the prompt
    cleaned_prompt = re.sub(r'[^\w\s]', ' ', prompt.lower())
    words = [word.strip() for word in cleaned_prompt.split() if word.strip()]
    
    # Filter out stop words and short words
    keywords = [word for word in words if word not in stop_words and len(word) > 2]
    
    # Return first max_keywords
    return keywords[:max_keywords]


def create_keyword_filename(prompt: str, source: str, timestamp: str, index: int = 1) -> str:
    """Create a filename based on keywords extracted from the prompt."""
    keywords = extract_keywords_from_prompt(prompt)
    
    if keywords:
        keyword_part = "_".join(keywords)
    else:
        keyword_part = "generated"
    
    # Sanitize filename
    keyword_part = re.sub(r'[^\w\-_]', '_', keyword_part)
    
    return f"{keyword_part}_{source}_{timestamp}_{index}.jpg"


def save_image_with_metadata(image_data: Dict[str, Any], output_dir: str = None) -> Dict[str, Any]:
    """Save an image with keyword-based filename and metadata."""
    if output_dir is None:
        output_dir = DEFAULT_IMAGES_DIR
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # Generate filename based on keywords
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prompt = image_data.get("prompt", "generated_image")
        source = image_data.get("source", "unknown")
        
        filename = create_keyword_filename(prompt, source, timestamp)
        filepath = os.path.join(output_dir, filename)
        
        # Save the image
        if "base64" in image_data and image_data["base64"]:
            # Decode and save base64 image
            image_bytes = base64.b64decode(image_data["base64"])
            with open(filepath, 'wb') as f:
                f.write(image_bytes)
        elif "image_bytes" in image_data and image_data["image_bytes"]:
            # Save raw image bytes
            with open(filepath, 'wb') as f:
                f.write(image_data["image_bytes"])
        else:
            return {
                "saved": False,
                "error": "No image data found to save"
            }
        
        # Create metadata file
        metadata_file = filepath.replace('.jpg', '_metadata.txt')
        with open(metadata_file, 'w', encoding='utf-8') as f:
            f.write(f"Generated Image Metadata\n")
            f.write(f"========================\n\n")
            f.write(f"Filename: {filename}\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Source: {image_data.get('source', 'unknown')}\n")
            f.write(f"Model: {image_data.get('model', 'unknown')}\n")
            f.write(f"Size: {image_data.get('width', 'unknown')}x{image_data.get('height', 'unknown')}\n")
            f.write(f"Keywords: {', '.join(extract_keywords_from_prompt(prompt))}\n\n")
            f.write(f"Original Prompt:\n{prompt}\n\n")
            
            # Add additional metadata based on source
            if source == "stable_diffusion":
                f.write(f"Negative Prompt: {image_data.get('negative_prompt', 'none')}\n")
                f.write(f"Seed: {image_data.get('seed', 'unknown')}\n")
                f.write(f"Steps: {image_data.get('steps', 'unknown')}\n")
                f.write(f"CFG Scale: {image_data.get('cfg_scale', 'unknown')}\n")
            elif source == "imagen4":
                f.write(f"Aspect Ratio: {image_data.get('aspect_ratio', 'unknown')}\n")
                f.write(f"MIME Type: {image_data.get('mime_type', 'unknown')}\n")
        
        file_size = os.path.getsize(filepath)
        
        logger.info(f"Image saved with keywords: {filename} ({file_size} bytes)")
        
        return {
            "saved": True,
            "filepath": filepath,
            "filename": filename,
            "file_size": file_size,
            "keywords": extract_keywords_from_prompt(prompt),
            "metadata_file": metadata_file
        }
        
    except Exception as e:
        logger.error(f"Failed to save image: {str(e)}")
        return {
            "saved": False,
            "error": str(e)
        }


class ImagenGenerationInput(BaseModel):
    """Input schema for Imagen 4 image generation tool."""
    prompt: str = Field(description="The text prompt for image generation")
    aspect_ratio: str = Field(default="1:1", description="Image aspect ratio: '1:1', '9:16', '16:9', '4:3', '3:4'")
    number_of_images: int = Field(default=1, description="Number of images to generate (1-8)")
    person_generation: str = Field(default="ALLOW_ADULT", description="Person generation policy: 'ALLOW_ADULT', 'BLOCK_SOME'")
    output_mime_type: str = Field(default="image/jpeg", description="Output format: 'image/jpeg' or 'image/png'")


class StableDiffusionInput(BaseModel):
    """Input schema for Stable Diffusion image generation tool."""
    prompt: str = Field(description="The text prompt for image generation")
    negative_prompt: str = Field(default="", description="Negative prompt to avoid certain elements")
    width: int = Field(default=1024, description="Image width in pixels")
    height: int = Field(default=1024, description="Image height in pixels")
    steps: int = Field(default=30, description="Number of inference steps (10-50)")
    cfg_scale: float = Field(default=7.0, description="Classifier-free guidance scale (1.0-20.0)")
    samples: int = Field(default=1, description="Number of images to generate (1-4)")


class PromptOptimizerInput(BaseModel):
    """Input schema for prompt optimization tool."""
    scene_description: str = Field(description="The original scene description")
    video_style: str = Field(default="professional", description="Overall video style (professional, cinematic, documentary, etc.)")
    consistency_elements: List[str] = Field(default=[], description="Elements to maintain consistency across images")
    target_service: str = Field(default="imagen4", description="Target image generation service (imagen4, stable_diffusion)")


def generate_imagen_image(
    prompt: str, 
    aspect_ratio: str = "1:1", 
    number_of_images: int = 1, 
    person_generation: str = "ALLOW_ADULT",
    output_mime_type: str = "image/jpeg"
) -> Dict[str, Any]:
    """
    Generate images using Google's Imagen 4 API.
    
    Args:
        prompt: The text prompt for image generation
        aspect_ratio: Image aspect ratio specification
        number_of_images: Number of images to generate
        person_generation: Person generation policy
        output_mime_type: Output image format
        
    Returns:
        Dict containing generated image data and metadata
    """
    try:
        # Input validation
        if not prompt or not prompt.strip():
            error = ValidationError("Prompt cannot be empty", field="prompt")
            log_error(logger, error)
            return create_error_response(error)
        
        if not IMAGEN_AVAILABLE:
            error = ProcessingError("Imagen dependencies not available. Install google-genai and PIL packages.")
            log_error(logger, error)
            return create_error_response(error)
        
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            error = APIError("GEMINI_API_KEY environment variable is not set", api_name="Imagen")
            log_error(logger, error)
            return create_error_response(error)
        
        # Validate and set parameters
        valid_aspect_ratios = ["1:1", "9:16", "16:9", "4:3", "3:4"]
        if aspect_ratio not in valid_aspect_ratios:
            logger.warning(f"Invalid aspect ratio {aspect_ratio}, defaulting to 1:1")
            aspect_ratio = "1:1"
        
        valid_person_generation = ["ALLOW_ADULT", "BLOCK_SOME"]
        if person_generation not in valid_person_generation:
            logger.warning(f"Invalid person generation policy {person_generation}, defaulting to ALLOW_ADULT")
            person_generation = "ALLOW_ADULT"
        
        valid_mime_types = ["image/jpeg", "image/png"]
        if output_mime_type not in valid_mime_types:
            logger.warning(f"Invalid mime type {output_mime_type}, defaulting to image/jpeg")
            output_mime_type = "image/jpeg"
        
        number_of_images = max(1, min(number_of_images, 8))  # Clamp between 1 and 8
        
        logger.info(f"Generating {number_of_images} images with Imagen 4: {prompt[:50]}...")
        
        # Initialize the Gemini client
        client = genai.Client(api_key=api_key)
        
        # Generate images using Imagen 4
        result = client.models.generate_images(
            model="models/imagen-4.0-generate-preview-06-06",
            prompt=prompt,
            config=dict(
                number_of_images=number_of_images,
                output_mime_type=output_mime_type,
                person_generation=person_generation,
                aspect_ratio=aspect_ratio,
            ),
        )
        
        if not result.generated_images:
            error = ProcessingError("No images generated by Imagen 4")
            log_error(logger, error, {"prompt": prompt})
            return create_error_response(error)
        
        # Extract and format generated images
        images = []
        for i, generated_image in enumerate(result.generated_images):
            try:
                # Convert image bytes to base64 for storage/transmission
                image_bytes = generated_image.image.image_bytes
                base64_image = base64.b64encode(image_bytes).decode('utf-8')
                
                # Get image dimensions using PIL
                image_pil = Image.open(BytesIO(image_bytes))
                width, height = image_pil.size
                
                formatted_image = {
                    "image_bytes": image_bytes,
                    "base64": base64_image,
                    "width": width,
                    "height": height,
                    "aspect_ratio": aspect_ratio,
                    "mime_type": output_mime_type,
                    "source": "imagen4",
                    "model": "imagen-4.0-generate-preview-06-06",
                    "status": "success",
                    "usage_rights": "Generated content - check Google usage policies",
                    "media_type": "image",
                    "prompt": prompt,
                    "image_id": f"imagen4_{i+1}",
                    "size_bytes": len(image_bytes)
                }
                images.append(formatted_image)
                
            except Exception as img_error:
                error_image = {
                    "image_bytes": "",
                    "base64": "",
                    "error": f"Failed to process generated image {i+1}: {str(img_error)}",
                    "source": "imagen4",
                    "status": "error"
                }
                images.append(error_image)
        
        successful_images = [img for img in images if img["status"] == "success"]
        logger.info(f"Successfully generated {len(successful_images)} images with Imagen 4")
        
        return {
            "images": images,
            "prompt": prompt,
            "total_images": len(successful_images),
            "source": "imagen4",
            "model": "imagen-4.0-generate-preview-06-06",
            "success": True
        }
        
    except Exception as e:
        error = APIError(f"Failed to generate image with Imagen 4: {str(e)}", api_name="Imagen")
        log_error(logger, error, {"prompt": prompt})
        return create_error_response(error)


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
    try:
        # Input validation
        if not prompt or not prompt.strip():
            error = ValidationError("Prompt cannot be empty", field="prompt")
            log_error(logger, error)
            return create_error_response(error)
        
        api_key = os.getenv("STABILITY_API_KEY")
        if not api_key:
            error = APIError("STABILITY_API_KEY environment variable is not set", api_name="StabilityAI")
            log_error(logger, error)
            return create_error_response(error)
        
        # Validate and clamp parameters
        width = max(512, min(width, 2048))
        height = max(512, min(height, 2048))
        steps = max(10, min(steps, 50))
        cfg_scale = max(1.0, min(cfg_scale, 20.0))
        samples = max(1, min(samples, 4))
        
        logger.info(f"Generating {samples} images with Stable Diffusion: {prompt[:50]}...")
        
        base_url = "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
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
        
        try:
            response = requests.post(
                base_url,
                headers=headers,
                json=payload,
                timeout=120  # Stable Diffusion can take time
            )
            response.raise_for_status()
            
        except requests.exceptions.Timeout as e:
            error = NetworkError(f"Stable Diffusion API request timed out: {str(e)}")
            log_error(logger, error, {"prompt": prompt})
            return create_error_response(error)
            
        except requests.exceptions.RequestException as e:
            error = APIError(f"Failed to generate image with Stable Diffusion: {str(e)}", api_name="StabilityAI")
            log_error(logger, error, {"prompt": prompt})
            return create_error_response(error)
        
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
        
        if not images:
            error = ProcessingError("No successful images generated by Stable Diffusion")
            log_error(logger, error, {"prompt": prompt})
            return create_error_response(error)
        
        logger.info(f"Successfully generated {len(images)} images with Stable Diffusion")
        
        return {
            "images": images,
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "total_images": len(images),
            "source": "stable_diffusion",
            "model": "stable-diffusion-xl-1024-v1-0",
            "success": True
        }
        
    except Exception as e:
        error = APIError(f"Unexpected error during Stable Diffusion generation: {str(e)}", api_name="StabilityAI")
        log_error(logger, error, {"prompt": prompt})
        return create_error_response(error)


def optimize_image_prompt(
    scene_description: str, 
    video_style: str = "professional", 
    consistency_elements: Optional[List[str]] = None, 
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
    try:
        # Input validation
        if not scene_description or not scene_description.strip():
            error = ValidationError("Scene description cannot be empty", field="scene_description")
            log_error(logger, error)
            return create_error_response(error)
        
        if consistency_elements is None:
            consistency_elements = []
        
        logger.info(f"Optimizing prompt for {target_service}: {scene_description[:50]}...")
        
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
        
        logger.info(f"Successfully optimized prompt for {target_service}")
        
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
            "success": True
        }
        
    except (ValidationError, ProcessingError) as e:
        log_error(logger, e, {"scene_description": scene_description})
        return create_error_response(e)
    
    except Exception as e:
        error = ProcessingError(f"Failed to optimize prompt: {str(e)}")
        log_error(logger, error, {"scene_description": scene_description})
        return create_error_response(error)


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
        # Input validation
        if not base_prompt or not base_prompt.strip():
            error = ValidationError("Base prompt cannot be empty", field="base_prompt")
            log_error(logger, error)
            return create_error_response(error)
        
        if num_variations < 1 or num_variations > 10:
            error = ValidationError("Number of variations must be between 1 and 10", field="num_variations")
            log_error(logger, error)
            return create_error_response(error)
        
        logger.info(f"Generating {num_variations} style variations for: {base_prompt[:50]}...")
        
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
        
        logger.info(f"Successfully generated {len(variations)} style variations")
        
        return {
            "base_prompt": base_prompt,
            "variations": variations,
            "total_variations": len(variations),
            "success": True
        }
        
    except (ValidationError, ProcessingError) as e:
        log_error(logger, e, {"base_prompt": base_prompt})
        return create_error_response(e)
    
    except Exception as e:
        error = ProcessingError(f"Failed to generate variations: {str(e)}")
        log_error(logger, error, {"base_prompt": base_prompt})
        return create_error_response(error)


# Health check function for image generation services
def check_image_generation_health() -> Dict[str, Any]:
    """Perform a health check on image generation capabilities."""
    try:
        # Check if API keys are configured
        imagen_key = os.getenv("GEMINI_API_KEY")
        stability_key = os.getenv("STABILITY_API_KEY")
        
        services_status = []
        
        # Check Imagen availability
        if imagen_key and IMAGEN_AVAILABLE:
            services_status.append({"service": "imagen4", "status": "configured"})
        else:
            services_status.append({"service": "imagen4", "status": "not_configured"})
        
        # Check Stability AI availability
        if stability_key:
            services_status.append({"service": "stable_diffusion", "status": "configured"})
        else:
            services_status.append({"service": "stable_diffusion", "status": "not_configured"})
        
        # Determine overall health
        configured_services = [s for s in services_status if s["status"] == "configured"]
        
        if configured_services:
            return {
                "status": "healthy",
                "details": {
                    "message": f"{len(configured_services)} image generation services available",
                    "services": services_status
                }
            }
        else:
            return {
                "status": "degraded",
                "details": {
                    "message": "No image generation services configured",
                    "services": services_status
                }
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "details": {"error": str(e)}
        }


# Create the ADK tool instances
imagen_generation_tool = FunctionTool(generate_imagen_image)
stable_diffusion_tool = FunctionTool(generate_stable_diffusion_image)
prompt_optimizer_tool = FunctionTool(optimize_image_prompt)
style_variations_tool = FunctionTool(generate_style_variations)
image_health_check_tool = FunctionTool(check_image_generation_health)
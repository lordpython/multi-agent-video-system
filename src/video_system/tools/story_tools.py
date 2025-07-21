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

"""Story tools for script generation and visual description with comprehensive error handling."""

import re
import sys
import os
from typing import Dict, Any, List
from pydantic import BaseModel, Field
from google.adk.tools import FunctionTool

# Add the project root to the Python path to access video_system.shared_libraries
project_root = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..')
sys.path.insert(0, project_root)

from video_system.shared_libraries import (
    ValidationError,
    ProcessingError,
    get_logger,
    log_error,
    create_error_response,
    with_resource_check
)

# Configure logger for story tools
logger = get_logger("story.tools")


class ScriptGenerationInput(BaseModel):
    """Input schema for script generation tool."""
    research_data: Dict[str, Any] = Field(description="Research data containing facts, sources, and key points")
    target_duration: int = Field(default=60, description="Target video duration in seconds")
    style: str = Field(default="professional", description="Video style preference")
    tone: str = Field(default="informative", description="Narrative tone")


class SceneBreakdownInput(BaseModel):
    """Input schema for scene breakdown tool."""
    script_content: str = Field(description="Raw script content to break down into scenes")
    target_duration: int = Field(default=60, description="Target total duration in seconds")
    scene_count: int = Field(default=5, description="Desired number of scenes")


class VisualDescriptionInput(BaseModel):
    """Input schema for visual description tool."""
    scene_content: str = Field(description="Content of the scene to generate visuals for")
    style: str = Field(default="professional", description="Visual style preference")
    duration: float = Field(description="Scene duration in seconds")


class VisualEnhancementInput(BaseModel):
    """Input schema for visual enhancement tool."""
    existing_requirements: List[str] = Field(description="Existing visual requirements to enhance")
    scene_context: str = Field(description="Context of the scene")
    target_audience: str = Field(default="general", description="Target audience")


@with_resource_check
def generate_video_script(
    research_data: Dict[str, Any],
    target_duration: int = 60,
    style: str = "professional",
    tone: str = "informative"
) -> Dict[str, Any]:
    """
    Generate a complete video script based on research data with comprehensive error handling.
    
    Args:
        research_data: Dictionary containing research facts, sources, and key points
        target_duration: Target video duration in seconds
        style: Video style preference (professional, casual, educational, etc.)
        tone: Narrative tone (informative, engaging, dramatic, etc.)
        
    Returns:
        Dict containing the generated video script with scenes and metadata
    """
    try:
        # Input validation
        if not isinstance(research_data, dict):
            error = ValidationError("Research data must be a dictionary", field="research_data")
            log_error(logger, error)
            return create_error_response(error)
        
        if not (10 <= target_duration <= 600):
            error = ValidationError("Target duration must be between 10 and 600 seconds", field="target_duration")
            log_error(logger, error)
            return create_error_response(error)
        
        valid_styles = ["professional", "casual", "educational", "entertainment", "documentary"]
        if style not in valid_styles:
            error = ValidationError(f"Style must be one of: {', '.join(valid_styles)}", field="style")
            log_error(logger, error)
            return create_error_response(error)
        
        logger.info(f"Generating video script with duration: {target_duration}s, style: {style}, tone: {tone}")
        
        # Extract research information
        facts = research_data.get("facts", [])
        key_points = research_data.get("key_points", [])
        sources = research_data.get("sources", [])
        context = research_data.get("context", {})
        
        if not facts and not key_points:
            error = ProcessingError("Insufficient research data to generate script - no facts or key points provided")
            log_error(logger, error, {"research_data_keys": list(research_data.keys())})
            return create_error_response(error)
        
        # Validate content quality
        total_content_length = sum(len(str(item)) for item in facts + key_points)
        if total_content_length < 50:
            error = ProcessingError("Research content is too brief to generate a meaningful script")
            log_error(logger, error, {"content_length": total_content_length})
            return create_error_response(error)
        
        # Determine optimal scene count based on duration
        scene_count = max(3, min(8, target_duration // 10))
        scene_duration = target_duration / scene_count
        
        logger.info(f"Planning {scene_count} scenes with {scene_duration:.1f}s each")
        
        # Generate title from key points or facts
        title = _generate_title(key_points, facts, context)
        
        # Create scenes based on research data
        scenes = _create_scenes_from_research(
            facts, key_points, scene_count, scene_duration, style, tone
        )
        
        if not scenes:
            error = ProcessingError("Failed to generate any scenes from research data")
            log_error(logger, error)
            return create_error_response(error)
        
        # Validate generated scenes
        validation_errors = _validate_generated_scenes(scenes, target_duration)
        if validation_errors:
            error = ProcessingError(f"Scene validation failed: {'; '.join(validation_errors)}")
            log_error(logger, error, {"validation_errors": validation_errors})
            return create_error_response(error)
        
        # Create the video script
        script_data = {
            "title": title,
            "total_duration": float(target_duration),
            "scenes": scenes,
            "metadata": {
                "style": style,
                "tone": tone,
                "source_count": len(sources),
                "fact_count": len(facts),
                "generated_scenes": len(scenes),
                "generation_timestamp": logger.handlers[0].formatter.formatTime(logger.makeRecord("", 0, "", 0, "", (), None)) if logger.handlers else "unknown"
            }
        }
        
        logger.info(f"Successfully generated script with {len(scenes)} scenes for {target_duration}s video")
        
        return {
            "script": script_data,
            "success": True,
            "message": f"Generated {len(scenes)} scenes for {target_duration}s video"
        }
        
    except (ValidationError, ProcessingError) as e:
        # These are already properly formatted VideoSystemError instances
        log_error(logger, e, {"target_duration": target_duration, "style": style})
        return create_error_response(e)
    
    except Exception as e:
        # Handle unexpected errors
        error = ProcessingError(f"Unexpected error during script generation: {str(e)}", original_exception=e)
        log_error(logger, error, {"target_duration": target_duration, "style": style})
        return create_error_response(error)


@with_resource_check
def create_scene_breakdown(
    script_content: str,
    target_duration: int = 60,
    scene_count: int = 5
) -> Dict[str, Any]:
    """
    Break down script content into individual scenes with timing and visual requirements.
    
    Args:
        script_content: Raw script content to break down
        target_duration: Target total duration in seconds
        scene_count: Desired number of scenes
        
    Returns:
        Dict containing scene breakdown with visual requirements and timing
    """
    try:
        # Input validation
        if not isinstance(script_content, str):
            error = ValidationError("Script content must be a string", field="script_content")
            log_error(logger, error)
            return create_error_response(error)
        
        if not script_content.strip():
            error = ValidationError("Script content cannot be empty", field="script_content")
            log_error(logger, error)
            return create_error_response(error)
        
        if not (10 <= target_duration <= 600):
            error = ValidationError("Target duration must be between 10 and 600 seconds", field="target_duration")
            log_error(logger, error)
            return create_error_response(error)
        
        if not (2 <= scene_count <= 10):
            error = ValidationError("Scene count must be between 2 and 10", field="scene_count")
            log_error(logger, error)
            return create_error_response(error)
        
        logger.info(f"Creating scene breakdown: {scene_count} scenes, {target_duration}s total")
        
        # Validate content length
        if len(script_content.strip()) < 100:
            error = ProcessingError("Script content is too short to create meaningful scenes")
            log_error(logger, error, {"content_length": len(script_content)})
            return create_error_response(error)
        
        # Calculate scene duration
        scene_duration = target_duration / scene_count
        
        # Split content into logical segments
        segments = _split_content_into_segments(script_content, scene_count)
        
        if not segments or len(segments) < scene_count:
            error = ProcessingError("Failed to split content into required number of segments")
            log_error(logger, error, {"segments_created": len(segments), "required": scene_count})
            return create_error_response(error)
        
        # Create scenes with visual requirements
        scenes = []
        for i, segment in enumerate(segments, 1):
            if not segment.strip():
                logger.warning(f"Empty segment found at position {i}")
                continue
                
            scene = _create_scene_from_segment(segment, i, scene_duration)
            scenes.append(scene)
        
        if not scenes:
            error = ProcessingError("No valid scenes could be created from the script content")
            log_error(logger, error)
            return create_error_response(error)
        
        # Validate scene breakdown
        validation_errors = _validate_scene_breakdown(scenes, target_duration)
        if validation_errors:
            error = ProcessingError(f"Scene breakdown validation failed: {'; '.join(validation_errors)}")
            log_error(logger, error, {"validation_errors": validation_errors})
            return create_error_response(error)
        
        logger.info(f"Successfully created {len(scenes)} scenes from script content")
        
        return {
            "scenes": scenes,
            "total_scenes": len(scenes),
            "total_duration": sum(scene["duration"] for scene in scenes),
            "success": True
        }
        
    except (ValidationError, ProcessingError) as e:
        log_error(logger, e, {"target_duration": target_duration, "scene_count": scene_count})
        return create_error_response(e)
    
    except Exception as e:
        error = ProcessingError(f"Unexpected error during scene breakdown: {str(e)}", original_exception=e)
        log_error(logger, error, {"target_duration": target_duration, "scene_count": scene_count})
        return create_error_response(error)


def generate_visual_descriptions(
    scene_content: str,
    style: str = "professional",
    duration: float = 10.0
) -> Dict[str, Any]:
    """
    Generate detailed visual descriptions and requirements for a scene.
    
    Args:
        scene_content: The textual content of the scene
        style: Visual style preference (professional, casual, educational, etc.)
        duration: Scene duration in seconds
        
    Returns:
        Dict containing visual requirements, shot suggestions, and timing
    """
    try:
        if not scene_content.strip():
            return {
                "error": "Scene content cannot be empty",
                "visual_requirements": []
            }
        
        # Analyze content for visual cues
        visual_elements = _extract_visual_elements(scene_content)
        
        # Generate style-specific requirements
        style_requirements = _get_style_requirements(style)
        
        # Create shot suggestions based on duration
        shot_suggestions = _generate_shot_suggestions(scene_content, duration)
        
        # Generate specific visual requirements
        visual_requirements = _create_visual_requirements(
            visual_elements, style_requirements, scene_content
        )
        
        # Create timing suggestions
        timing_suggestions = _create_timing_suggestions(visual_requirements, duration)
        
        return {
            "visual_requirements": visual_requirements,
            "shot_suggestions": shot_suggestions,
            "timing_suggestions": timing_suggestions,
            "style_elements": style_requirements,
            "detected_themes": visual_elements,
            "success": True
        }
        
    except Exception as e:
        return {
            "error": f"Failed to generate visual descriptions: {str(e)}",
            "visual_requirements": []
        }


def enhance_visual_requirements(
    existing_requirements: List[str],
    scene_context: str,
    target_audience: str = "general"
) -> Dict[str, Any]:
    """
    Enhance existing visual requirements with more specific details.
    
    Args:
        existing_requirements: List of existing visual requirements
        scene_context: Context of the scene for enhancement
        target_audience: Target audience for the content
        
    Returns:
        Dict containing enhanced visual requirements and suggestions
    """
    try:
        if not existing_requirements:
            return {
                "error": "No existing requirements to enhance",
                "enhanced_requirements": []
            }
        
        # Enhance each requirement
        enhanced_requirements = []
        for req in existing_requirements:
            enhanced = _enhance_single_requirement(req, scene_context, target_audience)
            enhanced_requirements.extend(enhanced)
        
        # Add audience-specific enhancements
        audience_enhancements = _get_audience_specific_requirements(target_audience)
        
        # Remove duplicates and organize
        all_requirements = list(set(enhanced_requirements + audience_enhancements))
        
        return {
            "enhanced_requirements": all_requirements,
            "original_count": len(existing_requirements),
            "enhanced_count": len(all_requirements),
            "audience_specific": audience_enhancements,
            "success": True
        }
        
    except Exception as e:
        return {
            "error": f"Failed to enhance visual requirements: {str(e)}",
            "enhanced_requirements": existing_requirements
        }


# Health check function for story generation services
def check_story_generation_health() -> Dict[str, Any]:
    """Perform a health check on story generation capabilities."""
    try:
        # Test script generation with minimal data
        test_data = {
            "facts": ["Test fact for health check"],
            "key_points": ["Test key point for health check"],
            "sources": [],
            "context": {"topic": "health check"}
        }
        
        result = generate_video_script(test_data, target_duration=30, style="professional")
        
        if result.get("success", False):
            return {
                "status": "healthy",
                "details": {"message": "Story generation is working normally"}
            }
        else:
            return {
                "status": "degraded",
                "details": {"error": "Story generation returned error response"}
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "details": {"error": str(e)}
        }


# Helper functions (implementation details)
def _generate_title(key_points: List[str], facts: List[str], context: Dict[str, Any]) -> str:
    """Generate an engaging title from research data."""
    # Try to extract topic from context
    topic = context.get("topic", "")
    if topic:
        return f"Understanding {topic}: Key Insights and Facts"
    
    # Use first key point if available
    if key_points:
        first_point = key_points[0][:50]  # Truncate if too long
        return f"{first_point}..." if len(key_points[0]) > 50 else first_point
    
    # Use first fact as fallback
    if facts:
        first_fact = facts[0][:50]
        return f"{first_fact}..." if len(facts[0]) > 50 else first_fact
    
    return "Educational Video: Key Information and Insights"


def _create_scenes_from_research(
    facts: List[str],
    key_points: List[str],
    scene_count: int,
    scene_duration: float,
    style: str,
    tone: str
) -> List[Dict[str, Any]]:
    """Create scenes based on research data."""
    scenes = []
    
    # Combine and organize content
    all_content = key_points + facts
    if not all_content:
        return scenes
    
    # Distribute content across scenes
    content_per_scene = max(1, len(all_content) // scene_count)
    
    for i in range(scene_count):
        start_idx = i * content_per_scene
        end_idx = start_idx + content_per_scene if i < scene_count - 1 else len(all_content)
        scene_content = all_content[start_idx:end_idx]
        
        if not scene_content:
            continue
        
        # Create scene
        scene = {
            "scene_number": i + 1,
            "description": _create_scene_description(scene_content, i + 1, scene_count),
            "visual_requirements": _generate_visual_requirements(scene_content, style),
            "dialogue": _create_dialogue(scene_content, tone, i + 1, scene_count),
            "duration": scene_duration,
            "assets": []
        }
        
        scenes.append(scene)
    
    return scenes


def _create_scene_description(content: List[str], scene_num: int, total_scenes: int) -> str:
    """Create a description for a scene based on its content."""
    if scene_num == 1:
        return f"Opening scene introducing the main topic: {content[0][:100]}..."
    elif scene_num == total_scenes:
        return f"Concluding scene summarizing key takeaways: {content[0][:100]}..."
    else:
        return f"Scene {scene_num} exploring: {content[0][:100]}..."


def _generate_visual_requirements(content: List[str], style: str) -> List[str]:
    """Generate visual requirements based on content and style."""
    requirements = []
    
    # Base requirements based on style
    if style == "professional":
        requirements.extend([
            "Clean, professional background",
            "High-quality graphics or charts",
            "Consistent color scheme"
        ])
    elif style == "educational":
        requirements.extend([
            "Educational diagrams or infographics",
            "Clear text overlays",
            "Illustrative examples"
        ])
    elif style == "documentary":
        requirements.extend([
            "Real-world footage or images",
            "Documentary-style visuals",
            "Authentic imagery"
        ])
    else:
        requirements.extend([
            "Engaging visuals",
            "Relevant imagery",
            "Clear presentation"
        ])
    
    # Content-specific requirements
    for item in content[:2]:  # Use first 2 content items
        if any(keyword in item.lower() for keyword in ["data", "statistic", "number"]):
            requirements.append("Data visualization or charts")
        elif any(keyword in item.lower() for keyword in ["technology", "tech", "digital"]):
            requirements.append("Technology-related imagery")
        elif any(keyword in item.lower() for keyword in ["people", "human", "social"]):
            requirements.append("People or social interaction visuals")
        else:
            requirements.append("Relevant stock imagery")
    
    return list(set(requirements))  # Remove duplicates


def _create_dialogue(content: List[str], tone: str, scene_num: int, total_scenes: int) -> str:
    """Create dialogue/narration for a scene."""
    if not content:
        return "No content available for this scene."
    
    # Opening scene
    if scene_num == 1:
        intro = "Welcome to today's exploration of an important topic. "
        main_content = " ".join(content[:2])  # Use first 2 items
        return f"{intro}{main_content}"
    
    # Closing scene
    elif scene_num == total_scenes:
        conclusion = "To summarize what we've learned today: "
        main_content = " ".join(content[:2])
        outro = " Thank you for watching, and we hope this information was valuable."
        return f"{conclusion}{main_content}{outro}"
    
    # Middle scenes
    else:
        transition = "Moving on to our next key point: " if scene_num > 1 else ""
        main_content = " ".join(content[:2])
        return f"{transition}{main_content}"


def _split_content_into_segments(content: str, segment_count: int) -> List[str]:
    """Split content into logical segments."""
    # Split by paragraphs first
    paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
    
    if len(paragraphs) >= segment_count:
        # Distribute paragraphs across segments
        segments = []
        paras_per_segment = len(paragraphs) // segment_count
        
        for i in range(segment_count):
            start_idx = i * paras_per_segment
            end_idx = start_idx + paras_per_segment if i < segment_count - 1 else len(paragraphs)
            segment_paras = paragraphs[start_idx:end_idx]
            segments.append('\n\n'.join(segment_paras))
        
        return segments
    else:
        # Split by sentences if not enough paragraphs
        sentences = [s.strip() + '.' for s in content.split('.') if s.strip()]
        sentences_per_segment = max(1, len(sentences) // segment_count)
        
        segments = []
        for i in range(segment_count):
            start_idx = i * sentences_per_segment
            end_idx = start_idx + sentences_per_segment if i < segment_count - 1 else len(sentences)
            segment_sentences = sentences[start_idx:end_idx]
            segments.append(' '.join(segment_sentences))
        
        return segments


def _create_scene_from_segment(segment: str, scene_num: int, duration: float) -> Dict[str, Any]:
    """Create a scene from a content segment."""
    # Extract key concepts for visual requirements
    words = segment.lower().split()
    visual_keywords = []
    
    # Look for visual cues in the content
    tech_keywords = ["technology", "digital", "computer", "software", "data"]
    people_keywords = ["people", "human", "person", "community", "social"]
    business_keywords = ["business", "company", "market", "economy", "financial"]
    
    if any(keyword in words for keyword in tech_keywords):
        visual_keywords.append("Technology and digital imagery")
    if any(keyword in words for keyword in people_keywords):
        visual_keywords.append("People and social interaction visuals")
    if any(keyword in words for keyword in business_keywords):
        visual_keywords.append("Business and professional imagery")
    
    # Default visual requirements
    if not visual_keywords:
        visual_keywords = ["Relevant stock imagery", "Clean professional visuals"]
    
    return {
        "scene_number": scene_num,
        "description": f"Scene {scene_num}: {segment[:100]}...",
        "visual_requirements": visual_keywords,
        "dialogue": segment,
        "duration": duration,
        "assets": []
    }


def _validate_generated_scenes(scenes: List[Dict[str, Any]], target_duration: float) -> List[str]:
    """Validate generated scenes for consistency and quality."""
    errors = []
    
    if not scenes:
        errors.append("No scenes generated")
        return errors
    
    # Check scene numbering
    expected_numbers = list(range(1, len(scenes) + 1))
    actual_numbers = [scene.get("scene_number", 0) for scene in scenes]
    if actual_numbers != expected_numbers:
        errors.append("Scene numbers are not sequential")
    
    # Check total duration
    total_scene_duration = sum(scene.get("duration", 0) for scene in scenes)
    if abs(total_scene_duration - target_duration) > 2.0:  # Allow 2 second tolerance
        errors.append(f"Total scene duration ({total_scene_duration}s) doesn't match target ({target_duration}s)")
    
    # Check individual scenes
    for i, scene in enumerate(scenes, 1):
        if not scene.get("description"):
            errors.append(f"Scene {i} missing description")
        
        if not scene.get("dialogue"):
            errors.append(f"Scene {i} missing dialogue")
        
        if not scene.get("visual_requirements"):
            errors.append(f"Scene {i} missing visual requirements")
        
        duration = scene.get("duration", 0)
        if duration <= 0 or duration > 120:
            errors.append(f"Scene {i} has invalid duration: {duration}s")
    
    return errors


def _validate_scene_breakdown(scenes: List[Dict[str, Any]], target_duration: float) -> List[str]:
    """Validate scene breakdown for consistency and quality."""
    errors = []
    
    if not scenes:
        errors.append("No scenes in breakdown")
        return errors
    
    # Check scene numbering
    for i, scene in enumerate(scenes, 1):
        if scene.get("scene_number") != i:
            errors.append(f"Scene {i} has incorrect scene number: {scene.get('scene_number')}")
    
    # Check total duration
    total_duration = sum(scene.get("duration", 0) for scene in scenes)
    if abs(total_duration - target_duration) > 2.0:  # Allow 2 second tolerance
        errors.append(f"Total duration ({total_duration}s) doesn't match target ({target_duration}s)")
    
    # Check scene content
    for i, scene in enumerate(scenes, 1):
        if not scene.get("dialogue", "").strip():
            errors.append(f"Scene {i} has empty dialogue")
        
        if len(scene.get("dialogue", "")) < 10:
            errors.append(f"Scene {i} dialogue is too short")
        
        if not scene.get("visual_requirements"):
            errors.append(f"Scene {i} missing visual requirements")
    
    return errors


# Visual description helper functions
def _extract_visual_elements(content: str) -> List[str]:
    """Extract visual elements and themes from content."""
    content_lower = content.lower()
    visual_elements = []
    
    # Technology and digital themes
    tech_patterns = [
        r'\b(technology|tech|digital|computer|software|app|internet|online|data|ai|artificial intelligence)\b',
        r'\b(smartphone|laptop|tablet|device|screen|interface)\b'
    ]
    
    # Business and professional themes
    business_patterns = [
        r'\b(business|company|corporate|office|meeting|presentation|professional)\b',
        r'\b(market|economy|financial|investment|revenue|profit|growth)\b'
    ]
    
    # People and social themes
    people_patterns = [
        r'\b(people|person|human|community|social|family|team|group)\b',
        r'\b(communication|interaction|relationship|collaboration)\b'
    ]
    
    # Education and learning themes
    education_patterns = [
        r'\b(education|learning|teaching|school|university|student|knowledge)\b',
        r'\b(research|study|analysis|information|facts|data)\b'
    ]
    
    # Health and wellness themes
    health_patterns = [
        r'\b(health|medical|wellness|fitness|exercise|nutrition|doctor)\b',
        r'\b(hospital|clinic|treatment|therapy|medicine)\b'
    ]
    
    # Nature and environment themes
    nature_patterns = [
        r'\b(nature|environment|green|sustainable|eco|climate|weather)\b',
        r'\b(forest|ocean|mountain|landscape|wildlife|plants)\b'
    ]
    
    # Check for patterns and add corresponding themes
    pattern_themes = [
        (tech_patterns, "technology"),
        (business_patterns, "business"),
        (people_patterns, "people"),
        (education_patterns, "education"),
        (health_patterns, "health"),
        (nature_patterns, "nature")
    ]
    
    for patterns, theme in pattern_themes:
        for pattern in patterns:
            if re.search(pattern, content_lower):
                visual_elements.append(theme)
                break
    
    return list(set(visual_elements))  # Remove duplicates


def _get_style_requirements(style: str) -> List[str]:
    """Get visual requirements based on style preference."""
    style_map = {
        "professional": [
            "Clean, minimalist design",
            "Professional color palette (blues, grays, whites)",
            "High-quality, crisp imagery",
            "Consistent typography and branding",
            "Polished, corporate aesthetic"
        ],
        "casual": [
            "Relaxed, approachable visuals",
            "Warm, friendly color palette",
            "Natural lighting and settings",
            "Informal, conversational tone in visuals",
            "Authentic, candid imagery"
        ],
        "educational": [
            "Clear, informative graphics",
            "Educational diagrams and charts",
            "Step-by-step visual progression",
            "Highlighting and annotation elements",
            "Academic or instructional aesthetic"
        ],
        "entertainment": [
            "Dynamic, engaging visuals",
            "Vibrant, energetic color palette",
            "Creative transitions and effects",
            "Entertainment-focused imagery",
            "Fun, playful visual elements"
        ],
        "documentary": [
            "Authentic, real-world footage",
            "Natural, unposed imagery",
            "Documentary-style cinematography",
            "Factual, evidence-based visuals",
            "Journalistic visual approach"
        ]
    }
    
    return style_map.get(style.lower(), style_map["professional"])


def _generate_shot_suggestions(content: str, duration: float) -> List[Dict[str, Any]]:
    """Generate shot suggestions based on content and duration."""
    shots = []
    
    # Determine number of shots based on duration
    if duration <= 5:
        shot_count = 1
    elif duration <= 15:
        shot_count = 2
    elif duration <= 30:
        shot_count = 3
    else:
        shot_count = min(5, int(duration / 10))
    
    shot_duration = duration / shot_count
    
    # Generate shots
    for i in range(shot_count):
        shot = {
            "shot_number": i + 1,
            "duration": shot_duration,
            "type": _determine_shot_type(content, i, shot_count),
            "description": _create_shot_description(content, i, shot_count)
        }
        shots.append(shot)
    
    return shots


def _determine_shot_type(content: str, shot_index: int, total_shots: int) -> str:
    """Determine the type of shot based on position and content."""
    if shot_index == 0:
        return "establishing_shot"
    elif shot_index == total_shots - 1:
        return "closing_shot"
    else:
        # Analyze content for shot type
        content_lower = content.lower()
        if any(word in content_lower for word in ["data", "chart", "graph", "statistic"]):
            return "detail_shot"
        elif any(word in content_lower for word in ["people", "person", "human"]):
            return "medium_shot"
        else:
            return "wide_shot"


def _create_shot_description(content: str, shot_index: int, total_shots: int) -> str:
    """Create a description for a specific shot."""
    if shot_index == 0:
        return f"Opening shot introducing the scene: {content[:50]}..."
    elif shot_index == total_shots - 1:
        return f"Closing shot concluding the scene: {content[-50:]}"
    else:
        mid_point = len(content) // 2
        return f"Shot {shot_index + 1} focusing on: {content[mid_point:mid_point+50]}..."


def _create_visual_requirements(
    visual_elements: List[str],
    style_requirements: List[str],
    content: str
) -> List[str]:
    """Create comprehensive visual requirements."""
    requirements = []
    
    # Add style requirements
    requirements.extend(style_requirements[:3])  # Top 3 style requirements
    
    # Add theme-specific requirements
    theme_requirements = {
        "technology": [
            "Modern technology imagery",
            "Digital interface elements",
            "Clean, tech-focused visuals"
        ],
        "business": [
            "Professional business imagery",
            "Corporate environment visuals",
            "Business-related graphics"
        ],
        "people": [
            "Human-centered imagery",
            "Social interaction visuals",
            "Diverse representation"
        ],
        "education": [
            "Educational graphics and diagrams",
            "Learning-focused imagery",
            "Instructional visual elements"
        ],
        "health": [
            "Health and wellness imagery",
            "Medical or fitness visuals",
            "Clean, health-focused aesthetics"
        ],
        "nature": [
            "Natural environment imagery",
            "Outdoor and landscape visuals",
            "Environmental themes"
        ]
    }
    
    for element in visual_elements:
        if element in theme_requirements:
            requirements.extend(theme_requirements[element][:2])
    
    # Add content-specific requirements
    if len(content) > 200:
        requirements.append("Multiple visual elements to support extended content")
    
    if any(word in content.lower() for word in ["important", "key", "crucial", "essential"]):
        requirements.append("Emphasis and highlighting elements")
    
    return list(set(requirements))  # Remove duplicates


def _create_timing_suggestions(requirements: List[str], duration: float) -> List[Dict[str, Any]]:
    """Create timing suggestions for visual elements."""
    timing_suggestions = []
    
    # Divide duration into segments
    segment_count = min(len(requirements), int(duration / 3))
    if segment_count == 0:
        segment_count = 1
    
    segment_duration = duration / segment_count
    
    for i, req in enumerate(requirements[:segment_count]):
        timing = {
            "requirement": req,
            "start_time": i * segment_duration,
            "duration": segment_duration,
            "priority": "high" if i < 2 else "medium"
        }
        timing_suggestions.append(timing)
    
    return timing_suggestions


def _enhance_single_requirement(req: str, context: str, audience: str) -> List[str]:
    """Enhance a single visual requirement with more specific details."""
    enhanced = [req]  # Keep original
    
    # Add context-specific enhancements
    if "professional" in req.lower():
        enhanced.append(f"Professional imagery relevant to: {context[:30]}...")
    
    if "imagery" in req.lower():
        enhanced.append(f"High-resolution imagery with {audience} appeal")
    
    if "color" in req.lower():
        enhanced.append("Color scheme optimized for video format")
    
    return enhanced


def _get_audience_specific_requirements(audience: str) -> List[str]:
    """Get visual requirements specific to target audience."""
    audience_map = {
        "general": [
            "Universally appealing visuals",
            "Clear, easy-to-understand imagery"
        ],
        "professional": [
            "Business-appropriate imagery",
            "Corporate-standard visual quality"
        ],
        "educational": [
            "Learning-focused visual elements",
            "Educational clarity and precision"
        ],
        "young_adult": [
            "Modern, trendy visual style",
            "Social media friendly aesthetics"
        ],
        "senior": [
            "Clear, high-contrast visuals",
            "Traditional, respectful imagery"
        ]
    }
    
    return audience_map.get(audience.lower(), audience_map["general"])


# Create the ADK tool instances
script_generation_tool = FunctionTool(generate_video_script)
scene_breakdown_tool = FunctionTool(create_scene_breakdown)
visual_description_tool = FunctionTool(generate_visual_descriptions)
visual_enhancement_tool = FunctionTool(enhance_visual_requirements)
story_health_check_tool = FunctionTool(check_story_generation_health)
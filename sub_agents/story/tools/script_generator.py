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

"""Script generation tools for the Story Agent with comprehensive error handling."""

from typing import Dict, Any, List
from pydantic import BaseModel, Field
from video_system.shared_libraries import (
    ValidationError,
    ProcessingError,
    get_logger,
    log_error,
    create_error_response,
    with_resource_check
)

# Configure logger for script generation
logger = get_logger("story.script_generator")


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


from google.adk.tools import FunctionTool
# Create tool functions for ADK
script_generation_tool = FunctionTool(generate_video_script)
scene_breakdown_tool = FunctionTool(create_scene_breakdown)
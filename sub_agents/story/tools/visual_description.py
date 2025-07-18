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

"""Visual description tools for generating detailed visual requirements for video scenes."""

import re
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


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


# Create tool functions for ADK
def visual_description_tool(scene_content: str, style: str = "professional", duration: float = 10.0) -> Dict[str, Any]:
    """Generate detailed visual descriptions and requirements for a scene."""
    return generate_visual_descriptions(scene_content, style, duration)

def visual_enhancement_tool(existing_requirements: List[str], scene_context: str, target_audience: str = "general") -> Dict[str, Any]:
    """Enhance existing visual requirements with more specific details."""
    return enhance_visual_requirements(existing_requirements, scene_context, target_audience)
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

"""Tests for the Story Agent and its tools."""

from sub_agents.story.tools.script_generator import (
    generate_video_script,
    create_scene_breakdown,
    _generate_title,
    _create_scenes_from_research
)
from sub_agents.story.tools.visual_description import (
    generate_visual_descriptions,
    enhance_visual_requirements,
    _extract_visual_elements as extract_visual_elements_vd,
    _get_style_requirements
)
from sub_agents.story.agent import story_agent


class TestScriptGeneration:
    """Test cases for script generation functionality."""
    
    def test_generate_video_script_success(self):
        """Test successful script generation with valid research data."""
        research_data = {
            "facts": [
                "Artificial Intelligence is transforming industries worldwide",
                "Machine learning algorithms can process vast amounts of data",
                "AI applications include healthcare, finance, and transportation"
            ],
            "key_points": [
                "AI adoption is accelerating across sectors",
                "Data quality is crucial for AI success",
                "Ethical considerations are increasingly important"
            ],
            "sources": ["https://example.com/ai-research"],
            "context": {"topic": "Artificial Intelligence"}
        }
        
        result = generate_video_script(
            research_data=research_data,
            target_duration=60,
            style="professional",
            tone="informative"
        )
        
        assert result["success"] is True
        assert "script" in result
        script_data = result["script"]
        
        # Validate script structure
        assert "title" in script_data
        assert "total_duration" in script_data
        assert "scenes" in script_data
        assert "metadata" in script_data
        
        # Validate scenes
        scenes = script_data["scenes"]
        assert len(scenes) > 0
        assert script_data["total_duration"] == 60.0
        
        # Validate scene structure
        for scene in scenes:
            assert "scene_number" in scene
            assert "description" in scene
            assert "visual_requirements" in scene
            assert "dialogue" in scene
            assert "duration" in scene
            assert "assets" in scene
    
    def test_generate_video_script_empty_research(self):
        """Test script generation with empty research data."""
        research_data = {
            "facts": [],
            "key_points": [],
            "sources": [],
            "context": {}
        }
        
        result = generate_video_script(research_data=research_data)
        
        assert "error" in result
        assert result["script"] is None
    
    def test_generate_video_script_different_durations(self):
        """Test script generation with different target durations."""
        research_data = {
            "facts": ["Test fact 1", "Test fact 2"],
            "key_points": ["Test point 1", "Test point 2"],
            "sources": ["https://example.com"],
            "context": {"topic": "Test Topic"}
        }
        
        # Test short duration
        result_30 = generate_video_script(research_data, target_duration=30)
        assert result_30["success"] is True
        assert result_30["script"]["total_duration"] == 30.0
        
        # Test long duration
        result_120 = generate_video_script(research_data, target_duration=120)
        assert result_120["success"] is True
        assert result_120["script"]["total_duration"] == 120.0
    
    def test_create_scene_breakdown_success(self):
        """Test successful scene breakdown creation."""
        script_content = """
        This is the introduction to our topic. We'll explore the key concepts and ideas.
        
        Moving on to the main discussion, we need to understand the fundamental principles.
        
        Let's examine some specific examples and case studies that illustrate these points.
        
        In conclusion, we've covered the essential aspects of this important subject.
        """
        
        result = create_scene_breakdown(
            script_content=script_content,
            target_duration=60,
            scene_count=4
        )
        
        assert result["success"] is True
        assert "scenes" in result
        assert len(result["scenes"]) == 4
        assert result["total_duration"] == 60.0
        
        # Validate scene structure
        for i, scene in enumerate(result["scenes"], 1):
            assert scene["scene_number"] == i
            assert "description" in scene
            assert "visual_requirements" in scene
            assert "dialogue" in scene
            assert scene["duration"] == 15.0  # 60/4
    
    def test_create_scene_breakdown_empty_content(self):
        """Test scene breakdown with empty content."""
        result = create_scene_breakdown(script_content="")
        
        assert "error" in result
        assert result["scenes"] == []
    
    def test_generate_title_from_context(self):
        """Test title generation from different data sources."""
        # Test with topic in context
        key_points = ["Point 1", "Point 2"]
        facts = ["Fact 1", "Fact 2"]
        context = {"topic": "Machine Learning"}
        
        title = _generate_title(key_points, facts, context)
        assert "Machine Learning" in title
        
        # Test with key points only
        title_kp = _generate_title(key_points, [], {})
        assert "Point 1" in title_kp
        
        # Test with facts only
        title_facts = _generate_title([], facts, {})
        assert "Fact 1" in title_facts
    
    def test_create_scenes_from_research(self):
        """Test scene creation from research data."""
        facts = ["AI is transforming healthcare", "Machine learning improves diagnostics"]
        key_points = ["Healthcare AI adoption is growing", "Patient outcomes are improving"]
        
        scenes = _create_scenes_from_research(
            facts=facts,
            key_points=key_points,
            scene_count=3,
            scene_duration=20.0,
            style="professional",
            tone="informative"
        )
        
        assert len(scenes) == 3
        for scene in scenes:
            assert scene["duration"] == 20.0
            assert len(scene["visual_requirements"]) > 0
            assert len(scene["dialogue"]) > 0


class TestVisualDescription:
    """Test cases for visual description functionality."""
    
    def test_generate_visual_descriptions_success(self):
        """Test successful visual description generation."""
        scene_content = "This scene discusses artificial intelligence and machine learning technologies in healthcare applications."
        
        result = generate_visual_descriptions(
            scene_content=scene_content,
            style="professional",
            duration=15.0
        )
        
        assert result["success"] is True
        assert "visual_requirements" in result
        assert "shot_suggestions" in result
        assert "timing_suggestions" in result
        assert "style_elements" in result
        assert "detected_themes" in result
        
        # Validate visual requirements
        assert len(result["visual_requirements"]) > 0
        
        # Validate shot suggestions
        shots = result["shot_suggestions"]
        assert len(shots) > 0
        for shot in shots:
            assert "shot_number" in shot
            assert "duration" in shot
            assert "type" in shot
            assert "description" in shot
    
    def test_generate_visual_descriptions_empty_content(self):
        """Test visual description generation with empty content."""
        result = generate_visual_descriptions(scene_content="")
        
        assert "error" in result
        assert result["visual_requirements"] == []
    
    def test_enhance_visual_requirements_success(self):
        """Test successful visual requirements enhancement."""
        existing_requirements = [
            "Professional imagery",
            "Technology-focused visuals",
            "Clean color palette"
        ]
        scene_context = "Discussion about artificial intelligence in healthcare"
        
        result = enhance_visual_requirements(
            existing_requirements=existing_requirements,
            scene_context=scene_context,
            target_audience="professional"
        )
        
        assert result["success"] is True
        assert "enhanced_requirements" in result
        assert len(result["enhanced_requirements"]) >= len(existing_requirements)
        assert result["original_count"] == 3
        assert result["enhanced_count"] > 3
    
    def test_enhance_visual_requirements_empty_list(self):
        """Test visual requirements enhancement with empty list."""
        result = enhance_visual_requirements(
            existing_requirements=[],
            scene_context="Test context"
        )
        
        assert "error" in result
        assert result["enhanced_requirements"] == []
    
    def test_extract_visual_elements(self):
        """Test visual element extraction from content."""
        content = "This discusses technology, business applications, and people using artificial intelligence."
        
        elements = extract_visual_elements_vd(content)
        
        assert "technology" in elements
        assert "business" in elements
        assert "people" in elements
    
    def test_get_style_requirements(self):
        """Test style-specific requirements generation."""
        # Test professional style
        prof_reqs = _get_style_requirements("professional")
        assert any("professional" in req.lower() for req in prof_reqs)
        
        # Test educational style
        edu_reqs = _get_style_requirements("educational")
        assert any("educational" in req.lower() for req in edu_reqs)
        
        # Test default fallback
        default_reqs = _get_style_requirements("unknown_style")
        assert len(default_reqs) > 0


class TestStoryAgent:
    """Test cases for the Story Agent integration."""
    
    def test_story_agent_initialization(self):
        """Test that the story agent is properly initialized."""
        assert story_agent.name == "story_agent"
        assert story_agent.model == "gemini-2.5-pro"
        assert len(story_agent.tools) == 4
        
        # Check tool functions
        tool_names = [tool.__name__ for tool in story_agent.tools]
        expected_tools = [
            "script_generation_tool",
            "scene_breakdown_tool",
            "visual_description_tool",
            "visual_enhancement_tool"
        ]
        
        for expected_tool in expected_tools:
            assert expected_tool in tool_names
    
    def test_story_agent_instruction_content(self):
        """Test that the story agent has comprehensive instructions."""
        instruction = story_agent.instruction
        
        # Check for key instruction components
        assert "Story Agent" in instruction
        assert "script" in instruction.lower()
        assert "visual" in instruction.lower()
        assert "scene" in instruction.lower()
        assert "narrative" in instruction.lower()


class TestIntegrationScenarios:
    """Integration test scenarios for the Story Agent."""
    
    def test_complete_script_generation_workflow(self):
        """Test the complete workflow from research data to final script."""
        # Sample research data
        research_data = {
            "facts": [
                "Climate change is affecting global weather patterns",
                "Renewable energy adoption is increasing worldwide",
                "Carbon emissions need to be reduced by 50% by 2030"
            ],
            "key_points": [
                "Urgent action is needed on climate change",
                "Technology solutions are becoming more viable",
                "International cooperation is essential"
            ],
            "sources": ["https://example.com/climate-research"],
            "context": {"topic": "Climate Change Solutions"}
        }
        
        # Step 1: Generate script
        script_result = generate_video_script(
            research_data=research_data,
            target_duration=90,
            style="documentary",
            tone="urgent"
        )
        
        assert script_result["success"] is True
        script_data = script_result["script"]
        
        # Step 2: Enhance visual requirements for each scene
        enhanced_scenes = []
        for scene in script_data["scenes"]:
            visual_result = generate_visual_descriptions(
                scene_content=scene["dialogue"],
                style="documentary",
                duration=scene["duration"]
            )
            
            if visual_result["success"]:
                # Enhance the visual requirements
                enhanced_result = enhance_visual_requirements(
                    existing_requirements=visual_result["visual_requirements"],
                    scene_context=scene["description"],
                    target_audience="general"
                )
                
                if enhanced_result["success"]:
                    scene["visual_requirements"] = enhanced_result["enhanced_requirements"]
            
            enhanced_scenes.append(scene)
        
        # Validate final result
        assert len(enhanced_scenes) == len(script_data["scenes"])
        for scene in enhanced_scenes:
            assert len(scene["visual_requirements"]) > 0
            assert len(scene["dialogue"]) > 0
    
    def test_error_handling_workflow(self):
        """Test error handling in various workflow scenarios."""
        # Test with invalid research data
        invalid_research = {"invalid": "data"}
        
        result = generate_video_script(research_data=invalid_research)
        assert "error" in result or result["script"] is None
        
        # Test with invalid scene content
        visual_result = generate_visual_descriptions(scene_content="")
        assert "error" in visual_result
        
        # Test with empty requirements list
        enhance_result = enhance_visual_requirements(
            existing_requirements=[],
            scene_context="test"
        )
        assert "error" in enhance_result


# Sample data for testing
SAMPLE_RESEARCH_DATA = {
    "facts": [
        "Artificial Intelligence is revolutionizing healthcare diagnostics",
        "Machine learning algorithms can analyze medical images with 95% accuracy",
        "AI-powered drug discovery is reducing development time by 30%"
    ],
    "key_points": [
        "AI is improving patient outcomes significantly",
        "Healthcare professionals are embracing AI tools",
        "Regulatory frameworks are evolving to support AI in medicine"
    ],
    "sources": [
        "https://example.com/ai-healthcare-study",
        "https://example.com/medical-ai-research"
    ],
    "context": {
        "topic": "AI in Healthcare",
        "industry": "healthcare",
        "target_audience": "medical professionals"
    }
}

SAMPLE_SCRIPT_CONTENT = """
Welcome to our exploration of artificial intelligence in healthcare. Today we'll discover how AI is transforming medical practice and improving patient care.

Artificial intelligence is revolutionizing healthcare diagnostics. Machine learning algorithms can now analyze medical images with remarkable accuracy, often matching or exceeding human specialists.

The impact extends beyond diagnostics. AI-powered drug discovery is accelerating the development of new treatments, potentially bringing life-saving medications to patients faster than ever before.

Healthcare professionals are increasingly embracing these AI tools, recognizing their potential to enhance rather than replace human expertise. The collaboration between human insight and artificial intelligence is creating unprecedented opportunities for medical advancement.

As we conclude, it's clear that AI in healthcare represents one of the most promising applications of artificial intelligence technology. The future of medicine is being written today, with AI as a crucial co-author in this story of human health and healing.
"""


if __name__ == "__main__":
    # Run basic functionality tests
    print("Running Story Agent tests...")
    
    # Test script generation
    print("\n1. Testing script generation...")
    result = generate_video_script(SAMPLE_RESEARCH_DATA, target_duration=60)
    if result.get("success"):
        print("✓ Script generation successful")
        print(f"  Generated {len(result['script']['scenes'])} scenes")
    else:
        print("✗ Script generation failed:", result.get("error"))
    
    # Test scene breakdown
    print("\n2. Testing scene breakdown...")
    breakdown_result = create_scene_breakdown(SAMPLE_SCRIPT_CONTENT, target_duration=90, scene_count=5)
    if breakdown_result.get("success"):
        print("✓ Scene breakdown successful")
        print(f"  Created {len(breakdown_result['scenes'])} scenes")
    else:
        print("✗ Scene breakdown failed:", breakdown_result.get("error"))
    
    # Test visual descriptions
    print("\n3. Testing visual descriptions...")
    visual_result = generate_visual_descriptions(
        "This scene discusses AI applications in medical diagnostics and patient care.",
        style="professional",
        duration=15.0
    )
    if visual_result.get("success"):
        print("✓ Visual descriptions successful")
        print(f"  Generated {len(visual_result['visual_requirements'])} requirements")
    else:
        print("✗ Visual descriptions failed:", visual_result.get("error"))
    
    print("\nStory Agent tests completed!")
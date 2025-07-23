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

"""Unit tests for the Image Generation Agent and its tools."""

import pytest
from unittest.mock import Mock, patch
from video_system.agents.image_generation_agent.agent import (
    root_agent as image_generation_agent,
)


class TestImagenGenerationTool:
    """Test cases for the Imagen 4 Generation Tool."""

    @pytest.fixture
    def mock_imagen_response(self):
        """Mock successful Imagen 4 API response."""
        mock_generated_image = Mock()
        mock_generated_image.image.image_bytes = b"fake_image_bytes_data"

        mock_result = Mock()
        mock_result.generated_images = [mock_generated_image]

        return mock_result

    def test_imagen_generation_without_api_key(self):
        """Test Imagen 4 generation behavior without API key."""
        with patch.dict("os.environ", {}, clear=True):
            result = generate_imagen_image("test prompt")
            assert result["total_images"] == 0
            assert len(result["images"]) == 1
            assert result["images"][0]["status"] == "error"
            assert (
                "GEMINI_API_KEY environment variable is not set"
                in result["images"][0]["error"]
            )

    @patch.dict("os.environ", {"GEMINI_API_KEY": "test_api_key"})
    @patch("google.genai.Client")
    @patch("PIL.Image.open")
    def test_imagen_generation_success(
        self, mock_pil_open, mock_client_class, mock_imagen_response
    ):
        """Test successful Imagen 4 image generation."""
        # Mock PIL Image
        mock_image = Mock()
        mock_image.size = (1024, 1024)
        mock_pil_open.return_value = mock_image

        # Mock Gemini client
        mock_client = Mock()
        mock_client.models.generate_images.return_value = mock_imagen_response
        mock_client_class.return_value = mock_client

        result = generate_imagen_image(
            "mountain landscape", aspect_ratio="1:1", number_of_images=1
        )

        # Verify API call
        mock_client.models.generate_images.assert_called_once()
        call_args = mock_client.models.generate_images.call_args
        assert call_args[1]["prompt"] == "mountain landscape"
        assert call_args[1]["config"]["aspect_ratio"] == "1:1"
        assert call_args[1]["config"]["number_of_images"] == 1
        assert call_args[1]["model"] == "models/imagen-4.0-generate-preview-06-06"

        # Verify result structure
        assert result["total_images"] == 1
        assert result["source"] == "imagen4"
        assert len(result["images"]) == 1

        # Verify image structure
        image = result["images"][0]
        assert image["status"] == "success"
        assert image["source"] == "imagen4"
        assert image["model"] == "imagen-4.0-generate-preview-06-06"
        assert "base64" in image
        assert "image_bytes" in image

    @patch.dict("os.environ", {"GEMINI_API_KEY": "test_api_key"})
    @patch("google.genai.Client")
    @patch("PIL.Image.open")
    def test_imagen_generation_with_invalid_parameters(
        self, mock_pil_open, mock_client_class, mock_imagen_response
    ):
        """Test Imagen 4 generation with invalid parameters (should use defaults)."""
        # Mock PIL Image
        mock_image = Mock()
        mock_image.size = (1024, 1024)
        mock_pil_open.return_value = mock_image

        # Mock Gemini client
        mock_client = Mock()
        mock_client.models.generate_images.return_value = mock_imagen_response
        mock_client_class.return_value = mock_client

        generate_imagen_image(
            "test", aspect_ratio="invalid_ratio", person_generation="invalid_policy"
        )

        # Verify parameters were corrected to defaults
        call_args = mock_client.models.generate_images.call_args
        assert call_args[1]["config"]["aspect_ratio"] == "1:1"  # Default
        assert call_args[1]["config"]["person_generation"] == "ALLOW_ADULT"  # Default

    @patch.dict("os.environ", {"GEMINI_API_KEY": "test_api_key"})
    @patch("google.genai.Client")
    def test_imagen_generation_request_exception(self, mock_client_class):
        """Test Imagen 4 generation handling when API request fails."""
        mock_client = Mock()
        mock_client.models.generate_images.side_effect = Exception("API error")
        mock_client_class.return_value = mock_client

        result = generate_imagen_image("test prompt")

        assert result["total_images"] == 0
        assert len(result["images"]) == 1
        assert result["images"][0]["status"] == "error"
        assert "Failed to generate image with Imagen 4" in result["images"][0]["error"]


class TestStableDiffusionTool:
    """Test cases for the Stable Diffusion Tool."""

    @pytest.fixture
    def mock_stable_diffusion_response(self):
        """Mock successful Stable Diffusion API response."""
        return {
            "artifacts": [
                {
                    "base64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==",
                    "seed": 1234567890,
                    "finishReason": "SUCCESS",
                }
            ]
        }

    def test_stable_diffusion_without_api_key(self):
        """Test Stable Diffusion generation behavior without API key."""
        with patch.dict("os.environ", {}, clear=True):
            result = generate_stable_diffusion_image("test prompt")
            assert result["total_images"] == 0
            assert len(result["images"]) == 1
            assert result["images"][0]["status"] == "error"
            assert (
                "STABILITY_API_KEY environment variable is not set"
                in result["images"][0]["error"]
            )

    @patch.dict("os.environ", {"STABILITY_API_KEY": "test_api_key"})
    @patch("requests.post")
    def test_stable_diffusion_generation_success(
        self, mock_post, mock_stable_diffusion_response
    ):
        """Test successful Stable Diffusion image generation."""
        mock_response = Mock()
        mock_response.json.return_value = mock_stable_diffusion_response
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        result = generate_stable_diffusion_image(
            "mountain landscape",
            negative_prompt="blurry, low quality",
            width=1024,
            height=1024,
            steps=30,
            cfg_scale=7.5,
        )

        # Verify API call
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[1]["json"]["text_prompts"][0]["text"] == "mountain landscape"
        assert call_args[1]["json"]["text_prompts"][1]["text"] == "blurry, low quality"
        assert call_args[1]["json"]["text_prompts"][1]["weight"] == -1.0
        assert call_args[1]["json"]["width"] == 1024
        assert call_args[1]["json"]["height"] == 1024
        assert call_args[1]["json"]["steps"] == 30
        assert call_args[1]["json"]["cfg_scale"] == 7.5

        # Verify result structure
        assert result["total_images"] == 1
        assert result["source"] == "stable_diffusion"
        assert len(result["images"]) == 1

        # Verify image structure
        image = result["images"][0]
        assert image["status"] == "success"
        assert image["source"] == "stable_diffusion"
        assert image["model"] == "stable-diffusion-xl-1024-v1-0"
        assert "base64" in image
        assert image["seed"] == 1234567890

    @patch.dict("os.environ", {"STABILITY_API_KEY": "test_api_key"})
    @patch("requests.post")
    def test_stable_diffusion_parameter_clamping(
        self, mock_post, mock_stable_diffusion_response
    ):
        """Test that Stable Diffusion parameters are properly clamped to valid ranges."""
        mock_response = Mock()
        mock_response.json.return_value = mock_stable_diffusion_response
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        # Test with out-of-range parameters
        generate_stable_diffusion_image(
            "test",
            width=100,  # Too small, should be clamped to 512
            height=5000,  # Too large, should be clamped to 2048
            steps=5,  # Too small, should be clamped to 10
            cfg_scale=25.0,  # Too large, should be clamped to 20.0
            samples=10,  # Too large, should be clamped to 4
        )

        # Verify parameters were clamped
        call_args = mock_post.call_args
        assert call_args[1]["json"]["width"] == 512
        assert call_args[1]["json"]["height"] == 2048
        assert call_args[1]["json"]["steps"] == 10
        assert call_args[1]["json"]["cfg_scale"] == 20.0
        assert call_args[1]["json"]["samples"] == 4


class TestPromptOptimizerTool:
    """Test cases for the Prompt Optimizer Tool."""

    def test_prompt_optimization_basic(self):
        """Test basic prompt optimization functionality."""
        result = optimize_image_prompt(
            "A mountain landscape",
            video_style="professional",
            consistency_elements=["blue sky", "green trees"],
            target_service="imagen4",
        )

        assert result["status"] == "success"
        assert "A mountain landscape" in result["optimized_prompt"]
        assert "blue sky" in result["optimized_prompt"]
        assert "green trees" in result["optimized_prompt"]
        assert "professional" in result["optimized_prompt"]
        assert result["target_service"] == "imagen4"
        assert "recommended_params" in result

    def test_prompt_optimization_cinematic_style(self):
        """Test prompt optimization with cinematic style."""
        result = optimize_image_prompt(
            "A city street at night",
            video_style="cinematic",
            target_service="stable_diffusion",
        )

        assert result["status"] == "success"
        assert "cinematic" in result["optimized_prompt"]
        assert "dramatic" in result["optimized_prompt"]
        assert result["target_service"] == "stable_diffusion"
        assert "negative_prompt" in result
        assert len(result["negative_prompt"]) > 0

    def test_prompt_optimization_with_consistency_elements(self):
        """Test prompt optimization with consistency elements."""
        consistency_elements = ["warm lighting", "vintage style", "film grain"]
        result = optimize_image_prompt(
            "Interior of a coffee shop",
            consistency_elements=consistency_elements,
            target_service="imagen4",
        )

        assert result["status"] == "success"
        for element in consistency_elements:
            assert element in result["optimized_prompt"]
        assert result["consistency_elements"] == consistency_elements

    def test_prompt_optimization_different_styles(self):
        """Test prompt optimization with different video styles."""
        styles = ["professional", "cinematic", "documentary", "corporate", "artistic"]

        for style in styles:
            result = optimize_image_prompt("A person working", video_style=style)
            assert result["status"] == "success"
            assert result["video_style"] == style
            assert len(result["optimized_prompt"]) > len("A person working")

    def test_style_variations_generation(self):
        """Test generation of style variations."""
        result = generate_style_variations("A beautiful sunset", num_variations=3)

        assert result["status"] == "success"
        assert result["base_prompt"] == "A beautiful sunset"
        assert result["total_variations"] == 3
        assert len(result["variations"]) == 3

        for i, variation in enumerate(result["variations"]):
            assert "A beautiful sunset" in variation["prompt"]
            assert variation["variation_id"] == i + 1
            assert len(variation["style_modifier"]) > 0

    def test_style_variations_with_large_number(self):
        """Test style variations with number larger than available modifiers."""
        result = generate_style_variations("Test prompt", num_variations=20)

        assert result["status"] == "success"
        # Should be limited to available style modifiers (8)
        assert result["total_variations"] <= 8
        assert len(result["variations"]) <= 8


class TestImageGenerationAgent:
    """Test cases for the Image Generation Agent integration."""

    def test_image_generation_agent_initialization(self):
        """Test that the image generation agent is properly initialized."""
        assert image_generation_agent.name == "image_generation_agent"
        assert image_generation_agent.model == "gemini-2.5-pro"
        assert len(image_generation_agent.tools) == 4

        # Check tool functions
        tool_names = [tool.__name__ for tool in image_generation_agent.tools]
        expected_tools = [
            "generate_imagen_image",
            "generate_stable_diffusion_image",
            "optimize_image_prompt",
            "generate_style_variations",
        ]

        for expected_tool in expected_tools:
            assert expected_tool in tool_names

    def test_image_generation_agent_instruction_content(self):
        """Test that the image generation agent has comprehensive instructions."""
        instruction = image_generation_agent.instruction

        # Check for key instruction components
        assert "Image Generation Agent" in instruction
        assert "custom visual assets" in instruction.lower()
        assert "ai image generation" in instruction.lower()
        assert "visual consistency" in instruction.lower()
        assert "asset sourcing agent" in instruction.lower()


class TestImageGenerationWorkflow:
    """Integration tests for image generation workflow."""

    @patch.dict(
        "os.environ",
        {
            "GEMINI_API_KEY": "test_gemini_key",
            "STABILITY_API_KEY": "test_stability_key",
        },
    )
    def test_multi_service_image_generation(self):
        """Test image generation across multiple AI services."""
        # Test prompt optimization for different services
        imagen_optimization = optimize_image_prompt(
            "A forest scene", target_service="imagen4"
        )
        sd_optimization = optimize_image_prompt(
            "A forest scene", target_service="stable_diffusion"
        )

        assert imagen_optimization["status"] == "success"
        assert sd_optimization["status"] == "success"
        assert imagen_optimization["target_service"] == "imagen4"
        assert sd_optimization["target_service"] == "stable_diffusion"

        # Verify different optimizations for different services
        assert (
            imagen_optimization["recommended_params"]
            != sd_optimization["recommended_params"]
        )

    def test_consistency_across_generations(self):
        """Test that consistency elements are maintained across generations."""
        consistency_elements = ["blue sky", "green grass", "sunny day"]

        # Test multiple optimizations with same consistency elements
        scene1 = optimize_image_prompt(
            "A park", consistency_elements=consistency_elements
        )
        scene2 = optimize_image_prompt(
            "A playground", consistency_elements=consistency_elements
        )

        assert scene1["status"] == "success"
        assert scene2["status"] == "success"

        # Verify consistency elements appear in both optimized prompts
        for element in consistency_elements:
            assert element in scene1["optimized_prompt"]
            assert element in scene2["optimized_prompt"]

    def test_fallback_mechanisms(self):
        """Test fallback mechanisms when services fail."""
        # Test with missing API keys
        with patch.dict("os.environ", {}, clear=True):
            imagen_result = generate_imagen_image("test prompt")
            sd_result = generate_stable_diffusion_image("test prompt")

            assert imagen_result["total_images"] == 0
            assert sd_result["total_images"] == 0
            assert imagen_result["images"][0]["status"] == "error"
            assert sd_result["images"][0]["status"] == "error"

    def test_prompt_optimization_error_handling(self):
        """Test error handling in prompt optimization."""
        # Test with invalid inputs
        result = optimize_image_prompt("", video_style="invalid_style")

        # Should still work with fallbacks
        assert result["status"] == "success"
        assert len(result["optimized_prompt"]) > 0

    @patch.dict("os.environ", {"GEMINI_API_KEY": "test_key"})
    @patch("google.genai.Client")
    @patch("PIL.Image.open")
    def test_image_generation_agent_tool_integration(
        self, mock_pil_open, mock_client_class
    ):
        """Test that image generation agent properly integrates with all tools."""
        # Mock PIL Image
        mock_image = Mock()
        mock_image.size = (1024, 1024)
        mock_pil_open.return_value = mock_image

        # Mock successful Imagen response
        mock_generated_image = Mock()
        mock_generated_image.image.image_bytes = b"test_image_data"

        mock_result = Mock()
        mock_result.generated_images = [mock_generated_image]

        mock_client = Mock()
        mock_client.models.generate_images.return_value = mock_result
        mock_client_class.return_value = mock_client

        # Verify all tools are accessible and callable
        tools = image_generation_agent.tools
        assert len(tools) == 4

        for tool in tools:
            assert callable(tool)

        # Test actual tool execution
        imagen_result = generate_imagen_image("test prompt")
        assert imagen_result["source"] == "imagen4"
        assert imagen_result["total_images"] == 1

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

"""Unit tests for the Audio Agent and its tools."""

import pytest
from unittest.mock import Mock, patch, mock_open
import tempfile
import os
from sub_agents.audio.tools.gemini_tts import generate_speech_with_gemini, convert_to_wav, parse_audio_mime_type
from sub_agents.audio.tools.audio_processing import calculate_audio_timing, convert_audio_format
from sub_agents.audio.agent import audio_agent


class TestGeminiTTSTool:
    """Test cases for the Gemini TTS Tool."""
    
    @pytest.fixture
    def mock_gemini_tts_response(self):
        """Mock successful Gemini TTS API response."""
        mock_chunk = Mock()
        mock_chunk.candidates = [Mock()]
        mock_chunk.candidates[0].content = Mock()
        mock_chunk.candidates[0].content.parts = [Mock()]
        mock_chunk.candidates[0].content.parts[0].inline_data = Mock()
        mock_chunk.candidates[0].content.parts[0].inline_data.data = b"fake_audio_data"
        mock_chunk.candidates[0].content.parts[0].inline_data.mime_type = "audio/L16;rate=24000"
        
        return [mock_chunk]
    
    def test_gemini_tts_without_api_key(self):
        """Test Gemini TTS behavior without API key."""
        with patch.dict('os.environ', {}, clear=True):
            result = generate_speech_with_gemini("test text")
            assert result["total_files"] == 0
            assert len(result["audio_files"]) == 1
            assert result["audio_files"][0]["status"] == "error"
            assert "GEMINI_API_KEY environment variable is not set" in result["audio_files"][0]["error"]
    
    @patch.dict('os.environ', {'GEMINI_API_KEY': 'test_api_key'})
    @patch('google.genai.Client')
    def test_gemini_tts_success(self, mock_client_class, mock_gemini_tts_response):
        """Test successful Gemini TTS generation."""
        # Mock Gemini client
        mock_client = Mock()
        mock_client.models.generate_content_stream.return_value = mock_gemini_tts_response
        mock_client_class.return_value = mock_client
        
        result = generate_speech_with_gemini("Hello world", voice_name="Zephyr", temperature=1.0)
        
        # Verify API call
        mock_client.models.generate_content_stream.assert_called_once()
        call_args = mock_client.models.generate_content_stream.call_args
        assert call_args[1]['model'] == "gemini-2.5-flash-preview-tts"
        
        # Verify result structure
        assert result["total_files"] == 1
        assert result["source"] == "gemini_tts"
        assert len(result["audio_files"]) == 1
        
        # Verify audio structure
        audio = result["audio_files"][0]
        assert audio["status"] == "success"
        assert audio["source"] == "gemini_tts"
        assert audio["model"] == "gemini-2.5-flash-preview-tts"
        assert audio["voice_name"] == "Zephyr"
        assert "base64" in audio
        assert "audio_data" in audio
    
    @patch.dict('os.environ', {'GEMINI_API_KEY': 'test_api_key'})
    @patch('google.genai.Client')
    def test_gemini_tts_with_invalid_voice(self, mock_client_class, mock_gemini_tts_response):
        """Test Gemini TTS with invalid voice name (should use default)."""
        mock_client = Mock()
        mock_client.models.generate_content_stream.return_value = mock_gemini_tts_response
        mock_client_class.return_value = mock_client
        
        result = generate_speech_with_gemini("test", voice_name="InvalidVoice")
        
        # Should still succeed with default voice
        assert result["total_files"] == 1
        assert result["audio_files"][0]["voice_name"] == "Zephyr"  # Default
    
    @patch.dict('os.environ', {'GEMINI_API_KEY': 'test_api_key'})
    @patch('google.genai.Client')
    def test_gemini_tts_request_exception(self, mock_client_class):
        """Test Gemini TTS handling when API request fails."""
        mock_client = Mock()
        mock_client.models.generate_content_stream.side_effect = Exception("API error")
        mock_client_class.return_value = mock_client
        
        result = generate_speech_with_gemini("test text")
        
        assert result["total_files"] == 0
        assert len(result["audio_files"]) == 1
        assert result["audio_files"][0]["status"] == "error"
        assert "Failed to generate speech with Gemini TTS" in result["audio_files"][0]["error"]
    
    def test_convert_to_wav(self):
        """Test WAV conversion functionality."""
        audio_data = b"fake_audio_data"
        mime_type = "audio/L16;rate=24000"
        
        wav_data = convert_to_wav(audio_data, mime_type)
        
        # Check that WAV header is added
        assert len(wav_data) > len(audio_data)
        assert wav_data.startswith(b"RIFF")
        assert b"WAVE" in wav_data[:20]
    
    def test_parse_audio_mime_type(self):
        """Test MIME type parsing."""
        # Test standard format
        result = parse_audio_mime_type("audio/L16;rate=24000")
        assert result["bits_per_sample"] == 16
        assert result["rate"] == 24000
        
        # Test different format
        result = parse_audio_mime_type("audio/L8;rate=16000")
        assert result["bits_per_sample"] == 8
        assert result["rate"] == 16000
        
        # Test malformed format (should use defaults)
        result = parse_audio_mime_type("audio/invalid")
        assert result["bits_per_sample"] == 16  # Default
        assert result["rate"] == 24000  # Default


class TestAudioProcessingTools:
    """Test cases for audio processing tools."""
    
    @pytest.fixture
    def sample_script_scenes(self):
        """Sample script scenes for testing."""
        return [
            {
                "scene_number": 1,
                "description": "Opening scene",
                "dialogue": "Welcome to our presentation",
                "duration": 5.0
            },
            {
                "scene_number": 2,
                "description": "Main content",
                "dialogue": "Today we will discuss the key features",
                "duration": 10.0
            },
            {
                "scene_number": 3,
                "description": "Conclusion",
                "dialogue": "Thank you for watching",
                "duration": 3.0
            }
        ]
    
    def test_calculate_audio_timing_success(self, sample_script_scenes):
        """Test successful audio timing calculation."""
        result = calculate_audio_timing(sample_script_scenes, 60.0)
        
        assert result["status"] == "success"
        assert result["scene_count"] == 3
        assert result["audio_segments_needed"] == 3
        assert len(result["timing_segments"]) == 3
        
        # Check timing segments
        segments = result["timing_segments"]
        assert segments[0]["start_time"] == 0.0
        assert segments[0]["dialogue"] == "Welcome to our presentation"
        assert segments[1]["start_time"] > segments[0]["end_time"]
        assert segments[2]["start_time"] > segments[1]["end_time"]
    
    def test_calculate_audio_timing_empty_scenes(self):
        """Test audio timing calculation with empty scenes."""
        result = calculate_audio_timing([], 60.0)
        
        assert result["status"] == "error"
        assert "No script scenes provided" in result["error"]
        assert len(result["timing_segments"]) == 0
    
    def test_calculate_audio_timing_no_durations(self):
        """Test audio timing calculation when scenes have no duration."""
        scenes = [
            {"scene_number": 1, "dialogue": "First scene"},
            {"scene_number": 2, "dialogue": "Second scene"}
        ]
        
        result = calculate_audio_timing(scenes, 60.0)
        
        assert result["status"] == "success"
        assert len(result["timing_segments"]) == 2
        # Should distribute evenly
        assert result["timing_segments"][0]["duration"] == 30.0
        assert result["timing_segments"][1]["duration"] == 30.0
    
    @patch('subprocess.run')
    def test_convert_audio_format_success(self, mock_subprocess):
        """Test successful audio format conversion."""
        # Mock FFmpeg availability check
        mock_subprocess.side_effect = [
            Mock(returncode=0),  # FFmpeg version check
            Mock(returncode=0)   # Actual conversion
        ]
        
        # Mock file operations
        with patch('tempfile.NamedTemporaryFile') as mock_temp, \
             patch('builtins.open', mock_open(read_data=b"converted_audio_data")) as mock_file:
            
            mock_temp.return_value.__enter__.return_value.name = "temp_file"
            
            result = convert_audio_format(b"original_audio_data", "wav", "mp3", "128k")
            
            assert result["status"] == "success"
            assert result["input_format"] == "wav"
            assert result["output_format"] == "mp3"
            assert result["bitrate"] == "128k"
            assert "converted_audio" in result
            assert "base64" in result
    
    @patch('subprocess.run')
    def test_convert_audio_format_no_ffmpeg(self, mock_subprocess):
        """Test audio format conversion when FFmpeg is not available."""
        # Mock FFmpeg not available
        mock_subprocess.side_effect = FileNotFoundError("FFmpeg not found")
        
        original_data = b"original_audio_data"
        result = convert_audio_format(original_data, "wav", "mp3")
        
        assert result["status"] == "warning"
        assert "FFmpeg not available" in result["warning"]
        assert result["converted_audio"] == original_data  # Should return original
    
    def test_convert_audio_format_empty_data(self):
        """Test audio format conversion with empty data."""
        result = convert_audio_format(b"", "wav", "mp3")
        
        assert result["status"] == "error"
        assert "No audio data provided" in result["error"]
    
    @patch('subprocess.run')
    def test_convert_audio_format_ffmpeg_error(self, mock_subprocess):
        """Test audio format conversion when FFmpeg fails."""
        # Mock FFmpeg available but conversion fails
        mock_subprocess.side_effect = [
            Mock(returncode=0),  # FFmpeg version check succeeds
            Mock(returncode=1, stderr="Conversion failed")  # Conversion fails
        ]
        
        with patch('tempfile.NamedTemporaryFile') as mock_temp:
            mock_temp.return_value.__enter__.return_value.name = "temp_file"
            
            original_data = b"original_audio_data"
            result = convert_audio_format(original_data, "wav", "mp3")
            
            assert result["status"] == "error"
            assert "FFmpeg conversion failed" in result["error"]
            assert result["converted_audio"] == original_data  # Should return original


class TestAudioAgent:
    """Test cases for the Audio Agent integration."""
    
    def test_audio_agent_initialization(self):
        """Test that the audio agent is properly initialized."""
        assert audio_agent.name == "audio_agent"
        assert audio_agent.model == "gemini-2.5-flash"
        assert len(audio_agent.tools) == 3
        
        # Check tool functions
        tool_names = [tool.__name__ for tool in audio_agent.tools]
        expected_tools = [
            "generate_speech_with_gemini",
            "calculate_audio_timing",
            "convert_audio_format"
        ]
        
        for expected_tool in expected_tools:
            assert expected_tool in tool_names
    
    def test_audio_agent_instruction_content(self):
        """Test that the audio agent has comprehensive instructions."""
        instruction = audio_agent.instruction
        
        # Check for key instruction components
        assert "Audio Agent" in instruction
        assert "text-to-speech" in instruction.lower()
        assert "gemini tts" in instruction.lower()
        assert "voice profiles" in instruction.lower()
        assert "synchronize" in instruction.lower()
        assert "Zephyr" in instruction  # Voice options
        assert "Charon" in instruction
        assert "Kore" in instruction
        assert "Fenrir" in instruction


class TestAudioWorkflow:
    """Integration tests for audio processing workflow."""
    
    @patch.dict('os.environ', {'GEMINI_API_KEY': 'test_key'})
    @patch('google.genai.Client')
    def test_complete_audio_workflow(self, mock_client_class):
        """Test complete audio processing workflow."""
        # Mock TTS response
        mock_chunk = Mock()
        mock_chunk.candidates = [Mock()]
        mock_chunk.candidates[0].content = Mock()
        mock_chunk.candidates[0].content.parts = [Mock()]
        mock_chunk.candidates[0].content.parts[0].inline_data = Mock()
        mock_chunk.candidates[0].content.parts[0].inline_data.data = b"fake_audio_data"
        mock_chunk.candidates[0].content.parts[0].inline_data.mime_type = "audio/L16;rate=24000"
        
        mock_client = Mock()
        mock_client.models.generate_content_stream.return_value = [mock_chunk]
        mock_client_class.return_value = mock_client
        
        # Test script scenes
        script_scenes = [
            {"scene_number": 1, "dialogue": "Hello world", "duration": 3.0},
            {"scene_number": 2, "dialogue": "This is a test", "duration": 4.0}
        ]
        
        # Step 1: Calculate timing
        timing_result = calculate_audio_timing(script_scenes, 30.0)
        assert timing_result["status"] == "success"
        
        # Step 2: Generate speech for each dialogue
        for scene in script_scenes:
            if scene["dialogue"]:
                tts_result = generate_speech_with_gemini(scene["dialogue"])
                assert tts_result["total_files"] == 1
                assert tts_result["audio_files"][0]["status"] == "success"
    
    def test_error_handling_scenarios(self):
        """Test error handling across different failure scenarios."""
        # Test missing API key
        with patch.dict('os.environ', {}, clear=True):
            tts_result = generate_speech_with_gemini("test")
            assert tts_result["total_files"] == 0
            assert "GEMINI_API_KEY" in tts_result["audio_files"][0]["error"]
        
        # Test invalid script scenes
        timing_result = calculate_audio_timing([], 60.0)
        assert timing_result["status"] == "error"
        assert "No script scenes provided" in timing_result["error"]
    
    def test_voice_profile_selection(self):
        """Test different voice profile selections."""
        voices = ["Zephyr", "Charon", "Kore", "Fenrir"]
        
        for voice in voices:
            with patch.dict('os.environ', {'GEMINI_API_KEY': 'test_key'}):
                with patch('google.genai.Client') as mock_client_class:
                    # Mock empty response to avoid processing
                    mock_client = Mock()
                    mock_client.models.generate_content_stream.return_value = []
                    mock_client_class.return_value = mock_client
                    
                    result = generate_speech_with_gemini("test", voice_name=voice)
                    # Should not error out with valid voice names
                    assert result["source"] == "gemini_tts"
    
    @patch.dict('os.environ', {'GEMINI_API_KEY': 'test_key'})
    @patch('google.genai.Client')
    def test_audio_agent_tool_integration(self, mock_client_class):
        """Test that audio agent properly integrates with all tools."""
        # Mock TTS response
        mock_chunk = Mock()
        mock_chunk.candidates = [Mock()]
        mock_chunk.candidates[0].content = Mock()
        mock_chunk.candidates[0].content.parts = [Mock()]
        mock_chunk.candidates[0].content.parts[0].inline_data = Mock()
        mock_chunk.candidates[0].content.parts[0].inline_data.data = b"test_audio"
        mock_chunk.candidates[0].content.parts[0].inline_data.mime_type = "audio/L16;rate=24000"
        
        mock_client = Mock()
        mock_client.models.generate_content_stream.return_value = [mock_chunk]
        mock_client_class.return_value = mock_client
        
        # Verify all tools are accessible and callable
        tools = audio_agent.tools
        assert len(tools) == 3
        
        for tool in tools:
            assert callable(tool)
        
        # Test actual tool execution
        tts_result = generate_speech_with_gemini("test text")
        assert tts_result["source"] == "gemini_tts"
        assert tts_result["total_files"] == 1
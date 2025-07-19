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

"""Google Gemini TTS API integration tool for audio agent with comprehensive error handling."""

import base64
import mimetypes
import os
import re
import struct
import tempfile
from typing import Dict, Any, List
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

from video_system.shared_libraries import (
    APIError,
    NetworkError,
    ValidationError,
    ProcessingError,
    TimeoutError,
    RetryConfig,
    retry_with_exponential_backoff,
    FallbackManager,
    FallbackConfig,
    create_error_response,
    get_logger,
    log_error,
    with_resource_check,
    with_rate_limit
)


class GeminiTTSInput(BaseModel):
    """Input schema for Gemini TTS tool."""
    text: str = Field(description="The text to convert to speech")
    voice_name: str = Field(default="Zephyr", description="Voice name: 'Zephyr', 'Charon', 'Kore', 'Fenrir'")
    temperature: float = Field(default=1.0, description="Temperature for speech generation (0.0-2.0)")
    output_format: str = Field(default="wav", description="Output audio format: 'wav', 'mp3'")


# Configure logger for TTS
logger = get_logger("audio.gemini_tts")

# Configure retry behavior for TTS
tts_retry_config = RetryConfig(
    max_attempts=3,
    base_delay=2.0,
    max_delay=30.0,
    exponential_base=2.0,
    jitter=True
)


@with_resource_check
@with_rate_limit(tokens=2)
def generate_speech_with_gemini(
    text: str, 
    voice_name: str = "Zephyr", 
    temperature: float = 1.0, 
    output_format: str = "wav"
) -> Dict[str, Any]:
    """
    Generate speech using Google's Gemini TTS API with comprehensive error handling.
    
    Args:
        text: The text to convert to speech
        voice_name: Voice name for speech synthesis
        temperature: Temperature for speech generation
        output_format: Output audio format
        
    Returns:
        Dict containing generated audio data and metadata
    """
    # Input validation
    if not isinstance(text, str) or not text.strip():
        error = ValidationError("Text cannot be empty", field="text")
        log_error(logger, error)
        return _create_error_audio_response(text, "Text cannot be empty")
    
    if len(text.strip()) > 5000:  # Reasonable limit for TTS
        error = ValidationError("Text is too long for TTS generation", field="text")
        log_error(logger, error, {"text_length": len(text)})
        return _create_error_audio_response(text, "Text is too long for TTS generation")
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        error = APIError("GEMINI_API_KEY environment variable is not set", api_name="Gemini")
        log_error(logger, error)
        return _create_error_audio_response(text, "GEMINI_API_KEY environment variable is not set")
    
    try:
        logger.info(f"Generating speech for text: {text[:50]}... (voice: {voice_name})")
        
        # Validate and sanitize parameters
        valid_voices = ["Zephyr", "Charon", "Kore", "Fenrir"]
        if voice_name not in valid_voices:
            logger.warning(f"Invalid voice '{voice_name}', using 'Charon' as fallback")
            voice_name = "Charon"
        
        temperature = max(0.0, min(temperature, 2.0))  # Clamp between 0.0 and 2.0
        
        # Use retry mechanism for TTS generation
        return _generate_speech_with_retry(text, voice_name, temperature, output_format, api_key)
        
    except (APIError, ValidationError, ProcessingError) as e:
        log_error(logger, e, {"text_length": len(text), "voice": voice_name})
        return _create_error_audio_response(text, str(e))
    
    except Exception as e:
        error = ProcessingError(f"Unexpected error during TTS generation: {str(e)}", original_exception=e)
        log_error(logger, error, {"text_length": len(text), "voice": voice_name})
        return _create_error_audio_response(text, str(error))


@retry_with_exponential_backoff(
    retry_config=tts_retry_config,
    exceptions=(APIError, NetworkError, TimeoutError),
    logger=logger
)
def _generate_speech_with_retry(text: str, voice_name: str, temperature: float, output_format: str, api_key: str) -> Dict[str, Any]:
    """Internal function to generate speech with retry logic."""
    try:
        # Initialize the Gemini client
        client = genai.Client(api_key=api_key)
        
        # Set up the content and configuration
        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=text)],
            ),
        ]
        
        generate_content_config = types.GenerateContentConfig(
            temperature=temperature,
            response_modalities=["audio"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice_name
                    )
                )
            ),
        )
        
        # Generate speech with timeout handling
        audio_files = []
        file_index = 0
        
        try:
            for chunk in client.models.generate_content_stream(
                model="gemini-2.5-flash-preview-tts",
                contents=contents,
                config=generate_content_config,
            ):
                if (chunk.candidates is None
                    or chunk.candidates[0].content is None
                    or chunk.candidates[0].content.parts is None):
                    continue
                
                if (chunk.candidates[0].content.parts[0].inline_data 
                    and chunk.candidates[0].content.parts[0].inline_data.data):
                    
                    inline_data = chunk.candidates[0].content.parts[0].inline_data
                    audio_data = inline_data.data
                    mime_type = inline_data.mime_type
                    
                    # Convert to WAV format if needed
                    if output_format.lower() == "wav":
                        audio_data = convert_to_wav(audio_data, mime_type)
                        file_extension = ".wav"
                        final_mime_type = "audio/wav"
                    else:
                        file_extension = mimetypes.guess_extension(mime_type) or ".wav"
                        final_mime_type = mime_type
                    
                    # Convert to base64 for storage/transmission
                    base64_audio = base64.b64encode(audio_data).decode('utf-8')
                    
                    formatted_audio = {
                        "audio_data": audio_data,
                        "base64": base64_audio,
                        "file_extension": file_extension,
                        "mime_type": final_mime_type,
                        "voice_name": voice_name,
                        "temperature": temperature,
                        "source": "gemini_tts",
                        "model": "gemini-2.5-flash-preview-tts",
                        "status": "success",
                        "usage_rights": "Generated content - check Google usage policies",
                        "media_type": "audio",
                        "text": text,
                        "file_id": f"gemini_tts_{file_index}",
                        "duration_estimate": estimate_audio_duration(text)
                    }
                    
                    audio_files.append(formatted_audio)
                    file_index += 1
        
        except Exception as stream_error:
            if "timeout" in str(stream_error).lower():
                raise TimeoutError(f"Gemini TTS request timed out: {str(stream_error)}")
            elif "network" in str(stream_error).lower() or "connection" in str(stream_error).lower():
                raise NetworkError(f"Network error during TTS generation: {str(stream_error)}")
            else:
                raise APIError(f"Gemini TTS API error: {str(stream_error)}", api_name="Gemini")
        
        if not audio_files:
            raise ProcessingError("No audio generated by Gemini TTS")
        
        logger.info(f"Successfully generated {len(audio_files)} audio files")
        
        return {
            "audio_files": audio_files,
            "text": text,
            "total_files": len(audio_files),
            "source": "gemini_tts",
            "model": "gemini-2.5-flash-preview-tts"
        }
        
    except Exception as e:
        # Re-raise known exceptions
        if isinstance(e, (APIError, NetworkError, TimeoutError, ProcessingError)):
            raise
        
        # Handle unexpected errors
        raise ProcessingError(f"Unexpected error in TTS generation: {str(e)}", original_exception=e)


def _create_error_audio_response(text: str, error_message: str) -> Dict[str, Any]:
    """Create a standardized error response for audio generation."""
    return {
        "audio_files": [{
            "audio_data": b"",
            "base64": "",
            "error": error_message,
            "source": "gemini_tts",
            "status": "error"
        }],
        "text": text,
        "total_files": 0,
        "source": "gemini_tts"
    }


def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    """
    Generates a WAV file header for the given audio data and parameters.
    
    Args:
        audio_data: The raw audio data as a bytes object.
        mime_type: Mime type of the audio data.
        
    Returns:
        A bytes object representing the WAV file header.
    """
    parameters = parse_audio_mime_type(mime_type)
    bits_per_sample = parameters["bits_per_sample"]
    sample_rate = parameters["rate"]
    num_channels = 1
    
    data_size = len(audio_data)
    bytes_per_sample = bits_per_sample // 8
    block_align = num_channels * bytes_per_sample
    byte_rate = sample_rate * block_align
    chunk_size = 36 + data_size  # 36 bytes for header fields before data chunk size
    
    # http://soundfile.sapp.org/doc/WaveFormat/
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",          # ChunkID
        chunk_size,       # ChunkSize (total file size - 8 bytes)
        b"WAVE",          # Format
        b"fmt ",          # Subchunk1ID
        16,               # Subchunk1Size (16 for PCM)
        1,                # AudioFormat (1 for PCM)
        num_channels,     # NumChannels
        sample_rate,      # SampleRate
        byte_rate,        # ByteRate
        block_align,      # BlockAlign
        bits_per_sample,  # BitsPerSample
        b"data",          # Subchunk2ID
        data_size         # Subchunk2Size (size of audio data)
    )
    
    return header + audio_data


def parse_audio_mime_type(mime_type: str) -> dict[str, int]:
    """
    Parses bits per sample and rate from an audio MIME type string.
    
    Args:
        mime_type: The audio MIME type string (e.g., "audio/L16;rate=24000").
        
    Returns:
        A dictionary with "bits_per_sample" and "rate" keys.
    """
    bits_per_sample = 16
    rate = 24000
    
    # Extract rate from parameters
    parts = mime_type.split(";")
    for param in parts:
        param = param.strip()
        if param.lower().startswith("rate="):
            try:
                rate_str = param.split("=", 1)[1]
                rate = int(rate_str)
            except (ValueError, IndexError):
                pass  # Keep rate as default
        elif param.startswith("audio/L"):
            try:
                bits_per_sample = int(param.split("L", 1)[1])
            except (ValueError, IndexError):
                pass  # Keep bits_per_sample as default
    
    return {"bits_per_sample": bits_per_sample, "rate": rate}


def estimate_audio_duration(text: str) -> float:
    """
    Estimate audio duration based on text length.
    
    Args:
        text: The text to estimate duration for
        
    Returns:
        Estimated duration in seconds
    """
    # Average speaking rate is about 150-160 words per minute
    # We'll use 150 WPM as a conservative estimate
    words = len(text.split())
    duration_minutes = words / 150.0
    duration_seconds = duration_minutes * 60.0
    
    return max(1.0, duration_seconds)  # Minimum 1 second


def check_gemini_tts_health() -> Dict[str, Any]:
    """Perform a health check on the Gemini TTS service."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {
            "status": "unhealthy",
            "details": {"error": "API key not configured"}
        }
    
    try:
        # Perform a simple test TTS generation
        test_result = generate_speech_with_gemini("test", "Charon", 1.0, "wav")
        if test_result.get("total_files", 0) > 0:
            return {
                "status": "healthy",
                "details": {"message": "Gemini TTS is responding normally"}
            }
        else:
            return {
                "status": "degraded",
                "details": {"error": "Gemini TTS returned no audio files"}
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "details": {"error": str(e)}
        }


# Create the tool function for ADK
gemini_tts_tool = generate_speech_with_gemini
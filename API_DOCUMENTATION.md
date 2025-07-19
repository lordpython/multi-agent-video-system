# Multi-Agent Video System API Documentation

## Overview

The Multi-Agent Video System provides both REST API and CLI interfaces for generating videos from text prompts using AI agents. This document covers the complete API specification, usage examples, and integration guidelines.

## Table of Contents

1. [REST API Reference](#rest-api-reference)
2. [CLI Reference](#cli-reference)
3. [Authentication](#authentication)
4. [Error Handling](#error-handling)
5. [Rate Limiting](#rate-limiting)
6. [Examples](#examples)
7. [SDKs and Integration](#sdks-and-integration)

## REST API Reference

### Base URL

```
http://localhost:8000
```

### Content Type

All API requests and responses use `application/json` content type.

### Endpoints

#### 1. Root Endpoint

**GET /**

Returns basic API information.

**Response:**
```json
{
  "name": "Multi-Agent Video System API",
  "version": "0.1.0",
  "description": "AI-powered video creation platform",
  "docs_url": "/docs",
  "health_url": "/health"
}
```

#### 2. Health Check

**GET /health**

Returns system health status for monitoring and load balancers.

**Response:**
```json
{
  "status": "healthy|degraded|unhealthy",
  "timestamp": "2025-01-19T10:30:00Z",
  "details": {
    "message": "All systems operational"
  }
}
```

**Status Codes:**
- `200`: System is healthy or degraded but operational
- `503`: System is unhealthy

#### 3. Generate Video

**POST /videos/generate**

Start video generation from a text prompt.

**Request Body:**
```json
{
  "prompt": "Create a professional video about artificial intelligence",
  "duration_preference": 60,
  "style": "professional",
  "voice_preference": "neutral",
  "quality": "high",
  "user_id": "optional-user-id"
}
```

**Parameters:**
- `prompt` (required): Text prompt for video generation (10-2000 characters)
- `duration_preference` (optional): Video duration in seconds (10-600, default: 60)
- `style` (optional): Video style - `professional`, `casual`, `educational`, `entertainment`, `documentary` (default: `professional`)
- `voice_preference` (optional): Voice preference for narration (default: `neutral`)
- `quality` (optional): Video quality - `low`, `medium`, `high`, `ultra` (default: `high`)
- `user_id` (optional): User identifier for tracking

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "message": "Video generation started successfully",
  "created_at": "2025-01-19T10:30:00Z",
  "estimated_completion": "2025-01-19T10:35:00Z"
}
```

**Status Codes:**
- `200`: Request accepted and processing started
- `400`: Invalid request parameters
- `500`: Internal server error

#### 4. Get Video Status

**GET /videos/{session_id}/status**

Get the current status of a video generation session.

**Path Parameters:**
- `session_id`: Session identifier

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "stage": "asset_sourcing",
  "progress": 0.65,
  "created_at": "2025-01-19T10:30:00Z",
  "updated_at": "2025-01-19T10:33:00Z",
  "estimated_completion": "2025-01-19T10:35:00Z",
  "error_message": null,
  "request_details": {
    "prompt": "Create a professional video about artificial intelligence",
    "duration_preference": 60,
    "style": "professional",
    "voice_preference": "neutral",
    "quality": "high"
  }
}
```

**Status Values:**
- `queued`: Session created, waiting to start
- `processing`: Video generation in progress
- `completed`: Video generation completed successfully
- `failed`: Video generation failed
- `cancelled`: Session cancelled by user

**Stage Values:**
- `initializing`: Setting up the generation process
- `researching`: Gathering information and context
- `scripting`: Creating video script and narrative
- `asset_sourcing`: Finding and generating visual assets
- `audio_generation`: Creating voiceover and audio
- `video_assembly`: Combining all elements into final video
- `finalizing`: Final processing and cleanup

**Status Codes:**
- `200`: Status retrieved successfully
- `404`: Session not found
- `500`: Internal server error

#### 5. Get Detailed Progress

**GET /videos/{session_id}/progress**

Get detailed progress information including stage-by-stage breakdown.

**Path Parameters:**
- `session_id`: Session identifier

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "overall_progress": 0.65,
  "current_stage": "asset_sourcing",
  "estimated_completion": "2025-01-19T10:35:00Z",
  "stage_details": {
    "researching": {
      "progress": 1.0,
      "weight": 0.15,
      "start_time": "2025-01-19T10:30:05Z",
      "end_time": "2025-01-19T10:30:35Z",
      "estimated_duration": 30
    },
    "scripting": {
      "progress": 1.0,
      "weight": 0.20,
      "start_time": "2025-01-19T10:30:35Z",
      "end_time": "2025-01-19T10:31:20Z",
      "estimated_duration": 45
    },
    "asset_sourcing": {
      "progress": 0.6,
      "weight": 0.25,
      "start_time": "2025-01-19T10:31:20Z",
      "end_time": null,
      "estimated_duration": 60
    }
  }
}
```

**Status Codes:**
- `200`: Progress retrieved successfully
- `404`: Session not found or not being monitored
- `500`: Internal server error

#### 6. Download Video

**GET /videos/{session_id}/download**

Download the generated video file.

**Path Parameters:**
- `session_id`: Session identifier

**Response:**
- Content-Type: `video/mp4`
- Content-Disposition: `attachment; filename="video_{session_id}.mp4"`

**Status Codes:**
- `200`: Video file returned
- `400`: Video generation not completed
- `404`: Session or video file not found
- `500`: Internal server error

#### 7. Cancel Video Generation

**DELETE /videos/{session_id}**

Cancel a video generation session.

**Path Parameters:**
- `session_id`: Session identifier

**Response:**
```json
{
  "message": "Session cancelled successfully",
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Status Codes:**
- `200`: Session cancelled successfully
- `404`: Session not found
- `500`: Internal server error

#### 8. List Video Sessions

**GET /videos**

List video generation sessions with optional filtering and pagination.

**Query Parameters:**
- `user_id` (optional): Filter by user ID
- `status` (optional): Filter by status (`queued`, `processing`, `completed`, `failed`, `cancelled`)
- `page` (optional): Page number (default: 1, min: 1)
- `page_size` (optional): Page size (default: 20, min: 1, max: 100)

**Response:**
```json
{
  "sessions": [
    {
      "session_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "completed",
      "stage": "completed",
      "progress": 1.0,
      "created_at": "2025-01-19T10:30:00Z",
      "updated_at": "2025-01-19T10:35:00Z",
      "estimated_completion": null,
      "error_message": null,
      "request_details": {
        "prompt": "Create a professional video about AI",
        "duration_preference": 60,
        "style": "professional"
      }
    }
  ],
  "total_count": 1,
  "page": 1,
  "page_size": 20
}
```

**Status Codes:**
- `200`: Sessions retrieved successfully
- `400`: Invalid query parameters
- `500`: Internal server error

#### 9. System Statistics

**GET /system/stats**

Get system statistics and health information.

**Response:**
```json
{
  "total_sessions": 150,
  "active_sessions": 5,
  "status_distribution": {
    "completed": 120,
    "processing": 5,
    "failed": 20,
    "cancelled": 5
  },
  "stage_distribution": {
    "researching": 2,
    "scripting": 1,
    "asset_sourcing": 1,
    "video_assembly": 1
  },
  "average_progress": 0.75,
  "system_health": {
    "status": "healthy",
    "details": {
      "message": "All systems operational"
    }
  }
}
```

**Status Codes:**
- `200`: Statistics retrieved successfully
- `500`: Internal server error

#### 10. Cleanup Sessions

**POST /system/cleanup**

Clean up old and completed sessions.

**Query Parameters:**
- `max_age_hours` (optional): Maximum age in hours for cleanup (default: 24, min: 1)

**Response:**
```json
{
  "message": "Cleaned up 15 expired sessions",
  "cleaned_count": 15,
  "max_age_hours": 24
}
```

**Status Codes:**
- `200`: Cleanup completed successfully
- `422`: Invalid parameters
- `500`: Internal server error

## CLI Reference

### Installation

The CLI is available as `video_cli.py` in the project root:

```bash
python video_cli.py --help
```

### Commands

#### 1. Generate Video

```bash
python video_cli.py generate [OPTIONS]
```

**Options:**
- `--prompt, -p TEXT`: Text prompt for video generation [required]
- `--duration, -d INTEGER`: Video duration in seconds (10-600) [default: 60]
- `--style, -s [professional|casual|educational|entertainment|documentary]`: Video style [default: professional]
- `--voice, -v TEXT`: Voice preference for narration [default: neutral]
- `--quality, -q [low|medium|high|ultra]`: Video quality setting [default: high]
- `--wait, -w`: Wait for completion and show progress
- `--output, -o PATH`: Output directory for generated video

**Examples:**
```bash
# Basic video generation
python video_cli.py generate --prompt "Create a video about machine learning"

# With custom options
python video_cli.py generate \
  --prompt "Educational video about climate change" \
  --duration 120 \
  --style educational \
  --quality ultra \
  --wait

# With output directory
python video_cli.py generate \
  --prompt "Marketing video for our product" \
  --style professional \
  --output ./videos/
```

#### 2. Check Status

```bash
python video_cli.py status [SESSION_ID] [OPTIONS]
```

**Options:**
- `--all, -a`: Show all sessions
- `--watch, -w`: Watch progress in real-time

**Examples:**
```bash
# Show recent sessions
python video_cli.py status

# Show specific session
python video_cli.py status 550e8400-e29b-41d4-a716-446655440000

# Show all sessions
python video_cli.py status --all

# Watch session progress
python video_cli.py status 550e8400-e29b-41d4-a716-446655440000 --watch
```

#### 3. Cancel Session

```bash
python video_cli.py cancel SESSION_ID [OPTIONS]
```

**Options:**
- `--keep-files`: Keep intermediate files

**Examples:**
```bash
# Cancel session and clean up files
python video_cli.py cancel 550e8400-e29b-41d4-a716-446655440000

# Cancel session but keep files
python video_cli.py cancel 550e8400-e29b-41d4-a716-446655440000 --keep-files
```

#### 4. Cleanup Sessions

```bash
python video_cli.py cleanup [OPTIONS]
```

**Options:**
- `--max-age INTEGER`: Maximum age in hours for cleanup [default: 24]
- `--dry-run`: Show what would be cleaned up without doing it

**Examples:**
```bash
# Clean up sessions older than 24 hours
python video_cli.py cleanup

# Clean up sessions older than 48 hours
python video_cli.py cleanup --max-age 48

# Dry run to see what would be cleaned
python video_cli.py cleanup --dry-run
```

#### 5. System Statistics

```bash
python video_cli.py stats
```

Shows system statistics including session counts, health status, and performance metrics.

#### 6. Start API Server

```bash
python video_cli.py serve [OPTIONS]
```

**Options:**
- `--host TEXT`: Host to bind the API server [default: 127.0.0.1]
- `--port INTEGER`: Port to bind the API server [default: 8000]
- `--reload`: Enable auto-reload for development

**Examples:**
```bash
# Start server on default host and port
python video_cli.py serve

# Start server on all interfaces
python video_cli.py serve --host 0.0.0.0 --port 9000

# Start with auto-reload for development
python video_cli.py serve --reload
```

## Authentication

Currently, the API does not require authentication. For production deployments, consider implementing:

- API key authentication
- OAuth 2.0 / JWT tokens
- Rate limiting per user/API key
- Request signing for sensitive operations

## Error Handling

### HTTP Status Codes

- `200`: Success
- `400`: Bad Request - Invalid parameters
- `404`: Not Found - Resource doesn't exist
- `422`: Unprocessable Entity - Validation error
- `500`: Internal Server Error
- `503`: Service Unavailable - System unhealthy

### Error Response Format

```json
{
  "error": "Error type",
  "detail": "Detailed error message",
  "timestamp": "2025-01-19T10:30:00Z"
}
```

### Common Error Scenarios

1. **Invalid Prompt Length**
   ```json
   {
     "error": "Validation Error",
     "detail": "Prompt must be between 10 and 2000 characters"
   }
   ```

2. **Session Not Found**
   ```json
   {
     "error": "Not Found",
     "detail": "Session not found"
   }
   ```

3. **System Overloaded**
   ```json
   {
     "error": "Service Unavailable",
     "detail": "System is currently overloaded, please try again later"
   }
   ```

## Rate Limiting

The system implements intelligent rate limiting based on:

- System resource availability
- Queue length and processing capacity
- User-specific limits (when authentication is implemented)

Rate limit headers are included in responses:
- `X-RateLimit-Limit`: Maximum requests allowed
- `X-RateLimit-Remaining`: Remaining requests in current window
- `X-RateLimit-Reset`: Time when rate limit resets

## Examples

### Python SDK Example

```python
import requests
import time

# Start video generation
response = requests.post('http://localhost:8000/videos/generate', json={
    'prompt': 'Create a professional video about artificial intelligence',
    'duration_preference': 90,
    'style': 'professional',
    'quality': 'high'
})

session_data = response.json()
session_id = session_data['session_id']
print(f"Started generation: {session_id}")

# Poll for completion
while True:
    response = requests.get(f'http://localhost:8000/videos/{session_id}/status')
    status_data = response.json()
    
    print(f"Status: {status_data['status']} - {status_data['progress']:.1%}")
    
    if status_data['status'] == 'completed':
        # Download the video
        response = requests.get(f'http://localhost:8000/videos/{session_id}/download')
        with open(f'video_{session_id}.mp4', 'wb') as f:
            f.write(response.content)
        print("Video downloaded successfully!")
        break
    elif status_data['status'] == 'failed':
        print(f"Generation failed: {status_data['error_message']}")
        break
    
    time.sleep(5)
```

### JavaScript/Node.js Example

```javascript
const axios = require('axios');

async function generateVideo() {
    try {
        // Start video generation
        const response = await axios.post('http://localhost:8000/videos/generate', {
            prompt: 'Create an educational video about renewable energy',
            duration_preference: 120,
            style: 'educational',
            quality: 'high'
        });
        
        const sessionId = response.data.session_id;
        console.log(`Started generation: ${sessionId}`);
        
        // Poll for completion
        while (true) {
            const statusResponse = await axios.get(`http://localhost:8000/videos/${sessionId}/status`);
            const statusData = statusResponse.data;
            
            console.log(`Status: ${statusData.status} - ${(statusData.progress * 100).toFixed(1)}%`);
            
            if (statusData.status === 'completed') {
                // Download the video
                const videoResponse = await axios.get(`http://localhost:8000/videos/${sessionId}/download`, {
                    responseType: 'stream'
                });
                
                const fs = require('fs');
                const writer = fs.createWriteStream(`video_${sessionId}.mp4`);
                videoResponse.data.pipe(writer);
                
                writer.on('finish', () => {
                    console.log('Video downloaded successfully!');
                });
                break;
            } else if (statusData.status === 'failed') {
                console.log(`Generation failed: ${statusData.error_message}`);
                break;
            }
            
            await new Promise(resolve => setTimeout(resolve, 5000));
        }
    } catch (error) {
        console.error('Error:', error.response?.data || error.message);
    }
}

generateVideo();
```

### cURL Examples

```bash
# Start video generation
curl -X POST "http://localhost:8000/videos/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Create a video about sustainable technology",
    "duration_preference": 60,
    "style": "professional",
    "quality": "high"
  }'

# Check status
curl "http://localhost:8000/videos/550e8400-e29b-41d4-a716-446655440000/status"

# Get detailed progress
curl "http://localhost:8000/videos/550e8400-e29b-41d4-a716-446655440000/progress"

# Download video
curl -O "http://localhost:8000/videos/550e8400-e29b-41d4-a716-446655440000/download"

# List sessions
curl "http://localhost:8000/videos?page=1&page_size=10"

# System health check
curl "http://localhost:8000/health"
```

## SDKs and Integration

### Webhook Support (Future)

Future versions will support webhooks for real-time notifications:

```json
{
  "webhook_url": "https://your-app.com/webhooks/video-status",
  "events": ["completed", "failed", "progress_update"]
}
```

### Batch Processing (Future)

Support for batch video generation:

```json
{
  "batch_requests": [
    {
      "prompt": "Video 1 prompt",
      "duration_preference": 60
    },
    {
      "prompt": "Video 2 prompt", 
      "duration_preference": 90
    }
  ]
}
```

### Integration Guidelines

1. **Polling Frequency**: Poll status every 5-10 seconds to avoid overwhelming the system
2. **Timeout Handling**: Set appropriate timeouts for long-running operations
3. **Error Retry**: Implement exponential backoff for retrying failed requests
4. **Resource Management**: Clean up completed sessions to avoid storage bloat
5. **Monitoring**: Monitor system health endpoint for service availability

## Support and Troubleshooting

### Common Issues

1. **Session Not Found**: Session may have been cleaned up or never existed
2. **Generation Timeout**: Large videos may take longer than expected
3. **Resource Limits**: System may queue requests during high load
4. **File Access**: Ensure proper permissions for video file downloads

### Logging and Debugging

Enable debug logging by setting environment variables:
```bash
export LOG_LEVEL=DEBUG
export ENABLE_TRACE_LOGGING=true
```

### Performance Optimization

- Use appropriate quality settings for your use case
- Consider shorter durations for faster processing
- Monitor system resources and scale accordingly
- Implement caching for frequently requested content

For additional support, please refer to the project documentation or submit issues through the appropriate channels.
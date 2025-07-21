#!/usr/bin/env python3
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

"""Demo script for CLI and API interfaces of the Multi-Agent Video System.

This script demonstrates the functionality of both the command-line interface
and the REST API for video generation.
"""

import json
import requests
import subprocess
import sys

def demo_cli_interface():
    """Demonstrate CLI interface functionality."""
    print("=" * 60)
    print("CLI INTERFACE DEMONSTRATION")
    print("=" * 60)
    
    # Show CLI help
    print("\n1. CLI Help:")
    result = subprocess.run([sys.executable, "video_cli.py", "--help"], 
                          capture_output=True, text=True)
    print(result.stdout)
    
    # Show generate command help
    print("\n2. Generate Command Help:")
    result = subprocess.run([sys.executable, "video_cli.py", "generate", "--help"], 
                          capture_output=True, text=True)
    print(result.stdout)
    
    # Demonstrate session creation (without waiting)
    print("\n3. Creating a Video Generation Session:")
    result = subprocess.run([
        sys.executable, "video_cli.py", "generate",
        "--prompt", "Create a professional video about artificial intelligence and machine learning",
        "--duration", "90",
        "--style", "professional",
        "--quality", "high"
    ], capture_output=True, text=True)
    
    print("Command output:")
    print(result.stdout)
    if result.stderr:
        print("Errors:")
        print(result.stderr)
    
    # Show system stats
    print("\n4. System Statistics:")
    result = subprocess.run([sys.executable, "video_cli.py", "stats"], 
                          capture_output=True, text=True)
    print(result.stdout)
    
    # Show recent sessions
    print("\n5. Recent Sessions:")
    result = subprocess.run([sys.executable, "video_cli.py", "status"], 
                          capture_output=True, text=True)
    print(result.stdout)


def demo_api_interface():
    """Demonstrate REST API interface functionality."""
    print("=" * 60)
    print("REST API DEMONSTRATION")
    print("=" * 60)
    
    # Note: This assumes the API server is running on localhost:8000
    base_url = "http://localhost:8000"
    
    try:
        # Test root endpoint
        print("\n1. Root Endpoint:")
        response = requests.get(f"{base_url}/")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        # Test health check
        print("\n2. Health Check:")
        response = requests.get(f"{base_url}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        # Start video generation
        print("\n3. Start Video Generation:")
        video_request = {
            "prompt": "Create an educational video about renewable energy and sustainability",
            "duration_preference": 120,
            "style": "educational",
            "voice_preference": "neutral",
            "quality": "high",
            "user_id": "demo-user"
        }
        
        response = requests.post(f"{base_url}/videos/generate", json=video_request)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            session_data = response.json()
            session_id = session_data["session_id"]
            print(f"Response: {json.dumps(session_data, indent=2)}")
            
            # Check session status
            print(f"\n4. Session Status (ID: {session_id[:8]}...):")
            response = requests.get(f"{base_url}/videos/{session_id}/status")
            print(f"Status: {response.status_code}")
            print(f"Response: {json.dumps(response.json(), indent=2)}")
            
            # Get detailed progress
            print("\n5. Detailed Progress:")
            response = requests.get(f"{base_url}/videos/{session_id}/progress")
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                print(f"Response: {json.dumps(response.json(), indent=2)}")
            else:
                print(f"Response: {response.text}")
        else:
            print(f"Error: {response.text}")
        
        # List sessions
        print("\n6. List Sessions:")
        response = requests.get(f"{base_url}/videos?page=1&page_size=5")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        # System statistics
        print("\n7. System Statistics:")
        response = requests.get(f"{base_url}/system/stats")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to API server.")
        print("Please start the API server first with: python video_cli.py serve")
    except Exception as e:
        print(f"ERROR: {str(e)}")


def show_integration_examples():
    """Show integration examples for different programming languages."""
    print("=" * 60)
    print("INTEGRATION EXAMPLES")
    print("=" * 60)
    
    print("\n1. Python Integration Example:")
    python_example = '''
import requests
import time

# Start video generation
response = requests.post('http://localhost:8000/videos/generate', json={
    'prompt': 'Create a video about climate change',
    'duration_preference': 60,
    'style': 'educational',
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
        print("Video downloaded!")
        break
    elif status_data['status'] == 'failed':
        print(f"Generation failed: {status_data['error_message']}")
        break
    
    time.sleep(5)
'''
    print(python_example)
    
    print("\n2. cURL Examples:")
    curl_examples = '''
# Start video generation
curl -X POST "http://localhost:8000/videos/generate" \\
  -H "Content-Type: application/json" \\
  -d '{
    "prompt": "Create a video about sustainable technology",
    "duration_preference": 60,
    "style": "professional",
    "quality": "high"
  }'

# Check status
curl "http://localhost:8000/videos/{session_id}/status"

# Download video
curl -O "http://localhost:8000/videos/{session_id}/download"

# List sessions
curl "http://localhost:8000/videos?page=1&page_size=10"
'''
    print(curl_examples)
    
    print("\n3. CLI Usage Examples:")
    cli_examples = '''
# Generate a video and wait for completion
python video_cli.py generate \\
  --prompt "Create an educational video about renewable energy" \\
  --duration 120 \\
  --style educational \\
  --quality ultra \\
  --wait

# Check status of all sessions
python video_cli.py status --all

# Watch progress in real-time
python video_cli.py status {session_id} --watch

# Start API server
python video_cli.py serve --host 0.0.0.0 --port 8000

# Clean up old sessions
python video_cli.py cleanup --max-age 24
'''
    print(cli_examples)


def main():
    """Main demo function."""
    print("Multi-Agent Video System - CLI and API Demo")
    print("=" * 60)
    
    if len(sys.argv) > 1:
        demo_type = sys.argv[1].lower()
        
        if demo_type == "cli":
            demo_cli_interface()
        elif demo_type == "api":
            demo_api_interface()
        elif demo_type == "examples":
            show_integration_examples()
        else:
            print(f"Unknown demo type: {demo_type}")
            print("Usage: python demo_cli_api.py [cli|api|examples]")
    else:
        # Run all demos
        demo_cli_interface()
        print("\n" + "=" * 60)
        print("To test the API, start the server first:")
        print("python video_cli.py serve")
        print("Then run: python demo_cli_api.py api")
        print("=" * 60)
        show_integration_examples()


if __name__ == "__main__":
    main()
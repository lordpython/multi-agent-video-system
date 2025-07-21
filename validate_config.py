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

"""Simple configuration validation script for the multi-agent video system."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from video_system.shared_libraries.config_manager import (
        get_config_manager,
        validate_system_configuration
    )
except ImportError as e:
    print(f"❌ Failed to import configuration manager: {e}")
    print("Make sure you have installed the required dependencies:")
    print("  pip install -r requirements.txt")
    sys.exit(1)


def main():
    """Main validation function."""
    print("🔍 Multi-Agent Video System Configuration Validation")
    print("=" * 55)
    
    # Check if .env file exists
    env_file = project_root / ".env"
    if not env_file.exists():
        print("❌ .env file not found")
        print(f"Please create {env_file} from .env.example and configure your settings")
        return 1
    
    try:
        # Load configuration
        print("Loading configuration...")
        config_manager = get_config_manager()
        config = config_manager.config
        
        print("✅ Configuration loaded successfully")
        
        # Validate configuration
        print("\nValidating configuration...")
        issues = validate_system_configuration()
        
        if not issues:
            print("✅ Configuration validation passed!")
            
            # Show summary
            print("\n📋 Configuration Summary:")
            summary = config_manager.get_config_summary()
            
            print(f"  Environment: {summary['environment']}")
            print(f"  Debug Mode: {summary['debug_mode']}")
            
            print("\n  🔑 API Keys:")
            api_keys = summary['api_keys_configured']
            for key, configured in api_keys.items():
                status = "✅" if configured else "❌"
                print(f"    {key}: {status}")
            
            print("\n  ☁️  Google Cloud:")
            gcp = summary['google_cloud']
            print(f"    Use Vertex AI: {gcp['use_vertexai']}")
            print(f"    Project ID: {gcp['project_id'] or 'Not set'}")
            print(f"    Location: {gcp['location']}")
            
            print("\n  🎬 Video Processing:")
            video = summary['video_processing']
            print(f"    FFmpeg Path: {video['ffmpeg_path']}")
            print(f"    Video Quality: {video['video_quality']}")
            print(f"    Resolution: {video['default_resolution']}")
            
            return 0
        else:
            print("❌ Configuration validation failed!")
            print(f"\n{len(issues)} issue(s) found:")
            for i, issue in enumerate(issues, 1):
                print(f"  {i}. {issue}")
            
            print("\n💡 Suggestions:")
            print("  1. Check your .env file and ensure all required values are set")
            print("  2. Verify API keys are valid and have proper permissions")
            print("  3. Ensure FFmpeg is installed and accessible")
            print("  4. Run: python setup_config.py --wizard for guided setup")
            
            return 1
            
    except Exception as e:
        print(f"❌ Configuration validation error: {str(e)}")
        print("\n💡 Troubleshooting:")
        print("  1. Check that your .env file is properly formatted")
        print("  2. Ensure all required dependencies are installed")
        print("  3. Run: python setup_config.py --create-env to recreate .env file")
        return 1


if __name__ == "__main__":
    sys.exit(main())
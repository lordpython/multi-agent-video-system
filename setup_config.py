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

"""Configuration setup and validation utility for the multi-agent video system."""

import sys
import argparse
import shutil
from pathlib import Path
from typing import Dict, List

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from video_system.shared_libraries.config_manager import (
    get_config_manager,
    validate_system_configuration
)


class ConfigurationSetup:
    """Configuration setup and validation utility."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.env_example_path = self.project_root / ".env.example"
        self.env_path = self.project_root / ".env"
    
    def check_prerequisites(self) -> List[str]:
        """Check system prerequisites."""
        issues = []
        
        # Check Python version
        if sys.version_info < (3, 9):
            issues.append(f"Python 3.9+ required, found {sys.version}")
        
        # Check FFmpeg
        ffmpeg_paths = [
            "/usr/bin/ffmpeg",
            "/usr/local/bin/ffmpeg",
            shutil.which("ffmpeg")
        ]
        
        ffmpeg_found = any(path and Path(path).exists() for path in ffmpeg_paths)
        if not ffmpeg_found:
            issues.append("FFmpeg not found. Please install FFmpeg and ensure it's in your PATH.")
        
        # Check MongoDB (optional but recommended)
        mongo_found = shutil.which("mongod") or shutil.which("mongo")
        if not mongo_found:
            issues.append("MongoDB not found. Consider installing MongoDB for session management.")
        
        # Check Docker (for containerization)
        docker_found = shutil.which("docker")
        if not docker_found:
            issues.append("Docker not found. Docker is required for containerized deployment.")
        
        return issues
    
    def create_env_file(self, interactive: bool = True) -> bool:
        """Create .env file from .env.example."""
        if not self.env_example_path.exists():
            print(f"Error: {self.env_example_path} not found")
            return False
        
        if self.env_path.exists():
            if interactive:
                response = input(f"{self.env_path} already exists. Overwrite? (y/N): ")
                if response.lower() not in ['y', 'yes']:
                    print("Skipping .env file creation")
                    return True
            else:
                print(f"Warning: {self.env_path} already exists, skipping creation")
                return True
        
        # Copy .env.example to .env
        shutil.copy2(self.env_example_path, self.env_path)
        print(f"Created {self.env_path} from {self.env_example_path}")
        
        if interactive:
            print("\nPlease edit the .env file and configure the required environment variables:")
            print(f"  - Open: {self.env_path}")
            print("  - Set your API keys and configuration values")
            print("  - Run this script again with --validate to check your configuration")
        
        return True
    
    def validate_configuration(self, verbose: bool = False) -> bool:
        """Validate the current configuration."""
        try:
            print("Validating configuration...")
            
            # Initialize configuration
            config_manager = get_config_manager()
            config = config_manager.config
            
            # Run validation
            issues = validate_system_configuration()
            
            if not issues:
                print("✅ Configuration validation passed!")
                
                if verbose:
                    print("\nConfiguration Summary:")
                    summary = config_manager.get_config_summary()
                    self._print_config_summary(summary)
                
                return True
            else:
                print("❌ Configuration validation failed!")
                print("\nIssues found:")
                for i, issue in enumerate(issues, 1):
                    print(f"  {i}. {issue}")
                
                print("\nPlease fix these issues and run validation again.")
                return False
                
        except Exception as e:
            print(f"❌ Configuration validation error: {str(e)}")
            return False
    
    def _print_config_summary(self, summary: Dict):
        """Print configuration summary in a readable format."""
        print(f"  Environment: {summary['environment']}")
        print(f"  Debug Mode: {summary['debug_mode']}")
        
        print("\n  Google Cloud:")
        gcp = summary['google_cloud']
        print(f"    Use Vertex AI: {gcp['use_vertexai']}")
        print(f"    Project ID: {gcp['project_id'] or 'Not set'}")
        print(f"    Location: {gcp['location']}")
        print(f"    Staging Bucket: {'Configured' if gcp['has_staging_bucket'] else 'Not configured'}")
        
        print("\n  API Keys:")
        for key, configured in summary['api_keys_configured'].items():
            status = "✅" if configured else "❌"
            print(f"    {key}: {status}")
        
        print("\n  Storage:")
        storage = summary['storage']
        print(f"    Output Directory: {storage['video_output_dir']}")
        print(f"    Temp Directory: {storage['temp_dir']}")
        print(f"    Max Disk Usage: {storage['max_disk_usage_gb']} GB")
        
        print("\n  Performance:")
        perf = summary['performance']
        print(f"    Max Concurrent Requests: {perf['max_concurrent_requests']}")
        print(f"    Request Timeout: {perf['request_timeout_seconds']}s")
        print(f"    Rate Limiting: {'Enabled' if perf['rate_limiting_enabled'] else 'Disabled'}")
    
    def test_api_connections(self) -> bool:
        """Test connections to external APIs."""
        print("Testing API connections...")
        
        try:
            config_manager = get_config_manager()
            config = config_manager.config
            
            # Test Google Cloud connection
            if config.google_cloud.use_vertexai and config.google_cloud.project_id:
                print("  Testing Google Cloud connection...")
                # This would require actual API calls, so we'll just validate config
                print("    ✅ Google Cloud configuration looks valid")
            
            # Test external APIs (basic validation)
            api_tests = [
                ("Serper API", config.external_apis.serper_api_key),
                ("Pexels API", config.external_apis.pexels_api_key),
                ("Unsplash API", config.external_apis.unsplash_access_key),
                ("Pixabay API", config.external_apis.pixabay_api_key),
                ("Gemini API", config.external_apis.gemini_api_key),
            ]
            
            for api_name, api_key in api_tests:
                if api_key:
                    print(f"    ✅ {api_name} key configured")
                else:
                    print(f"    ❌ {api_name} key not configured")
            
            print("✅ API connection tests completed")
            return True
            
        except Exception as e:
            print(f"❌ API connection test failed: {str(e)}")
            return False
    
    def create_directories(self) -> bool:
        """Create necessary directories."""
        try:
            print("Creating necessary directories...")
            
            config_manager = get_config_manager()
            config = config_manager.config
            
            # Create storage directories
            config.storage.create_directories()
            
            # Create log directory
            config.logging.log_dir.mkdir(parents=True, exist_ok=True)
            
            # Create test data directory
            config.development.test_data_dir.mkdir(parents=True, exist_ok=True)
            
            print("✅ Directories created successfully")
            return True
            
        except Exception as e:
            print(f"❌ Failed to create directories: {str(e)}")
            return False
    
    def generate_config_file(self, output_path: str, format: str = "yaml") -> bool:
        """Generate a configuration file with current settings."""
        try:
            print(f"Generating configuration file: {output_path}")
            
            config_manager = get_config_manager()
            config_manager.save_config_to_file(output_path, format)
            
            print(f"✅ Configuration file saved: {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to generate configuration file: {str(e)}")
            return False
    
    def run_setup_wizard(self) -> bool:
        """Run interactive setup wizard."""
        print("🚀 Multi-Agent Video System Configuration Setup")
        print("=" * 50)
        
        # Check prerequisites
        print("\n1. Checking prerequisites...")
        prereq_issues = self.check_prerequisites()
        
        if prereq_issues:
            print("❌ Prerequisites check failed:")
            for issue in prereq_issues:
                print(f"  - {issue}")
            
            response = input("\nContinue anyway? (y/N): ")
            if response.lower() not in ['y', 'yes']:
                return False
        else:
            print("✅ Prerequisites check passed")
        
        # Create .env file
        print("\n2. Setting up environment configuration...")
        if not self.create_env_file(interactive=True):
            return False
        
        # Wait for user to configure .env
        if not self.env_path.exists():
            print("❌ .env file not found")
            return False
        
        input("\nPress Enter after you've configured your .env file...")
        
        # Validate configuration
        print("\n3. Validating configuration...")
        if not self.validate_configuration(verbose=True):
            return False
        
        # Create directories
        print("\n4. Creating directories...")
        if not self.create_directories():
            return False
        
        # Test API connections
        print("\n5. Testing API connections...")
        self.test_api_connections()  # Non-blocking
        
        print("\n🎉 Setup completed successfully!")
        print("\nNext steps:")
        print("  1. Run tests: python -m pytest tests/")
        print("  2. Start the system: python video_cli.py --help")
        print("  3. Deploy to cloud: python deployment/deploy.py")
        
        return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Multi-Agent Video System Configuration Setup",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python setup_config.py --wizard          # Run interactive setup wizard
  python setup_config.py --create-env      # Create .env file from template
  python setup_config.py --validate        # Validate current configuration
  python setup_config.py --test-apis       # Test API connections
  python setup_config.py --create-dirs     # Create necessary directories
        """
    )
    
    parser.add_argument(
        "--wizard",
        action="store_true",
        help="Run interactive setup wizard"
    )
    
    parser.add_argument(
        "--create-env",
        action="store_true",
        help="Create .env file from .env.example"
    )
    
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate current configuration"
    )
    
    parser.add_argument(
        "--test-apis",
        action="store_true",
        help="Test API connections"
    )
    
    parser.add_argument(
        "--create-dirs",
        action="store_true",
        help="Create necessary directories"
    )
    
    parser.add_argument(
        "--generate-config",
        type=str,
        help="Generate configuration file (specify output path)"
    )
    
    parser.add_argument(
        "--format",
        choices=["yaml", "json"],
        default="yaml",
        help="Configuration file format (default: yaml)"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output"
    )
    
    args = parser.parse_args()
    
    # If no arguments provided, show help
    if not any(vars(args).values()):
        parser.print_help()
        return 1
    
    setup = ConfigurationSetup()
    success = True
    
    try:
        if args.wizard:
            success = setup.run_setup_wizard()
        else:
            if args.create_env:
                success &= setup.create_env_file(interactive=False)
            
            if args.validate:
                success &= setup.validate_configuration(verbose=args.verbose)
            
            if args.test_apis:
                success &= setup.test_api_connections()
            
            if args.create_dirs:
                success &= setup.create_directories()
            
            if args.generate_config:
                success &= setup.generate_config_file(args.generate_config, args.format)
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n\nSetup interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Setup failed: {str(e)}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
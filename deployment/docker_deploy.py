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

"""Docker deployment script for the multi-agent video system following ADK patterns."""

import os
import sys
import subprocess
import argparse
import json
import time
from pathlib import Path
from typing import Dict, List, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from video_system.shared_libraries.config_manager import get_config_manager, validate_system_configuration
from video_system.shared_libraries.logging_config import get_logger


logger = get_logger("docker_deploy")


class DockerDeployment:
    """Docker deployment manager for the video system."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.docker_compose_file = project_root / "docker-compose.yml"
        self.dockerfile = project_root / "Dockerfile"
        self.env_file = project_root / ".env"
    
    def check_prerequisites(self) -> List[str]:
        """Check deployment prerequisites."""
        issues = []
        
        # Check Docker
        try:
            result = subprocess.run(["docker", "--version"], capture_output=True, text=True)
            if result.returncode != 0:
                issues.append("Docker is not installed or not accessible")
            else:
                logger.info(f"Docker version: {result.stdout.strip()}")
        except FileNotFoundError:
            issues.append("Docker is not installed")
        
        # Check Docker Compose
        try:
            result = subprocess.run(["docker", "compose", "version"], capture_output=True, text=True)
            if result.returncode != 0:
                # Try legacy docker-compose
                result = subprocess.run(["docker-compose", "--version"], capture_output=True, text=True)
                if result.returncode != 0:
                    issues.append("Docker Compose is not installed")
                else:
                    logger.info(f"Docker Compose version: {result.stdout.strip()}")
            else:
                logger.info(f"Docker Compose version: {result.stdout.strip()}")
        except FileNotFoundError:
            issues.append("Docker Compose is not installed")
        
        # Check required files
        required_files = [self.dockerfile, self.docker_compose_file]
        for file_path in required_files:
            if not file_path.exists():
                issues.append(f"Required file missing: {file_path}")
        
        # Check .env file
        if not self.env_file.exists():
            issues.append(f".env file missing: {self.env_file}")
        
        return issues
    
    def validate_configuration(self) -> bool:
        """Validate system configuration before deployment."""
        try:
            logger.info("Validating configuration...")
            
            # Load and validate configuration
            config_issues = validate_system_configuration()
            
            if config_issues:
                logger.error("Configuration validation failed:")
                for issue in config_issues:
                    logger.error(f"  - {issue}")
                return False
            
            logger.info("Configuration validation passed")
            return True
            
        except Exception as e:
            logger.error(f"Configuration validation error: {str(e)}")
            return False
    
    def build_image(self, tag: str = "multi-agent-video-system:latest", no_cache: bool = False) -> bool:
        """Build Docker image."""
        try:
            logger.info(f"Building Docker image: {tag}")
            
            cmd = ["docker", "build", "-t", tag]
            if no_cache:
                cmd.append("--no-cache")
            cmd.extend(["-f", str(self.dockerfile), str(self.project_root)])
            
            result = subprocess.run(cmd, cwd=self.project_root)
            
            if result.returncode == 0:
                logger.info(f"Successfully built image: {tag}")
                return True
            else:
                logger.error(f"Failed to build image: {tag}")
                return False
                
        except Exception as e:
            logger.error(f"Error building image: {str(e)}")
            return False
    
    def start_services(self, profiles: Optional[List[str]] = None, detached: bool = True) -> bool:
        """Start Docker Compose services."""
        try:
            logger.info("Starting Docker Compose services...")
            
            cmd = ["docker", "compose", "-f", str(self.docker_compose_file)]
            
            if profiles:
                for profile in profiles:
                    cmd.extend(["--profile", profile])
            
            cmd.append("up")
            
            if detached:
                cmd.append("-d")
            
            result = subprocess.run(cmd, cwd=self.project_root)
            
            if result.returncode == 0:
                logger.info("Successfully started services")
                return True
            else:
                logger.error("Failed to start services")
                return False
                
        except Exception as e:
            logger.error(f"Error starting services: {str(e)}")
            return False
    
    def stop_services(self) -> bool:
        """Stop Docker Compose services."""
        try:
            logger.info("Stopping Docker Compose services...")
            
            cmd = ["docker", "compose", "-f", str(self.docker_compose_file), "down"]
            result = subprocess.run(cmd, cwd=self.project_root)
            
            if result.returncode == 0:
                logger.info("Successfully stopped services")
                return True
            else:
                logger.error("Failed to stop services")
                return False
                
        except Exception as e:
            logger.error(f"Error stopping services: {str(e)}")
            return False
    
    def get_service_status(self) -> Dict[str, str]:
        """Get status of Docker Compose services."""
        try:
            cmd = ["docker", "compose", "-f", str(self.docker_compose_file), "ps", "--format", "json"]
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)
            
            if result.returncode == 0:
                services = {}
                for line in result.stdout.strip().split('\n'):
                    if line:
                        service_info = json.loads(line)
                        services[service_info['Service']] = service_info['State']
                return services
            else:
                logger.error("Failed to get service status")
                return {}
                
        except Exception as e:
            logger.error(f"Error getting service status: {str(e)}")
            return {}
    
    def wait_for_services(self, timeout: int = 120) -> bool:
        """Wait for services to be healthy."""
        logger.info("Waiting for services to be healthy...")
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = self.get_service_status()
            
            if not status:
                time.sleep(5)
                continue
            
            # Check if all services are running
            all_running = all(state == "running" for state in status.values())
            
            if all_running:
                logger.info("All services are running")
                
                # Additional health check for video-system service
                if self._check_video_system_health():
                    logger.info("Video system is healthy")
                    return True
            
            logger.info(f"Services status: {status}")
            time.sleep(10)
        
        logger.error(f"Services did not become healthy within {timeout} seconds")
        return False
    
    def _check_video_system_health(self) -> bool:
        """Check if the video system service is healthy."""
        try:
            cmd = ["docker", "compose", "-f", str(self.docker_compose_file), "exec", "-T", "video-system", 
                   "python", "-c", "from video_system.shared_libraries.config_manager import validate_system_configuration; exit(0 if not validate_system_configuration() else 1)"]
            
            result = subprocess.run(cmd, capture_output=True, cwd=self.project_root)
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"Error checking video system health: {str(e)}")
            return False
    
    def show_logs(self, service: Optional[str] = None, follow: bool = False, tail: int = 100) -> bool:
        """Show service logs."""
        try:
            cmd = ["docker", "compose", "-f", str(self.docker_compose_file), "logs"]
            
            if follow:
                cmd.append("-f")
            
            cmd.extend(["--tail", str(tail)])
            
            if service:
                cmd.append(service)
            
            result = subprocess.run(cmd, cwd=self.project_root)
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"Error showing logs: {str(e)}")
            return False
    
    def cleanup(self, volumes: bool = False, images: bool = False) -> bool:
        """Clean up Docker resources."""
        try:
            logger.info("Cleaning up Docker resources...")
            
            # Stop and remove containers
            cmd = ["docker", "compose", "-f", str(self.docker_compose_file), "down"]
            
            if volumes:
                cmd.append("-v")
                logger.info("Removing volumes...")
            
            result = subprocess.run(cmd, cwd=self.project_root)
            
            if result.returncode != 0:
                logger.error("Failed to stop and remove containers")
                return False
            
            # Remove images if requested
            if images:
                logger.info("Removing images...")
                cmd = ["docker", "image", "rm", "multi-agent-video-system:latest"]
                subprocess.run(cmd, cwd=self.project_root)  # Don't fail if image doesn't exist
            
            logger.info("Cleanup completed")
            return True
            
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
            return False
    
    def deploy(self, profiles: Optional[List[str]] = None, build: bool = True, wait: bool = True) -> bool:
        """Full deployment process."""
        logger.info("Starting deployment process...")
        
        # Check prerequisites
        prereq_issues = self.check_prerequisites()
        if prereq_issues:
            logger.error("Prerequisites check failed:")
            for issue in prereq_issues:
                logger.error(f"  - {issue}")
            return False
        
        # Validate configuration
        if not self.validate_configuration():
            return False
        
        # Build image if requested
        if build:
            if not self.build_image():
                return False
        
        # Start services
        if not self.start_services(profiles=profiles):
            return False
        
        # Wait for services to be healthy
        if wait:
            if not self.wait_for_services():
                logger.error("Services failed to become healthy")
                return False
        
        logger.info("Deployment completed successfully!")
        
        # Show service status
        status = self.get_service_status()
        logger.info("Service status:")
        for service, state in status.items():
            logger.info(f"  {service}: {state}")
        
        return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Docker deployment for Multi-Agent Video System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python docker_deploy.py --deploy                    # Full deployment
  python docker_deploy.py --build                     # Build image only
  python docker_deploy.py --start                     # Start services
  python docker_deploy.py --stop                      # Stop services
  python docker_deploy.py --status                    # Show service status
  python docker_deploy.py --logs video-system         # Show logs for specific service
  python docker_deploy.py --cleanup --volumes         # Clean up including volumes
        """
    )
    
    parser.add_argument("--deploy", action="store_true", help="Full deployment process")
    parser.add_argument("--build", action="store_true", help="Build Docker image")
    parser.add_argument("--start", action="store_true", help="Start services")
    parser.add_argument("--stop", action="store_true", help="Stop services")
    parser.add_argument("--status", action="store_true", help="Show service status")
    parser.add_argument("--logs", type=str, help="Show logs for service")
    parser.add_argument("--cleanup", action="store_true", help="Clean up resources")
    
    parser.add_argument("--profiles", nargs="+", help="Docker Compose profiles to use")
    parser.add_argument("--no-cache", action="store_true", help="Build without cache")
    parser.add_argument("--no-build", action="store_true", help="Skip building image")
    parser.add_argument("--no-wait", action="store_true", help="Don't wait for services")
    parser.add_argument("--volumes", action="store_true", help="Remove volumes during cleanup")
    parser.add_argument("--images", action="store_true", help="Remove images during cleanup")
    parser.add_argument("--follow", action="store_true", help="Follow logs")
    parser.add_argument("--tail", type=int, default=100, help="Number of log lines to show")
    
    args = parser.parse_args()
    
    # If no arguments provided, show help
    if not any(vars(args).values()):
        parser.print_help()
        return 1
    
    deployment = DockerDeployment(project_root)
    success = True
    
    try:
        if args.deploy:
            success = deployment.deploy(
                profiles=args.profiles,
                build=not args.no_build,
                wait=not args.no_wait
            )
        else:
            if args.build:
                success &= deployment.build_image(no_cache=args.no_cache)
            
            if args.start:
                success &= deployment.start_services(profiles=args.profiles)
            
            if args.stop:
                success &= deployment.stop_services()
            
            if args.status:
                status = deployment.get_service_status()
                print("Service Status:")
                for service, state in status.items():
                    print(f"  {service}: {state}")
            
            if args.logs:
                success &= deployment.show_logs(
                    service=args.logs,
                    follow=args.follow,
                    tail=args.tail
                )
            
            if args.cleanup:
                success &= deployment.cleanup(
                    volumes=args.volumes,
                    images=args.images
                )
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\nDeployment interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Deployment failed: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
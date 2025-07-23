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

"""System initialization script for the multi-agent video system with comprehensive error handling."""

import sys
import signal
import atexit
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from video_system.shared_libraries import (
    log_system_shutdown,
    get_health_monitor,
    get_logger,
)
from video_system.agent import initialize_video_system


def signal_handler(signum, frame):
    """Handle system signals for graceful shutdown."""
    logger = get_logger("system")
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")

    # Stop health monitoring
    health_monitor = get_health_monitor()
    health_monitor.stop_monitoring()

    # Log system shutdown
    log_system_shutdown()

    sys.exit(0)


def main():
    """Main initialization function."""
    print("Initializing Multi-Agent Video System...")

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Register cleanup function
    atexit.register(log_system_shutdown)

    try:
        # Initialize the video system
        initialize_video_system()

        logger = get_logger("system")
        logger.info("Multi-Agent Video System initialized successfully")

        # Get system status
        health_monitor = get_health_monitor()
        system_status = health_monitor.get_system_status()

        print("\n" + "=" * 60)
        print("MULTI-AGENT VIDEO SYSTEM STATUS")
        print("=" * 60)
        print(
            f"Overall Health: {'✓ HEALTHY' if system_status['overall_healthy'] else '✗ UNHEALTHY'}"
        )
        print(f"Timestamp: {system_status['timestamp']}")
        print(f"Degradation Level: {system_status['degradation_level']}")

        # Display service health
        print("\nService Health:")
        for service_name, health in system_status.get("service_health", {}).items():
            status_icon = (
                "✓"
                if health["status"] == "healthy"
                else "⚠"
                if health["status"] == "degraded"
                else "✗"
            )
            print(f"  {status_icon} {service_name}: {health['status'].upper()}")

        # Display resource status
        resource_status = system_status.get("resource_status", {})
        if resource_status:
            print("\nResource Status:")
            metrics = resource_status.get("metrics", {})
            if metrics:
                print(f"  CPU: {metrics.get('cpu_percent', 0):.1f}%")
                print(f"  Memory: {metrics.get('memory_percent', 0):.1f}%")
                print(f"  Disk: {metrics.get('disk_percent', 0):.1f}%")
                print(
                    f"  Available Memory: {metrics.get('available_memory_gb', 0):.1f} GB"
                )

        # Display quality settings
        quality_settings = system_status.get("quality_settings", {})
        if quality_settings:
            print("\nCurrent Quality Settings:")
            print(
                f"  Video Quality: {quality_settings.get('video_quality', 'unknown')}"
            )
            print(
                f"  Audio Quality: {quality_settings.get('audio_quality', 'unknown')}"
            )
            print(f"  Max Duration: {quality_settings.get('max_duration', 0)}s")

        print("=" * 60)
        print("System is ready for video generation requests.")
        print("Use the ADK CLI or API endpoints to interact with the system.")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"Failed to initialize system: {str(e)}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

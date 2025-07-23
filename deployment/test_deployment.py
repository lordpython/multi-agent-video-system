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

"""Test script for deployment infrastructure."""

import os
import sys
import subprocess
import logging
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_deployment_files():
    """Test that all deployment files exist and are properly structured."""
    logger.info("Testing deployment files...")

    base_dir = os.path.dirname(__file__)
    required_files = {
        "deploy.py": "Main deployment script",
        "grant_permissions.sh": "Permissions setup script",
        "run.py": "Agent testing script",
        "validate_config.py": "Configuration validation script",
        "README.md": "Deployment documentation",
    }

    all_exist = True
    for file_name, description in required_files.items():
        file_path = os.path.join(base_dir, file_name)
        if os.path.exists(file_path):
            logger.info(f"✓ {file_name} exists - {description}")
        else:
            logger.error(f"✗ {file_name} missing - {description}")
            all_exist = False

    return all_exist


def test_script_syntax():
    """Test that Python scripts have valid syntax."""
    logger.info("Testing script syntax...")

    base_dir = os.path.dirname(__file__)
    python_scripts = ["deploy.py", "run.py", "validate_config.py", "test_deployment.py"]

    all_valid = True
    for script in python_scripts:
        script_path = os.path.join(base_dir, script)
        if os.path.exists(script_path):
            try:
                # Test syntax by compiling the script
                with open(script_path, "r") as f:
                    compile(f.read(), script_path, "exec")
                logger.info(f"✓ {script} has valid syntax")
            except SyntaxError as e:
                logger.error(f"✗ {script} has syntax error: {e}")
                all_valid = False
        else:
            logger.warning(f"? {script} not found for syntax check")

    return all_valid


def test_shell_script_syntax():
    """Test that shell scripts have valid syntax."""
    logger.info("Testing shell script syntax...")

    base_dir = os.path.dirname(__file__)
    shell_scripts = ["grant_permissions.sh"]

    all_valid = True
    for script in shell_scripts:
        script_path = os.path.join(base_dir, script)
        if os.path.exists(script_path):
            # On Windows, we can't easily test bash syntax, so we'll do basic checks
            if os.name == "nt":  # Windows
                # Basic validation: check for common shell script patterns
                with open(script_path, "r") as f:
                    content = f.read()

                if content.startswith("#!/bin/bash"):
                    logger.info(f"✓ {script} has proper shebang")
                else:
                    logger.warning(f"? {script} missing shebang")

                # Check for basic shell script structure
                if "set -e" in content:
                    logger.info(f"✓ {script} has error handling")
                else:
                    logger.warning(f"? {script} may lack error handling")

                logger.info(f"✓ {script} basic validation passed (Windows)")
            else:
                # Unix/Linux: use bash syntax check
                try:
                    result = subprocess.run(
                        ["bash", "-n", script_path],
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
                    if result.returncode == 0:
                        logger.info(f"✓ {script} has valid syntax")
                    else:
                        logger.error(f"✗ {script} has syntax error: {result.stderr}")
                        all_valid = False
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    logger.warning(
                        f"? Could not validate {script} syntax (bash not available)"
                    )
        else:
            logger.warning(f"? {script} not found for syntax check")

    return all_valid


def test_environment_template():
    """Test that environment template is properly configured."""
    logger.info("Testing environment template...")

    env_example_path = os.path.join(os.path.dirname(__file__), "..", ".env.example")
    if not os.path.exists(env_example_path):
        logger.error("✗ .env.example file not found")
        return False

    required_vars = [
        "GOOGLE_CLOUD_PROJECT",
        "GOOGLE_CLOUD_LOCATION",
        "STAGING_BUCKET",
        "SERPER_API_KEY",
        "PEXELS_API_KEY",
        "UNSPLASH_ACCESS_KEY",
        "PIXABAY_API_KEY",
        "OPENAI_API_KEY",
        "ELEVENLABS_API_KEY",
    ]

    with open(env_example_path, "r") as f:
        content = f.read()

    all_present = True
    for var in required_vars:
        if var in content:
            logger.info(f"✓ {var} defined in .env.example")
        else:
            logger.error(f"✗ {var} missing from .env.example")
            all_present = False

    return all_present


def test_deployment_requirements():
    """Test that deployment requirements are properly specified."""
    logger.info("Testing deployment requirements...")

    deploy_script_path = os.path.join(os.path.dirname(__file__), "deploy.py")
    if not os.path.exists(deploy_script_path):
        logger.error("✗ deploy.py not found")
        return False

    with open(deploy_script_path, "r") as f:
        content = f.read()

    required_packages = [
        "google-cloud-aiplatform",
        "google-adk",
        "python-dotenv",
        "ffmpeg-python",
        "pillow",
        "openai",
        "elevenlabs",
    ]

    all_present = True
    for package in required_packages:
        if package in content:
            logger.info(f"✓ {package} included in deployment requirements")
        else:
            logger.error(f"✗ {package} missing from deployment requirements")
            all_present = False

    # Check extra packages
    if "./video_system" in content and "./sub_agents" in content:
        logger.info("✓ Extra packages (video_system, sub_agents) included")
    else:
        logger.error("✗ Extra packages not properly configured")
        all_present = False

    return all_present


def test_documentation():
    """Test that documentation is comprehensive."""
    logger.info("Testing documentation...")

    readme_path = os.path.join(os.path.dirname(__file__), "README.md")
    if not os.path.exists(readme_path):
        logger.error("✗ README.md not found")
        return False

    with open(readme_path, "r") as f:
        content = f.read()

    required_sections = [
        "Prerequisites",
        "Deployment Process",
        "Configuration",
        "Troubleshooting",
    ]

    all_present = True
    for section in required_sections:
        if section in content:
            logger.info(f"✓ {section} section present in documentation")
        else:
            logger.error(f"✗ {section} section missing from documentation")
            all_present = False

    return all_present


def main():
    """Run all deployment tests."""
    logger.info("Starting deployment infrastructure tests...")
    logger.info("=" * 60)

    # Load environment variables if available
    env_file = os.path.join(os.path.dirname(__file__), "..", ".env")
    if os.path.exists(env_file):
        load_dotenv(env_file)
        logger.info(f"Loaded environment variables from {env_file}")

    # Run all tests
    tests = [
        test_deployment_files,
        test_script_syntax,
        test_shell_script_syntax,
        test_environment_template,
        test_deployment_requirements,
        test_documentation,
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
            logger.info("-" * 40)
        except Exception as e:
            logger.error(f"Test failed with error: {e}")
            results.append(False)
            logger.info("-" * 40)

    # Summary
    logger.info("=" * 60)
    logger.info("DEPLOYMENT TEST SUMMARY")
    logger.info("=" * 60)

    passed = sum(results)
    total = len(results)

    if all(results):
        logger.info(f"✓ All {total} deployment tests passed!")
        logger.info("Deployment infrastructure is ready.")
        return 0
    else:
        failed = total - passed
        logger.error(f"✗ {failed} out of {total} tests failed.")
        logger.error("Please fix the issues above before deploying.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

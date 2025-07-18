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

"""Configuration validation script for deployment."""

import os
import sys
from dotenv import load_dotenv
import subprocess
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def validate_environment_variables():
    """Validate that all required environment variables are set."""
    logger.info("Validating environment variables...")
    
    required_vars = {
        'GOOGLE_CLOUD_PROJECT': 'Google Cloud Project ID',
        'GOOGLE_CLOUD_LOCATION': 'Google Cloud Location (e.g., us-central1)',
        'STAGING_BUCKET': 'Staging bucket for deployment (gs://bucket-name)',
    }
    
    optional_vars = {
        'SERPER_API_KEY': 'Serper API key for web search',
        'PEXELS_API_KEY': 'Pexels API key for stock media',
        'UNSPLASH_ACCESS_KEY': 'Unsplash API key for stock images',
        'PIXABAY_API_KEY': 'Pixabay API key for stock media',
        'OPENAI_API_KEY': 'OpenAI API key for image generation',
        'ELEVENLABS_API_KEY': 'ElevenLabs API key for text-to-speech',
    }
    
    missing_required = []
    missing_optional = []
    
    # Check required variables
    for var, description in required_vars.items():
        value = os.getenv(var)
        if not value:
            missing_required.append(f"{var}: {description}")
        else:
            logger.info(f"✓ {var} is set")
    
    # Check optional variables
    for var, description in optional_vars.items():
        value = os.getenv(var)
        if not value:
            missing_optional.append(f"{var}: {description}")
        else:
            logger.info(f"✓ {var} is set")
    
    if missing_required:
        logger.error("Missing required environment variables:")
        for var in missing_required:
            logger.error(f"  - {var}")
        return False
    
    if missing_optional:
        logger.warning("Missing optional environment variables (some features may not work):")
        for var in missing_optional:
            logger.warning(f"  - {var}")
    
    return True

def validate_staging_bucket():
    """Validate staging bucket format and accessibility."""
    logger.info("Validating staging bucket...")
    
    staging_bucket = os.getenv('STAGING_BUCKET')
    if not staging_bucket:
        logger.error("STAGING_BUCKET not set")
        return False
    
    if not staging_bucket.startswith('gs://'):
        logger.error("STAGING_BUCKET must start with 'gs://'")
        return False
    
    bucket_name = staging_bucket[5:]  # Remove 'gs://'
    if not bucket_name:
        logger.error("STAGING_BUCKET must include a bucket name")
        return False
    
    logger.info(f"✓ Staging bucket format is valid: {staging_bucket}")
    
    # Try to check if bucket is accessible (requires gcloud CLI)
    try:
        result = subprocess.run(
            ['gsutil', 'ls', staging_bucket],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            logger.info("✓ Staging bucket is accessible")
        else:
            logger.warning(f"Could not access staging bucket: {result.stderr}")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        logger.warning("Could not verify bucket accessibility (gsutil not available or timeout)")
    
    return True

def validate_gcloud_auth():
    """Validate Google Cloud authentication."""
    logger.info("Validating Google Cloud authentication...")
    
    try:
        result = subprocess.run(
            ['gcloud', 'auth', 'list', '--filter=status:ACTIVE', '--format=value(account)'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0 and result.stdout.strip():
            active_account = result.stdout.strip()
            logger.info(f"✓ Authenticated with Google Cloud as: {active_account}")
            return True
        else:
            logger.error("No active Google Cloud authentication found")
            logger.error("Please run: gcloud auth application-default login")
            return False
            
    except (subprocess.TimeoutExpired, FileNotFoundError):
        logger.error("gcloud CLI not found or not responding")
        logger.error("Please install Google Cloud CLI and authenticate")
        return False

def validate_project_access():
    """Validate access to the specified Google Cloud project."""
    logger.info("Validating project access...")
    
    project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
    if not project_id:
        logger.error("GOOGLE_CLOUD_PROJECT not set")
        return False
    
    try:
        result = subprocess.run(
            ['gcloud', 'projects', 'describe', project_id],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            logger.info(f"✓ Project {project_id} is accessible")
            return True
        else:
            logger.error(f"Cannot access project {project_id}: {result.stderr}")
            return False
            
    except (subprocess.TimeoutExpired, FileNotFoundError):
        logger.error("Could not validate project access (gcloud CLI issue)")
        return False

def validate_required_apis():
    """Validate that required APIs are enabled."""
    logger.info("Validating required APIs...")
    
    project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
    if not project_id:
        return False
    
    required_apis = [
        'aiplatform.googleapis.com',
        'storage.googleapis.com',
        'logging.googleapis.com',
    ]
    
    all_enabled = True
    
    for api in required_apis:
        try:
            result = subprocess.run(
                ['gcloud', 'services', 'list', '--enabled', f'--filter=name:{api}', '--format=value(name)'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and api in result.stdout:
                logger.info(f"✓ API {api} is enabled")
            else:
                logger.error(f"API {api} is not enabled")
                logger.error(f"Enable it with: gcloud services enable {api}")
                all_enabled = False
                
        except (subprocess.TimeoutExpired, FileNotFoundError):
            logger.warning(f"Could not verify API {api} status")
    
    return all_enabled

def validate_deployment_files():
    """Validate that all deployment files exist and are properly configured."""
    logger.info("Validating deployment files...")
    
    base_dir = os.path.dirname(__file__)
    required_files = [
        'deploy.py',
        'grant_permissions.sh',
        'run.py'
    ]
    
    all_exist = True
    
    for file_name in required_files:
        file_path = os.path.join(base_dir, file_name)
        if os.path.exists(file_path):
            logger.info(f"✓ {file_name} exists")
            
            # Check if shell script is executable
            if file_name.endswith('.sh') and os.name != 'nt':
                if os.access(file_path, os.X_OK):
                    logger.info(f"✓ {file_name} is executable")
                else:
                    logger.warning(f"{file_name} is not executable, run: chmod +x {file_path}")
        else:
            logger.error(f"Required file {file_name} not found")
            all_exist = False
    
    return all_exist

def main():
    """Main validation function."""
    logger.info("Starting deployment configuration validation...")
    
    # Load environment variables
    env_file = os.path.join(os.path.dirname(__file__), '..', '.env')
    if os.path.exists(env_file):
        load_dotenv(env_file)
        logger.info(f"Loaded environment variables from {env_file}")
    else:
        logger.warning("No .env file found, using system environment variables")
    
    # Run all validations
    validations = [
        validate_environment_variables,
        validate_staging_bucket,
        validate_gcloud_auth,
        validate_project_access,
        validate_required_apis,
        validate_deployment_files,
    ]
    
    results = []
    for validation in validations:
        try:
            result = validation()
            results.append(result)
        except Exception as e:
            logger.error(f"Validation failed with error: {e}")
            results.append(False)
    
    # Summary
    logger.info("\n" + "="*50)
    logger.info("VALIDATION SUMMARY")
    logger.info("="*50)
    
    if all(results):
        logger.info("✓ All validations passed! Ready for deployment.")
        return 0
    else:
        failed_count = len([r for r in results if not r])
        logger.error(f"✗ {failed_count} validation(s) failed. Please fix the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
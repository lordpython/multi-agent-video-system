# Deployment Guide

This directory contains the deployment infrastructure for the Multi-Agent Video System, following Google ADK (Agent Development Kit) patterns.

## Overview

The deployment infrastructure consists of:

- **deploy.py**: Main deployment script for Vertex AI Agent Engine
- **grant_permissions.sh**: Script to set up necessary IAM permissions
- **run.py**: Script to test the deployed agent
- **validate_config.py**: Configuration validation script
- **README.md**: This documentation

## Prerequisites

### 1. Google Cloud Setup

1. **Google Cloud Project**: You need an active Google Cloud project
2. **Authentication**: Set up authentication using one of these methods:
   ```bash
   # Option 1: Application Default Credentials (recommended)
   gcloud auth application-default login
   
   # Option 2: Service Account Key (for production)
   export GOOGLE_APPLICATION_CREDENTIALS="path/to/service-account-key.json"
   ```

3. **Required APIs**: Enable the following APIs in your project:
   ```bash
   gcloud services enable aiplatform.googleapis.com
   gcloud services enable storage.googleapis.com
   gcloud services enable logging.googleapis.com
   ```

### 2. Environment Configuration

1. **Copy Environment File**:
   ```bash
   cp ../.env.example ../.env
   ```

2. **Configure Required Variables**:
   ```bash
   # Required for deployment
   GOOGLE_CLOUD_PROJECT=your-project-id
   GOOGLE_CLOUD_LOCATION=us-central1
   STAGING_BUCKET=gs://your-staging-bucket
   
   # Required for video generation functionality
   SERPER_API_KEY=your-serper-key
   PEXELS_API_KEY=your-pexels-key
   UNSPLASH_ACCESS_KEY=your-unsplash-key
   PIXABAY_API_KEY=your-pixabay-key
   OPENAI_API_KEY=your-openai-key
   ELEVENLABS_API_KEY=your-elevenlabs-key
   ```

### 3. Staging Bucket Setup

Create a Google Cloud Storage bucket for deployment staging:

```bash
# Create the bucket
gsutil mb gs://your-staging-bucket

# Set appropriate permissions
gsutil iam ch serviceAccount:service-PROJECT_NUMBER@gcp-sa-aiplatform-re.iam.gserviceaccount.com:objectAdmin gs://your-staging-bucket
```

## Deployment Process

### Step 1: Validate Configuration

Before deploying, validate your configuration:

```bash
python validate_config.py
```

This script will check:
- Environment variables
- Google Cloud authentication
- Project access
- Required APIs
- Staging bucket accessibility
- Deployment files

### Step 2: Deploy the Agent

Deploy the agent to Vertex AI Agent Engine:

```bash
python deploy.py
```

This script will:
- Initialize Vertex AI with your project settings
- Create an ADK app with the root agent
- Deploy to Vertex AI Agent Engine
- Update your `.env` file with the agent engine ID

### Step 3: Grant Permissions

Set up necessary IAM permissions:

```bash
chmod +x grant_permissions.sh
./grant_permissions.sh
```

This script will:
- Create a custom IAM role with required permissions
- Grant the role to the AI Platform Reasoning Engine Service Agent
- Enable necessary service identities

### Step 4: Test the Deployment

Test the deployed agent:

```bash
python run.py
```

This script will:
- Connect to your deployed agent
- Send test queries about video generation
- Display the agent's responses

## Configuration Details

### Environment Variables

#### Required Variables
- `GOOGLE_CLOUD_PROJECT`: Your Google Cloud project ID
- `GOOGLE_CLOUD_LOCATION`: Deployment region (e.g., us-central1)
- `STAGING_BUCKET`: GCS bucket for deployment artifacts (gs://bucket-name)

#### API Keys (Required for full functionality)
- `SERPER_API_KEY`: For web search functionality
- `PEXELS_API_KEY`: For stock photo/video sourcing
- `UNSPLASH_ACCESS_KEY`: For high-quality stock images
- `PIXABAY_API_KEY`: For additional stock media
- `OPENAI_API_KEY`: For AI image generation (DALL-E)
- `ELEVENLABS_API_KEY`: For text-to-speech synthesis

#### Optional Variables
- `AGENT_ENGINE_ID`: Auto-populated after deployment
- `MONGODB_CONNECTION_STRING`: For session persistence
- `FFMPEG_PATH`: Path to FFmpeg binary
- `VIDEO_OUTPUT_DIR`: Directory for video outputs
- `TEMP_DIR`: Temporary files directory

### IAM Permissions

The deployment requires the following permissions:

#### For the Service Account
- `storage.objects.*`: Access to staging bucket
- `aiplatform.endpoints.predict`: AI Platform predictions
- `aiplatform.models.predict`: Model predictions
- `secretmanager.versions.access`: Access to secrets
- `logging.logEntries.create`: Create log entries
- `monitoring.*`: Create monitoring metrics

#### For Your User Account
- `aiplatform.reasoningEngines.create`: Create agent engines
- `iam.roles.create`: Create custom IAM roles
- `iam.serviceAccounts.actAs`: Act as service accounts

## Troubleshooting

### Common Issues

1. **Authentication Errors**
   ```bash
   # Re-authenticate
   gcloud auth application-default login
   
   # Verify authentication
   gcloud auth list
   ```

2. **Permission Denied**
   ```bash
   # Check project permissions
   gcloud projects get-iam-policy PROJECT_ID
   
   # Re-run permission script
   ./grant_permissions.sh
   ```

3. **Staging Bucket Issues**
   ```bash
   # Verify bucket exists and is accessible
   gsutil ls gs://your-staging-bucket
   
   # Check bucket permissions
   gsutil iam get gs://your-staging-bucket
   ```

4. **API Not Enabled**
   ```bash
   # Enable required APIs
   gcloud services enable aiplatform.googleapis.com
   gcloud services enable storage.googleapis.com
   ```

### Validation Failures

If `validate_config.py` reports issues:

1. **Missing Environment Variables**: Update your `.env` file
2. **Authentication Issues**: Run `gcloud auth application-default login`
3. **Project Access**: Verify project ID and permissions
4. **API Issues**: Enable required APIs using `gcloud services enable`
5. **Bucket Issues**: Create bucket or fix permissions

### Deployment Failures

If deployment fails:

1. **Check Logs**: Look for error messages in the deployment output
2. **Verify Dependencies**: Ensure all required packages are available
3. **Resource Limits**: Check if you've hit any quotas or limits
4. **Network Issues**: Verify internet connectivity and firewall settings

## Monitoring and Maintenance

### Monitoring Deployment

After deployment, monitor your agent:

1. **Vertex AI Console**: Check agent status in the Google Cloud Console
2. **Logs**: View logs in Cloud Logging
3. **Metrics**: Monitor performance in Cloud Monitoring

### Updating the Agent

To update the deployed agent:

1. Make changes to your agent code
2. Re-run the deployment script:
   ```bash
   python deploy.py
   ```

### Cleanup

To remove the deployed agent:

```bash
# Delete the agent engine (replace with your actual resource name)
gcloud ai reasoning-engines delete AGENT_ENGINE_ID --region=LOCATION
```

## Security Considerations

1. **API Keys**: Store sensitive API keys in Google Secret Manager
2. **IAM**: Follow principle of least privilege for permissions
3. **Network**: Consider VPC and firewall rules for production
4. **Audit**: Enable audit logging for compliance

## Support

For issues with:
- **ADK Framework**: Check [ADK Documentation](https://google.github.io/adk-docs/)
- **Vertex AI**: Check [Vertex AI Documentation](https://cloud.google.com/vertex-ai/docs)
- **This Project**: Check the main README.md or create an issue
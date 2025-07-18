#!/bin/bash
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

# Script to grant necessary permissions for the Multi-Agent Video System

set -e

# Load environment variables from .env file
SCRIPT_DIR="$(dirname "$0")"
ENV_FILE="${SCRIPT_DIR}/../.env"
if [ -f "$ENV_FILE" ]; then
  source "$ENV_FILE"
else
  echo "Error: .env file not found at $ENV_FILE"
  exit 1
fi

# Get the project ID from environment variable
PROJECT_ID="$GOOGLE_CLOUD_PROJECT"
if [ -z "$PROJECT_ID" ]; then
  echo "No project ID found. Please set your project ID with 'gcloud config set project YOUR_PROJECT_ID'"
  exit 1
fi

# Get the project number
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")
if [ -z "$PROJECT_NUMBER" ]; then
  echo "Failed to retrieve project number for project $PROJECT_ID"
  exit 1
fi

# Define the service account
SERVICE_ACCOUNT="service-${PROJECT_NUMBER}@gcp-sa-aiplatform-re.iam.gserviceaccount.com"

echo "Granting permissions to $SERVICE_ACCOUNT..."

# Ensure the AI Platform service identity exists
gcloud alpha services identity create --service=aiplatform.googleapis.com --project="$PROJECT_ID"

# Create a custom role with necessary permissions for video generation
ROLE_ID="videoSystemRole"
ROLE_TITLE="Video System Role"
ROLE_DESCRIPTION="Custom role with permissions for multi-agent video system"

# Check if the custom role already exists
echo "Checking if custom role $ROLE_ID exists..."
if gcloud iam roles describe "$ROLE_ID" --project="$PROJECT_ID" &>/dev/null; then
  echo "Custom role $ROLE_ID already exists."
else
  echo "Custom role $ROLE_ID does not exist. Creating it..."
  gcloud iam roles create "$ROLE_ID" \
    --project="$PROJECT_ID" \
    --title="$ROLE_TITLE" \
    --description="$ROLE_DESCRIPTION" \
    --permissions="storage.objects.create,storage.objects.delete,storage.objects.get,storage.objects.list,aiplatform.endpoints.predict"
  echo "Custom role $ROLE_ID created successfully."
fi

# Grant the custom role to the service account
echo "Granting custom role for video system permissions..."
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$SERVICE_ACCOUNT" \
  --role="projects/$PROJECT_ID/roles/$ROLE_ID"

echo "Permissions granted successfully."
echo "Service account $SERVICE_ACCOUNT can now access required resources for video generation."
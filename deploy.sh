#!/bin/bash
set -e

# Configuration
SERVICE_NAME="agentic-retail-demo"
REGION="us-central1"

# Check if PROJECT_ID is set
if [ -z "$PROJECT_ID" ]; then
    echo "Error: PROJECT_ID environment variable is not set."
    echo "Please export PROJECT_ID=your-gcp-project-id"
    exit 1
fi

echo "Deploying $SERVICE_NAME to Cloud Run in project $PROJECT_ID..."

# Submit build to Cloud Build (or deploy source directly if preferred, but build is safer for reproducibility)
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME

# Deploy to Cloud Run
gcloud run deploy $SERVICE_NAME \
    --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --set-env-vars PROJECT_ID=$PROJECT_ID,LOCATION=$REGION,GCS_BUCKET_NAME=$GCS_BUCKET_NAME,VEO_MODEL_NAME=veo-001,IMAGEN_MODEL_NAME=imagen-3.0-generate-001

echo "Deployment complete!"

#!/usr/bin/env bash
# rotate_google_api_key.sh
# Usage: ./scripts/rotate_google_api_key.sh NEW_KEY
# Requires gcloud CLI configured with appropriate permissions.

set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 NEW_KEY"
  exit 1
fi

NEW_KEY="$1"

# Create secret in Google Secret Manager and add the key
if ! command -v gcloud >/dev/null 2>&1; then
  echo "gcloud CLI not found. Install and authenticate first."
  exit 2
fi

SECRET_NAME=google-api-key

echo "Creating/updating secret in Google Secret Manager: $SECRET_NAME"
if gcloud secrets describe "$SECRET_NAME" >/dev/null 2>&1; then
  echo "Secret exists — adding new version"
  echo -n "$NEW_KEY" | gcloud secrets versions add "$SECRET_NAME" --data-file=-
else
  echo -n "$NEW_KEY" | gcloud secrets create "$SECRET_NAME" --replication-policy="automatic" --data-file=-
fi

echo "Secret stored. Now revoke any old API key manually via Console or use gcloud services api-keys delete KEY_ID"

echo "Done. Remember to update your CI/CD or deployment to use Secret Manager or repository secrets."

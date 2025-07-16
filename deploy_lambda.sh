#!/bin/bash

# Exit on error
set -e

echo "=== Updating OSCAR Slack Bot Lambda Function ==="

# Create a temporary directory for the Lambda package
echo "Creating Lambda deployment package..."
mkdir -p lambda_package

# Copy the app.py file
echo "Copying app.py..."
cp slack-bot/app.py lambda_package/

# Install dependencies
echo "Installing dependencies..."
pip install -r slack-bot/requirements.txt -t lambda_package/

# Create the zip file
echo "Creating zip file..."
cd lambda_package
zip -r ../lambda_package.zip .
cd ..

# Update the Lambda function
echo "Updating Lambda function..."
aws lambda update-function-code \
  --function-name oscar-slack-bot \
  --zip-file fileb://lambda_package.zip \
  --region us-west-2

# Clean up
echo "Cleaning up..."
rm -rf lambda_package
rm lambda_package.zip

echo "Lambda function updated successfully!"
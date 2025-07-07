#!/bin/bash

# Install serverless framework if not installed
if ! command -v serverless &> /dev/null; then
    echo "Installing Serverless Framework..."
    npm install -g serverless
fi

# Install serverless plugins
npm install serverless-python-requirements

# Deploy to AWS
echo "Deploying OSCAR Slack Bot..."
serverless deploy

echo "Deployment complete! Don't forget to:"
echo "1. Copy the webhook URL from the output"
echo "2. Configure it in your Slack app settings"
echo "3. Add the bot to your Slack workspace"
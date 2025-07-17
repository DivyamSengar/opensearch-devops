#!/bin/bash

# Exit on error
set -e

# Parse command line arguments
ENABLE_DM="false"

while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        --enable-dm)
            ENABLE_DM="true"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--enable-dm]"
            exit 1
            ;;
    esac
done

# Export the ENABLE_DM environment variable
export ENABLE_DM

echo "=== OSCAR Slack Bot Serverless Deployment ==="
echo "DM functionality: $([ "$ENABLE_DM" == "true" ] && echo "enabled" || echo "disabled")"

# Install serverless framework if not installed
if ! command -v serverless &> /dev/null; then
    echo "Installing Serverless Framework..."
    npm install -g serverless
fi

# Install serverless plugins
echo "Installing Serverless plugins..."
npm install serverless-python-requirements

# Run tests before deployment
echo "Running tests..."
if [ -f "slack-bot/tests/run_tests.sh" ]; then
    chmod +x slack-bot/tests/run_tests.sh
    cd slack-bot
    ./tests/run_tests.sh
    TEST_EXIT_CODE=$?
    cd ..
    
    if [ $TEST_EXIT_CODE -ne 0 ]; then
        echo "Warning: Some tests failed, but continuing with deployment."
    fi
else
    echo "Warning: Test script not found, skipping tests"
fi

# Deploy to AWS
echo "Deploying OSCAR Slack Bot..."
serverless deploy

echo "Deployment complete! Don't forget to:"
echo "1. Copy the webhook URL from the output"
echo "2. Configure it in your Slack app settings"
echo "3. Add the bot to your Slack workspace"
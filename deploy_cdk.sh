#!/bin/bash

# Exit on error
set -e

# Display usage information
function show_usage {
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  -a, --account ACCOUNT_ID   AWS Account ID (default: extracted from .env)"
    echo "  -r, --region REGION        AWS Region (default: extracted from .env)"
    echo "  -h, --help                 Show this help message"
    exit 1
}

# Parse command line arguments
AWS_ACCOUNT_ID=""
AWS_REGION=""

while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        -a|--account)
            AWS_ACCOUNT_ID="$2"
            shift 2
            ;;
        -r|--region)
            AWS_REGION="$2"
            shift 2
            ;;
        -h|--help)
            show_usage
            ;;
        *)
            echo "Unknown option: $1"
            show_usage
            ;;
    esac
done

echo "=== OSCAR Slack Bot CDK Deployment ==="

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "AWS CLI is not installed. Please install it first."
    exit 1
fi

# Check if CDK is installed
if ! command -v cdk &> /dev/null; then
    echo "Installing AWS CDK..."
    npm install -g aws-cdk
fi

# If account ID or region not provided, extract from .env file
if [ -z "$AWS_ACCOUNT_ID" ] || [ -z "$AWS_REGION" ]; then
    if [ -f "slack-bot/.env" ]; then
        echo "Reading AWS account and region from .env file..."
        MODEL_ARN=$(grep MODEL_ARN slack-bot/.env | cut -d= -f2)
        
        # Extract account ID and region from MODEL_ARN if not provided as arguments
        if [ -z "$AWS_ACCOUNT_ID" ]; then
            AWS_ACCOUNT_ID=$(echo $MODEL_ARN | sed -n 's/.*:bedrock:\([^:]*\):\([^:]*\):.*/\2/p')
            echo "Using AWS Account ID from .env: $AWS_ACCOUNT_ID"
        fi
        
        if [ -z "$AWS_REGION" ]; then
            AWS_REGION=$(echo $MODEL_ARN | sed -n 's/.*:bedrock:\([^:]*\):.*/\1/p')
            echo "Using AWS Region from .env: $AWS_REGION"
        fi
        
        # Export MODEL_ARN for the stack
        export MODEL_ARN
        
        # Also export KNOWLEDGE_BASE_ID
        export KNOWLEDGE_BASE_ID=$(grep KNOWLEDGE_BASE_ID slack-bot/.env | cut -d= -f2)
        echo "Using Knowledge Base ID: $KNOWLEDGE_BASE_ID"
    else
        echo "Error: .env file not found in slack-bot directory and no account/region provided."
        echo "Please provide AWS account ID and region as command-line arguments or create the .env file."
        exit 1
    fi
else
    echo "Using provided AWS Account ID: $AWS_ACCOUNT_ID"
    echo "Using provided AWS Region: $AWS_REGION"
    
    # Still need to get KNOWLEDGE_BASE_ID from .env
    if [ -f "slack-bot/.env" ]; then
        export KNOWLEDGE_BASE_ID=$(grep KNOWLEDGE_BASE_ID slack-bot/.env | cut -d= -f2)
        export MODEL_ARN=$(grep MODEL_ARN slack-bot/.env | cut -d= -f2)
        echo "Using Knowledge Base ID: $KNOWLEDGE_BASE_ID"
    else
        echo "Warning: .env file not found. KNOWLEDGE_BASE_ID and MODEL_ARN will be set to placeholder values."
        export KNOWLEDGE_BASE_ID="PLACEHOLDER_KNOWLEDGE_BASE_ID"
        export MODEL_ARN="arn:aws:bedrock:$AWS_REGION::foundation-model/anthropic.claude-v2"
    fi
fi

# Validate account ID and region
if [ -z "$AWS_ACCOUNT_ID" ]; then
    echo "Error: AWS Account ID is required. Please provide it as a command-line argument or in the .env file."
    exit 1
fi

if [ -z "$AWS_REGION" ]; then
    echo "Error: AWS Region is required. Please provide it as a command-line argument or in the .env file."
    exit 1
fi

# Export for CDK
export CDK_DEFAULT_ACCOUNT=$AWS_ACCOUNT_ID
export CDK_DEFAULT_REGION=$AWS_REGION

# Update cdk.context.json with the correct region
echo "Updating CDK context with region: $AWS_REGION"
cat > cdk/cdk.context.json << EOF
{
  "aws:cdk:toolkit:default-region": "$AWS_REGION"
}
EOF

# Create virtual environment for CDK
echo "Setting up Python virtual environment..."
python -m venv .venv
source .venv/bin/activate

# Install CDK dependencies
echo "Installing CDK dependencies..."
pip install -r cdk/requirements.txt

# Create build_docs directory if it doesn't exist
echo "Creating build_docs directory..."
mkdir -p build_docs
echo "# Sample Documentation" > build_docs/sample.md
echo "This is a sample document for the knowledge base." >> build_docs/sample.md

# Bootstrap CDK (if not already done)
echo "Bootstrapping CDK environment..."
cd cdk
AWS_REGION=$AWS_REGION AWS_DEFAULT_REGION=$AWS_REGION cdk bootstrap aws://$AWS_ACCOUNT_ID/$AWS_REGION --force

# Deploy the stack
echo "Deploying OSCAR Slack Bot stack..."
AWS_REGION=$AWS_REGION AWS_DEFAULT_REGION=$AWS_REGION cdk deploy --require-approval never

# Get outputs
cd ..
LAMBDA_FUNCTION_NAME=$(AWS_DEFAULT_REGION=$AWS_REGION aws cloudformation describe-stacks --stack-name OscarSlackBotStack --query "Stacks[0].Outputs[?OutputKey=='LambdaFunctionName'].OutputValue" --output text --region $AWS_REGION)
SECRETS_ARN=$(AWS_DEFAULT_REGION=$AWS_REGION aws cloudformation describe-stacks --stack-name OscarSlackBotStack --query "Stacks[0].Outputs[?OutputKey=='SlackSecretsArn'].OutputValue" --output text --region $AWS_REGION)
WEBHOOK_URL=$(AWS_DEFAULT_REGION=$AWS_REGION aws cloudformation describe-stacks --stack-name OscarSlackBotStack --query "Stacks[0].Outputs[?OutputKey=='SlackWebhookUrl'].OutputValue" --output text --region $AWS_REGION)

# Prepare Lambda package
echo "Preparing Lambda package..."
mkdir -p lambda_package
cp slack-bot/app.py lambda_package/
cp slack-bot/requirements.txt lambda_package/

# Modify app.py to use Secrets Manager
echo "Updating app.py to use Secrets Manager..."
cat > lambda_package/secrets_manager_patch.py << 'EOF'
import json
import boto3
from botocore.exceptions import ClientError

# Initialize Secrets Manager client
secrets_client = boto3.client('secretsmanager')

def get_slack_secrets():
    """Get Slack credentials from Secrets Manager"""
    try:
        secret_arn = os.environ.get('SLACK_SECRETS_ARN')
        response = secrets_client.get_secret_value(SecretId=secret_arn)
        secrets = json.loads(response['SecretString'])
        return secrets.get('SLACK_BOT_TOKEN'), secrets.get('SLACK_SIGNING_SECRET')
    except ClientError as e:
        print(f"Error retrieving secrets: {e}")
        raise
EOF

# Prepend the secrets manager code to app.py
cat lambda_package/secrets_manager_patch.py lambda_package/app.py > lambda_package/app.py.new
mv lambda_package/app.py.new lambda_package/app.py

# Replace environment variable initialization in app.py
sed -i.bak 's/# Initialize Slack app/# Get Slack credentials from Secrets Manager\nslack_token, slack_signing_secret = get_slack_secrets()\n\n# Initialize Slack app/g' lambda_package/app.py
sed -i.bak 's/token=os.environ.get("SLACK_BOT_TOKEN")/token=slack_token/g' lambda_package/app.py
sed -i.bak 's/signing_secret=os.environ.get("SLACK_SIGNING_SECRET")/signing_secret=slack_signing_secret/g' lambda_package/app.py

# Install dependencies
echo "Installing Lambda dependencies..."
pip install -r lambda_package/requirements.txt -t lambda_package/

# Create deployment package
echo "Creating Lambda deployment package..."
cd lambda_package
zip -r ../lambda_package.zip .
cd ..

# Update Lambda function code
echo "Updating Lambda function code..."
AWS_DEFAULT_REGION=$AWS_REGION aws lambda update-function-code --function-name $LAMBDA_FUNCTION_NAME --zip-file fileb://lambda_package.zip --region $AWS_REGION

# Update Lambda environment variables
echo "Updating Lambda environment variables..."
AWS_DEFAULT_REGION=$AWS_REGION aws lambda update-function-configuration \
  --function-name $LAMBDA_FUNCTION_NAME \
  --environment "Variables={KNOWLEDGE_BASE_ID=$KNOWLEDGE_BASE_ID,MODEL_ARN=$MODEL_ARN,SLACK_SECRETS_ARN=$SECRETS_ARN}" \
  --region $AWS_REGION

# Clean up
echo "Cleaning up..."
rm -rf lambda_package
rm -f lambda_package.zip

# Update Secrets Manager with Slack credentials if .env exists
if [ -f "slack-bot/.env" ]; then
    echo "Updating Secrets Manager with Slack credentials..."
    SLACK_BOT_TOKEN=$(grep SLACK_BOT_TOKEN slack-bot/.env | cut -d= -f2)
    SLACK_SIGNING_SECRET=$(grep SLACK_SIGNING_SECRET slack-bot/.env | cut -d= -f2)

    AWS_DEFAULT_REGION=$AWS_REGION aws secretsmanager update-secret \
      --secret-id $SECRETS_ARN \
      --secret-string "{\"SLACK_BOT_TOKEN\":\"$SLACK_BOT_TOKEN\",\"SLACK_SIGNING_SECRET\":\"$SLACK_SIGNING_SECRET\"}" \
      --region $AWS_REGION
else
    echo "Warning: .env file not found. Slack credentials not updated in Secrets Manager."
    echo "You will need to manually update the Slack credentials in the AWS Secrets Manager console."
fi

echo "Deployment complete!"
echo ""
echo "=== Configuration Steps ==="
echo "1. Slack secrets have been automatically configured in AWS Secrets Manager"
echo ""
echo "2. Configure Slack App:"
echo "   - Go to https://api.slack.com/apps"
echo "   - Create a new app or update your existing app"
echo "   - Under 'Event Subscriptions', enable events and set the Request URL to: $WEBHOOK_URL"
echo "   - Subscribe to 'app_mention' and 'message.im' events"
echo "   - Under 'OAuth & Permissions', add the required scopes:"
echo "     * app_mentions:read"
echo "     * chat:write"
echo "     * channels:history"
echo "     * im:history"
echo "   - Install the app to your workspace"
echo ""
echo "3. Test your bot by mentioning it in a channel or sending a direct message"

# Deactivate virtual environment
deactivate
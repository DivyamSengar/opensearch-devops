# OSCAR Slack Bot

AI-powered Slack bot with thread-based context and knowledge base integration using Amazon Bedrock.

## Architecture

The OSCAR Slack bot is built using the following components:

- **Slack Bolt Framework**: Handles Slack events and message processing
- **AWS Lambda**: Serverless execution environment
- **DynamoDB**: Session storage for thread context (with TTL)
- **Amazon Bedrock**: Knowledge base queries with context preservation
- **AWS Secrets Manager**: Secure storage for Slack credentials

### Key Components

#### 1. Event Handling
The bot handles two main types of events:
- **Mentions**: When the bot is mentioned in a channel (`@oscar`)
- **Direct Messages**: When users send private messages to the bot

#### 2. Context Management
- **Thread-Based Context**: Messages in the same thread maintain conversation context
- **Session Storage**: Uses DynamoDB to store session IDs and conversation history
- **TTL Mechanism**: Automatically expires old sessions (1 hour) and context (48 hours)

#### 3. Knowledge Base Integration
- **Amazon Bedrock**: Uses Bedrock's RetrieveAndGenerate API for knowledge base queries
- **Context Enhancement**: Includes previous conversation context in queries
- **Prompt Engineering**: Custom prompt templates for optimal responses

#### 4. Deduplication System
- **Multi-Layer Deduplication**: Prevents duplicate responses to the same message
- **Event Fingerprinting**: Creates unique identifiers for each message
- **Response Tracking**: Checks if the bot has already responded to a message

#### 5. Emoji Reactions
- **Visual Feedback**: Adds emoji reactions to acknowledge messages
- **Processing Indicator**: Uses 👀 (eyes) emoji while processing
- **Completion Status**: Uses ✅ (white_check_mark) for success or ❌ (x) for errors

## Code Structure

- **app.py**: Main application code with event handlers and business logic
- **socket_app.py**: Alternative implementation for WebSocket-based deployments
- **requirements.txt**: Python dependencies
- **deploy.sh**: Deployment script for Serverless Framework
- **.env**: Environment variables (not committed to repository)
- **.env.example**: Example environment variables template

## Environment Variables

The following environment variables are required:

```
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
SLACK_SIGNING_SECRET=your-slack-signing-secret
KNOWLEDGE_BASE_ID=your-bedrock-knowledge-base-id
MODEL_ARN=arn:aws:bedrock:region:account:inference-profile/model-id
```

## Deployment (Serverless Framework)

This directory contains a Serverless Framework deployment configuration as an alternative to the CDK deployment.

### Prerequisites

1. Node.js and npm installed
2. Serverless Framework installed (`npm install -g serverless`)
3. AWS credentials configured
4. Slack app created with appropriate permissions

### Deployment Steps

1. Configure environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your values
   ```

2. Deploy using the provided script:
   ```bash
   chmod +x deploy.sh
   ./deploy.sh
   ```

3. Configure Slack app with the webhook URL from the deployment output

### Serverless Configuration

The `serverless.yml` file defines:

- Lambda function configuration
- API Gateway endpoint
- DynamoDB tables
- IAM permissions
- Environment variables

## Usage Examples

### Channel Mentions

Mention the bot in any channel:
```
@oscar What's the status of OpenSearch 2.11?
```

Reply in thread to maintain context:
```
@oscar What about security issues?
```

### Direct Messages

Send a direct message to the bot:
```
What's new in the latest release?
```

## Development

### Local Testing

To test the bot locally:

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Use socket mode for local development:
   ```bash
   python socket_app.py
   ```

### Adding Features

When adding new features:

1. Update the appropriate event handler in app.py
2. Test locally using socket mode
3. Update the deployment configuration if necessary
4. Deploy using either CDK or Serverless Framework

### Updating the Lambda Function

To update just the Lambda function code:

```bash
# Create a deployment package with dependencies
mkdir -p lambda_package
cp app.py lambda_package/
pip install -r requirements.txt -t lambda_package/
cd lambda_package
zip -r ../lambda_package.zip .
cd ..

# Update the Lambda function
aws lambda update-function-code \
  --function-name oscar-slack-bot \
  --zip-file fileb://lambda_package.zip \
  --region us-west-2

# Clean up
rm -rf lambda_package
rm lambda_package.zip
```

## Troubleshooting

### Common Issues

1. **Bot Not Responding**:
   - Check Lambda function logs in CloudWatch
   - Verify Slack event subscription is properly configured
   - Ensure the bot has been invited to the channel
   - Check Secrets Manager for correct Slack credentials

2. **Knowledge Base Issues**:
   - Verify the KNOWLEDGE_BASE_ID environment variable
   - Check Bedrock permissions in IAM
   - Ensure the knowledge base has been properly indexed

3. **Context Not Working**:
   - Check DynamoDB tables for session and context data
   - Verify TTL settings are correct
   - Ensure you're replying in a thread

4. **Emoji Reactions Not Working**:
   - Verify the bot has the `reactions:write` scope
   - Check Lambda function logs for reaction-related errors
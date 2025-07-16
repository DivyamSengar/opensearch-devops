# OSCAR CDK Deployment

This directory contains the AWS Cloud Development Kit (CDK) code for deploying the OSCAR Slack bot infrastructure.

## Architecture

The CDK stack creates the following AWS resources:

- **Lambda Function**: Serverless execution environment for the Slack bot
- **API Gateway**: HTTP endpoint for receiving Slack events
- **DynamoDB Tables**:
  - `oscar-sessions`: Stores active Bedrock sessions (1 hour TTL)
  - `oscar-context`: Stores conversation context (48 hour TTL)
- **S3 Bucket**: Stores documentation for the knowledge base
- **Secrets Manager**: Securely stores Slack credentials
- **IAM Roles**: Provides necessary permissions for all components

## Prerequisites

1. **AWS Account** with appropriate permissions
2. **AWS CLI** installed and configured
3. **Node.js and npm** installed
4. **Python 3.9+** installed
5. **Slack Workspace** where you have permissions to create apps

## Deployment Instructions

### Step 1: Create Slack App

1. Go to https://api.slack.com/apps
2. Click "Create New App" > "From scratch"
3. Enter app name (e.g., "OSCAR") and select your workspace
4. Click "Create App"
5. Note down the "Signing Secret" from the "Basic Information" page
6. Go to "OAuth & Permissions" and add the following scopes:
   - `app_mentions:read`
   - `chat:write`
   - `channels:history`
   - `im:history`
   - `reactions:write` (for emoji reactions)
7. Click "Install App to Workspace" and authorize
8. Note down the "Bot User OAuth Token" (starts with `xoxb-`)

### Step 2: Configure Environment

1. Create a `.env` file in the `slack-bot` directory:
   ```bash
   cd slack-bot
   cp .env.example .env
   ```

2. Edit the `.env` file with your Slack credentials:
   ```
   SLACK_BOT_TOKEN=xoxb-your-token
   SLACK_SIGNING_SECRET=your-signing-secret
   KNOWLEDGE_BASE_ID=your-knowledge-base-id
   MODEL_ARN=arn:aws:bedrock:region:account:inference-profile/model-id
   ```

### Step 3: Deploy with CDK

Run the deployment script with your AWS account ID and region:

```bash
./deploy_cdk.sh -a YOUR_AWS_ACCOUNT_ID -r YOUR_AWS_REGION
```

For example:
```bash
./deploy_cdk.sh -a 123456789012 -r us-west-2
```

The script will:
1. Bootstrap the CDK environment
2. Deploy all required AWS resources
3. Upload the Lambda function code
4. Configure Secrets Manager with your Slack credentials
5. Provide you with the webhook URL for Slack configuration

### Step 4: Complete Slack App Configuration

1. Go to your Slack App configuration at https://api.slack.com/apps
2. Select your OSCAR app
3. Go to "Event Subscriptions"
4. Toggle "Enable Events" to On
5. Enter the webhook URL from the deployment output as the Request URL
6. Under "Subscribe to bot events", add:
   - `app_mention`
   - `message.im`
7. Click "Save Changes"
8. Go to "App Home" and enable "Messages Tab"
9. Check "Allow users to send Slash commands and messages from the messages tab"
10. Click "Save Changes"

### Step 5: Test Your Bot

1. In Slack, invite the bot to a channel: `/invite @oscar`
2. Mention the bot: `@oscar What's the status of OpenSearch 2.11?`
3. The bot should respond with information from your knowledge base
4. Try replying in a thread to test context preservation
5. Try sending a direct message to the bot
6. Notice the emoji reactions (👀 while processing, ✅ when complete)

## Stack Details

The `OscarSlackBotStack` class in `stacks/oscar_slack_bot_stack.py` defines all the AWS resources:

- **Secrets Manager**: Stores Slack credentials securely
- **DynamoDB Tables**: Store session and context information
- **S3 Bucket**: Stores documentation for the knowledge base
- **Lambda Function**: Runs the Slack bot code
- **API Gateway**: Provides HTTP endpoint for Slack events
- **IAM Roles**: Grants necessary permissions

## Customization

You can customize the deployment by modifying:

- **Memory and Timeout**: Adjust Lambda function resources in `oscar_slack_bot_stack.py`
- **Region and Account**: Specify different values when running `deploy_cdk.sh`
- **TTL Settings**: Change the time-to-live values for DynamoDB tables
- **Model Selection**: Use a different Bedrock model by updating the MODEL_ARN
- **Emoji Reactions**: Modify the emoji reactions in `app.py`

## Troubleshooting

### Common Issues

1. **Deployment Fails with Region Error**:
   - Ensure you're specifying the correct region with `-r` flag
   - Check that AWS CLI is configured correctly

2. **Lambda Function Errors**:
   - Check CloudWatch Logs for detailed error messages
   - Verify that all environment variables are set correctly
   - Ensure Secrets Manager contains valid Slack credentials

3. **Slack Integration Issues**:
   - Verify the webhook URL is correctly configured in Slack
   - Check that all required scopes are added to the Slack app
   - Ensure the bot is invited to the channel

4. **Knowledge Base Issues**:
   - Verify that the KNOWLEDGE_BASE_ID environment variable is set correctly
   - Check that the knowledge base exists and is active

## Clean Up

To remove all deployed resources:

```bash
cd cdk
cdk destroy
```
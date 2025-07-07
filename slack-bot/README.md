# OSCAR Slack Bot

AI-powered Slack bot with thread-based context and knowledge base integration.

## Architecture

- **Lambda Function**: Serverless execution with auto-scaling
- **DynamoDB**: Session storage for thread context (24h TTL)
- **Bedrock**: Knowledge base queries with context preservation
- **Slack Bolt**: Event handling and message processing

## Setup

1. **Create Slack App**:
   - Go to https://api.slack.com/apps
   - Create new app from scratch
   - Enable Event Subscriptions, Bot Token Scopes
   - Add scopes: `app_mentions:read`, `chat:write`, `channels:history`

2. **Configure Environment**:
   ```bash
   cp .env.example .env
   # Fill in your values
   ```

3. **Deploy**:
   ```bash
   chmod +x deploy.sh
   ./deploy.sh
   ```

4. **Configure Slack**:
   - Copy webhook URL from deployment output
   - Set as Request URL in Slack app Event Subscriptions
   - Subscribe to `app_mention` events
   - Install app to workspace

## Context Management

- **Thread Context**: Messages in same thread maintain conversation context
- **New Messages**: Direct channel messages start fresh context
- **Session Storage**: DynamoDB with 24h auto-expiry

## Usage

Mention the bot in any channel:
```
@oscar What's the status of OpenSearch 2.11?
```

Reply in thread to maintain context:
```
@oscar What about security issues?
```
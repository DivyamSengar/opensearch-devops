# OSCAR - OpenSearch Context-Aware Release Assistant

OSCAR is an AI-powered Slack bot designed to assist with OpenSearch release management by providing context-aware responses using Amazon Bedrock and a knowledge base of OpenSearch documentation.

## Repository Structure

This repository contains the following components:

- **[slack-bot/](./slack-bot/)**: The core Slack bot implementation using Slack Bolt framework and AWS Lambda
- **[cdk/](./cdk/)**: AWS CDK infrastructure as code for deploying all required AWS resources
- **[POC/](./POC/)**: Proof of concept implementations and experimental features
- **[build_docs/](./build_docs/)**: Documentation files used to populate the knowledge base

## Key Features

- **Thread-Based Context**: Maintains conversation context within Slack threads
- **Knowledge Base Integration**: Connects to Amazon Bedrock for intelligent responses
- **Serverless Architecture**: Runs on AWS Lambda with auto-scaling capabilities
- **Context Preservation**: Stores conversation history in DynamoDB with TTL
- **Secure Credential Management**: Uses AWS Secrets Manager for secure storage of Slack credentials
- **Emoji Reactions**: Provides visual feedback with emoji reactions to acknowledge messages

## Architecture Overview

![Architecture Diagram](https://via.placeholder.com/800x400?text=OSCAR+Architecture+Diagram)

1. **User Interaction**: Users interact with OSCAR through Slack by mentioning the bot or sending direct messages
2. **API Gateway**: Receives events from Slack and forwards them to Lambda
3. **Lambda Function**: Processes messages and manages conversation flow
4. **DynamoDB**: Stores conversation context and session information
5. **Amazon Bedrock**: Provides AI capabilities and knowledge base integration
6. **Secrets Manager**: Securely stores Slack API credentials

## Deployment Options

OSCAR can be deployed using two methods:

1. **AWS CDK (Recommended)**: For a complete infrastructure deployment with all required resources
   - See [cdk/README.md](./cdk/README.md) for detailed instructions

2. **Serverless Framework (Alternative)**: For a simpler deployment focused on the Lambda function
   - See [slack-bot/README.md](./slack-bot/README.md) for details

## Getting Started

To get started with OSCAR, follow these steps:

1. Clone this repository
2. Follow the deployment instructions in [cdk/README.md](./cdk/README.md)
3. Configure your Slack app as described in the deployment guide
4. Start interacting with OSCAR in your Slack workspace

## Knowledge Base Configuration

OSCAR uses an Amazon Bedrock knowledge base with the following configuration:

- **Knowledge Base ID**: 5FBGMYGHPK
- **Embedding Model**: Amazon Titan Embed Text v2
- **Storage**: OpenSearch Serverless
- **Chunking Strategy**: Fixed Size (8192 tokens with 20% overlap)
- **Parsing Strategy**: Bedrock Data Automation

The knowledge base is connected to an S3 bucket containing OpenSearch documentation files.

## License

[MIT License](LICENSE)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
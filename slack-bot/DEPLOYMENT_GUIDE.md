# OSCAR Slack Bot - Cloud Deployment Guide

## 📊 Logistics & Considerations

### **Context Duration & Length Limits**
- **Bedrock Sessions**: 1 hour inactivity timeout → automatic expiry
- **Extended Context**: 48 hours → DynamoDB TTL cleanup  
- **Conversation Length**: ~50-100 turns per session before degradation
- **Context Summary**: 3KB limit per thread (auto-truncated to keep recent context)

### **Cost Analysis (Monthly Estimates)**
- **Lambda**: $5-10 for moderate usage (1000 invocations/day)
- **DynamoDB**: $2-5 for context storage (pay-per-request)
- **Bedrock**: $20-50 depending on query volume (~$0.003 per 1K tokens)
- **Total**: ~$30-70/month for team usage

### **Use Cases Optimized For**
- **Release Planning**: Multi-day discussions with preserved context
- **Troubleshooting**: Technical context maintained across shifts  
- **Documentation Queries**: Knowledge base integration with OpenSearch docs
- **Team Collaboration**: Cross-timezone context preservation

### **Scaling Considerations**
- **Lambda Concurrency**: 10 reserved (adjustable in serverless.yml)
- **DynamoDB**: Auto-scaling with pay-per-request billing
- **Context Cleanup**: Automatic TTL prevents storage bloat
- **Error Handling**: Graceful degradation when services unavailable

## 🚀 Cloud Deployment Steps

### **Step 1: Configure AWS Credentials**
```bash
aws configure
```
Enter:
- AWS Access Key ID: `your-access-key`
- AWS Secret Access Key: `your-secret-key`
- Default region: `us-west-2`
- Default output format: `json`

### **Step 2: Install Serverless Framework**
```bash
npm install -g serverless
```

### **Step 3: Install Project Dependencies**
```bash
cd /path/to/OSCAR/slack-bot
npm install
```

### **Step 4: Verify Environment Variables**
Ensure your `.env` file contains:
```
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_SIGNING_SECRET=your-signing-secret
KNOWLEDGE_BASE_ID=5FBGMYGHPK
MODEL_ARN=arn:aws:bedrock:us-west-2:691536381143:inference-profile/us.anthropic.claude-3-7-sonnet-20250219-v1:0
```

### **Step 5: Deploy to AWS**
```bash
serverless deploy
```

Expected output:
```
Service deployed to stack oscar-slack-bot-dev
endpoints:
  POST - https://xxxxxxxxxx.execute-api.us-west-2.amazonaws.com/dev/slack/events
functions:
  slack-bot: oscar-slack-bot-dev-slack-bot
```

### **Step 6: Configure Slack App Webhook**
1. Go to your Slack app at https://api.slack.com/apps
2. Navigate to **"Event Subscriptions"**
3. Set **Request URL** to the endpoint from Step 5
4. Subscribe to **Bot Events**: `app_mention`
5. Save changes

### **Step 7: Test Deployment**
1. Mention the bot in a Slack channel: `@oscar What is OpenSearch?`
2. Reply in the same thread: `@oscar Tell me more about security`
3. Verify context is preserved between messages

## 🔧 Post-Deployment Configuration

### **Monitor Costs**
- Check AWS CloudWatch for Lambda invocations
- Monitor DynamoDB usage in AWS Console
- Set up billing alerts for cost control

### **Adjust Scaling**
Edit `serverless.yml` to modify:
- `reservedConcurrency`: Increase for higher traffic
- TTL values: Adjust context retention duration
- Memory/timeout: Optimize for performance vs cost

### **Update Bot**
To deploy changes:
```bash
serverless deploy
```

To deploy only function code (faster):
```bash
serverless deploy function -f slack-bot
```

## 🛠️ Troubleshooting

### **Common Issues**
- **403 Forbidden**: Check Slack signing secret
- **Context not preserved**: Verify DynamoDB tables created
- **Timeout errors**: Increase Lambda timeout in serverless.yml
- **High costs**: Reduce context retention or add usage limits

### **Logs & Debugging**
```bash
serverless logs -f slack-bot --tail
```

### **Local Testing**
Use Socket Mode for development:
```bash
python socket_app.py
```

## 📈 Monitoring & Maintenance

### **Key Metrics to Watch**
- Lambda invocation count and duration
- DynamoDB read/write capacity
- Bedrock token usage
- Error rates and timeouts

### **Regular Maintenance**
- Review and clean up old DynamoDB entries
- Update Slack app permissions as needed
- Monitor AWS costs monthly
- Update dependencies periodically

## 🔒 Security Considerations

### **Environment Variables**
- Never commit `.env` to version control
- Use AWS Systems Manager Parameter Store for production secrets
- Rotate Slack tokens periodically

### **IAM Permissions**
The deployment creates minimal IAM roles with only required permissions:
- DynamoDB: Read/Write to oscar-* tables only
- Bedrock: Invoke model and retrieve from knowledge base
- CloudWatch: Write logs only

### **Network Security**
- Lambda runs in AWS managed VPC
- All communication over HTTPS
- Slack webhook verification enabled
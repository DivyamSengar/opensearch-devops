from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    CustomResource,
    aws_lambda as lambda_,
    aws_dynamodb as dynamodb,
    aws_iam as iam,
    aws_secretsmanager as secretsmanager,
    aws_s3 as s3,
    aws_s3_deployment as s3_deployment,
    aws_apigateway as apigateway,
    aws_logs as logs,
    CfnOutput
)
from constructs import Construct
import os

class OscarSlackBotStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create Secrets for Slack credentials
        slack_secrets = secretsmanager.Secret(
            self, "SlackSecrets",
            secret_name="oscar-slack-bot-secrets",
            description="Secrets for OSCAR Slack Bot",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template='{"SLACK_BOT_TOKEN":"","SLACK_SIGNING_SECRET":""}',
                generate_string_key="dummy"
            )
        )

        # Create DynamoDB Tables
        sessions_table = dynamodb.Table(
            self, "OscarSessionsTable",
            table_name="oscar-sessions",
            partition_key=dynamodb.Attribute(
                name="session_key",
                type=dynamodb.AttributeType.STRING
            ),
            time_to_live_attribute="ttl",
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY
        )

        context_table = dynamodb.Table(
            self, "OscarContextTable",
            table_name="oscar-context",
            partition_key=dynamodb.Attribute(
                name="thread_key",
                type=dynamodb.AttributeType.STRING
            ),
            time_to_live_attribute="ttl",
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY
        )

        # Create S3 bucket for knowledge base documents
        docs_bucket = s3.Bucket(
            self, "OscarDocsBucket",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )

        # Deploy documents to S3 bucket
        try:
            s3_deployment.BucketDeployment(
                self, "DeployDocs",
                sources=[s3_deployment.Source.asset("../build_docs")],
                destination_bucket=docs_bucket
            )
        except Exception as e:
            print(f"Warning: Could not deploy documents to S3 bucket: {e}")
            print("Continuing without document deployment...")
            
        # Create IAM role for Bedrock Knowledge Base
        kb_role = iam.Role(
            self, "BedrockKnowledgeBaseRole",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
            role_name=f"OscarBedrockKBRole-{self.account}-{self.region}"
        )
        
        # Add permissions for S3
        kb_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "s3:GetObject",
                    "s3:ListBucket"
                ],
                resources=[
                    docs_bucket.bucket_arn,
                    f"{docs_bucket.bucket_arn}/*"
                ]
            )
        )

        # Create Lambda function
        lambda_role = iam.Role(
            self, "OscarLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ]
        )

        # Add permissions for Bedrock
        lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:RetrieveAndGenerate",
                    "bedrock:Retrieve",
                    "bedrock:GetFoundationModel",
                    "bedrock:ListFoundationModels",
                    "bedrock:GetKnowledgeBase",
                    "bedrock:ListKnowledgeBases",
                    "bedrock:GetInferenceProfile",
                    "bedrock:ListInferenceProfiles",
                    "bedrock-agent-runtime:Retrieve",
                    "bedrock-agent-runtime:RetrieveAndGenerate",
                    "bedrock-agent-runtime:InvokeAgent"
                ],
                resources=["*"]
            )
        )

        # Add permissions for DynamoDB
        lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "dynamodb:GetItem",
                    "dynamodb:PutItem",
                    "dynamodb:UpdateItem",
                    "dynamodb:DeleteItem",
                    "dynamodb:Query"
                ],
                resources=[
                    sessions_table.table_arn,
                    context_table.table_arn
                ]
            )
        )

        # Add permissions for Secrets Manager
        lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "secretsmanager:GetSecretValue"
                ],
                resources=[slack_secrets.secret_arn]
            )
        )

        # Create Lambda function with placeholder code
        lambda_function = lambda_.Function(
            self, "OscarSlackBotFunction",
            function_name="oscar-slack-bot",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="app.lambda_handler",
            code=lambda_.Code.from_inline("""
import os
def lambda_handler(event, context):
    return {
        'statusCode': 200,
        'body': 'Lambda function deployed successfully. Will be updated with full code.'
    }
"""),
            timeout=Duration.seconds(30),
            memory_size=512,
            environment={
                # Required configuration
                "KNOWLEDGE_BASE_ID": os.environ.get("KNOWLEDGE_BASE_ID", "PLACEHOLDER_KNOWLEDGE_BASE_ID"),
                "MODEL_ARN": os.environ.get("MODEL_ARN", "arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-v2"),
                "SLACK_SECRETS_ARN": slack_secrets.secret_arn,
                
                # Optional configuration
                # Note: AWS_REGION is a reserved environment variable in Lambda and cannot be set manually
                "SESSIONS_TABLE_NAME": os.environ.get("SESSIONS_TABLE_NAME", "oscar-sessions"),
                "CONTEXT_TABLE_NAME": os.environ.get("CONTEXT_TABLE_NAME", "oscar-context"),
                "DEDUP_TTL": os.environ.get("DEDUP_TTL", "300"),
                "SESSION_TTL": os.environ.get("SESSION_TTL", "3600"),
                "CONTEXT_TTL": os.environ.get("CONTEXT_TTL", "172800"),
                "MAX_CONTEXT_LENGTH": os.environ.get("MAX_CONTEXT_LENGTH", "3000"),
                "CONTEXT_SUMMARY_LENGTH": os.environ.get("CONTEXT_SUMMARY_LENGTH", "500"),
                
                # Feature flags
                "ENABLE_DM": os.environ.get("ENABLE_DM", "false"),
                
                # Prompt template (if provided)
                **({"PROMPT_TEMPLATE": os.environ.get("PROMPT_TEMPLATE")} if os.environ.get("PROMPT_TEMPLATE") else {})
            },
            role=lambda_role
        )

        # Create API Gateway
        api = apigateway.LambdaRestApi(
            self, "OscarSlackBotApi",
            handler=lambda_function,
            proxy=False
        )

        # Add Slack events endpoint
        slack_events = api.root.add_resource("slack").add_resource("events")
        slack_events.add_method("POST")

        # Outputs
        CfnOutput(
            self, "SlackWebhookUrl",
            value=f"{api.url}slack/events",
            description="URL to configure in Slack Events API"
        )
        
        CfnOutput(
            self, "SlackSecretsArn",
            value=slack_secrets.secret_arn,
            description="ARN of the Slack secrets in Secrets Manager"
        )
        
        CfnOutput(
            self, "DocsBucketName",
            value=docs_bucket.bucket_name,
            description="Name of the S3 bucket for knowledge base documents"
        )
        
        CfnOutput(
            self, "LambdaFunctionName",
            value=lambda_function.function_name,
            description="Name of the Lambda function"
        )
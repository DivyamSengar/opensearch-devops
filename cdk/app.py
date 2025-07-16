#!/usr/bin/env python3
import os
import sys
from aws_cdk import (
    App,
    Environment
)
from stacks.oscar_slack_bot_stack import OscarSlackBotStack

app = App()

# Get account and region from environment variables
account = os.environ.get("CDK_DEFAULT_ACCOUNT")
region = os.environ.get("CDK_DEFAULT_REGION")

print(f"Deploying to account: {account}")
print(f"Deploying to region: {region}")

# Validate region
if region != "us-west-2":
    print(f"ERROR: Region is set to {region}, but should be us-west-2")
    print("Please make sure CDK_DEFAULT_REGION is set correctly")
    sys.exit(1)

OscarSlackBotStack(
    app, 
    "OscarSlackBotStack",
    env=Environment(
        account=account,
        region=region
    )
)

app.synth()
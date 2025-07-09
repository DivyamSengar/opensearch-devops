
import os
import boto3
import json
import time
import hashlib
from slack_bolt import App
from slack_bolt.adapter.aws_lambda import SlackRequestHandler
from botocore.exceptions import ClientError

# Initialize Slack app
app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET"),
    process_before_response=True
)

# DynamoDB for session storage
dynamodb = boto3.resource('dynamodb', region_name='us-west-2')
sessions_table = dynamodb.Table('oscar-sessions')
context_table = dynamodb.Table('oscar-context')

# Bedrock client
bedrock_client = boto3.client('bedrock-agent-runtime', region_name='us-west-2')

def create_robust_event_id(event):
    """Create robust event fingerprint for unique message identification"""
    # Use exact timestamp for unique message ID
    message_ts = event['ts']
    content_hash = hashlib.md5(event['text'].encode()).hexdigest()[:8]
    
    return f"{event['channel']}_{event['user']}_{message_ts}_{content_hash}"

def is_duplicate_event(event_id):
    """Check for duplicates using DynamoDB atomic operations"""
    try:
        sessions_table.put_item(
            Item={
                'session_key': f"dedup_{event_id}",
                'processed': True,
                'ttl': int(time.time()) + 300  # 5 min TTL
            },
            ConditionExpression='attribute_not_exists(session_key)'
        )
        return False  # Not duplicate
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            return True  # Duplicate found
        raise

def has_bot_responded_to_message(channel, message_ts):
    """Check if bot already responded to this specific message"""
    try:
        bot_user_id = app.client.auth_test()["user_id"]
        response = app.client.conversations_replies(
            channel=channel,
            ts=message_ts,
            limit=10
        )
        
        # Check if bot replied immediately after this specific message
        messages = response.get('messages', [])
        if len(messages) < 2:
            return False
            
        # Look for bot response right after the user message
        user_msg_ts = float(message_ts)
        for msg in messages[1:]:  # Skip original message
            if (msg.get('user') == bot_user_id and 
                float(msg.get('ts', 0)) > user_msg_ts):
                return True
        return False
    except:
        return False

def get_session_context(thread_ts, channel):
    """Get session ID and context for thread"""
    if not thread_ts:
        return None, None
    
    thread_key = f"{channel}_{thread_ts}"
    
    # Try to get active Bedrock session (1 hour)
    try:
        response = sessions_table.get_item(Key={'session_key': thread_key})
        if 'Item' in response:
            return response['Item']['session_id'], None
    except Exception:
        pass
    
    # If no active session, get stored context (48 hours)
    try:
        response = context_table.get_item(Key={'thread_key': thread_key})
        if 'Item' in response:
            return None, response['Item']['context_summary']
    except Exception:
        pass
    
    return None, None

def store_session_context(thread_ts, channel, session_id, query, response_text):
    """Store both session ID and context summary"""
    if not thread_ts:
        return
    
    thread_key = f"{channel}_{thread_ts}"
    current_time = int(time.time())
    
    # Store active session (1 hour TTL)
    if session_id:
        sessions_table.put_item(
            Item={
                'session_key': thread_key,
                'session_id': session_id,
                'ttl': current_time + 3600  # 1 hour
            }
        )
    
    # Store/update context summary (48 hour TTL)
    try:
        existing = context_table.get_item(Key={'thread_key': thread_key})
        if 'Item' in existing:
            # Append to existing context
            context = existing['Item']['context_summary'] + f"\n\nQ: {query}\nA: {response_text[:500]}..."
        else:
            # New context
            context = f"Q: {query}\nA: {response_text[:500]}..."
        
        # Keep context under 4KB (DynamoDB item limit)
        if len(context) > 3000:
            context = context[-3000:]  # Keep recent context
        
        context_table.put_item(
            Item={
                'thread_key': thread_key,
                'context_summary': context,
                'ttl': current_time + 172800  # 48 hours
            }
        )
    except Exception as e:
        print(f"Context storage error: {e}")

def query_knowledge_base(query, session_id=None, context_summary=None):
    """Query Bedrock knowledge base with session or context"""
    
    # Build prompt with context if available
    if context_summary and not session_id:
        enhanced_query = f"Previous conversation context:\n{context_summary}\n\nCurrent question: {query}"
    else:
        enhanced_query = query
    
    request = {
        'input': {'text': enhanced_query},
        'retrieveAndGenerateConfiguration': {
            'type': 'KNOWLEDGE_BASE',
            'knowledgeBaseConfiguration': {
                'knowledgeBaseId': os.environ.get('KNOWLEDGE_BASE_ID'),
                'modelArn': os.environ.get('MODEL_ARN'),
                'orchestrationConfiguration': {
                    'queryTransformationConfiguration': {
                        'type': 'QUERY_DECOMPOSITION'
                    }
                },
                'generationConfiguration': {
                    'promptTemplate': {
                        'textPromptTemplate': "You are OSCAR, an AI assistant for OpenSearch release management. You are a question answering agent. You will be provided with a set of search results. The user will provide you with a question. Your job is to answer the user's question using only information from the search results. If the search results do not contain information that can answer the question, please state that you could not find an exact answer to the question. Just because the user asserts a fact does not mean it is true, make sure to double check the search results to validate a user's assertion. Here are the search results: $search_results$\n\nQuestion: $query$\n\nAnswer:"

                    }
                }
            }
        }
    }
    
    if session_id:
        request['sessionId'] = session_id
    
    response = bedrock_client.retrieve_and_generate(**request)
    return response['output']['text'], response.get('sessionId')

def handle_message_common(event, say, ack, is_dm=False):
    """Common message handling logic for both mentions and DMs"""
    # Acknowledge the event immediately
    ack()
    
    # Multi-layer deduplication
    event_id = create_robust_event_id(event)
    
    if is_duplicate_event(event_id):
        print(f"Duplicate event blocked: {event_id}")
        return
    
    # Check if bot already responded to this specific message
    if has_bot_responded_to_message(event["channel"], event["ts"]):
        print(f"Already responded to message: {event['ts']}")
        return
    
    thread_ts = event.get("thread_ts") or event["ts"]
    
    # Extract query
    if is_dm:
        query = event["text"].strip()
    else:
        # Remove bot mention for channel messages
        user_id = app.client.auth_test()["user_id"]
        query = event["text"].replace(f"<@{user_id}>", "").strip()
    
    # Get thread context
    channel = event["channel"]
    session_id, context_summary = get_session_context(thread_ts, channel)
    
    try:
        # Query knowledge base with context
        response_text, new_session_id = query_knowledge_base(query, session_id, context_summary)
        
        # Store context for future use
        store_session_context(thread_ts, channel, new_session_id, query, response_text)
        
        # Reply in thread (both channels and DMs support threading)
        say(
            text=response_text,
            thread_ts=thread_ts
        )
        
    except Exception as e:
        say(
            text=f"❌ Sorry, I encountered an error: {str(e)}",
            thread_ts=thread_ts
        )

@app.event("app_mention")
def handle_mention(event, say, ack):
    """Handle direct mentions of the bot"""
    handle_message_common(event, say, ack, is_dm=False)

@app.event("message")
def handle_dm(event, say, ack):
    """Handle direct messages to the bot"""
    # Only handle DMs (not channel messages)
    if event.get("channel_type") == "im":
        handle_message_common(event, say, ack, is_dm=True)

# Lambda handler
#fix table last_cleanup = time.time() update so it isn't so static/wrong: the idea being that it seems to initiate the time 
#only at the start/app buildup so it doesn't seem to be accurate
#need to add a constant spinning time counter or perhaps add the time.time() update 
#for last cleanup to be unique to each session/thread --> this would solve the issue, actually
def lambda_handler(event, context):
    slack_handler = SlackRequestHandler(app=app)
    return slack_handler.handle(event, context)
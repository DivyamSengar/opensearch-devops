
import os
import boto3
import json
import time
from slack_bolt import App
from slack_bolt.adapter.aws_lambda import SlackRequestHandler

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

# Global deduplication cache with TTL cleanup
processed_events = {}
last_cleanup = time.time()

def cleanup_processed_events():
    """Clean up old processed events every 5 minutes"""
    global last_cleanup, processed_events
    current_time = time.time()
    if current_time - last_cleanup > 300:  # 5 minutes
        processed_events.clear()
        last_cleanup = current_time

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

@app.event("app_mention")
def handle_mention(event, say, ack):
    """Handle direct mentions of the bot"""
    # Acknowledge the event immediately
    ack()
    
    # Clean up old events periodically
    cleanup_processed_events()
    
    # Multi-layer deduplication
    event_id = f"{event['channel']}_{event['ts']}"
    content_hash = hash(f"{event['text']}_{event['user']}_{event['channel']}")
    
    if event_id in processed_events or content_hash in processed_events:
        print(f"Duplicate blocked: {event_id} or {content_hash}")
        return
    
    processed_events[event_id] = time.time()
    processed_events[content_hash] = time.time()
    
    # Extract query (remove bot mention)
    user_id = app.client.auth_test()["user_id"]
    query = event["text"].replace(f"<@{user_id}>", "").strip()
    
    # Get thread context
    thread_ts = event.get("thread_ts") or event["ts"]
    channel = event["channel"]
    session_id, context_summary = get_session_context(thread_ts, channel)
    
    try:
        # Query knowledge base with context
        response_text, new_session_id = query_knowledge_base(query, session_id, context_summary)
        
        # Store context for future use
        store_session_context(thread_ts, channel, new_session_id, query, response_text)
        
        # Reply in thread
        say(
            text=response_text,
            thread_ts=thread_ts
        )
        
    except Exception as e:
        say(
            text=f"❌ Sorry, I encountered an error: {str(e)}",
            thread_ts=thread_ts
        )

# Lambda handler
#fix table last_cleanup = time.time() update so it isn't so static/wrong: the idea being that it seems to initiate the time 
#only at the start/app buildup so it doesn't seem to be accurate
#need to add a constant spinning time counter or perhaps add the time.time() update 
#for last cleanup to be unique to each session/thread --> this would solve the issue, actually
def lambda_handler(event, context):
    slack_handler = SlackRequestHandler(app=app)
    return slack_handler.handle(event, context)
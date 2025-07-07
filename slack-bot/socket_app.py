import os
import boto3
import time
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# In-memory session storage for Socket Mode
sessions = {}

# Socket Mode App (no webhooks needed)
app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET")
)

# Same bedrock/dynamodb setup as before
bedrock_client = boto3.client('bedrock-agent-runtime', region_name='us-west-2')

def get_session_id(thread_ts, channel):
    """Get session ID for thread context"""
    if thread_ts:
        session_key = f"{channel}_{thread_ts}"
        return sessions.get(session_key)
    return None

def store_session_id(thread_ts, channel, session_id):
    """Store session ID for thread"""
    if thread_ts and session_id:
        session_key = f"{channel}_{thread_ts}"
        sessions[session_key] = session_id

def query_knowledge_base(query, session_id=None):
    """Query with optional session context"""
    request = {
        'input': {'text': query},
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
                        'textPromptTemplate': "You are OSCAR, an AI assistant for OpenSearch release management. Answer questions using the provided search results. Here are the search results: $search_results$\n\nQuestion: $query$\n\nAnswer:"
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
def handle_mention(event, say):
    # Remove bot mention from query
    user_id = app.client.auth_test()["user_id"]
    query = event["text"].replace(f"<@{user_id}>", "").strip()
    
    # Get thread context
    thread_ts = event.get("thread_ts") or event["ts"]
    channel = event["channel"]
    session_id = get_session_id(thread_ts, channel)
    
    try:
        response_text, new_session_id = query_knowledge_base(query, session_id)
        
        # Store session for thread context
        if new_session_id:
            store_session_id(thread_ts, channel, new_session_id)
        
        say(text=f"🤖 {response_text}", thread_ts=thread_ts)
    except Exception as e:
        say(text=f"❌ Error: {str(e)}", thread_ts=thread_ts)

if __name__ == "__main__":
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    handler.start()
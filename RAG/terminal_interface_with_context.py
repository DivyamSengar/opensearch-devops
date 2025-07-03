#!/usr/bin/env python3
import boto3
import sys
import time

def stream_text(text, delay=0.02):
    """Stream text to terminal character by character"""
    for char in text:
        print(char, end='', flush=True)
        time.sleep(delay)
    print()  # New line at end

# Global session ID for context persistence
session_id = None

def query_knowledge_base_streaming(query):
    global session_id
    client = boto3.client('bedrock-agent-runtime', region_name='us-west-2')
    
    print("\n🔍 Searching knowledge base...")
    
    # Build request
    request = {
        'input': {'text': query},
        'retrieveAndGenerateConfiguration': {
            'type': 'KNOWLEDGE_BASE',
            'knowledgeBaseConfiguration': {
                'knowledgeBaseId': '5FBGMYGHPK',
                'modelArn': 'arn:aws:bedrock:us-west-2:691536381143:inference-profile/us.anthropic.claude-sonnet-4-20250514-v1:0',
                'orchestrationConfiguration': {
                    'queryTransformationConfiguration': {
                        'type': 'QUERY_DECOMPOSITION'
                    }
                },
                'generationConfiguration': {
                    'promptTemplate': {
                        'textPromptTemplate': "You are a question answering agent. You will be provided with a set of search results. The user will provide you with a question. Your job is to answer the user's question using only information from the search results. If the search results do not contain information that can answer the question, please state that you could not find an exact answer to the question. Just because the user asserts a fact does not mean it is true, make sure to double check the search results to validate a user's assertion. Here are the search results: $search_results$\n\nQuestion: $query$\n\nAnswer:"
                    }
                }
            }
        }
    }
    
    # Add session ID for context if available
    if session_id:
        request['sessionId'] = session_id
    
    response = client.retrieve_and_generate(**request)
    
    # Store session ID for future context
    if 'sessionId' in response:
        session_id = response['sessionId']
        print(f"💬 Session: {session_id[:8]}...")
    
    print("\n📖 Response:")
    stream_text(response['output']['text'])
    return response['output']['text']

def main():
    print("🤖 OSCAR Knowledge Base Interface (With Context)")
    print("Context is maintained across queries in this session\n")
    
    while True:
        query = input("\nQuery: ").strip()
        if query.lower() in ['exit', 'quit', 'q']:
            break
        if query.lower() == 'reset':
            global session_id
            session_id = None
            print("🔄 Context reset")
            continue
        if query:
            try:
                query_knowledge_base_streaming(query)
            except Exception as e:
                print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
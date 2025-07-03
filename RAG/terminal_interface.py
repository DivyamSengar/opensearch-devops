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

def query_knowledge_base_streaming(query):
    client = boto3.client('bedrock-agent-runtime', region_name='us-west-2')
    
    print("\n🔍 Searching knowledge base...")
    
    response = client.retrieve_and_generate(
        input={'text': query},
        retrieveAndGenerateConfiguration={
            'type': 'KNOWLEDGE_BASE',
            'knowledgeBaseConfiguration': {
                'knowledgeBaseId': '5FBGMYGHPK',
                
                # Model Selection - Comment/uncomment to switch
                'modelArn': 'arn:aws:bedrock:us-west-2:691536381143:inference-profile/us.anthropic.claude-sonnet-4-20250514-v1:0',  # Claude 4 Sonnet
                # 'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0',  # Claude 3.5 Sonnet
                
                # # Retrieval Configuration - Controls document search
                # 'retrievalConfiguration': {
                #     'vectorSearchConfiguration': {
                #         'numberOfResults': 5,  # Number of docs to retrieve (1-100)
                #         # 'overrideSearchType': 'HYBRID',  # SEMANTIC, HYBRID - combines vector + keyword search
                #         # 'filter': {  # Filter results by metadata
                #         #     'equals': {'key': 'source', 'value': 'documentation'}
                #         # }
                #     }
                # },
                
                # Orchestration Configuration - Controls query processing
                'orchestrationConfiguration': {
                    'queryTransformationConfiguration': {
                        'type': 'QUERY_DECOMPOSITION'  # Breaks complex queries into parts
                    },
                    # 'inferenceConfig': {  # Model inference settings
                    #     'textInferenceConfig': {
                    #         'temperature': 0.1,  # Creativity (0.0-1.0) - lower = more focused
                    #         'topP': 0.9,  # Nucleus sampling (0.0-1.0)
                    #         'maxTokens': 2048,  # Max response length
                    #         'stopSequences': ['\n\n']  # Stop generation at these sequences
                    #     }
                    # }
                },
                
                # Generation Configuration - Controls response formatting
                'generationConfiguration': {
                    'promptTemplate': {
                        'textPromptTemplate': "You are a question answering agent. You will be provided with a set of search results. The user will provide you with a question. " 
                        +"Your job is to answer the user\'s question using only information from the search results. If the search results do not contain " 
                        +"information that can answer the question, please state that you could not find an exact answer to the question. Just because " 
                        +"the user asserts a fact does not mean it is true, make sure to double check the search results to validate a user's assertion. " 
                        +"Here are the search results: $search_results$\n\nQuestion: $query$\n\nAnswer:"
                    },
                    # 'guardrailConfiguration': {  # Content filtering
                    #     'guardrailId': 'your-guardrail-id',
                    #     'guardrailVersion': 'DRAFT'
                    # },
                    # 'inferenceConfig': {  # Override model settings for generation
                    #     'textInferenceConfig': {
                    #         'temperature': 0.0,  # More deterministic for final answer
                    #         'topP': 0.95,
                    #         'maxTokens': 1024
                    #     }
                    # }
                }
            }
        }
    )
    
    print("\n📖 Response:")
    stream_text(response['output']['text'])
    return response['output']['text']

def main():
    print("OSCAR Knowledge Base Interface")
    while True:
        query = input("\nQuery: ").strip()
        if query.lower() in ['exit', 'quit', 'q']:
            break
        if query:
            try:
                query_knowledge_base_streaming(query)
            except Exception as e:
                print(f"Error: {e}")

if __name__ == "__main__":
    main()
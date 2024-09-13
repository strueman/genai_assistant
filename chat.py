# import logging
from context_manager import ContextManager
import context_manager as cm
from connector import LLMConnector
import json
import os


try:
    provider = 'openai'
    model = 'gpt-4o-mini'#'claude-3-5-sonnet-20240620'#'meta-llama/llama-3.1-70b-instruct'
    functions =['reddit_summary']#,'ask_tavily']#None
    user_id = "1100110010010_qa8"
    # Load the system prompt from the file
    system_prompt_path = 'prompts/main_chat.md'
    temperature = 0.4
    try:
        with open(system_prompt_path, 'r') as file:
            system_prompt = file.read()
    except FileNotFoundError:
        print(f"Warning: System prompt file not found at {system_prompt_path}. Using default prompt.")
        system_prompt = "You are a helpful assistant."
    except IOError as e:
        print(f"Error reading system prompt file: {e}")
        system_prompt = "You are a helpful assistant."

    def main():
        connector = LLMConnector(provider=provider)  # Remove log_level parameter
        context_manager = ContextManager(connector, user_id=user_id, session_id=None) # Pass session_id if continuing a session else None
        
        session_id = context_manager.get_session_id()
        print(f"Chat interface initialized. Session ID: {session_id}")
        print("Type 'exit' to quit, 'load' to see available sessions, or 'load [session_id]' to load a specific session.")
        print(f"Session ID: {session_id}")
        try:
            while True:
                
                user_input = input("You: ").strip()
                
                if user_input.lower() == 'exit':
                    print("Exiting chat...")
                    break
                
                if user_input.lower() == 'load':
                    if os.path.exists('chat_histories.json'):
                        with open('chat_histories.json', 'r') as f:
                            histories = json.load(f)
                        print("Available sessions:")
                        for sid in histories.keys():
                            print(sid)
                    else:
                        print("No saved sessions found.")
                    continue
                
                if user_input.lower().startswith('load '):
                    session_to_load = user_input.split()[1]
                    context_manager.load_history(session_to_load)
                    print(f"Loaded session: {session_to_load}")
                    continue
                
                if user_input:
                    response = context_manager.send_message(
                        user_input,
                        model=model,
                        functions=functions,
                        system_prompt=system_prompt,
                        max_tokens=4096,
                        temperature=temperature
                    )
                    
                    if isinstance(response, dict):
                        if 'error' in response:
                            print(f"Error: {response['error']}")
                        else:
                            assistant_message = response.get('text', 'No response text')
                            print(f"Assistant: {assistant_message}")
                        
                    else:
                        print(f"Unexpected response type: {type(response)}")
                else:
                    print("Please enter a message.")
        finally:
            print("Ending session and saving chat history...")
            context_manager._shutdown()
            return

except Exception as e:
    print(f"Unexpected error: {str(e)}")
    pass
if __name__ == "__main__":
    main()

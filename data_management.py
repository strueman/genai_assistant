#this file will contain the code for the database management, file management, data storage and retrieval
from connector import LLMConnector
import json
import os
import ast
import re
import signal
from contextlib import contextmanager
import time
#Print debug messages TO BE REMOVED
debug = False
info = True
class TimeoutException(Exception):
    pass

@contextmanager
def time_limit(seconds):
    def signal_handler(signum, frame):
        raise TimeoutException("Timed out!")
    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)

def make_json_serializable(obj):
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    elif isinstance(obj, list):
        return [make_json_serializable(item) for item in obj]
    elif isinstance(obj, dict):
        return {str(key): make_json_serializable(value) for key, value in obj.items()}
    else:
        return str(obj)

memories = []
def load_and_process_chat_histories(user_id):
    session_index = load_session_index(user_id)
    payload = []
    empty_sessions = []
    
    for session_id, session_info in session_index.items():
        if not session_info['consolidated']:
            try:
                chat_history = load_session_history(user_id, session_id)
                filtered_history = filter_and_strip(chat_history)
                
                if filtered_history:
                    formatted_history = format_chat_history(filtered_history, session_id)
                    if formatted_history.strip():  # Check if formatted history is not empty
                        payload.append({'content': formatted_history, 'session_id': session_id})
                    else:
                        empty_sessions.append(session_id)
                else:
                    empty_sessions.append(session_id)
            except Exception as e:
                print(f"Error processing session {session_id}: {str(e)}")
                empty_sessions.append(session_id)
    
    if payload:
        process_unconsolidated_items(items=payload, user_id=user_id)
        if info: print(f"Processed {len(payload)} unconsolidated sessions")
    else:
        if debug: print("No unconsolidated sessions to process")
    
    # Handle empty sessions
    if empty_sessions:
        update_empty_sessions(user_id, empty_sessions)
        if info: print(f"Marked {len(empty_sessions)} sessions as empty")

def load_session_index(user_id):
    file_path = f"users/{user_id}/session_history/session_index.json"
    if not os.path.exists(file_path):
        return {}
    with open(file_path, 'r') as f:
        return json.load(f)

def load_session_history(user_id, session_id):
    file_path = f"users/{user_id}/session_history/{session_id}.json"
    if not os.path.exists(file_path):
        return []
    with open(file_path, 'r') as f:
        data = json.load(f)
        return data.get(session_id, [])

def update_session_index(user_id, session_summaries):
    file_path = f"users/{user_id}/session_history/session_index.json"
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            session_index = json.load(f)
    else:
        session_index = {}

    for session_id, summary in session_summaries.items():
        try:
            if session_id in session_index:
                session_index[session_id]['summary'] = summary['summary']
                session_index[session_id]['consolidated'] = True
            else:
                session_index[session_id] = {
                    'timestamp': str(int(time.time())),
                    'summary': summary['summary'],
                    'consolidated': True
                }
        except:
            pass
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w') as f:
        json.dump(session_index, f, indent=2)

    if info: print(f"Updated session index for {len(session_summaries)} sessions")

def format_chat_history(chat_history, session_id=None):
    formatted_text = ""
    for item in chat_history:
        if item['role'] == 'user':
            formatted_text += f"human says: {item['content']}\n"
        elif item['role'] == 'assistant':
            formatted_text += f"chatbot replies: {item['content']}\n"
    return formatted_text.strip()

def process_unconsolidated_items(items, user_id=None):
    global memories
    processed_count = 0
    session_summaries = {}
    for index, item in enumerate(items):
        try:
            with time_limit(30):  # Set a 30-second timeout for LLM processing
                session_id = item['session_id']
                if info: print(f"Processing item {index + 1}/{len(items)}: {session_id}")
                resp = llm_consolidation(data=item['content'], user_id=user_id, session_id=session_id)
                if resp:
                    serializable_resp = make_json_serializable(resp)
                    if isinstance(serializable_resp, list) and serializable_resp:
                        for memory in serializable_resp:
                            memory['session_id'] = session_id
                            if memory.get('metadata') and 'summary' in memory.get('metadata'):
                                session_summaries[session_id] = memory.get('summary', '')
                        memories.extend(serializable_resp)
                        processed_count += len(serializable_resp)
                        if debug: print(f"Processed item {index + 1}/{len(items)}: Added {len(serializable_resp)} memory/memories")
                    elif isinstance(serializable_resp, dict):
                        serializable_resp['session_id'] = session_id
                        if serializable_resp.get('metadata') and 'summary' in serializable_resp.get('metadata'):
                            session_summaries[session_id] = serializable_resp.get('summary', '')
                        memories.append(serializable_resp)
                        processed_count += 1
                        if debug: print(f"Processed item {index + 1}/{len(items)}: Added 1 memory")
                    else:
                        if debug: print(f"Processed item {index + 1}/{len(items)}: No valid data to save")
                else:
                    if debug: print(f"Processed item {index + 1}/{len(items)}: No valid response")
        except TimeoutException:
            print(f"LLM processing timed out for item {index + 1}/{len(items)}")
        except Exception as e:
            print(f"Error processing item {index + 1}/{len(items)}. Error: {str(e)}")
        
        # Ensure the session is marked as consolidated even if there was an error
        if session_id not in session_summaries:
            session_summaries[session_id] = ''
    
    if debug: print(f"Total processed memories: {processed_count}")
    save_memories_to_file(memories=memories, user_id=user_id)
    memories.clear()
    
    # Update session index with summaries
    update_session_index(user_id, session_summaries)

    if debug: print(f"Session summaries: {session_summaries}")

def update_empty_sessions(user_id, empty_sessions):
    session_index = load_session_index(user_id)
    for session_id in empty_sessions:
        if session_id in session_index:
            session_index[session_id]['summary'] = 'No summary available'
            session_index[session_id]['consolidated'] = True
        else:
            session_index[session_id] = {
                'timestamp': str(int(time.time())),
                'summary': 'No summary available',
                'consolidated': True
            }
    update_session_index(user_id, session_index)

# def ensure_session_structure(session_data):
#     default_structure = {
#         'timestamp': str(int(time.time())),
#         'summary': 'No summary available',
#         'consolidated': False
#     }
#     return {**default_structure, **session_data}

def llm_consolidation(data, user_id, session_id):
    system_prompt = open("prompts/consolidation_prompt.md", "r").read()
    
    connector_openai = LLMConnector(provider='openai')
    response_openai = connector_openai.chat(
        str(data),
        functions=None,
        system_prompt=system_prompt,
        model="gpt-4o-mini",
        response_format ='json',
        temperature=0.0,
        max_tokens=4096)
    

    if response_openai['text']:
        if debug == True: print(f"Raw LLM response:\n{response_openai['text']}\n")
        processed_data = process_llm_response(response_openai['text'])
        for item in processed_data:
            item['session_id'] = session_id
            item['user_id'] = user_id
        if processed_data:
            if debug: print(f"LLM response processed successfully. Result: {json.dumps(processed_data, indent=2)}")
            return processed_data
       
    else:
        print("No text in LLM response")
    
    return None

def process_llm_response(response):
    # Remove markdown code block delimiters if present
    cleaned_response = re.sub(r'```json\s*|\s*```', '', response.strip())
    
    try:
        # First, try to parse as JSON
        data = json.loads(cleaned_response)
        if debug == True: print("Successfully parsed response as JSON")
    except json.JSONDecodeError:
        try:
            # If JSON parsing fails, try to evaluate as a Python literal
            data = ast.literal_eval(cleaned_response)
            if debug == True: print("Successfully parsed response as Python literal")
        except (SyntaxError, ValueError):
            # If both methods fail, attempt to recover the data
            data = recover_malformed_data(cleaned_response)
            if debug == True: print(f"Recovered malformed data: {data}")
    
    # Ensure the result is a list
    if isinstance(data, list):
        return data
    elif isinstance(data, dict):
        return [data]
    elif isinstance(data, str):
        return [data]
    else:
        print(f"Unexpected data type: {type(data)}")
        return None

def recover_malformed_data(text):
    # Remove any remaining quotes and split by commas
    items = text.replace('"', '').replace("'", "").split(',')
    # Strip whitespace from each item and remove empty items
    return [item.strip() for item in items if item.strip()]

def save_memories_to_file(memories=None, user_id=None):
    file_path = f'users/{user_id}/memories.json'
    
    # Load existing memories if the file exists
    existing_memories = []
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            try:
                existing_memories = json.load(f)
            except json.JSONDecodeError:
                print("Error reading existing memories file. Starting with empty memories.")

    # Append new memories to existing ones
    combined_memories = existing_memories + memories

    # Write combined memories back to file
    with open(file_path, 'w') as f:
        json.dump(combined_memories, f, indent=2, default=str)
    
    if info: print(f"Saved {len(memories)} new memories. Total memories: {len(combined_memories)}")

def filter_and_strip(chat_history):
    filtered_history = []
    for message in chat_history:
        if isinstance(message, dict) and 'content' in message:
            if "<subconscious>" not in message['content'] and "<*ACCEPTED*>" not in message['content']:
                filtered_history.append({
                    'role': message.get('role', ''),
                    'content': message['content']
                })
    return filtered_history

# Example usage
if __name__ == "__main__":
    user_id = "1100110010010_qa8"  # Example user ID
    load_and_process_chat_histories(user_id)
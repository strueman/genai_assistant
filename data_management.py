#this file will contain the code for the database management, file management, data storage and retrieval
from connector import LLMConnector
import json
import os
import ast
import re
import signal
from contextlib import contextmanager
import time
import concurrent.futures
from functools import partial

update_profile_llm_connector = LLMConnector(provider='openai')
#Print debug messages TO BE REMOVED
debug = False
info = True
more_info = False
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

data = []
memories = []
def load_and_process_chat_histories(user_id):
    session_index = _load_session_index(user_id)
    payload = []
    empty_sessions = []
    
    for session_id, session_info in session_index.items():
        if not session_info['consolidated']:
            try:
                chat_history = _load_session_history(user_id, session_id)
                filtered_history = _filter_and_strip(chat_history)
                
                if filtered_history:
                    formatted_history = _format_chat_history(filtered_history, session_id)
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
        process_unconsolidated_items(items=payload, user_id=user_id, empty_sessions=empty_sessions)
        if info: print(f"Processed {len(payload)} unconsolidated sessions")
    else:  
        # Handle empty sessions for if theres only empty sessions, otherwise they are handled in process_unconsolidated_items()
        if empty_sessions:
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
            if info: print(f"Updated session index for {len(empty_sessions)} empty sessions")
        else:
            if info: print("No sessions to update")
            return
            
def update_session_index(user_id, session_summaries, empty_sessions=None):
    file_path = f"users/{user_id}/session_history/session_index.json"
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            session_index = json.load(f)
    else:
        session_index = {}
    if empty_sessions:
        for session_id in empty_sessions:
            session_index[session_id] = {
                'summary': 'No summary available',
                'consolidated': True
            }
        if info: print(f"Updated session index for {len(empty_sessions)} empty sessions")
    for session_id, summary in session_summaries.items():
        if session_id in session_index:
            if summary != '' or summary != " ":
                session_index[session_id]['summary'] = summary
                session_index[session_id]['consolidated'] = True
            else:
                print(f"Empty summary for session {session_id}")
        else:
            session_index[session_id] = {
                'timestamp': str(int(time.time())),
                'summary': summary,
                'consolidated': True
            }

    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w') as f:
        json.dump(session_index, f, indent=2)

    if info: print(f"Updated session index for {len(session_summaries)} sessions")





def process_unconsolidated_items(items, user_id=None, empty_sessions=None):
    global memories
    processed_count = 0
    session_summaries = {}
    all_user_info = []

    process_item_partial = partial(process_single_item, user_id=user_id)

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_item = {executor.submit(process_item_partial, item): item for item in items}
        for future in concurrent.futures.as_completed(future_to_item):
            item = future_to_item[future]
            try:
                result_consolidation, result_user_info = future.result()
                if result_consolidation:
                    memories.extend(result_consolidation['memories'])
                    processed_count += len(result_consolidation['memories'])
                    if result_consolidation['summary']:
                        session_summaries[item['session_id']] = result_consolidation['summary']
                        if debug: print(f"Added summary for session {item['session_id']}: {result_consolidation['summary']}")
                    else:
                        session_summaries[item['session_id']] = 'Summary not available'
                        if debug: print(f"No summary for session {item['session_id']}")
                    if debug: print(f"Processed item for session {item['session_id']}: Added {len(result_consolidation['memories'])} memory/memories")
                else:
                    if debug: print(f"Processed item for session {item['session_id']}: No valid consolidation result")
                if result_user_info:
                    all_user_info.extend(result_user_info)
                    if debug: print(f"Extracted user info for session {item['session_id']}: {result_user_info}")
                else:
                    if debug: print(f"Processed item for session {item['session_id']}: No valid user info result")
            except Exception as e:
                pass
            # Ensure the session is marked as consolidated even if there was an error
            if item['session_id'] not in session_summaries:
                session_summaries[item['session_id']] = 'Summary not available'
                if debug: print(f"Marked empty summary for session {item['session_id']}")

    if debug: print(f"Total processed memories: {processed_count}")
    _save_memories_to_file(memories=memories, user_id=user_id)
    memories.clear()   
    # Update session index with summaries
    update_session_index(user_id, session_summaries, empty_sessions)
    if debug: print(f"Session summaries: {session_summaries}")

    # Save user info
    if all_user_info:
        save_user_info_to_file(all_user_info, user_id)
    else:
        if info: print("No user info extracted")

def process_single_item(item, user_id):
    session_id = item['session_id']
    try:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_consolidation = executor.submit(process_item_with_llm, item, user_id, session_id)
            future_user_info = executor.submit(process_item_for_user_info, item, user_id, session_id)
            
            result_consolidation = future_consolidation.result(timeout=30)
            result_user_info = future_user_info.result(timeout=30)
            
            if result_consolidation:
                if more_info: print(f"Consolidation result for session {session_id}: ok")
            else:
                if more_info: print(f"No valid consolidation result for session {session_id}")
            
            if result_user_info:
                if more_info: print(f"User info result for session {session_id}: ok")

            
            return result_consolidation, result_user_info
    except concurrent.futures.TimeoutError:
        print(f"LLM processing timed out for session {session_id}")
    except Exception as e:
        pass
    return None, []

def process_item_with_llm(item, user_id, session_id):
    if len(item['content']) < 5:
        return None
    resp = llm_consolidation(data=item['content'], user_id=user_id, session_id=session_id)
    if resp:
        serializable_resp = _make_json_serializable(resp)
        if debug: print(f"Serializable response for session {session_id}: {serializable_resp}")
        if isinstance(serializable_resp, list):
            memories = []
            summary = ''
            for memory in serializable_resp:
                if isinstance(memory, dict):
                    memory['session_id'] = session_id
                    memories.append(memory)
                    if 'summary' in memory:
                        summary = memory['summary']
                        break  # We've found the summary, no need to continue
            if debug: print(f"Extracted summary for session {session_id}: {summary}")
            return {'memories': memories, 'summary': summary}
        elif isinstance(serializable_resp, dict):
            serializable_resp['session_id'] = session_id
            summary = serializable_resp.get('summary', '')
            if debug: print(f"Extracted summary for session {session_id}: {summary}")
            return {'memories': [serializable_resp], 'summary': summary}
        else:
            print(f"Unexpected response type from llm_consolidation: {type(serializable_resp)}")
            return {'memories': [], 'summary': ''}
    return {'memories': [], 'summary': ''}

def process_item_for_user_info(item, user_id, session_id):
    resp = llm_user_info_extraction(data=item['content'], user_id=user_id, session_id=session_id)
    if resp:
        serializable_resp = _make_json_serializable(resp)
        if debug: print(f"Serializable user info response for session {session_id}: {serializable_resp}")
        return serializable_resp
    return []

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

def llm_user_info_extraction(data, user_id, session_id):
    if len(data) < 5:
        return None
    system_prompt = open("prompts/user_info_prompt.md", "r").read()
    connector_openai = LLMConnector(provider='openai')
    response_openai = connector_openai.chat(
        str(data),
        functions=None,
        system_prompt=system_prompt,
        model="gpt-4o-mini",
        response_format='json',
        temperature=0.0,
        max_tokens=4096)
    
    if response_openai['text']:
        if debug: print(f"Raw LLM user info response:\n{response_openai['text']}\n")
        processed_data = process_llm_response(response_openai['text'])
        if processed_data:
            if debug: print(f"LLM user info response processed successfully. Result: {json.dumps(processed_data, indent=2)}")
            return processed_data
    else:
        print("No text in LLM user info response")
    return None

def process_llm_response(response):
    # Remove markdown code block delimiters if present
    cleaned_response = re.sub(r'```json\s*|\s*```', '', response.strip())
    
    try:
        # First, try to parse as JSON
        data = json.loads(cleaned_response)
        if debug: print("Successfully parsed response as JSON")
    except json.JSONDecodeError:
        try:
            # If JSON parsing fails, try to evaluate as a Python literal
            data = ast.literal_eval(cleaned_response)
            print("process_llm_response: data type: ", type(data), "data length: ", len(data))
            if debug == True: print("Successfully parsed response as Python literal")
        except (SyntaxError, ValueError):

            data = _recover_malformed_data(data)
            print("process_llm_response: data type: ", type(data), "data length: ", len(data))
            if debug: print(f"Recovered malformed data: {data}")
    
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


# TO BE REPLACED WITH ADD TO MEM0 DATABASE
def _save_memories_to_file(memories=None, user_id=None):
    file_path = f'users/{user_id}/memories.json'
    existing_memories = []
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            try:
                existing_memories = json.load(f)
            except json.JSONDecodeError:
                print("Error reading existing memories file. Starting with empty memories.")
    combined_memories = existing_memories + memories
    with open(file_path, 'w') as f:
        json.dump(combined_memories, f, indent=2, default=str)  
    if info: print(f"Saved {len(memories)} new memories. Total memories: {len(combined_memories)}")

def save_user_info_to_file(user_info, user_id):
    file_path = f'users/{user_id}/user_info_data.json'
    existing_user_info = []
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            try:
                existing_user_info = json.load(f)
            except json.JSONDecodeError:
                print("Error reading existing user info file. Starting with empty user info.")
    
    # Merge new user info with existing info
    for new_info in user_info:
        existing_info = next((item for item in existing_user_info if item['type'] == new_info['type']), None)
        if existing_info:
            if existing_info['value'] != new_info['value']:
                existing_info['value'] = new_info['value']
        else:
            existing_user_info.append(new_info)
    
    # with open(file_path, 'w') as f:
    #     json.dump(existing_user_info, f, indent=2, default=str)
    # if info: print(f"Saved user info to {file_path}")
    _update_profile_thread(input_data=existing_user_info, user_id=user_id)


def _is_dict_in_list(d, lst):
    """Check if a dictionary is already in a list of dictionaries."""
    return any(d.items() <= existing_dict.items() for existing_dict in lst)

def _deep_update(d, u):
    for k, v in u.items():
        if isinstance(v, dict):
            d[k] = _deep_update(d.get(k, {}), v)
        elif isinstance(v, list):
            if not isinstance(d.get(k), list):
                d[k] = []
            for item in v:
                if isinstance(item, dict):
                    if not _is_dict_in_list(item, d[k]):
                        d[k].append(item)
                elif item not in d[k]:
                    d[k].append(item)
        elif v is not None:
            d[k] = v
    return d

def _update_profile_thread(input_data, user_id) -> None:
    profile_output_file_path = f"users/{user_id}/user_profile.json"
    try:
        if not input_data:
            return

        with open("prompts/update_profile.md", 'r') as f:
            system_prompt = f.read().strip()

        input_data_str = json.dumps(input_data, indent=2)
        
        # Load existing profile or create a new one from schema
        if os.path.exists(profile_output_file_path):
            with open(profile_output_file_path, 'r') as f:
                existing_profile = json.load(f)
        else:
            # Load blank schema
            schema_path = "users/default/profile_schema.json"
            with open(schema_path, 'r') as f:
                existing_profile = json.load(f)
            
            # Insert user_id
            existing_profile['user_id'] = user_id

        existing_profile_str = json.dumps(existing_profile, indent=2)

        full_prompt = f"{system_prompt}\n\nInput Data:\nExisting Profile to be updated:{existing_profile_str}\nNew Data to be analyse for update:{input_data_str}\n\nPlease update the profile based on this information."

        response = update_profile_llm_connector.chat(full_prompt, model="gpt-4o-mini", temperature=0.0, max_tokens=8192, response_format='json')

        if response is None or 'text' not in response:
            raise ValueError("No valid response from LLM connector")

        response_text = response['text']
        if response_text.startswith("```json\n") and response_text.endswith("\n```"):
            response_text = response_text[8:-4]
        
        try:
            updated_profile = json.loads(response_text)
        except json.JSONDecodeError:
            raise ValueError("LLM response is not a valid JSON object")

        # Ensure user_summary and personality_report are dictionaries
        if existing_profile['user_summary'] is None:
            existing_profile['user_summary'] = {}
        if existing_profile['personality_report'] is None:
            existing_profile['personality_report'] = {}

        # Update the existing profile with the new information
        existing_profile = _deep_update(existing_profile, updated_profile)

        os.makedirs(os.path.dirname(profile_output_file_path), exist_ok=True)

        with open(profile_output_file_path, 'w') as f:
            json.dump(existing_profile, f, indent=2)

        if info: print(f"Profile updated successfully: {profile_output_file_path}")

    except Exception as e:
        print(f"Error updating profile: {e}")
        import traceback
        traceback.print_exc()

# Helper functions
def _make_json_serializable(obj):
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    elif isinstance(obj, list):
        return [_make_json_serializable(item) for item in obj]
    elif isinstance(obj, dict):
        return {str(key): _make_json_serializable(value) for key, value in obj.items()}
    else:
        return str(obj)
    
def _format_chat_history(chat_history, session_id=None):
    formatted_messages = []
    for item in chat_history:
        try:
            role = 'human' if item['role'] == 'user' else 'chatbot'
            verb = 'says' if item['role'] == 'user' else 'replies'
            formatted_messages.append(f"{role} {verb}: {item['content']}")
        except Exception as e:
            print(f"Error formatting message in format_chat_history: {e}")
    return '\n'.join(formatted_messages)

def _filter_and_strip(chat_history):
    filtered = []
    for message in chat_history:
        try:
            if (isinstance(message, dict) and 'content' in message
                and "<subconscious>" not in message['content']
                and "<*ACCEPTED*>" not in message['content']):
                filtered.append({
                    'role': message.get('role', ''),
                    'content': message['content']
                })
        except Exception as e:
            print(f"Error processing message in filter_and_strip: {e}")
    return filtered

def _recover_malformed_data(text):
    # Remove any remaining quotes and split by commas
    items = text.replace('"', '').replace("'", "").split(',')
    # Strip whitespace from each item and remove empty items
    return [item.strip() for item in items if item.strip()]
    
def _load_session_index(user_id):
    file_path = f"users/{user_id}/session_history/session_index.json"
    if not os.path.exists(file_path):
        return {}
    with open(file_path, 'r') as f:
        return json.load(f)
    
def _load_session_history(user_id, session_id):
    file_path = f"users/{user_id}/session_history/{session_id}.json"
    if not os.path.exists(file_path):
        return []
    with open(file_path, 'r') as f:
        data = json.load(f)
        return data.get(session_id, [])
    

# Example usage
if __name__ == "__main__":
    user_id = "1100110010010_qa8"  # Example user ID
    load_and_process_chat_histories(user_id)
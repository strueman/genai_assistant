#this file will contain the code for the database management, file management, data storage and retrieval
from connector import LLMConnector
import json
import os
import ast
memories = []
def load_and_process_chat_histories(user_id):
    chat_histories = load_chat_histories(user_id)
    payload = []
    for session_id, chat_history in chat_histories.items():
        unconsolidated_items = [item for item in chat_history if not item.get('metadata', {}).get('consolidated', False)]
        
        if unconsolidated_items:
            payload.append(unconsolidated_items)
    process_unconsolidated_items(unconsolidated_items)
    print(len(unconsolidated_items))
    for session_id, chat_history in chat_histories.items():
        for item in chat_history:
            item['metadata']['consolidated'] = True
    update_chat_histories(user_id, chat_histories)
    #save_memories_to_file()
    #update_chat_histories(user_id, chat_histories)

def load_chat_histories(user_id):
    file_path = f"users/{user_id}/chat_histories.json"
    if not os.path.exists(file_path):
        return {}
    with open(file_path, 'r') as f:
        return json.load(f)

def process_unconsolidated_items(items):
    for item in items:
        resp = llm_consolidation(data=item)
        # if resp:
        #     # Ensure resp is JSON serializable
        #     serializable_resp = make_json_serializable(resp)
        #     memories.append(serializable_resp)
        # item['metadata']['consolidated'] = True
       # print(serializable_resp)
    # Save memories to file after all items have been processed
    save_memories_to_file()
    
    

def save_memories_to_file():
    file_path = 'memories.json'
    
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
    
    print(f"Saved {len(memories)} new memories. Total memories: {len(combined_memories)}")

    # Clear the global memories list after saving
    memories.clear()

# def make_json_serializable(obj):
#     if isinstance(obj, (str, int, float, bool, type(None))):
#         return obj
#     elif isinstance(obj, list):
#         return [make_json_serializable(item) for item in obj]
#     elif isinstance(obj, dict):
#         return {str(key): make_json_serializable(value) for key, value in obj.items()}
#     else:
#         return str(obj)

def update_chat_histories(user_id, chat_histories):
    file_path = f"users/{user_id}/chat_histories.json"
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w') as f:
        json.dump(chat_histories, f, indent=2)

def llm_consolidation(data):
    #system_prompt = open("prompts/consolidation_prompt.md", "r").read()
    
    system_prompt = open("prompts/user_info_prompt.md", "r").read()
    
    connector_openai = LLMConnector(provider='openai')
    response_openai = connector_openai.chat(
        str(data),
        functions=None,#['get_current_date','ask_tavily'],''
        system_prompt=system_prompt,
        model="gpt-4o-mini",
        max_tokens=1500)
    
    if response_openai['text']:
        processed_data = process_llm_response(response_openai['text'])
        if processed_data:
            memories.append(processed_data)
            print(json.dumps(processed_data, indent=2) + '\n')
    
    return memories

def process_llm_response(response):
    try:
        # First, try to parse as JSON
        cleaned_response = response.strip().replace('\n', '').replace('\\', '')
        data = json.loads(cleaned_response)
    except json.JSONDecodeError:
        try:
            # If JSON parsing fails, try to evaluate as a Python literal
            data = ast.literal_eval(cleaned_response)
        except (SyntaxError, ValueError):
            # If both methods fail, attempt to recover the data
            data = recover_malformed_data(cleaned_response)
    
    # Ensure the result is a list
    if isinstance(data, list):
        return data
    elif isinstance(data, str):
        return [data]
    else:
        return None

def recover_malformed_data(text):
    # Remove any remaining quotes and split by commas
    items = text.replace('"', '').replace("'", "").split(',')
    # Strip whitespace from each item and remove empty items
    return [item.strip() for item in items if item.strip()]

# Example usage
if __name__ == "__main__":
    user_id = "1100110010010_qa8"  # Example user ID
    load_and_process_chat_histories(user_id)

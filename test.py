import warnings
import logging
import json, os
from memory_system import MemorySystem
import concurrent.futures
# Suppress warnings from mem0
warnings.filterwarnings("ignore", category=UserWarning, module="mem0")
logging.getLogger('chromadb.segment.impl.vector.local_persistent_hnsw').setLevel(logging.ERROR)
# Create an instance of MemorySystem
user_id = "1100110010010_qa8"
memory_system = MemorySystem(user_id=user_id)
info = True
def load_memories(user_id):
    file_path = f'users/{user_id}/memories.json'
    existing_memories = []
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            try:
                existing_memories = json.load(f)
            except json.JSONDecodeError:
                print("Error reading existing memories file. Starting with empty memories.")
    result = _add_memories_to_db(memories=existing_memories, user_id=user_id)
    return result

def _add_memories_to_db(memories=None, user_id=None):
    memory_system = MemorySystem(user_id=user_id)

    def process_memory(item):
        if 'data' in item:
            data = item['data']
        else:
            data = item['summary']
        
        metadata = {}
        if 'metadata' in item and isinstance(item['metadata'], list):
            for meta in item['metadata']:
                if isinstance(meta, dict):
                    metadata.update(meta)
                else:
                    metadata['tag'] = meta
        
        if 'session_id' in item:
            metadata['session_id'] = item['session_id']
        
        try:
            result = memory_system.add_memory(memory=data, user_id=user_id, metadata=metadata)
            return result
        except Exception as e:
            try:
                print(f"Error adding memory: {e}")
                print("Retrying with default user ID...")
                result = memory_system.add_memory(memory=data, user_id="1100110010010_qa8", metadata=metadata)
                return result
            except Exception as e:
                print(f'Failed to add memory: {e}')
                return None

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(process_memory, memories))
    
    successful_additions = sum(1 for result in results if result is not None)
    if info:
        print(f"Successfully added {successful_additions} out of {len(memories)} memories to the database.")

    return #results

def _save_memories_to_file(memories=None, user_id=None):
    for item in memories:
        if 'data' in item:
            data = item['data']
        else:
            data = item['summary']
        
        metadata = {}
        if 'metadata' in item and isinstance(item['metadata'], list):
            for meta in item['metadata']:
                if isinstance(meta, dict):
                    metadata.update(meta)
                else:
                    metadata['tag'] = meta
        
        if 'session_id' in item:
            metadata['session_id'] = item['session_id']
        try: 
            result = memory_system.add_memory(memory=data, user_id="1100110010010_qa8", metadata=metadata)
 
        except Exception as e:
            try:
                print(e)
                result = memory_system.add_memory(memory=data, user_id="1100110010010_qa8", metadata=metadata)
            except:
                print('Failed to add memory')
                pass
    return 'done'

def find_memory(user_id=None,query=None):
    memory_system = MemorySystem(user_id=user_id)
    output = memory_system.search(query=query,user_id=user_id)
    sorted_results = sorted(output['results'], key=lambda x: x['score'])[:3]
    payload = []
    for item in sorted_results:
        if item['score'] < 1:
  
            if item['updated_at']:
                timestamp = item['updated_at']
            else:
                timestamp = item['created_at']  
            memory = f"Memory from {timestamp}, in chat session ID {item['metadata']['session_id']}, The memory is, '{item['memory']}'."
            payload.append(memory)
    if len(payload) == 0:
        return None
    result = '. '.join(payload)
    return result
print(find_memory(user_id=user_id,query='Detailed the intricacies of geothermal energy'))

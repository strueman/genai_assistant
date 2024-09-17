import threading
import time
import json
from typing import List, Dict, Any
from connector import LLMConnector
import uuid
import os
import logging
from filelock import FileLock, Timeout
import tiktoken
from datetime import datetime
import data_management
from memory_system import MemorySystem
from plugins.cache_api import APICache
# Set up logging
logging.basicConfig(level=logging.CRITICAL)
logger = logging.getLogger(__name__)

class ContextManager:#                      max_tokens = is limit to triger summerising current chat history
    def __init__(self, llm_connector: LLMConnector, max_history_tokens: int = 32768, 
                 save_interval: int = 120, user_id: str = '', session_id = None):
        self.livefeed_indices = []
        self.first_run = True
        self.llm_connector = llm_connector
        self.cache_time = datetime.now().timestamp()
        self.max_history_tokens = max_history_tokens
        self.save_interval = save_interval
        self.last_save_time = time.time()
        self.history_lock = threading.Lock()
        self.save_lock = threading.Lock()
        self.user_id = user_id
        self.session_id = session_id
        # File paths
        self.main_system_prompt_path = 'prompts/main_chat.md'
        self.user_path = f'users/{self.user_id}/'
        self.profile_path = f'{self.user_path}user_profile.json'
        with open(self.profile_path, 'r') as f:
            self.user_profile_dict = json.loads(f.read())
        self.user_profile = json.dumps(self.user_profile_dict)
        with open(self.main_system_prompt_path, 'r') as f:
            self.main_system_prompt = f.read()
        self.main_system_prompt = json.dumps(self.main_system_prompt)
        self.chat_history: List[Dict[str, Any]] = []
        self.current_token_count = 0
        self.encoder = tiktoken.encoding_for_model("gpt-4o-mini")  # or whichever model you're using

        self.session_index_file = f'{self.user_path}session_history/session_index.json'
        self.shutdown_lock = threading.Lock()

        self.start_new_session()  # This replaces the direct session_id assignment
      

    def get_user_timezone(self):
        offset= self.user_profile_dict["timezone"]["offset"]
        name = self.user_profile_dict["timezone"]["name"]
        return f"{name}, ({offset})"
 

    def start_new_session(self):
        if self.session_id is None: 
            self.session_id = str(uuid.uuid4())
            self.chat_history = []
            self.history_path = f'{self.user_path}session_history/'
            self.history_file = f'{self.history_path}{self.session_id}.json'
            os.makedirs(os.path.dirname(self.history_path), exist_ok=True)
            is_new_session = True
        else:
            # Resuming an existing session
            self.history_path = f'{self.user_path}session_history/'
            self.history_file = f'{self.history_path}{self.session_id}.json'
            self.load_history(self.session_id)
            is_new_session = False

        self.current_token_count = 0
        self.last_save_time = time.time()

        try: #Insert initial memory context, user profile and previous session summaries
            recent_summaries = self.get_recent_summaries()
            self.last_session_summary = recent_summaries["latest"]["Summary"]
            self.last_session_date = recent_summaries["latest"]["Date"]
            self.previous_session_summary = recent_summaries["previous"]["Summary"] if recent_summaries["previous"] else "No previous session summary available."
            self.previous_session_date = recent_summaries["previous"]["Date"] if recent_summaries["previous"] else "No previous session date available."
            self.older_session_summary = recent_summaries["older"]["Summary"] if recent_summaries["older"] else "No older session summary available."
            self.older_session_date = recent_summaries["older"]["Date"] if recent_summaries["older"] else "No older session date available."
        except Exception as e:
            logger.error(f"Error getting recent summaries: {str(e)}")
            self.last_session_summary = "No previous session summary available."
            self.last_session_date = "No previous session date available."
            self.previous_session_summary = "No previous session summary available."
            self.previous_session_date = "No previous session date available."
            self.older_session_summary = "No older session summary available."
            self.older_session_date = "No older session date available."

        
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            message = f"""Current time: {current_time} User timezone: {self.get_user_timezone()}
            Older session date: {self.older_session_date}
            Older session summary: {self.older_session_summary}
            Previous session date: {self.previous_session_date}
            Previous session summary: {self.previous_session_summary}                                        
            Latest session date: {self.last_session_date} 
            Latest session summary: {self.last_session_summary}
            Profile summary of your user: {json.loads(self.user_profile)['user_profile_summary']}"""
            self.subconscious_injection(message=message, relevance='bypass',reply="I acknowledge the subconscious data injection, I will keep that in mind")
        except Exception as e:
            print(f"Error in subconscious_injection: {str(e)}")
        self._update_session_index(is_new_session)
        
    def _update_session_index(self, is_new_session: bool):
        try:
            with self.save_lock:
                if os.path.exists(self.session_index_file):
                    with open(self.session_index_file, 'r') as f:
                        session_index = json.load(f)
                else:
                    session_index = {}

                timestamp = str(int(time.time()))
                
                if is_new_session:
                    session_index[self.session_id] = {
                        "timestamp": timestamp,
                        "summary": "New session started",
                        "consolidated": False
                    }
                else:
                    # Update existing session
                    if self.session_id in session_index:
                        session_index[self.session_id]["timestamp"] = timestamp
                        session_index[self.session_id]["consolidated"] = False
                        # Keep the existing summary
                    else:
                        # If somehow the session_id is not in the index, treat it as a new session
                        session_index[self.session_id] = {
                            "timestamp": timestamp,
                            "summary": "Resumed session",
                            "consolidated": False
                        }

                with open(self.session_index_file, 'w') as f:
                    json.dump(session_index, f, indent=2)
        except Exception as e:
            logger.error(f"Error updating session index: {str(e)}")

    def add_message(self, role: str, content: str, inject=False, metadata: Dict[str, Any] = None) -> None:
        if metadata is None:
            metadata = {"consolidated": False}
        else:
            metadata.setdefault("consolidated", False)
        
        if inject:
            try:
                new_message = ({
                    "role": 'user',
                    "content": inject,
                    "metadata": metadata
                },
                {
                    "role": 'assistant',
                    "content": '<^>',
                    "metadata": metadata
                })
            except Exception as e:
                print('Error in inject', e)
        else:
            new_message = {
                "role": role,
                "content": content,
                "metadata": metadata
            }
        
        new_message_tokens = len(self.encoder.encode(content))
        
        if self.current_token_count + new_message_tokens > self.max_history_tokens:
            self._condense_context_length()
        
        if isinstance(new_message, tuple):
            self.chat_history.extend(new_message)
            self.current_token_count += sum(len(self.encoder.encode(msg['content'])) for msg in new_message)
        else:
            self.chat_history.append(new_message)
            self.current_token_count += new_message_tokens
        
        if '<live!feed>' in content and role == 'user':
            self.livefeed_indices.append(len(self.chat_history) - 1)
        
        self._check_save_history()

    def _condense_context_length(self) -> None: # Sumerises part of the chat history to reduce the context length
        if len(self.chat_history) < 4:  # Need at least 4 messages to consolidate
            return

        midpoint = len(self.chat_history) // 2
        to_summarize = self.chat_history[:midpoint]
        
        summary_prompt = "Summarize the following conversation, preserving key points and context:\n\n"
        for msg in to_summarize:
            summary_prompt += f"{msg['role'].capitalize()}: {msg['content']}\n\n"
        
        summary_response = self.llm_connector.chat(summary_prompt, model="gpt-4o-mini")
        summary = summary_response.get('text', '')
        consolidated_message = {
            "role": "system",
            "content": f"[Summary of previous messages: {summary}]",
            "metadata": {"consolidated": True}
        }
        
        # Replace the summarized messages with the consolidated message
        self.chat_history = [consolidated_message] + self.chat_history[midpoint:]
        
        # Recalculate token count
        self.current_token_count = sum(len(self.encoder.encode(msg['content'])) for msg in self.chat_history)

    def send_message(self, user_prompt: str, system_prompt=None,functions=None, subcon=False, **kwargs) -> Dict:
        try:
            #self.inject_feeds(cache_duration=300)
            #  if tool_calls is None and function_call is None:
            if subcon == False:
                memory = self.find_memory(user_id=self.user_id, query=user_prompt)
                if memory is not None:
                    self.inject_memory(user_id=self.user_id, memory=memory, user_prompt=user_prompt) 
                    
            context = self._prepare_context(system_prompt)
            full_prompt = f"{context}\n\nUser: {user_prompt}"
            self.add_message("user", user_prompt)
            response = self.llm_connector.chat(full_prompt, system_prompt=system_prompt, functions=functions, **kwargs)
            if response is None:
                return {"error": "No response from LLM connector"}
            if "<live!feed>" in response.get('text', ''):
                print("Live feed detected in response")
                self.inject_feeds(cache_duration=None)

            assistant_message = response.get('text', '')
            self.add_message("assistant", assistant_message)
            self._handle_function_call(response)

            response['session_id'] = self.session_id
            return response
        except Exception as e:
            print('Error in send_message', user_prompt)
            print(f"Error details: {str(e)}")
            return {"error": str(e)}

    def _handle_function_call(self, response: Dict) -> None:
        if not response:
            print("Error: Empty response in _handle_function_call")
            return

        function_call = response.get('function_call')

        tool_calls = response.get('tool_calls', [])

        if not function_call and tool_calls and isinstance(tool_calls, list) and len(tool_calls) > 0:
            function_call = tool_calls[0]

        if function_call:
            function_name = function_call.get('name') or function_call.get('function', {}).get('name')
            function_args = function_call.get('arguments') or function_call.get('function', {}).get('arguments')

            if function_name and function_args:
                self.add_message("function", f"Called {function_name} with args: {function_args}")
                
                if function_name == 'reddit_summary':
                    from plugins.tools.reddit_summary import reddit_summary
                    try:
                        result = reddit_summary(**json.loads(function_args))
                    except Exception as e:
                        print(f"Error calling {function_name}: {str(e)}")
        else:
            return

    def _prepare_context(self, system_prompt=None) -> str:
        if system_prompt:
             context = f"System: {system_prompt}\n\n"
        else:
            context = ""
        for message in self.chat_history:
            role = message['role'].capitalize()
            content = message['content']
            context += f"{role}: {content}\n\n"
        return context.strip()

    def save_history(self) -> None:
        """Save the chat history to a JSON file, updating only the current session."""
        with self.history_lock:
            with self.save_lock:
                histories = {}
                if os.path.exists(self.history_file):
                    with open(self.history_file, 'r') as f:
                        try:
                            histories = json.load(f)
                        except json.JSONDecodeError:
                            print("Error reading existing history file. Creating a new one.")

                # Update only the current session
                histories[self.session_id] = self.chat_history

                with open(self.history_file, 'w') as f:
                    json.dump(histories, f, indent=2)

        self.last_save_time = time.time()  # Update the last save time
        #self.update_profile()

    def load_history(self, session_id: str) -> None:
        try:
            with self.save_lock:
                if os.path.exists(self.history_file):
                    with open(self.history_file, 'r') as f:
                        histories = json.load(f)
                    
                    if session_id in histories:
                        with self.history_lock:
                            loaded_history = histories[session_id]
                            # Ensure all loaded messages have the metadata structure
                            for message in loaded_history:
                                if 'metadata' not in message:
                                    message['metadata'] = {"consolidated": False}
                                elif 'consolidated' not in message['metadata']:
                                    message['metadata']['consolidated'] = False
                            self.chat_history = loaded_history
                            self.current_token_count = sum(len(self.encoder.encode(msg['content'])) for msg in self.chat_history)
                    else:
                        logger.info(f"No history found for session {session_id}. Starting a new session.")
                        self.chat_history = []
                else:
                    logger.info("No chat history file found. Starting a new session.")
                    self.chat_history = []
        except Exception as e:
            logger.error(f"Error loading chat history: {str(e)}")
            self.chat_history = []

    def _shutdown(self):
        try:
            with self.shutdown_lock:
                #logger.info("Initiating shutdown...")
                self.save_history()
                print("Memory Consolidation.......")
                data_management.load_and_process_chat_histories(user_id=self.user_id)
                print('Cleaning up........')
                self.cleanup()
                print("Shutdown completed successfully")
                logger.info("Shutdown completed successfully")
        except Exception as e:
            logger.error(f"Error during shutdown: {str(e)}")
        finally:
            logger.info("Shutdown process finished")

    def cleanup(self):
        logger.info("Starting cleanup...")
        # Cancel any scheduled tasks
        if hasattr(self, 'save_timer'):
            self.save_timer.cancel()
            logger.info("Save timer cancelled")
        print("Closing threads........")
        # Join any running threads
        for thread in threading.enumerate():
            if thread != threading.current_thread() and thread.is_alive():
                logger.info(f"Attempting to join thread: {thread.name}")
                thread.join(timeout=5.0)  # Wait up to 5 seconds for each thread
                if thread.is_alive():
                    logger.warning(f"Thread {thread.name} did not terminate within timeout")
        logger.info("Cleanup completed")


    def get_session_id(self) -> str:
        return self.session_id

    def _check_save_history(self) -> None:
        current_time = time.time()
        if current_time - self.last_save_time >= self.save_interval:
            self.save_history()

    def relevance_filter(self, injection_data: str, relevance_threshold: float = 0.6, relevance=None, reply=None) -> None:
        recent_history = self.get_recent_history(num_pairs=5)  # Get last 5 message pairs
        print('relevance', relevance)
        try:
            if not isinstance(injection_data, str):
                raise ValueError("Injection data is not a string")
            if reply is None:
                reply = "I acknowledge the data injection, I will keep that in mind"
            if not isinstance(reply, str):
                reply = "Acknowledged subconscious"
        except:    
            print('Error relevance_filter @ string check', e)
            return
        if relevance == 'bypass':
            print('relevance is true')
            try:
                print("Injection_data Type:",type(injection_data))
                message=injection_data
                self.add_message(role='user', content=message)
                print("reply:", reply)
                self.add_message(role='assistant', content=reply)
                return              
            except Exception as e:
                print('Error relevance_filter @ relevance bypass', e)
        # Load the system prompt from the file
        relevance_prompt_path = 'prompts/relevance.md'
        with open(relevance_prompt_path, 'r') as f:
            system_prompt = f.read()
        
        llm_input = f"Recent conversation:\n{recent_history}\n\nInjection data:\n{injection_data}"
        llm_con = LLMConnector(provider="openai")
        response = llm_con.chat(llm_input, system_prompt=system_prompt, model="gpt-4o-mini", provider="openai", functions=None, response_format='json')
        print(response['text'])
        # Parse the JSON response
        try:
            result = json.loads(response['text'])
            relevance_score = float(result['relevance_score'])
            reasoning = result['chain_of_thought_reasoning']
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Error parsing LLM response: {e}")
            return
        if reply is None:
            reply = "Acknowledged subconscious"
        if relevance_score > relevance_threshold:
            self.add_message(role='user', content=injection_data)
            self.add_message(role='assistant', content=f"Acknowledged. This information is relevant (score: {relevance_score}). Reasoning: {reasoning}")
        else:
            print(f"Information not injected. Relevance score: {relevance_score}. Reasoning: {reasoning}")

    def get_recent_history(self, num_pairs: int) -> str:
        recent_messages = self.chat_history[-2*num_pairs:]
        return "\n".join([f"{msg['role']}: {msg['content']}" for msg in recent_messages])

    def subconscious_injection(self, message: str, relevance=None, reply="Acknowledged subconscious") -> None:
        try:
            message = "<subconscious>" + message + "</subconscious>"
            self.relevance_filter(message, relevance=relevance, reply=reply)
        except Exception as e:
            print(f"Error in subconscious_injection: {str(e)}")

    def inject_feeds(self, cache_duration=None):
        cache = APICache(process_name='rss_feeds')
        try:
            feeds = cache.get_cache('news_brief')
            if feeds is None:
                print("No 'news_brief' found in cache")
                return
            feed = f"<live!feed>{feeds}</live!feed>\n\n"
            print(f"Injecting new feed")
            self.subconscious_injection(message=feed, relevance='bypass', reply="I acknowledge the livefeed data injection, I will keep that in mind")
        except Exception as e:
            print('Failed to inject livefeeds:', str(e))

    def find_memory(self,user_id=None,query=None):
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
                memory = f"Memory from {timestamp}, in chat session ID {item['metadata']['session_id']}, The memory is, '{item['memory'][:1500]}'."
                payload.append(memory)
        if len(payload) == 0:
            return None
        result = '. '.join(payload)
        return result
    
    def inject_memory(self, user_id=None, memory=None, user_prompt=None):
        try:
            print('\n\nMemory injected: ', memory,"\n\n")
            memory_message = f"[BACKGROUND INFORMATION START] {memory} [BACKGROUND INFORMATION END]. IMPORTANT: This is not part of the current conversation. It's contextual information to enhance your understanding. Do not respond to this directly or treat it as user input."
            reply = "I've processed the background information and will use it to inform my responses if relevant."
            self.subconscious_injection(message=memory_message, reply=reply)
        except Exception as e:
            print('Failed to inject memory')
            print(e)
            self.send_message(user_prompt=user_prompt, system_prompt=self.main_system_prompt, user_id=user_id , subcon=False)

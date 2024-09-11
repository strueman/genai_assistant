import threading
import time
import json
from typing import List, Dict, Any
from connector import LLMConnector
import uuid
import os
import re
import logging
from filelock import FileLock, Timeout
import tiktoken
from datetime import datetime
import data_management
# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ContextManager:#                      max_tokens = is limit to triger summerising current chat history
    def __init__(self, llm_connector: LLMConnector, max_history_tokens: int = 32768, 
                 save_interval: int = 120, user_id: str = '', session_id = None):
        self.llm_connector = llm_connector
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
            self.user_profile = json.loads(f.read())
        self.user_profile = json.dumps(self.user_profile)
        with open(self.main_system_prompt_path, 'r') as f:
            self.main_system_prompt = f.read()
        self.main_system_prompt = json.dumps(self.main_system_prompt)
        self.chat_history: List[Dict[str, Any]] = []
        self.current_token_count = 0
        self.encoder = tiktoken.encoding_for_model("gpt-4o-mini")  # or whichever model you're using

        self.session_index_file = f'{self.user_path}session_history/session_index.json'
        self.shutdown_lock = threading.Lock()

        self.start_new_session()  # This replaces the direct session_id assignment

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
        print(self.history_path)

        try:
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

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:    
            self.subconscious_injection(message=f"""Current time: {current_time}
            Older session date: {self.older_session_date}
            Older session summary: {self.older_session_summary}
            Previous session date: {self.previous_session_date}
            Previous session summary: {self.previous_session_summary}                                        
            Latest session date: {self.last_session_date}
            Latest session summary: {self.last_session_summary}
            Profile of your user: {self.user_profile}""")
        except Exception as e:
            logger.error(f"Error in subconscious_injection: {str(e)}")
       # self.subconscious_injection(message=self.user_profile)
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

    def add_message(self, role: str, content: str, metadata: Dict[str, Any] = None) -> None:
        if metadata is None:
            metadata = {"consolidated": False}
        else:
            metadata.setdefault("consolidated", False)

        new_message = {
            "role": role,
            "content": content,
            "metadata": metadata
        }
        
        new_message_tokens = len(self.encoder.encode(content))
        
        if self.current_token_count + new_message_tokens > self.max_history_tokens:
            self._condense_context_length()
        
        self.chat_history.append(new_message)
        self.current_token_count += new_message_tokens
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

    def send_message(self, user_prompt: str,system_prompt=None, **kwargs) -> Dict:
        try:
            context = self._prepare_context(system_prompt)
            full_prompt = f"{context}\n\nUser: {user_prompt}"
            self.add_message("user", user_prompt)

            response = self.llm_connector.chat(full_prompt, **kwargs)

            if response is None:
                return {"error": "No response from LLM connector"}

            assistant_message = response.get('text', '')
            self.add_message("assistant", assistant_message)
            self._handle_function_call(response)

            # Parse and store tagged information
            #self._parse_and_store_tags(assistant_message)

            response['session_id'] = self.session_id
            return response
        except Exception as e:
            return {"error": str(e)}

    def _handle_function_call(self, response: Dict) -> None:
        if not response:
            return

        function_call = response.get('function_call')
        if not function_call:
            tool_calls = response.get('tool_calls', [])
            if tool_calls and isinstance(tool_calls, list) and len(tool_calls) > 0:
                function_call = tool_calls[0]
        
        if function_call:
            function_name = function_call.get('name') or function_call.get('function', {}).get('name')
            function_args = function_call.get('arguments') or function_call.get('function', {}).get('arguments')
            if function_name and function_args:
                self.add_message("function", f"Called {function_name} with args: {function_args}")

    def _prepare_context(self, system_prompt: str) -> str:
        context = f"System: {system_prompt}\n\n" if system_prompt else ""
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
                logger.info("Initiating shutdown...")
                self.save_history()
                data_management.load_and_process_chat_histories(user_id=self.user_id)
               # self._update_session_summary()
                self.cleanup()
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

        # Join any running threads
        for thread in threading.enumerate():
            if thread != threading.current_thread() and thread.is_alive():
                logger.info(f"Attempting to join thread: {thread.name}")
                thread.join(timeout=5.0)  # Wait up to 5 seconds for each thread
                if thread.is_alive():
                    logger.warning(f"Thread {thread.name} did not terminate within timeout")

        # Close any other resources (e.g., database connections)
        # self.db_connection.close()  # Uncomment if you have a database connection

        logger.info("Cleanup completed")


    def get_session_id(self) -> str:
        return self.session_id

    def _check_save_history(self) -> None:
        current_time = time.time()
        if current_time - self.last_save_time >= self.save_interval:
            self.save_history()

    def subconscious_injection(self, message: str) -> None:
        try:
            message = "<subconscious>"+message+" don't add this information the the user profile, just keep it in your mind</subconscious>"
            response = self.send_message(
                    user_prompt=message,
                    model='gpt-4o-mini',
                    functions=None,
                    system_prompt=self.main_system_prompt,
                    max_tokens=50,
                    temperature=0.0
                )
                
        except Exception as e:
            logger.error(f"Error in subconscious_injection: {str(e)}")

    def get_recent_summaries(self) -> Dict[str, Any]:
        try:
            with open(self.session_index_file, 'r') as f:
                session_index = json.load(f)
            
            if not session_index:
                return {
                    "latest": {"Date": "No date available", "Summary": "No sessions found."},
                    "previous": None,
                    "older": None
                }
            
            # Sort sessions by timestamp in descending order
            def get_timestamp(item):
                session_id, entry = item
                return int(entry.get('timestamp', 0))

            sorted_sessions = sorted(session_index.items(), key=get_timestamp, reverse=True)
            
            summaries = []
            for session_id, entry in sorted_sessions[:3]:  # Get up to 3 most recent sessions
                timestamp = entry.get('timestamp', '')
                summary_data = entry.get('summary', {})
                
                if isinstance(summary_data, dict):
                    summary = summary_data.get('summary', 'No summary available')
                else:
                    summary = str(summary_data) if summary_data else 'No summary available'
                
                if timestamp:
                    date_time = datetime.fromtimestamp(int(timestamp))
                    formatted_date = date_time.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    formatted_date = "Date not available"
                
                summaries.append({"Date": formatted_date, "Summary": summary})
            
            result = {
                "latest": summaries[0] if summaries else {"Date": "No date available", "Summary": "No sessions found."},
                "previous": summaries[1] if len(summaries) > 1 else None,
                "older": summaries[2] if len(summaries) > 2 else None
            }
            
            return result
        except FileNotFoundError:
            return {
                "latest": {"Date": "No date available", "Summary": "No session index file found."},
                "previous": None,
                "older": None
            }
        except json.JSONDecodeError:
            return {
                "latest": {"Date": "No date available", "Summary": "Error reading session index file."},
                "previous": None,
                "older": None
            }
        except Exception as e:
            logger.error(f"Error getting recent summaries: {str(e)}")
            return {
                "latest": {"Date": "No date available", "Summary": "Error retrieving summaries."},
                "previous": None,
                "older": None
            }
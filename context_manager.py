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

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ContextManager:#                      max_tokens = is limit to triger summerising current chat history
    def __init__(self, llm_connector: LLMConnector, max_history_tokens: int = 32768, 
                 save_interval: int = 120, user_id: str = '', session_id = None):
        self.llm_connector = llm_connector
        self.update_profile_llm_connector = LLMConnector(provider='openai')
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
        self.user_info_file = f'{self.user_path}user_info_data.json'
        self.useful_info_file = f'{self.user_path}useful_info_data.json'

        self.profile_system_prompt_path = 'prompts/update_profile.md'
        self.profile_data_file_path = f'{self.user_path}user_info_data.json'
        self.profile_output_file_path = f'{self.user_path}user_profile.json'

        self.profile_data_lock = FileLock(f"{self.profile_data_file_path}.lock", timeout=10)     
        with open(self.profile_output_file_path, 'r') as f:
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
            os.makedirs(os.path.dirname(self.history_path), exist_ok=True)
        self.history_path = f'{self.user_path}session_history/'
        self.history_file = f'{self.history_path}{self.session_id}.json'
        if self.session_id is not None:
            self.chat_history = []
            self.load_history(self.session_id)

        self.current_token_count = 0
        self.last_save_time = time.time()
        print(self.session_id)
        # Call any additional functions or perform any actions needed for a new session
        try:
            self.last_session_summary = self.get_latest_summary()["Summary"]
            self.last_session_date = self.get_latest_summary()["Date"]
        except Exception as e:
            self.last_session_summary = "No previous session summary available."
            self.last_session_date = "No previous session date available."
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:    
            self.subconscious_injection(message=f"Current time: {current_time}\nLast session date: {self.last_session_date}\nLast session summary: {self.last_session_summary}\nProfile of your user: {self.user_profile}")
        except Exception as e:
            logger.error(f"Error in subconscious_injection: {str(e)}")
       # self.subconscious_injection(message=self.user_profile)
        self._update_session_index()
        
    def _update_session_index(self):
        try:
            with self.save_lock:
                if os.path.exists(self.session_index_file):
                    with open(self.session_index_file, 'r') as f:
                        session_index = json.load(f)
                else:
                    session_index = {}

                timestamp = str(int(time.time()))
                session_index[self.session_id] = {
                    "timestamp": timestamp,
                    "summary": "New session started",
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
            self._consolidate_history()
        
        self.chat_history.append(new_message)
        self.current_token_count += new_message_tokens
        self._check_save_history()

    def _consolidate_history(self) -> None:
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
            self._parse_and_store_tags(assistant_message)

            response['session_id'] = self.session_id
            return response
        except Exception as e:
            return {"error": str(e)}

    def _parse_and_store_tags(self, message: str) -> None:
        try:
            self._parse_and_store_user_info(message)
            self._parse_and_store_useful_info(message)
            self._handle_long_term_memory(message)
        except Exception as e:
            logger.error(f"Error parsing tags: {str(e)}")

    def _parse_and_store_user_info(self, message: str) -> None:
        user_info_tags = self._safe_findall(r'<userinfo>(.{1,500}?)</userinfo>', message, limit=5)
        if user_info_tags:
            try:
                with self.profile_data_lock:
                    try:
                        with open(self.profile_data_file_path, 'r+') as f:
                            user_info_data = json.load(f)
                    except (json.JSONDecodeError, FileNotFoundError):
                        user_info_data = {}

                    for info in user_info_tags:
                        user_info_data[str(uuid.uuid4())] = {
                            "session_id": self.session_id,
                            "timestamp": time.time(),
                            "info": info.strip()
                        }

                    with open(self.profile_data_file_path, 'w') as f:
                        json.dump(user_info_data, f, indent=2)
            except Timeout:
                logger.error(f"Timeout while trying to acquire lock for {self.profile_data_file_path}")
            except Exception as e:
                logger.error(f"Error storing user info: {str(e)}")

    def _parse_and_store_useful_info(self, message: str) -> None:
        useful_info_tags = self._safe_findall(r'<useful_info>(.{1,1000}?)</useful_info>', message, limit=5)
        if useful_info_tags:
            with self.save_lock:
                try:
                    if os.path.exists(self.useful_info_file):
                        with open(self.useful_info_file, 'r') as f:
                            useful_info_data = json.load(f)
                    else:
                        useful_info_data = {}

                    for info in useful_info_tags:
                        useful_info_data[str(uuid.uuid4())] = {
                            "session_id": self.session_id,
                            "timestamp": time.time(),
                            "info": info.strip()
                        }

                    with open(self.useful_info_file, 'w') as f:
                        json.dump(useful_info_data, f, indent=2)
                except Exception as e:
                    logger.error(f"Error storing useful info: {str(e)}")

    def _handle_long_term_memory(self, message: str) -> None:
        access_tags = self._safe_findall(r'<access_long_term_memory>(.{1,500}?)</access_long_term_memory>', message, limit=3)
        store_tags = self._safe_findall(r'<store_long_term_memory>(.{1,1000}?)</store_long_term_memory>', message, limit=3)

        for tag in access_tags:
            self._trigger_long_term_memory_function("access", tag.strip())

        for tag in store_tags:
            self._trigger_long_term_memory_function("store", tag.strip())

    def _safe_findall(self, pattern: str, string: str, timeout: int = 3, limit: int = 30) -> List[str]:
        def _findall_with_timeout(pattern, string, result):
            try:
                matches = re.findall(pattern, string, re.DOTALL)
                result.extend(matches[:limit])
            except Exception as e:
                logger.error(f"Error in regex operation: {str(e)}")

        result = []
        thread = threading.Thread(target=_findall_with_timeout, args=(pattern, string, result))
        thread.start()
        thread.join(timeout)
        
        if thread.is_alive():
            logger.warning(f"Regex timeout for pattern: {pattern}")
            return []
        
        return result

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
        self.update_profile()

    def load_history(self, session_id: str) -> None:
        try:
            with self.save_lock:
                if os.path.exists(self.history_file):
                    with open(self.history_file, 'r') as f:
                        histories = json.load(f)
                    
                    if session_id in histories:
                        with self.history_lock:
                            self.session_id = session_id
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
                        self.start_new_session()
                else:
                    logger.info("No chat history file found. Starting a new session.")
                    self.start_new_session()
        except Exception as e:
            logger.error(f"Error loading chat history: {str(e)}")
            self.start_new_session()

    def _shutdown(self):
        try:
            with self.shutdown_lock:
                logger.info("Initiating shutdown...")
                self.save_history()
                self._update_session_summary()
                self.cleanup()
                logger.info("Shutdown completed successfully")
        except Exception as e:
            logger.error(f"Error during shutdown: {str(e)}")
        finally:
            logger.info("Shutdown process finished")

    def cleanup(self):
        logger.info("Starting cleanup...")
        # Close any open file handles
        # if hasattr(self, 'history_file'):
        #     if isinstance(self.history_file, str):
        #         logger.warning("history_file is a string, not a file object. Skipping file close.")
        #     elif hasattr(self.history_file, 'closed'):
        #         if not self.history_file.closed:
        #             self.history_file.close()
        #             logger.info("History file closed")
        #     else:
        #         logger.warning("history_file doesn't have 'closed' attribute. Skipping file close.")

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

    # def _update_session_summary(self):
    #     try:
    #         summary = self._generate_session_summary()
    #         with self.save_lock:
    #             with open(self.session_index_file, 'r') as f:
    #                 session_index = json.load(f)
                
    #             for timestamp, session_data in session_index.items():
    #                 if session_data["session_id"] == self.session_id:
    #                     session_data["summary"] = ''
    #                    # session_data["consolidated"] = False
    #                     break

    #             with open(self.session_index_file, 'w') as f:
    #                 json.dump(session_index, f, indent=2)
    #     except Exception as e:
    #         logger.error(f"Error updating session summary: {str(e)}")

    def _generate_session_summary(self) -> str:
        summary_prompt = "Summarize the following conversation in a brief sentence:\n\n"
        for msg in self.chat_history[-10:]:  # Use last 10 messages for summary
            summary_prompt += f"{msg['role'].capitalize()}: {msg['content']}\n\n"
        
        summary_response = self.llm_connector.chat(summary_prompt, model="gpt-4o-mini", max_tokens=50)
        return summary_response.get('text', 'Session ended')

    def get_session_id(self) -> str:
        return self.session_id

    def _check_save_history(self) -> None:
        current_time = time.time()
        if current_time - self.last_save_time >= self.save_interval:
            self.save_history()

    def update_profile(self) -> None:
        thread = threading.Thread(target=self._update_profile_thread)
        thread.start()

    # def _update_profile_thread(self) -> None:
    #     try:
    #         with self.profile_data_lock.acquire(timeout=30):
    #             # Check if the profile data file is empty or doesn't exist
    #             if not os.path.exists(self.profile_data_file_path) or os.path.getsize(self.profile_data_file_path) == 0:
    #                 #logger.info("No new data to process. Skipping profile update.")
    #                 return

    #             # Load the data file
    #             with open(self.profile_data_file_path, 'r') as f:
    #                 input_data = json.load(f)

    #             # If the input data is empty (e.g., '{}'), return early
    #             if not input_data:
    #                 #logger.info("Input data is empty. Skipping profile update.")
    #                 return

    #             # Load the system prompt
    #             with open(self.profile_system_prompt_path, 'r') as f:
    #                 system_prompt = f.read().strip()

    #             # Prepare the input data as a string
    #             input_data_str = json.dumps(input_data, indent=2)
                
    #             # Load existing profile or create a new one from schema
    #             if os.path.exists(self.profile_output_file_path):
    #                 with open(self.profile_output_file_path, 'r') as f:
    #                     existing_profile = json.load(f)
    #             else:
    #                 # Load blank schema
    #                 schema_path = "plugins/users/default/profile_schema.json"
    #                 with open(schema_path, 'r') as f:
    #                     existing_profile = json.load(f)
                    
    #                 # Insert user_id
    #                 existing_profile['user_id'] = self.user_id

    #             existing_profile_str = json.dumps(existing_profile, indent=2)

    #             # Prepare the full prompt
    #             full_prompt = f"{system_prompt}\n\nInput Data:\nExisting Profile to be updated:{existing_profile_str}\nNew Data to be analyse for update:{input_data_str}\n\nPlease update the profile based on this information."

    #             # Call the LLM
    #             response = self.update_profile_llm_connector.chat(full_prompt, model="gpt-4o-mini", temperature=0.0, max_tokens=8192, response_format='json')

    #             if response is None or 'text' not in response:
    #                 raise ValueError("No valid response from LLM connector")

    #             # Parse the LLM's response
    #             response_text = response['text']
    #             # Remove markdown code block if present
    #             if response_text.startswith("```json\n") and response_text.endswith("\n```"):
    #                 response_text = response_text[8:-4]  # Remove ```json\n from start and \n``` from end
                
    #             try:
    #                 updated_profile = json.loads(response_text)
    #             except json.JSONDecodeError:
    #                 logger.error("Failed to parse LLM response as JSON. Response content:")
    #                 logger.error(response_text)
    #                 raise ValueError("LLM response is not a valid JSON object")

    #             # Update the existing profile with the new information
    #             self._deep_update(existing_profile, updated_profile)

    #             # Ensure the directory exists
    #             os.makedirs(os.path.dirname(self.profile_output_file_path), exist_ok=True)

    #             # Save the updated profile
    #             with open(self.profile_output_file_path, 'w') as f:
    #                 json.dump(existing_profile, f, indent=2)

    #             #logger.info(f"Profile updated successfully: {self.profile_output_file_path}")

    #             # Clear the input data file after successful update
    #             with open(self.profile_data_file_path, 'w') as f:
    #                 json.dump({}, f)

        except Timeout:
            logger.error(f"Timeout while trying to acquire lock for {self.profile_data_file_path}")
        except FileNotFoundError as e:
            logger.error(f"File not found: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decoding error: {str(e)}")
        except ValueError as e:
            logger.error(str(e))
        except Exception as e:
            logger.error(f"Unexpected error updating profile in thread: {str(e)}", exc_info=True)

    # def _deep_update(self, d, u):
    #     for k, v in u.items():
    #         if isinstance(v, dict):
    #             d[k] = self._deep_update(d.get(k, {}), v)
    #         else:
    #             d[k] = v
    #     return d

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

    def get_latest_summary(self) -> str:
        try:
            with open(self.session_index_file, 'r') as f:
                session_index = json.load(f)
            
            if not session_index:
                return "No sessions found."
            
            latest_timestamp = max(session_index.keys())
            latest_entry = session_index[latest_timestamp]
            
            # Convert Unix timestamp to human-readable date
            date_time = datetime.fromtimestamp(int(latest_timestamp))
            formatted_date = date_time.strftime("%Y-%m-%d %H:%M:%S")
            
            latest_summary = latest_entry["summary"]
            
            return f"Date: {formatted_date}\nSummary: {latest_summary}"
        except FileNotFoundError:
            return "No session index file found."
        except json.JSONDecodeError:
            return "Error reading session index file."
        except Exception as e:
            logger.error(f"Error getting latest summary: {str(e)}")
            return "Error retrieving latest summary."
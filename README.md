# Virtual Assistant Project

## Overview

This project aims to develop a highly modifiable and easily expandable virtual assistant program. The system is designed to be UI-independent, allowing for easy integration with various platforms such as web, mobile, and desktop. The core functionality is implemented in Python, utilizing OpenAI for LLM (Large Language Model) and Text Embedding, and Langchain as the framework to connect the LLM and Vector Database.

## Core Architecture

### Goals
- Develop a highly modifiable and easily expandable program.
- Design the system to be UI-independent for easy integration with various platforms.
- Use Python as the primary programming language.
- Utilize OpenAI for LLM and Text Embedding.
- Implement Langchain as the framework to connect LLM and Vector Database.

### Initial Features
- Create a Python program that can connect to any OpenAI-compatible LLM.
- Implement a config file system for easy editing of settings (endpoint, API keys, temperature, max_tokens, etc.).
- Develop an interface for viewing and changing settings.
- Implement a database to store chat history.

### Future Enhancements
- Design a modular architecture for plugins and mods.
- Add support for other OpenAI-compatible LLMs.
- Implement RAG (Retrieval-Augmented Generation) integration.
- Add web search and internet access capabilities.
- Develop file search functionality.
- Create a system to scrape, index, and store documentation from websites for RAG.
- Process saved chat histories for information extraction, categorization, and indexing.
- Develop a web-based UI for user interaction.
- Create a web-based admin interface for managing the database, configurations, and mods/plugins.


## ContextManager

The `ContextManager` class manages the context of conversations, including chat history, user profiles, and memory management.

### Initialization

```python
from context_manager import ContextManager
from connector import LLMConnector

llm_connector = LLMConnector(provider='openai')
context_manager = ContextManager(llm_connector, user_id='user123')
```

### Methods

- **start_new_session**: Initializes a new chat session.
- **add_message**: Adds a new message to the chat history.
- **send_message**: Sends a message to the LLM and processes the response.
- **save_history**: Saves the chat history.
- **load_history**: Loads the chat history.
- **update_profile**: Updates the user profile.
- **subconscious_injection**: Inject

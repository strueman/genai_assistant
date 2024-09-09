# from connector import LLMConnector

# # Test with OpenAI
# connector_openai = LLMConnector(provider='openai')
# response_openai = connector_openai.chat(
#     "What's today's date?",
#     functions=['get_current_date','ask_tavily'],
#     system_prompt="You are a helpful assistant. When asked about the current date, use the get_current_date function.",
#     model="gpt-4o-mini"
# )
# print("OpenAI tool response:", response_openai['text'])

# # Test with Anthropic
# connector_anthropic = LLMConnector(provider='anthropic')
# response_anthropic = connector_anthropic.chat(
#     "Get the current date.",
#     model="claude-3-5-sonnet-20240620",
#     functions=['get_current_date','ask_tavily']
# )
# print("Anthropic tool response:", response_anthropic['text'])

# # Test with OpenRouter
# connector_or = LLMConnector(provider='openrouter')
# response_or = connector_or.chat(
#     "whats the date, include a test sentenct as well",
#     model="openai/gpt-4o-mini",
#     functions=['get_current_date']
# )
# print("OpenRouter tool response:" , response_or['text'])

# Test with OpenAI - No function call
# connector_openai = LLMConnector(provider='openai')
# response_openai = connector_openai.chat(
#     "respond 'OK'",
#     #functions=['hi'],
#     system_prompt="You are a helpful assistant. When asked about the current date, use the get_current_date function.",
#     model="gpt-4o-mini"
# )
# print("OpenAI:", response_openai['text'])

# # Test with Anthropic
# connector_anthropic = LLMConnector(provider='anthropic')
# response_anthropic = connector_anthropic.chat(
#     "respond 'OK'",
#    # model="claude-3-5-sonnet-20240620",
#    # functions=['get_current_date']
# )
# print("Anthropic:", response_anthropic['text'])

# # Test with OpenRouter
# connector_or = LLMConnector(provider='openrouter')
# response_or = connector_or.chat(
#     "Hi! How are you? what is the date?",
#     model="google/gemini-flash-1.5-exp",
#     functions=['get_current_date']
# )
# print("OpenRouter:" , response_or['text'])

# from context_manager import ContextManager
# from connector import LLMConnector
# print("imports complete")
# connector_or = LLMConnector(provider='openai')
# context_manager = ContextManager(connector_or)
# print("context manager created")
# response = context_manager.send_message(
#     "Hi! How are you? what is the date?",
#     model="gpt-4o-mini",
#     functions=['get_current_date']
# )
# print("response received")
# print("Openai:", response['text'])

# # You can also access the chat history
# # print("\nChat History:")
# for message in context_manager.chat_history:
#     print(f"{message['role']}: {message['content']}")

from context_manager import ContextManager
from connector import LLMConnector
import logging

connector_openai = LLMConnector(provider='openrouter')
context_manager = ContextManager(connector_openai, log_level=logging.INFO)

print("Sending message through ContextManager")
response = context_manager.send_message(
    "Hi! How are you? what is the date?",
    model="google/gemini-flash-1.5-exp",
    functions=''#['get_current_date']
)
print("Response received from ContextManager")
print("OpenAI:", response.get('text', 'No response text'))

print("Test script completed")
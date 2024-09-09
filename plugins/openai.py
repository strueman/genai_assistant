import requests
import json
import os
import time
from requests.exceptions import RequestException

def send_request(api_key, messages, model, temperature, max_tokens, function_schemas=None, max_retries=3, initial_delay=2,response_format=None):
    if response_format =='json':
        response_format={"type": "json_object"}
    else:
        response_format={"type": "text"}
   # print(f"OpenAI plugin send_request called with model: {model}")  # Debug print
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "response_format": response_format
    }
    if function_schemas:
        data["tools"] = function_schemas

    for attempt in range(max_retries):
        try:
           # print(f"Sending request to OpenAI API (attempt {attempt + 1})")  # Debug print
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
          #  print("Received response from OpenAI API")  # Debug print
            return response.json()
        except RequestException as e:
            print(f"Error in OpenAI API request: {str(e)}")  # Debug print
            if attempt == max_retries - 1:
                return format_error_as_response(message=str(e))
            delay = initial_delay * (2 ** attempt)
            time.sleep(delay)

def format_response(response):
    choice = response["choices"][0]

    payload = {
                "provider": "openai",
                "model": response["model"],
            "text": choice["message"].get("content"),
            "usage": {
                "input_tokens": response["usage"]["prompt_tokens"],
                "output_tokens": response["usage"]["completion_tokens"],
                "total_tokens": response["usage"]["total_tokens"]
            },
            "finish_reason": choice.get("finish_reason"),
            "refusal": choice["message"].get("refusal"),
            "function_call": choice["message"].get("function_call"),
            "tool_calls": choice["message"].get("tool_calls"),
            "logprobs": response.get("logprobs"),
            "stop_sequence": None,  # OpenAI doesn't have this
            "stop_reason": choice.get("finish_reason")  # Equivalent to finish_reason
        }
    return payload

    
def format_error_as_response(message):
    message=message.split(":")
    payload = {
        'id': 'internal_error_handler_'+str(int(time.time())),
        'object': 'chat.completion', 'created': int(time.time()),
        'model': 'internal_error_handler',
        'choices': [{'index': 0, 'message': {'role': 'assistant', 'content': "Technical difficulties, please try again in a few minutes. The API response was: "+message[0], 'refusal': None},
        'logprobs': None, 'finish_reason': 'api_error'}],
        'usage': {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0},
        'system_fingerprint': 'internal_error_handler'}
   #print(payload)
    return payload

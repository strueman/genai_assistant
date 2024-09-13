import requests
import json
import time

def send_request(api_key, messages, model, system_prompt, max_tokens, function_schemas=None, max_retries=3):
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": api_key,
        "anthropic-version": "2023-06-01"
    }
    
    data = {
        "model": model,
        "messages": messages,
        "system": system_prompt,
        "max_tokens": max_tokens
    }
    
    if function_schemas:
        tools = []
        for schema in function_schemas:
            tool = {
                "name": schema["function"]["name"],
                "description": schema["function"]["description"],
                "input_schema": schema["function"]["parameters"]
            }
            tools.append(tool)
        data["tools"] = tools
    
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            print(f"Error in Anthropic API call: {e}")
            print(f'headers: {headers}')
            print(f'data: {data}')
            error_code = e.response.status_code
            error_message = e.response.json().get('error', {}).get('message', str(e))
            
            if error_code in [429, 500, 529]:
                if attempt < max_retries - 1:
                    if error_code == 429:
                        wait_time = 30 ** attempt # 30 seconds for rate limit
                    else:
                        wait_time = 3 ** attempt  # Exponential backoff for other errors
                    time.sleep(wait_time)
                    continue
                else:
                    # Construct a message for the user
                    user_message = construct_error_message(error_code)
                    return format_error_as_response(user_message)
            else: 
                user_message = construct_error_message(error_code)
                return format_error_as_response(user_message)
    
    raise ValueError("Max retries reached. Unable to get a successful response.")

def construct_error_message(error_code):
    if error_code == 429:
        return "The Anthropic API is currently rate limited. Please try again in a few minutes."
    elif error_code == 500:
        return "The Anthropic API encountered an internal server error. Please try again in a few minutes."
    elif error_code == 529:
        return "The Anthropic API is currently overloaded. Please try again in a few minutes."
    else:
        return f"We are experiancing technical difficulties, please try again in a few minutes. Error code: {error_code}"
    
def format_error_as_response(message):
    return {
        "provider": "anthropic",
        "model": "error_handler",
        "text": message,
        "usage": {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0
        },
        "finish_reason": "error",
        "refusal": None,
        "tool_calls": [],
        "logprobs": None,
        "stop_sequence": None,
        "stop_reason": "error",
        "content": [{"type": "text", "text": message}]
    }

def format_response(response):
    return {
        "provider": "anthropic",
        "model": response["model"],
        "text": next((content['text'] for content in response['content'] if content['type'] == 'text'), None),
        "usage": {
            "input_tokens": response["usage"]["input_tokens"],
            "output_tokens": response["usage"]["output_tokens"],
            "total_tokens": response["usage"]["input_tokens"] + response["usage"]["output_tokens"]
        },
        "finish_reason": response.get("stop_reason"),
        "refusal": None,
        "tool_calls": [
            {
                "id": tool_call['id'],
                "name": tool_call['name'],
                "arguments": tool_call['input']
            }
            for content in response['content']
            if content['type'] == 'tool_use'
            for tool_call in [content]
        ],
        "logprobs": None,
        "stop_sequence": response.get("stop_sequence"),
        "stop_reason": response.get("stop_reason"),
        "content": response['content']
    }

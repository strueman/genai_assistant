import configparser
import importlib
import os
import json

class LLMConnector:
    def __init__(self, provider=None):
        self.config = configparser.ConfigParser()
        try:
            self.config.read('settings.cfg')
            self.provider = provider or self.config['provider']['llm']
            self.api_key = self.config[self.provider]['api_key']
            self.model = self.config[self.provider].get('default_model')
            self.plugin = importlib.import_module(f'plugins.{self.provider}')
            self.tools = self.load_tools()
        except Exception as e:
            raise ValueError(f"Error reading configuration: {e}")

    def load_tools(self):
        tools = {}
        tools_dir = os.path.join('plugins', 'tools')
        for filename in os.listdir(tools_dir):
            if filename.endswith('.py'):
                module_name = filename[:-3]
                try:
                    module = importlib.import_module(f'plugins.tools.{module_name}')
                    tool_info = {'function': None, 'schemas': {}}

                    # Get the function name
                    if hasattr(module, 'function_name'):
                        function_name = module.function_name.get('function')
                        if function_name and hasattr(module, function_name):
                            tool_info['function'] = getattr(module, function_name)
                        else:
                            raise ValueError(f"Invalid or missing function in {module_name}")
                    else:
                        raise ValueError(f"Missing function_name in {module_name}")

                    # Get schemas and perform sanity check
                    for attr in dir(module):
                        if attr.endswith('_tool_schema') or attr.endswith('_function_schema'):
                            provider = attr.rsplit('_', 2)[0]
                            schema = getattr(module, attr)
                            
                            # Sanity check: ensure function name in schema matches function_name
                            schema_func_name = schema.get('function', {}).get('name')
                            if schema_func_name != function_name:
                                raise ValueError(f"Function name mismatch in {module_name} for {provider} schema")
                            
                            tool_info['schemas'][provider] = schema

                    if tool_info['function'] and tool_info['schemas']:
                        tools[module_name] = tool_info
                    else:
                        raise ValueError(f"Incomplete tool definition in {module_name}")

                except Exception as e:
                    continue
                   # print(f"Error loading tool {module_name}: {e}")

        return tools

    def chat(self, user_prompt, system_prompt="You are a helpful assistant. keep responses short and concise.", model=None, temperature=0.7, max_tokens=4096, functions=None, response_format=None):
        model = model or self.model
        try:
            function_schemas = None
            if functions:
                if self.provider == "anthropic":
                    function_schemas = [
                        self.tools[f]['schemas']['anthropic']
                        for f in functions if f in self.tools
                    ]
                else:  # openai or other providers
                    function_schemas = [self.tools[f]['schemas']['openai'] for f in functions if f in self.tools]

            if self.provider == "anthropic":
                messages = [
                    {"role": "user", "content": user_prompt}
                ]
                while True:
                    response = self.plugin.send_request(self.api_key, messages, model, system_prompt, max_tokens, function_schemas)
                    formatted_response = self.plugin.format_response(response)
                    
                    if formatted_response.get('stop_reason') != "tool_use":
                        return formatted_response

                    for tool_call in formatted_response.get('tool_calls', []):
                        tool_name = tool_call['name']
                        tool_input = tool_call['arguments']
                        tool_result = self.tools[tool_name]['function'](**tool_input)

                        messages.append({
                            "role": "assistant",
                            "content": formatted_response['content']
                        })
                        messages.append({
                            "role": "user",
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": tool_call['id'],
                                    "content": str(tool_result),
                                }
                            ],
                        })

            else:# self.provider == "openrouter":  # openrouter
                messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
                while True:
                    response = self.plugin.send_request(self.api_key, messages, model, temperature, max_tokens, function_schemas, response_format=None)
                    formatted_response = self.plugin.format_response(response)

                    if not formatted_response.get('tool_calls'):
                        return formatted_response
                    try:
                        function_name = formatted_response['tool_calls'][0]['function']['name']
                        function_args = json.loads(formatted_response['tool_calls'][0]['function']['arguments'])
                        function_result = self.tools[function_name]['function'](**function_args)
                        messages.append({
                            "role": "function",
                            "name": function_name,
                            "content": str(function_result)
                        })
                        messages.append({
                            "role": "user",
                            "content": f"The function {function_name} returned: {function_result}. Please provide a final response based on this information."
                        })
                    except Exception as e:
                        print(f"Error in LLMConnector.chat function call: {str(e)}")
                        messages.append({
                        "role": "function",
                        "name": function_name,
                        "content": "Error in tool query"
                        })
                        messages.append({
                            "role": "user",
                            "content": f"The function {function_name} returned an error. Please provide a final response based on this information."
                        })
        except Exception as e:
            raise ValueError(f"Error during API call: {e}")

    def _send_request(self, user_prompt, system_prompt, model, temperature, max_tokens, function_schemas, additional_messages=None, response_format=None):
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        if additional_messages:
            messages.extend(additional_messages)

        if self.provider == "anthropic":
            return self.plugin.send_request(self.api_key, messages, model, max_tokens)
        else:  # openai or other providers
            return self.plugin.send_request(self.api_key, messages, model, temperature, max_tokens, function_schemas, response_format)

if __name__ == "__main__":
    provider = input("Enter provider (leave blank to use default from config): ")
    provider = provider if provider else None
    connector = LLMConnector(provider)
    print("This will send a prompt to your LLM model and provider as configured in settings.cfg")
    prompt = input("Enter a test prompt:")
    response = connector.chat(prompt)
    print(f"Response: {response['text']}")

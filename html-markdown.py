import html2text

def html_to_markdown(html_content):
    h = html2text.HTML2Text()
    h.ignore_links = False
    markdown_content = h.handle(html_content)
    return markdown_content

# Example usage
html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LLMConnector Documentation</title>
</head>
<body>
    <h1>Usage Instructions for <code>LLMConnector</code></h1>

    <h2>Initialization</h2>
    <p>You can initialize the <code>LLMConnector</code> class by optionally passing a provider name. If no provider is passed, it will default to the provider specified in the <code>settings.cfg</code> file.</p>

    <h3>Arguments:</h3>
    <ul>
        <li><code>provider</code> (optional): The name of the provider to use (<code>"anthropic"</code> or <code>"openai"</code>). If not provided, it defaults to the provider specified in the <code>settings.cfg</code> file.</li>
    </ul>

    <h3>Example:</h3>
    <pre><code>from llm_connector import LLMConnector

# Initialize with default provider from settings.cfg
connector = LLMConnector()

# Initialize with a specific provider
connector = LLMConnector(provider="anthropic")
</code></pre>

    <h2>Chat Method</h2>
    <p>The <code>chat</code> method sends a prompt to the configured LLM model and returns the response in a unified format.</p>

    <h3>Arguments:</h3>
    <ul>
        <li><code>user_prompt</code> (str): The prompt from the user.</li>
        <li><code>system_prompt</code> (optional, str): The system prompt to set the context. Defaults to "You are a helpful assistant."</li>
        <li><code>model</code> (optional, str): The model to use. Defaults to the model configured for the provider.</li>
        <li><code>temperature</code> (optional, float): The sampling temperature. Defaults to 0.7.</li>
        <li><code>max_tokens</code> (optional, int): The maximum number of tokens to generate. Defaults to 150.</li>
    </ul>

    <h3>Returns:</h3>
    <ul>
        <li>A dictionary with the following keys:
            <ul>
                <li><code>provider</code> (str): The name of the provider (<code>"anthropic"</code> or <code>"openai"</code>).</li>
                <li><code>model</code> (str): The model used for the completion.</li>
                <li><code>text</code> (str): The generated text from the LLM model.</li>
                <li><code>usage</code> (dict): A dictionary with token usage information:
                    <ul>
                        <li><code>input_tokens</code> (int): The number of input tokens.</li>
                        <li><code>output_tokens</code> (int): The number of output tokens.</li>
                        <li><code>total_tokens</code> (int): The total number of tokens used.</li>
                    </ul>
                </li>
            </ul>
        </li>
    </ul>

    <h3>Example:</h3>
    <pre><code># Initialize the connector
connector = LLMConnector()

# Send a chat prompt
response = connector.chat(user_prompt="Tell me a joke.")
print(response)
</code></pre>

    <h2>Full Example:</h2>
    <pre><code>from llm_connector import LLMConnector

# Initialize with default provider from settings.cfg
connector = LLMConnector()

# Send a chat prompt
response = connector.chat(user_prompt="What is the capital of France?")
print(response)

# Initialize with a specific provider
connector = LLMConnector(provider="anthropic")

# Send a chat prompt
response = connector.chat(user_prompt="Tell me a joke.")
print(response)
</code></pre>

    <h2>Notes:</h2>
    <ul>
        <li>Ensure that the <code>settings.cfg</code> file is properly configured with the necessary API keys and endpoints for the providers.</li>
        <li>The <code>provider</code> argument can be <code>"anthropic"</code> or <code>"openai"</code>. If not provided, the default provider from the <code>settings.cfg</code> file will be used.</li>
        <li>The <code>usage</code> dictionary in the response provides standardized token usage information for both providers.</li>
    </ul>
</body>
</html>
"""

markdown_content = html_to_markdown(html_content)
print(markdown_content)

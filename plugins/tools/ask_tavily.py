from tavily import TavilyClient
from pathlib import Path
import configparser
def get(name="none"):
    return "ask_tavily"
def ask_tavily(query):
    p = str(Path(__file__).parents[2])
    config = configparser.ConfigParser()
    config.read(p+'/settings.cfg')
    api_key = config['tavily']['api_key']   
    tavily_client = TavilyClient(api_key=api_key)
    answer = tavily_client.qna_search(query)

    return answer

function_name = {"function":"ask_tavily"}

openai_function_schema = {
        "type": "function",
        "function": {
            "name": "ask_tavily",
            "description": "Ask Tavily a question. Tavily is a search engine that can answer basic questions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to use. For example: 'Latest news on Nvidia stock performance'"
                    }
                },
                "required": ["query"],
                "additionalProperties": False
            }
        }
    }


anthropic_tool_schema = {
    "type": "function",
    "function": {
        "name": "ask_tavily",
        "description": "Ask Tavily a question. Tavily is a search engine that can answer basic questions.",
        "parameters": {
            "type": "object",
        "properties": {"query": {
                "type": "string", 
                "description": "The search query to use. For example: 'Latest news on Nvidia stock performance'"
            },
        },
            "required": ['query']
        }
    }
}

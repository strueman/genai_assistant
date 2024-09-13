from datetime import datetime
def get(name="none"):
    return "get_current_date"
def get_current_date(date=None,**kwargs):
    return str(datetime.now().strftime("%Y-%m-%d"))

function_name = {"function":"get_current_date"}

openai_function_schema = {
        "type": "function",
        "function": {
            "name": "get_current_date",
            "description": "Get the delivery date for a customer's order. Call this whenever you need to know the delivery date, for example when a customer asks 'Where is my package'",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "The current date"
                    }
                },
                "required": [],
                "additionalProperties": False
            }
        }
    }


anthropic_tool_schema = {
    "type": "function",
    "function": {
        "name": "get_current_date",
        "description": "Get the current date. Use this when you need to know the current date.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
}


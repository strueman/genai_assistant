from pathlib import Path
import json
import os
def get(name="none"):
    return "profile_tool"
# Load the profile schema
schema_path = 'users/default/profile_schema.json'
with open(schema_path, 'r') as schema_file:
    profile_schema = json.load(schema_file)

def profile_tool(query=None, command=None, user_id=None):
    if command != 'update' or not query or not user_id:
        return "Error: Invalid command or missing parameters"

    user_profile_path = f'users/{user_id}/user_profile.json'

    try:
        # Parse the query as JSON
        new_profile = json.loads(query) if isinstance(query, str) else query

        # Validate the new profile against the schema
        if validate_profile(new_profile, profile_schema):
            # Save the updated profile
            with open(user_profile_path, 'w') as profile_file:
                json.dump(new_profile, profile_file, indent=2)
            return "Profile updated successfully"
        else:
            return "Error: Profile does not match the required schema"
    except json.JSONDecodeError:
        return "Error: Invalid JSON in query"
    except Exception as e:
        return f"Error: {str(e)}"

def validate_profile(profile, schema):
    for key, value in schema.items():
        if key not in profile:
            return False
        if isinstance(value, dict):
            if not isinstance(profile[key], dict):
                return False
            if not validate_profile(profile[key], value):
                return False
        elif isinstance(value, list):
            if not isinstance(profile[key], list):
                return False
    return True

function_name = {"function": "profile_tool"}

openai_function_schema = {
    "type": "function",
    "function": {
        "name": "profile_tool",
        "description": "Update the user profile information.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "object",
                    "description": "The updated user profile data following the profile schema structure.",
                    "properties": profile_schema
                },
                "command": {
                    "type": "string",
                    "enum": ["update"],
                    "description": "The command to update the user profile."
                },
                "user_id": {
                    "type": "string",
                    "description": "The unique identifier for the user."
                }
            },
            "required": ["query", "command", "user_id"]
        }
    }
}

anthropic_tool_schema = {
    "type": "function",
    "function": {
        "name": "profile_tool",
        "description": "Update the user profile information.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "object",
                    "description": "The updated user profile data following the profile schema structure."
                },
                "command": {
                    "type": "string",
                    "description": "The command to update the user profile (should be 'update')."
                },
                "user_id": {
                    "type": "string",
                    "description": "The unique identifier for the user."
                }
            },
            "required": ["query", "command", "user_id"]
        }
    }
}

from fastapi import FastAPI, HTTPException, Depends, Security, Request
from fastapi.security import APIKeyHeader
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Dict, Any
import uvicorn
import secrets
import configparser
import os
import uuid
import logging

# Set up logging
logging.basicConfig(level=logging.CRITICAL)
logger = logging.getLogger(__name__)

app = FastAPI()
templates = Jinja2Templates(directory="templates")
cache: Dict[str, Dict[str, Any]] = {}

# Load or generate API keys
config = configparser.ConfigParser()
config_file = 'settings.cfg'

API_KEYS = []
USING_EMERGENCY_KEY = False
emergency_key = None

logger.info(f"Checking for config file: {config_file}")
if os.path.exists(config_file):
    logger.info("Config file found. Reading API keys.")
    config.read(config_file)
    API_KEYS = config.get('cache_api', 'API_KEY', fallback='').split(',')
    API_KEYS = [key.strip() for key in API_KEYS if key.strip()]
    logger.info(f"API keys read from config: {API_KEYS}")
else:
    logger.info("Config file not found.")

if not API_KEYS:
    logger.info("No valid API keys found. Generating a new key.")
    new_key = secrets.token_urlsafe(32)
    API_KEYS.append(new_key)
    if 'cache_api' not in config:
        config['cache_api'] = {}
    config['cache_api']['API_KEY'] = new_key
    try:
        with open(config_file, 'w') as configfile:
            config.write(configfile)
        logger.info(f"New API Key generated and saved to {config_file}")
    except Exception as e:
        logger.error(f"Failed to write to config file: {e}")

if API_KEYS:
    logger.info(f"Final API Keys: {', '.join(API_KEYS)}")
else:
    logger.error("No API keys available. Generating emergency key.")
    emergency_key = secrets.token_urlsafe(32)
    API_KEYS.append(emergency_key)
    USING_EMERGENCY_KEY = True
    logger.warning(f"Emergency API key generated: {emergency_key}")

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

class Variable(BaseModel):
    process: str
    name: str
    value: Any

# Modify the get_api_key function to allow the emergency key
def get_api_key(api_key_header: str = Security(api_key_header)):
    if api_key_header in API_KEYS or (USING_EMERGENCY_KEY and api_key_header == "emergency"):
        return api_key_header
    raise HTTPException(status_code=403, detail="Could not validate credentials")

@app.post("/set")
def set_variable(variable: Variable, api_key: str = Depends(get_api_key)):
    if variable.process not in cache:
        cache[variable.process] = {}
    cache[variable.process][variable.name] = variable.value
    return {"success": True}

@app.get("/get/{process}/{name}")
def get_variable(process: str, name: str, api_key: str = Depends(get_api_key)):
    if process not in cache or name not in cache[process]:
        raise HTTPException(status_code=404, detail="Variable not found")
    return {"process": process, "name": name, "value": cache[process][name]}

@app.get("/list/{process}")
def list_variables(process: str, api_key: str = Depends(get_api_key)):
    if process not in cache:
        return {"process": process, "variables": []}
    return {"process": process, "variables": list(cache[process].keys())}

@app.delete("/clear/{process}")
def clear_process(process: str, api_key: str = Depends(get_api_key)):
    if process in cache:
        cache[process].clear()
        return {"success": True, "message": f"All variables for process '{process}' have been cleared"}
    return {"success": False, "message": f"Process '{process}' not found"}

@app.delete("/clear_all")
def clear_all(api_key: str = Depends(get_api_key)):
    cache.clear()
    return {"success": True, "message": "All variables across all processes have been cleared"}

@app.post("/generate_api_key")
def generate_api_key(current_api_key: str = Depends(get_api_key)):
    new_key = secrets.token_urlsafe(32)
    API_KEYS.append(new_key)
    print(f"New API Key generated: {new_key}")
    config.read(config_file)
    current_keys = config.get('cache_api', 'API_KEY', fallback='').split(',')
    current_keys.append(new_key)
    config['cache_api']['API_KEY'] = ','.join(current_keys)
    
    with open(config_file, 'w') as configfile:
        config.write(configfile)
    
    return {"new_api_key": new_key}

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Add an endpoint to retrieve the emergency key if we're using one
@app.get("/emergency_key")
def get_emergency_key():
    if USING_EMERGENCY_KEY:
        return {"emergency_key": API_KEYS[0]}
    else:
        raise HTTPException(status_code=404, detail="No emergency key available")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="critical")

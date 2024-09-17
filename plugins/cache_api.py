import requests
import json
import configparser
import os
from pathlib import Path
import ast
class APICache:
    def __init__(self, process_name='default',api_key=None):
        if api_key:
            self.api_key = api_key
        else:
            self.api_key = self._load_api_key()
        self.process_name = process_name
        self.base_url = 'http://localhost:8000'
        self.headers = {'X-API-Key': self.api_key}

    def _load_api_key(self):
        config = configparser.ConfigParser()
        self.p = str(Path(__file__).parents[1])
        config_file = f'{self.p}/settings.cfg'
        if os.path.exists(config_file):
            config.read(config_file)
            return config.get('cache_api', 'API_KEY', fallback=None)
            
        else:
            raise FileNotFoundError(f"Configuration file {config_file} not found.")

    def get_cache(self, variable_name=None):
        response = requests.get(f'{self.base_url}/get/{self.process_name}/{variable_name}', headers=self.headers)
        if response.status_code == 200:
            return response.json()['value']
        else:
            return None
    
    def set_cache(self, variable_name=None, payload=None):
        data = {'process': self.process_name, 'name': variable_name, 'value': payload}
        response = requests.post(f'{self.base_url}/set', json=data, headers=self.headers)
        if response.status_code == 200:
            return True
        else:
            return False

    def list_cache(self):
        response = requests.get(f'{self.base_url}/list/{self.process_name}', headers=self.headers)
        if response.status_code == 200:
            return response.json()['variables']
        else:
            return None

    def clear_cache(self):
        response = requests.delete(f'{self.base_url}/clear/{self.process_name}', headers=self.headers)
        if response.status_code == 200:
            return True
        else:
            return False

    def clear_all_cache(self):
        response = requests.delete(f'{self.base_url}/clear_all', headers=self.headers)
        if response.status_code == 200:
            return True
        else:
            return False

# Example usage:
# if __name__ == "__main__":
#     cache = APICache(process_name='example_process')
    
#     # Set a variable
#     cache.set_cache('my_var', 'Hello, World!')
    
#     # Get a variable
#     value = cache.get_cache('my_var')
#     print(f"Retrieved value: {value}")
    
#     # List variables
#     variables = cache.list_cache()
#     print(f"Variables in cache: {variables}")
    
#     # Clear process cache
#     cache.clear_cache()
    
#     # Clear all cache
#     cache.clear_all_cache()
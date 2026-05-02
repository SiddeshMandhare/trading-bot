# token_storage.py - Persistent Token Storage
import json
import os
import time
from datetime import datetime
from typing import Optional, Dict

class TokenStorage:
    def __init__(self, client_code: str, storage_file: str = "token_cache.json"):
        self.client_code = client_code
        self.storage_file = storage_file
        self._ensure_storage_file()
    
    def _ensure_storage_file(self):
        if not os.path.exists(self.storage_file):
            self._save_token_data({})
    
    def _load_token_data(self) -> Dict:
        try:
            with open(self.storage_file, 'r') as f:
                return json.load(f)
        except:
            return {}
    
    def _save_token_data(self, data: Dict):
        try:
            with open(self.storage_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Failed to save token: {e}")
    
    def get_token(self) -> Optional[str]:
        data = self._load_token_data()
        client_data = data.get(self.client_code, {})
        token = client_data.get('access_token')
        expires_at = client_data.get('expires_at', 0)
        
        if token and expires_at > time.time():
            return token
        return None
    
    def save_token(self, access_token: str, expiry_seconds: int = 82800) -> bool:
        data = self._load_token_data()
        data[self.client_code] = {
            'access_token': access_token,
            'expires_at': time.time() + expiry_seconds,
            'generated_at': time.time(),
            'cached_at': datetime.now().isoformat()
        }
        self._save_token_data(data)
        return True
    
    def clear_token(self):
        data = self._load_token_data()
        if self.client_code in data:
            del data[self.client_code]
            self._save_token_data(data)
    
    def get_token_info(self) -> Optional[Dict]:
        data = self._load_token_data()
        client_data = data.get(self.client_code, {})
        if not client_data:
            return None
        
        return {
            'has_token': bool(client_data.get('access_token')),
            'is_valid': client_data.get('expires_at', 0) > time.time(),
            'expires_at': datetime.fromtimestamp(client_data.get('expires_at', 0)).strftime('%Y-%m-%d %H:%M:%S') if client_data.get('expires_at') else None
        }
    
    def is_token_valid(self) -> bool:
        info = self.get_token_info()
        return info and info['is_valid'] if info else False
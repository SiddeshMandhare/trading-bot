# auth_service.py - TOTP Authentication with Persistent Storage
import pyotp
import requests
import time
import json
import os
from typing import Optional
from Dhan_Tradehull_V3 import Tradehull
from token_storage import TokenStorage

_token_storage = None

def get_token_storage(client_code: str) -> TokenStorage:
    global _token_storage
    if _token_storage is None or _token_storage.client_code != client_code:
        _token_storage = TokenStorage(client_code)
    return _token_storage

def generate_access_token(client_code: str, pin: str, totp_secret: str, force_new: bool = False) -> Optional[str]:
    """Generate a fresh access token"""
    if not force_new:
        storage = get_token_storage(client_code)
        if storage.is_token_valid():
            cached_token = storage.get_token()
            if cached_token:
                return cached_token
    
    try:
        totp = pyotp.TOTP(totp_secret)
        current_totp = totp.now()
        
        url = f"https://auth.dhan.co/app/generateAccessToken?dhanClientId={client_code}&pin={pin}&totp={current_totp}"
        response = requests.post(url, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            access_token = data.get('accessToken') or data.get('access_token')
            if access_token:
                storage = get_token_storage(client_code)
                storage.save_token(access_token, expiry_seconds=82800)
                return access_token
        return None
    except Exception as e:
        print(f"Token generation error: {e}")
        return None

def create_tradehull_with_totp(client_code: str, pin: str, totp_secret: str, retries: int = 3) -> Optional[Tradehull]:
    """Create Tradehull instance using TOTP"""
    for attempt in range(retries):
        try:
            access_token = generate_access_token(client_code, pin, totp_secret, force_new=(attempt > 0))
            if not access_token:
                time.sleep(2)
                continue
            
            tsl = Tradehull(client_code, access_token)
            if not hasattr(tsl, 'dhan_client_id'):
                tsl.dhan_client_id = client_code
            
            print(f"✅ Authentication successful for {client_code}")
            return tsl
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            time.sleep(2)
    
    return None

def get_token_status(client_code: str) -> dict:
    storage = get_token_storage(client_code)
    return storage.get_token_info() or {'has_token': False}

# Add these functions to auth_service.py

def verify_authentication():
    """Verify that authentication is working"""
    try:
        from config import Config
        test_tsl = create_tradehull_with_totp(Config.CLIENT_CODE, Config.PIN, Config.TOTP_SECRET, force_new=True)
        
        if test_tsl:
            # Test API call
            balance = test_tsl.get_balance()
            return {
                'authenticated': True,
                'balance': balance,
                'client_code': Config.CLIENT_CODE
            }
        else:
            return {'authenticated': False, 'error': 'Failed to create Tradehull instance'}
    except Exception as e:
        return {'authenticated': False, 'error': str(e)}

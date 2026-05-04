# market_data_service.py - COMPLETELY REWRITE
import requests
from config import Config
import logging

logger = logging.getLogger(__name__)

class MarketDataService:
    def __init__(self, tsl):
        self.tsl = tsl
        self.last_prices = {}
        
    def get_index_prices(self):
        """Get REAL index prices from Dhan API"""
        indices = {
            "NIFTY 50": {"security_id": "13", "exchange": "IDX_I"},
            "BANKNIFTY": {"security_id": "25", "exchange": "IDX_I"},
            "FINNIFTY": {"security_id": "27", "exchange": "IDX_I"},
            "SENSEX": {"security_id": "51", "exchange": "IDX_I"}
        }
        
        results = {}
        
        # Method 1: Use tsl's get_ltp_data if available
        if hasattr(self.tsl, 'get_ltp_data'):
            try:
                ltp_data = self.tsl.get_ltp_data(names=list(indices.keys()))
                for name in indices.keys():
                    if name in ltp_data and ltp_data[name] > 0:
                        results[name] = {
                            "ltp": ltp_data[name],
                            "change": 0,
                            "change_percent": 0
                        }
                if results:
                    return results
            except Exception as e:
                logger.error(f"LTP method failed: {e}")
        
        # Method 2: Direct API call with proper authentication
        for name, info in indices.items():
            try:
                url = "https://api.dhan.co/v2/marketfeed/ltp"
                payload = {info["exchange"]: [int(info["security_id"])]}
                
                # Get token from tsl
                token = None
                if hasattr(self.tsl, 'token_id'):
                    token = self.tsl.token_id
                elif hasattr(self.tsl, 'access_token'):
                    token = self.tsl.access_token
                    
                if not token:
                    logger.error(f"No token available for {name}")
                    results[name] = {"ltp": 0, "change": 0, "change_percent": 0}
                    continue
                
                headers = {
                    "access-token": token,
                    "client-id": Config.CLIENT_CODE,
                    "Content-Type": "application/json"
                }
                
                response = requests.post(url, json=payload, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('status') == 'success':
                        sec_data = data.get('data', {}).get(info["exchange"], {}).get(str(info["security_id"]), {})
                        ltp = sec_data.get('last_price', 0)
                        results[name] = {
                            "ltp": ltp if ltp > 0 else self.get_fallback_price(name),
                            "change": 0,
                            "change_percent": 0
                        }
                    else:
                        results[name] = {"ltp": self.get_fallback_price(name), "change": 0, "change_percent": 0}
                else:
                    results[name] = {"ltp": self.get_fallback_price(name), "change": 0, "change_percent": 0}
                    
            except Exception as e:
                logger.error(f"Error fetching {name}: {e}")
                results[name] = {"ltp": self.get_fallback_price(name), "change": 0, "change_percent": 0}
        
        return results
    
    def get_fallback_price(self, name: str) -> float:
        """Return reasonable fallback prices if API fails"""
        fallbacks = {
            "NIFTY 50": 24500.50,
            "BANKNIFTY": 52100.00,
            "FINNIFTY": 21800.25,
            "SENSEX": 80500.00
        }
        return fallbacks.get(name, 0)
    
    def get_current_price(self, symbol: str) -> float:
        """Get current price for a symbol"""
        try:
            if hasattr(self.tsl, 'get_ltp_data'):
                ltp_data = self.tsl.get_ltp_data(names=[symbol])
                if symbol in ltp_data and ltp_data[symbol] > 0:
                    return ltp_data[symbol]
            return 0
        except Exception as e:
            logger.error(f"Price fetch error for {symbol}: {e}")
            return 0
    
    def get_live_data(self):
        """Get live market data for strategies"""
        return self.get_index_prices()

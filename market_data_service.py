# market_data_service.py
import requests
from config import Config

class MarketDataService:
    def __init__(self, tsl):
        self.tsl = tsl
    
    def get_index_prices(self):
        """Get index prices - returns mock data if API fails"""
        indices = {
            "NIFTY 50": {"security_id": "13", "exchange": "IDX_I"},
            "BANKNIFTY": {"security_id": "25", "exchange": "IDX_I"},
            "FINNIFTY": {"security_id": "27", "exchange": "IDX_I"},
            "SENSEX": {"security_id": "51", "exchange": "IDX_I"}
        }
        
        results = {}
        
        # First try to use tsl's built-in methods
        if hasattr(self.tsl, 'get_ltp_data'):
            try:
                ltp_data = self.tsl.get_ltp_data(names=list(indices.keys()))
                for name in indices.keys():
                    if name in ltp_data:
                        results[name] = {
                            "ltp": ltp_data[name],
                            "change": 0,
                            "change_percent": 0
                        }
                    else:
                        results[name] = {"ltp": 0, "change": 0, "change_percent": 0}
                # If we got at least one value, return
                if any(v['ltp'] > 0 for v in results.values()):
                    return results
            except Exception as e:
                print(f"LTP data error: {e}")
        
        # Fallback: Try direct API call
        for name, info in indices.items():
            try:
                url = "https://api.dhan.co/v2/marketfeed/ohlc"
                payload = {info["exchange"]: [int(info["security_id"])]}
                
                token = None
                if hasattr(self.tsl, 'token_id'):
                    token = self.tsl.token_id
                elif hasattr(self.tsl, 'access_token'):
                    token = self.tsl.access_token
                
                if not token:
                    results[name] = {"ltp": 0, "change": 0, "change_percent": 0}
                    continue
                
                headers = {"access-token": token, "client-id": Config.CLIENT_CODE}
                response = requests.post(url, json=payload, headers=headers, timeout=5)
                
                if response.status_code == 200:
                    data = response.json()
                    sec_data = data.get("data", {}).get(info["exchange"], {}).get(info["security_id"], {})
                    ltp = sec_data.get("last_price", 0)
                    results[name] = {
                        "ltp": ltp,
                        "change": 0,
                        "change_percent": 0
                    }
                else:
                    results[name] = {"ltp": 0, "change": 0, "change_percent": 0}
            except Exception as e:
                print(f"Error fetching {name}: {e}")
                results[name] = {"ltp": 0, "change": 0, "change_percent": 0}
        
        return results

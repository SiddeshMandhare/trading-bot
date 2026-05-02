# market_data_service.py
import requests
from config import Config

class MarketDataService:
    def __init__(self, tsl):
        self.tsl = tsl
    
    def get_index_prices(self):
        indices = {
            "NIFTY 50": {"security_id": "13", "exchange": "IDX_I"},
            "BANKNIFTY": {"security_id": "25", "exchange": "IDX_I"},
            "FINNIFTY": {"security_id": "27", "exchange": "IDX_I"}
        }
        
        results = {}
        for name, info in indices.items():
            try:
                url = "https://api.dhan.co/v2/marketfeed/ohlc"
                payload = {info["exchange"]: [int(info["security_id"])]}
                headers = {"access-token": self.tsl.access_token, "client-id": Config.CLIENT_CODE}
                response = requests.post(url, json=payload, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    sec_data = data.get("data", {}).get(info["exchange"], {}).get(info["security_id"], {})
                    ltp = sec_data.get("last_price", 0)
                    results[name] = {"ltp": ltp, "change": 0, "change_percent": 0}
                else:
                    results[name] = {"ltp": 0, "change": 0, "change_percent": 0}
            except:
                results[name] = {"ltp": 0, "change": 0, "change_percent": 0}
        
        return results
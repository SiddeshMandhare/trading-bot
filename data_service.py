# data_service.py
import pandas as pd
import time
from typing import Optional
from config import Config

class DataService:
    def __init__(self, tsl):
        self.tsl = tsl
    
    def get_symbol_data(self, symbol: str, retries: int = 3) -> Optional[pd.DataFrame]:
        exchange_options = self._get_exchange_options(symbol)
        
        for attempt in range(retries):
            for exchange in exchange_options:
                try:
                    chart = self.tsl.get_historical_data(
                        tradingsymbol=symbol, exchange=exchange, timeframe=Config.TIMEFRAME
                    )
                    if self._validate_data(chart):
                        return chart
                except Exception:
                    continue
            if attempt < retries - 1:
                time.sleep(2)
        return None
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        try:
            ltp_data = self.tsl.get_ltp_data(names=[symbol])
            return ltp_data.get(symbol)
        except Exception:
            return None
    
    def _get_exchange_options(self, symbol: str) -> list:
        symbol = str(symbol).upper()
        if symbol in Config.INDEX_SYMBOLS:
            return ["INDICES", "NSE", "NFO"]
        return ["NSE", "BSE", "NFO"]
    
    def _validate_data(self, chart) -> bool:
        if not isinstance(chart, pd.DataFrame) or len(chart) < 20:
            return False
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        return all(col in chart.columns for col in required_cols)
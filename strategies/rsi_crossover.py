# strategies/rsi_crossover.py
import pandas as pd
import talib
from typing import Dict, Any
from .base import TradingStrategy

class RSI_50_Crossover(TradingStrategy):
    def get_strategy_name(self) -> str: return "RSI_50_Crossover"
    
    def calculate_indicators(self, chart: pd.DataFrame) -> None:
        chart['rsi'] = talib.RSI(chart['close'], timeperiod=14)
    
    def generate_signals(self, chart: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        if len(chart) < 2: return {'buy_call': False, 'buy_put': False}
        cc, prev = chart.iloc[-1], chart.iloc[-2]
        return {'buy_call': cc['rsi'] > 50 and prev['rsi'] <= 50,
                'buy_put': cc['rsi'] < 50 and prev['rsi'] >= 50}
                
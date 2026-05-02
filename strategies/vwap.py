# strategies/vwap.py
import pandas as pd
import talib
from typing import Dict, Any
from .base import TradingStrategy

class VWAP_Strategy(TradingStrategy):
    def get_strategy_name(self) -> str: return "VWAP_Reversion"
    
    def calculate_indicators(self, chart: pd.DataFrame) -> None:
        typical = (chart['high'] + chart['low'] + chart['close']) / 3
        chart['vwap'] = (typical * chart['volume']).cumsum() / chart['volume'].cumsum()
        chart['volume_ma'] = talib.SMA(chart['volume'], timeperiod=20)
        chart['rsi'] = talib.RSI(chart['close'], timeperiod=14)
    
    def generate_signals(self, chart: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        if len(chart) < 2: return {'buy_call': False, 'buy_put': False}
        cc, prev = chart.iloc[-1], chart.iloc[-2]
        buy = (prev['close'] < prev['vwap'] and cc['close'] > cc['vwap'] and 
               cc['volume'] > cc['volume_ma'] * 2 and not pd.isna(cc['rsi']) and cc['rsi'] < 70)
        sell = (prev['close'] > prev['vwap'] and cc['close'] < cc['vwap'] and 
                cc['volume'] > cc['volume_ma'] * 2 and not pd.isna(cc['rsi']) and cc['rsi'] > 30)
        return {'buy_call': buy, 'buy_put': sell}
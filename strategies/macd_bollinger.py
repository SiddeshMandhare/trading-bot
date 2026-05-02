# strategies/macd_bollinger.py
import pandas as pd
import talib
from typing import Dict, Any
from .base import TradingStrategy

class MACD_Bollinger_Strategy(TradingStrategy):
    def get_strategy_name(self) -> str: return "MACD_Bollinger"
    
    def calculate_indicators(self, chart: pd.DataFrame) -> None:
        chart['macd'], chart['macd_signal'], _ = talib.MACD(chart['close'])
        chart['upper_band'], _, chart['lower_band'] = talib.BBANDS(chart['close'])
        chart['volume_ma'] = talib.SMA(chart['volume'], timeperiod=20)
        chart['adx'] = talib.ADX(chart['high'], chart['low'], chart['close'], timeperiod=14)
    
    def generate_signals(self, chart: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        if len(chart) < 2: return {'buy_call': False, 'buy_put': False}
        cc = chart.iloc[-1]
        buy = (cc['macd'] > cc['macd_signal'] and cc['close'] > cc['upper_band'] and 
               cc['volume'] > cc['volume_ma'] * 1.5 and not pd.isna(cc['adx']) and cc['adx'] > 25)
        sell = (cc['macd'] < cc['macd_signal'] and cc['close'] < cc['lower_band'] and 
                cc['volume'] > cc['volume_ma'] * 1.5 and not pd.isna(cc['adx']) and cc['adx'] > 25)
        return {'buy_call': buy, 'buy_put': sell}
        
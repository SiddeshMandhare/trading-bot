# strategies/orb.py
import pandas as pd
import talib
from typing import Dict, Any
from .base import TradingStrategy

class OpeningRangeBreakout(TradingStrategy):
    def get_strategy_name(self) -> str: return "ORB_30min"
    
    def calculate_indicators(self, chart: pd.DataFrame) -> None:
        if 'timestamp' in chart.columns:
            chart.set_index('timestamp', inplace=True)
        chart['volume_ma'] = chart['volume'].rolling(20).mean()
        chart['rsi'] = talib.RSI(chart['close'], timeperiod=14)
        chart['adx'] = talib.ADX(chart['high'], chart['low'], chart['close'], timeperiod=14)
    
    def generate_signals(self, chart: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        signals = {'buy_call': False, 'buy_put': False}
        df = chart.copy()
        if not isinstance(df.index, pd.DatetimeIndex):
            try: df.index = pd.to_datetime(df.index)
            except: return signals
        try: opening_range = df.between_time('09:15', '09:45')
        except: opening_range = df.iloc[:5] if len(df) >= 5 else df
        if len(opening_range) < 5: return signals
        high, low = opening_range['high'].max(), opening_range['low'].min()
        cc = chart.iloc[-1]
        signals['buy_call'] = (cc['close'] > high and cc['volume'] > cc['volume_ma'] * 1.5 and cc['rsi'] < 70 and cc['adx'] > 25)
        signals['buy_put'] = (cc['close'] < low and cc['volume'] > cc['volume_ma'] * 1.5 and cc['rsi'] > 30 and cc['adx'] > 25)
        return signals
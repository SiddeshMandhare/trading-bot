# strategies/ema_rsi.py
import numpy as np
import pandas as pd
import talib
from typing import Dict, Any
from .base import TradingStrategy

class EMA_RSI_Strategy(TradingStrategy):
    def get_strategy_name(self) -> str: return "EMA_RSI"
    
    def calculate_indicators(self, chart: pd.DataFrame) -> None:
        chart['ema_9'] = talib.EMA(chart['close'], timeperiod=9)
        chart['ema_15'] = talib.EMA(chart['close'], timeperiod=15)
        chart['rsi'] = talib.RSI(chart['close'], timeperiod=14)
        chart['volume_ma'] = talib.SMA(chart['volume'], timeperiod=20)
        chart['atr'] = talib.ATR(chart['high'], chart['low'], chart['close'], timeperiod=14)
        chart['sma_20'] = talib.SMA(chart['close'], timeperiod=20)
        conditions = [chart['close'] > chart['sma_20'], chart['close'] < chart['sma_20']]
        chart['market_type'] = np.select(conditions, ['bullish', 'bearish'], default='neutral')
    
    def generate_signals(self, chart: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        if len(chart) < 2: return {'buy_call': False, 'buy_put': False}
        cc, prev = chart.iloc[-1], chart.iloc[-2]
        bullish = prev['ema_9'] < prev['ema_15'] and cc['ema_9'] > cc['ema_15']
        bearish = prev['ema_9'] > prev['ema_15'] and cc['ema_9'] < cc['ema_15']
        return {'buy_call': cc['rsi'] > 50 and bullish and cc['market_type'] != "neutral",
                'buy_put': cc['rsi'] < 50 and bearish and cc['market_type'] != "neutral"}
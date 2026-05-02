# strategies/ma_crossover.py
import pandas as pd
import talib
from typing import Dict, Any
from .base import TradingStrategy

class MovingAverageCrossover(TradingStrategy):
    def get_strategy_name(self) -> str: return "MA_Crossover_50_200"
    
    def calculate_indicators(self, chart: pd.DataFrame) -> None:
        chart['ma_50'] = talib.SMA(chart['close'], timeperiod=50)
        chart['ma_200'] = talib.SMA(chart['close'], timeperiod=200)
        chart['volume_ma'] = talib.SMA(chart['volume'], timeperiod=20)
        chart['adx'] = talib.ADX(chart['high'], chart['low'], chart['close'], timeperiod=14)
    
    def generate_signals(self, chart: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        if len(chart) < 2: return {'buy_call': False, 'buy_put': False}
        cc, prev = chart.iloc[-1], chart.iloc[-2]
        golden = prev['ma_50'] < prev['ma_200'] and cc['ma_50'] > cc['ma_200']
        death = prev['ma_50'] > prev['ma_200'] and cc['ma_50'] < cc['ma_200']
        buy = golden and cc['volume'] > cc['volume_ma'] * 1.5 and not pd.isna(cc['adx']) and cc['adx'] > 25
        sell = death and cc['volume'] > cc['volume_ma'] * 1.5 and not pd.isna(cc['adx']) and cc['adx'] > 25
        return {'buy_call': buy, 'buy_put': sell}
# strategies/base.py
from abc import ABC, abstractmethod
import pandas as pd
from typing import Dict, Any

class TradingStrategy(ABC):
    @abstractmethod
    def calculate_indicators(self, chart: pd.DataFrame) -> None: pass
    @abstractmethod
    def generate_signals(self, chart: pd.DataFrame, symbol: str) -> Dict[str, Any]: pass
    @abstractmethod
    def get_strategy_name(self) -> str: pass
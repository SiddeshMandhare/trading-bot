# position_sizing.py
from typing import Dict, List
from config import Config

class KellyPositionSizer:
    def __init__(self):
        self.strategy_stats = {}
    
    def calculate_kelly_size(self, strategy_name: str, current_capital: float,
                           atr_points: float, current_price: float,
                           completed_orders: List[Dict]) -> int:
        wins = 0
        losses = 0
        total_profit = 0
        total_loss = 0
        
        for trade in completed_orders:
            if trade.get('strategy') == strategy_name:
                pnl = trade.get('pnl', 0)
                if pnl > 0:
                    wins += 1
                    total_profit += pnl
                elif pnl < 0:
                    losses += 1
                    total_loss += abs(pnl)
        
        total_trades = wins + losses
        
        if total_trades < Config.MIN_KELlY_TRADES:
            risk_amount = current_capital * Config.BASE_CAPITAL_RISK_PERCENT
            return int(risk_amount / atr_points) if atr_points > 0 else 1
        
        win_rate = wins / total_trades
        avg_win = total_profit / wins if wins > 0 else 1
        avg_loss = total_loss / losses if losses > 0 else 1
        
        b = avg_win / avg_loss if avg_loss > 0 else 1
        kelly_fraction = (win_rate * b - (1 - win_rate)) / b
        
        if Config.HALF_KELLY:
            kelly_fraction = kelly_fraction * 0.5
        
        kelly_fraction = max(0.01, min(0.03, kelly_fraction))
        risk_amount = current_capital * kelly_fraction
        position_size = int(risk_amount / atr_points) if atr_points > 0 else 1
        
        return max(1, position_size)


class StrategyWeightOptimizer:
    """Dynamically adjust strategy weights based on performance"""
    
    def __init__(self):
        self.weights = {}
        self.last_update = None
        
    def update_weights(self, completed_orders: List[Dict]):
        """Recalculate optimal strategy weights"""
        
        if len(completed_orders) < 20:
            return
        
        strategy_performance = {}
        
        for trade in completed_orders[-100:]:
            strategy = trade.get('strategy')
            pnl = trade.get('pnl', 0)
            
            if not strategy:
                continue
                
            if strategy not in strategy_performance:
                strategy_performance[strategy] = {
                    'trades': 0,
                    'profit': 0,
                    'wins': 0
                }
            
            strategy_performance[strategy]['trades'] += 1
            strategy_performance[strategy]['profit'] += pnl
            if pnl > 0:
                strategy_performance[strategy]['wins'] += 1
        
        scores = {}
        total_score = 0
        
        for strategy, perf in strategy_performance.items():
            if perf['trades'] < 5:
                continue
                
            win_rate = perf['wins'] / perf['trades']
            profit_factor = perf['profit'] / 1000
            
            score = (win_rate * 0.6) + (min(profit_factor, 1) * 0.4)
            scores[strategy] = max(0.1, min(0.5, score))
            total_score += scores[strategy]
        
        if total_score > 0:
            for strategy in scores:
                normalized_weight = scores[strategy] / total_score
                self.weights[strategy] = normalized_weight
                Config.STRATEGY_WEIGHTS[strategy] = normalized_weight
            
            print(f"\n📊 Updated Strategy Weights:")
            for strategy, weight in self.weights.items():
                print(f"   {strategy}: {weight:.1%}")
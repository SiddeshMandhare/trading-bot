# trade_execution.py
import time
import datetime
from typing import Dict, Optional
from config import Config
from risk_management import DynamicExitCalculator

class TradeExecution:
    def __init__(self, tsl, multi_account_manager=None):
        self.tsl = tsl
        self.multi_account_manager = multi_account_manager
        self.orderbook = {}
        self.completed_orders = []
        self.ist = Config.IST
        self.current_balance = Config.BASE_CAPITAL

    def get_balance(self):
        try:
            return self.tsl.get_balance()
        except:
            return Config.BASE_CAPITAL

    def get_available_capital(self):
        try:
            balance = self.tsl.get_balance()
            if balance and balance > 0:
                return balance
        except:
            pass
        return Config.BASE_CAPITAL

    def calculate_position_size(self, atr_points: float, current_price: float, strategy_name: str = None) -> int:
        current_capital = self.get_available_capital()
        if current_capital <= Config.Minimum_trading_capital:
            return 0
        
        risk_amount = current_capital * Config.BASE_CAPITAL_RISK_PERCENT
        position_size = int(risk_amount / atr_points) if atr_points > 0 else 1
        return max(1, position_size)
    
    def place_super_order(self, name: str, action: str, qty: int, entry_price: float, 
                         atr_points: float, strategy_name: str, chart) -> Optional[Dict]:
        try:
            if action == 'BUY':
                stop_loss_price = round(entry_price - atr_points, 2)
                target_price = round(entry_price + (atr_points * Config.RISK_REWARD_RATIO), 2)
            else:
                stop_loss_price = round(entry_price + atr_points, 2)
                target_price = round(entry_price - (atr_points * Config.RISK_REWARD_RATIO), 2)
            
            super_order_id = self.tsl.place_super_order(
                tradingsymbol=name, exchange='NSE', transaction_type=action, quantity=qty,
                order_type='MARKET', trade_type='MIS', price=0,
                target_price=target_price, stop_loss_price=stop_loss_price, trailing_jump=0
            )
            
            if super_order_id:
                current_time = datetime.datetime.now(self.ist)
                return {
                    'name': name, 'options_name': name, 'option_type': 'STOCK',
                    'date': str(current_time.date()), 'entry_time': current_time.strftime('%H:%M:%S'),
                    'max_holding_time': current_time + datetime.timedelta(hours=Config.MAX_HOLDING_HOURS),
                    'super_order_id': super_order_id, 'entry_price': entry_price, 'qty': qty,
                    'sl': stop_loss_price, 'target': target_price, 'strategy': strategy_name,
                    'atr': atr_points, 'trade_type': 'EQUITY', 'buy_sell': action,
                    'position_type': "LONG" if action == 'BUY' else "SHORT",
                    'traded': "yes", 'order_type': 'SUPER_OPTIMIZED'
                }
            return None
        except Exception as e:
            print(f"Super Order error: {e}")
            return None
    
    def place_traditional_order(self, name: str, action: str, qty: int, atr_points: float) -> Optional[Dict]:
        try:
            entry_orderid = self.tsl.order_placement(
                tradingsymbol=name, exchange='NSE', quantity=qty, price=0,
                trigger_price=0, order_type='MARKET', transaction_type=action, trade_type='MIS'
            )
            
            if not entry_orderid:
                return None
            
            time.sleep(2)
            ltp_data = self.tsl.get_ltp_data(names=[name])
            entry_price = ltp_data.get(name, 0)
            
            if action == 'BUY':
                stop_loss_price = round(entry_price - atr_points, 2)
                target_price = round(entry_price + (atr_points * Config.RISK_REWARD_RATIO), 2)
            else:
                stop_loss_price = round(entry_price + atr_points, 2)
                target_price = round(entry_price - (atr_points * Config.RISK_REWARD_RATIO), 2)
            
            current_time = datetime.datetime.now(self.ist)
            return {
                'name': name, 'options_name': name, 'option_type': 'STOCK',
                'date': str(current_time.date()), 'entry_time': current_time.strftime('%H:%M:%S'),
                'max_holding_time': current_time + datetime.timedelta(hours=Config.MAX_HOLDING_HOURS),
                'entry_orderid': entry_orderid, 'entry_price': entry_price, 'qty': qty,
                'sl': stop_loss_price, 'target': target_price, 'strategy': 'MULTI',
                'atr': atr_points, 'trade_type': 'EQUITY', 'buy_sell': action,
                'position_type': "LONG" if action == 'BUY' else "SHORT",
                'traded': "yes", 'order_type': 'TRADITIONAL'
            }
        except Exception as e:
            print(f"Traditional order error: {e}")
            return None
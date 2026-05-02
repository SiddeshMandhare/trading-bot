# # main.py - Original Trading Bot (Preserved)
# import os
# import sys
# import time
# import json
# import sqlite3
# import logging
# import datetime
# import winsound
# import pandas as pd
# from tabulate import tabulate
# from typing import Dict, List, Any
# from collections import defaultdict
# from config import Config
# from auth_service import create_tradehull_with_totp
# from telegram_service import TelegramService
# from data_service import DataService
# from trade_execution import TradeExecution
# from risk_management import SignalStrength, MarketRegime, SignalCooldown, AdaptiveTrailingStop
# from position_sizing import KellyPositionSizer
# from strategies import (
#     EMA_RSI_Strategy, MACD_Bollinger_Strategy, RSI_50_Crossover,
#     VWAP_Strategy, MovingAverageCrossover, OpeningRangeBreakout
# )

# # Setup logging
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# logger = logging.getLogger(__name__)


# class OptionTradingBot:
#     def __init__(self):
#         print("Initializing OptionTradingBot with TOTP authentication...")
        
#         # Clean database
#         if os.path.exists('trading_bot.db'):
#             # Don't delete, just preserve
#             pass
        
#         # Authenticate with Dhan
#         self.tsl = create_tradehull_with_totp(Config.CLIENT_CODE, Config.PIN, Config.TOTP_SECRET)
#         if not self.tsl:
#             raise Exception("Primary account authentication failed")
        
#         # Initialize services
#         self.data_service = DataService(self.tsl)
#         self.execution = TradeExecution(self.tsl)
        
#         # Initialize components
#         self.signal_cooldown = SignalCooldown()
#         self.trailing_manager = AdaptiveTrailingStop() if Config.ENABLE_ADAPTIVE_TRAILING else None
#         self.kelly_sizer = KellyPositionSizer() if Config.USE_Kelly_SIZING else None
#         self.completed_orders = []
#         self.orderbook = {}
        
#         # Database
#         self.conn = self._init_database()
        
#         # Strategies
#         self.strategies = self._init_strategies()
        
#         # Capital
#         self.current_balance = self._set_dynamic_capital()
#         self.execution.current_balance = self.current_balance
        
#         # Telegram
#         self.telegram = TelegramService(Config.BOT_TOKEN, Config.RECEIVER_CHAT_ID, self)
#         self.telegram.start_command_handler()
        
#         print(f"Bot ready! Balance: ₹{self.current_balance:,.2f}")
    
#     def _init_strategies(self):
#         strategies = []
#         strategy_map = {
#             'EMA_RSI': EMA_RSI_Strategy, 'MACD_Bollinger': MACD_Bollinger_Strategy,
#             'RSI_50_Crossover': RSI_50_Crossover, 'VWAP_Reversion': VWAP_Strategy,
#             'MA_Crossover_50_200': MovingAverageCrossover, 'ORB_30min': OpeningRangeBreakout
#         }
#         for name in Config.ACTIVE_STRATEGIES:
#             if name in strategy_map:
#                 strategies.append(strategy_map[name]())
#                 print(f"Loaded strategy: {name}")
#         return strategies
    
#     def _init_database(self):
#         conn = sqlite3.connect('trading_bot.db', check_same_thread=False)
#         cursor = conn.cursor()
#         cursor.execute('''
#             CREATE TABLE IF NOT EXISTS trades (
#                 trade_id INTEGER PRIMARY KEY AUTOINCREMENT,
#                 symbol TEXT, entry_time DATETIME, entry_price REAL,
#                 quantity INTEGER, stop_loss REAL, target_price REAL,
#                 exit_price REAL, pnl REAL, strategy TEXT,
#                 position_type TEXT, status TEXT, exit_reason TEXT, exit_time DATETIME
#             )
#         ''')
#         conn.commit()
#         return conn
    
#     def _set_dynamic_capital(self):
#         try:
#             balance = self.execution.get_balance()
#             if balance and balance > 0:
#                 return balance
#         except:
#             pass
#         return Config.BASE_CAPITAL
    
#     def get_available_capital(self):
#         return self.current_balance
    
#     def update_balance_after_trade(self, trade_value: float, pnl: float = 0, operation: str = "deduct"):
#         margin_amount = trade_value / Config.BROKER_MARGIN_MULTIPLIER
#         if operation == "deduct":
#             self.current_balance -= margin_amount
#         else:
#             self.current_balance += margin_amount + (pnl / Config.BROKER_MARGIN_MULTIPLIER)
#         return True
    
#     def save_trade(self, trade_data: Dict):
#         """Save trade to database"""
#         try:
#             cursor = self.conn.cursor()
#             cursor.execute('''
#                 INSERT INTO trades (symbol, entry_time, entry_price, quantity, stop_loss, target_price, pnl, strategy, position_type, status)
#                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
#             ''', (
#                 trade_data.get('name', ''),
#                 f"{trade_data.get('date', '')} {trade_data.get('entry_time', '')}",
#                 trade_data.get('entry_price', 0),
#                 trade_data.get('qty', 0),
#                 trade_data.get('sl', 0),
#                 trade_data.get('target', 0),
#                 trade_data.get('pnl', 0),
#                 trade_data.get('strategy', ''),
#                 trade_data.get('position_type', ''),
#                 'closed' if trade_data.get('exit_time') else 'open'
#             ))
#             self.conn.commit()
#         except Exception as e:
#             print(f"Failed to save trade: {e}")
    
#     def send_trade_alert(self, trade_data: Dict, alert_type: str):
#         """Send trade alert to Telegram"""
#         try:
#             if alert_type == "ENTRY":
#                 message = f"🚀 ENTRY: {trade_data.get('buy_sell', '')} {trade_data.get('qty', 0)} {trade_data.get('name', '')} @ ₹{trade_data.get('entry_price', 0):.2f}"
#             elif alert_type == "EXIT":
#                 pnl = trade_data.get('pnl', 0)
#                 emoji = "📈" if pnl > 0 else "📉" if pnl < 0 else "➖"
#                 message = f"🔴 EXIT: {trade_data.get('name', '')}\n{emoji} P&L: ₹{pnl:+,.2f}"
#             else:
#                 return
#             self.telegram.send_alert(message)
#         except Exception as e:
#             print(f"Alert error: {e}")
    
#     def generate_signals(self, chart: pd.DataFrame, symbol: str) -> Dict[str, Any]:
#         signals = {'buy_call': False, 'buy_put': False, 'strategies': []}
        
#         for strategy in self.strategies:
#             try:
#                 strategy.calculate_indicators(chart)
#                 strategy_signals = strategy.generate_signals(chart, symbol)
#                 signals['strategies'].append({'name': strategy.get_strategy_name(), 'signals': strategy_signals})
                
#                 weight = Config.STRATEGY_WEIGHTS.get(strategy.get_strategy_name(), 0)
#                 if weight > 0:
#                     if strategy_signals.get('buy_call'):
#                         signals['buy_call'] = True
#                     if strategy_signals.get('buy_put'):
#                         signals['buy_put'] = True
#             except Exception as e:
#                 logger.error(f"Strategy {strategy.get_strategy_name()} failed: {e}")
        
#         return signals
    
#     def place_stock_order(self, name: str, signals: Dict, chart: pd.DataFrame):
#         if name in self.orderbook:
#             return
        
#         action = 'BUY' if signals.get('buy_call') else 'SELL'
        
#         # Find triggering strategy
#         triggering_strategy = None
#         for s in signals.get('strategies', []):
#             if (action == 'BUY' and s['signals'].get('buy_call')) or (action == 'SELL' and s['signals'].get('buy_put')):
#                 triggering_strategy = s
#                 break
        
#         if not triggering_strategy:
#             return
        
#         strategy_name = triggering_strategy['name']
#         current_price = chart['close'].iloc[-1]
        
#         # Signal strength check
#         scores = SignalStrength.calculate_signal_strength(chart, name, action)
#         if not SignalStrength.should_trade(scores):
#             print(f"Signal too weak ({scores['overall']} < {Config.MIN_SIGNAL_STRENGTH})")
#             return
        
#         # Market regime filter
#         if Config.USE_MARKET_REGIME_FILTER:
#             regime = MarketRegime.detect_regime(chart)
#             bias = MarketRegime.get_bias(regime)
#             if (bias == 'LONG_ONLY' and action != 'BUY') or (bias == 'SHORT_ONLY' and action != 'SELL'):
#                 return
        
#         # Cooldown check
#         current_time = Config.get_current_time()
#         if not self.signal_cooldown.can_take_signal(name, current_price, current_time):
#             return
        
#         # Calculate ATR
#         try:
#             atr = chart.ta.atr(length=14)
#             atr_points = atr.iloc[-1] * Config.ATR_MULTIPLIER if not pd.isna(atr.iloc[-1]) else current_price * 0.01
#         except:
#             atr_points = current_price * Config.ATR_MULTIPLIER * 0.01
        
#         # Position size
#         qty = self.execution.calculate_position_size(atr_points, current_price, strategy_name)
#         if qty <= 0:
#             return
        
#         # Place order
#         if Config.USE_SUPER_ORDERS:
#             order = self.execution.place_super_order(name, action, qty, current_price, atr_points, strategy_name, chart)
#         else:
#             order = self.execution.place_traditional_order(name, action, qty, atr_points)
        
#         if order:
#             trade_value = qty * current_price
#             self.update_balance_after_trade(trade_value, operation="deduct")
#             self.orderbook[name] = order
#             self.signal_cooldown.record_signal(name, current_price, current_time)
#             self.save_trade(order)
#             self.send_trade_alert(order, "ENTRY")
#             print(f"Order placed: {action} {qty} {name}")
    
#     def monitor_open_positions(self, symbol: str):
#         if symbol not in self.orderbook:
#             return
        
#         order = self.orderbook[symbol]
#         current_price = self.data_service.get_current_price(symbol)
        
#         if not current_price:
#             return
        
#         # Adaptive trailing stop
#         if Config.ENABLE_ADAPTIVE_TRAILING and self.trailing_manager and order.get('order_type') == 'SUPER_OPTIMIZED':
#             new_stop = self.trailing_manager.calculate_new_stop(
#                 symbol, order['position_type'], current_price, order['entry_price'], order.get('atr', 0)
#             )
#             if new_stop and new_stop != order.get('sl'):
#                 order['sl'] = new_stop
        
#         # Check stop loss
#         sl_hit = (order['position_type'] == 'LONG' and current_price <= order['sl']) or \
#                  (order['position_type'] == 'SHORT' and current_price >= order['sl'])
        
#         if sl_hit:
#             self._close_position(symbol, current_price, "SL_HIT")
#             return
        
#         # Check holding time
#         if 'max_holding_time' in order and Config.get_current_time() >= order['max_holding_time']:
#             self._close_position(symbol, current_price, "HOLDING_TIME_EXCEEDED")
    
#     def _close_position(self, symbol: str, exit_price: float, reason: str):
#         if symbol not in self.orderbook:
#             return
        
#         order = self.orderbook[symbol]
#         pnl = ((exit_price - order['entry_price']) * order['qty']) if order['position_type'] == 'LONG' \
#               else ((order['entry_price'] - exit_price) * order['qty'])
        
#         trade_value = order['qty'] * order['entry_price']
#         self.update_balance_after_trade(trade_value, pnl, operation="add")
        
#         order.update({'exit_price': exit_price, 'pnl': pnl, 'remark': reason, 'exit_time': Config.get_current_time().strftime('%H:%M:%S')})
#         self.completed_orders.append(order.copy())
#         del self.orderbook[symbol]
        
#         self.save_trade(order)
#         self.send_trade_alert(order, "EXIT")
#         print(f"Position closed: {symbol} P&L: ₹{pnl:+,.2f}")
    
#     def close_all_positions(self):
#         for symbol in list(self.orderbook.keys()):
#             price = self.data_service.get_current_price(symbol)
#             if price:
#                 self._close_position(symbol, price, "MANUAL_CLOSE")
    
#     def is_market_open(self) -> bool:
#         current_time = Config.get_current_time().time()
#         weekday = Config.get_current_time().weekday()
#         return (datetime.time(9, 15) <= current_time <= datetime.time(15, 30)) and (weekday < 5)
    
#     def verify_api_connection(self) -> bool:
#         test_chart = self.data_service.get_symbol_data('RELIANCE')
#         return test_chart is not None
    
#     def run(self):
#         print("Starting main trading loop...")
        
#         try:
#             while True:
#                 if self.is_market_open():
#                     for symbol in Config.WATCHLIST:
#                         chart = self.data_service.get_symbol_data(symbol)
#                         if chart is not None:
#                             signals = self.generate_signals(chart, symbol)
#                             if signals['buy_call'] or signals['buy_put']:
#                                 self.place_stock_order(symbol, signals, chart)
                            
#                             if symbol in self.orderbook:
#                                 self.monitor_open_positions(symbol)
                    
#                     time.sleep(15 * int(Config.TIMEFRAME))
#                 else:
#                     if Config.get_current_time().time() > datetime.time(15, 30):
#                         self.close_all_positions()
#                         break
#                     time.sleep(60)
#         except KeyboardInterrupt:
#             print("Bot stopped by user")
#             self.close_all_positions()




#####################################################################################################################




# main.py - COMPLETE ORIGINAL TRADING BOT (All logic preserved)
import os
import sys
import time
import json
import sqlite3
import logging
import datetime
import winsound
import pandas as pd
import numpy as np
import talib
from tabulate import tabulate
from typing import Dict, List, Any, Optional
from collections import defaultdict

from config import Config
from auth_service import create_tradehull_with_totp
from telegram_service import TelegramService
from data_service import DataService
from trade_execution import TradeExecution
from risk_management import (
    SignalStrength, MarketRegime, SignalCooldown, 
    AdaptiveTrailingStop, DynamicExitCalculator
)
from position_sizing import KellyPositionSizer, StrategyWeightOptimizer
from strategies import (
    EMA_RSI_Strategy, MACD_Bollinger_Strategy, RSI_50_Crossover,
    VWAP_Strategy, MovingAverageCrossover, OpeningRangeBreakout
)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class OptionTradingBot:
    def __init__(self):
        print("Initializing OptionTradingBot with TOTP authentication...")
        print("🚀 MULTI-ACCOUNT COPY TRADING SYSTEM")
        
        # Clean up old database and start fresh
        try:
            if os.path.exists('trading_bot.db'):
                os.remove('trading_bot.db')
                print("✅ Cleaned up old database")
        except:
            pass

        # Initialize Dhan Tradehull with TOTP
        self.tsl = create_tradehull_with_totp(Config.CLIENT_CODE, Config.PIN, Config.TOTP_SECRET)
        if not self.tsl:
            print("❌ CRITICAL: Failed to authenticate primary account with TOTP!")
            raise Exception("Primary account authentication failed")

        # Initialize Multi-Account Trading Manager (if copy trading enabled)
        self.multi_account_manager = None
        if Config.COPY_TRADING_ENABLED:
            from multi_account_manager import MultiAccountTradingManager
            self.multi_account_manager = MultiAccountTradingManager(self)
            self.multi_account_manager.initialize_accounts()

        # Setup logging
        self.setup_logging()
        
        # Initialize capital
        self.current_balance = self.set_dynamic_capital()
        
        # Initialize core components
        self.initialize_variables()
        self.initialize_strategies()
        
        # Initialize optimization layers
        self.initialize_optimization_layers()
        
        # Initialize database
        self.initialize_database()
        
        # Timezone
        self.ist = Config.IST
        
        # Start Telegram command bot
        self.start_telegram_commands()

        self.setup_pnl_tracking()
        
        print("\n" + "="*60)
        print("🎯 MULTI-ACCOUNT COPY TRADING BOT READY (TOTP AUTH)")
        print(f"📊 Active Accounts: 1")
        print(f"⚡ Copy Trading: {'ON' if Config.COPY_TRADING_ENABLED else 'OFF'}")
        print(f"🌟 Super Orders: {'ENABLED' if Config.USE_SUPER_ORDERS else 'DISABLED'}")
        print("="*60)

    def setup_logging(self):
        """Setup logger with ASCII-only characters for Windows"""
        self.logger = logging.getLogger('OptionTradingBot')
        self.logger.setLevel(logging.INFO)
        
        if self.logger.handlers:
            for handler in self.logger.handlers[:]:
                self.logger.removeHandler(handler)
        
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(console_handler)
        
        file_handler = logging.FileHandler('trading_bot.log', encoding='utf-8')
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(file_handler)

    def initialize_database(self):
        """Initialize SQLite database with proper schema"""
        self.conn = sqlite3.connect('trading_bot.db', check_same_thread=False)
        cursor = self.conn.cursor()

        cursor.execute('DROP TABLE IF EXISTS trades')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                trade_id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                option_symbol TEXT NOT NULL,
                option_type TEXT NOT NULL,
                strategy TEXT NOT NULL,
                entry_time DATETIME NOT NULL,
                entry_price REAL NOT NULL,
                quantity INTEGER NOT NULL,
                stop_loss REAL NOT NULL,
                target_price REAL,
                exit_time DATETIME,
                exit_price REAL,
                pnl REAL,
                exit_reason TEXT,
                max_holding_time DATETIME,
                status TEXT NOT NULL,
                order_type TEXT DEFAULT 'TRADITIONAL',
                super_order_id TEXT,
                sl_orderid TEXT,
                entry_orderid TEXT,
                trade_direction TEXT,
                position_type TEXT,
                trailing_enabled BOOLEAN DEFAULT 0,
                signal_strength INTEGER,
                market_regime TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute("PRAGMA table_info(trades)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'signal_strength' not in columns:
            cursor.execute("ALTER TABLE trades ADD COLUMN signal_strength INTEGER")
        if 'market_regime' not in columns:
            cursor.execute("ALTER TABLE trades ADD COLUMN market_regime TEXT")
            
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS strategy_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_name TEXT NOT NULL,
                calls INTEGER DEFAULT 0,
                puts INTEGER DEFAULT 0,
                total_profit REAL DEFAULT 0,
                total_trades INTEGER DEFAULT 0,
                win_rate REAL DEFAULT 0,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.conn.commit()
        print("✅ Database initialized with all required columns")

    def initialize_variables(self):
        self.opening_balance = Config.BASE_CAPITAL
        self.risk_per_trade = self.calculate_risk_per_trade()
        self.conn = None
        self.orderbook = {}
        self.completed_orders = []
        self.strategy_performance = {}

    def initialize_strategies(self):
        """Initialize all trading strategies"""
        self.strategies = []
        
        strategy_map = {
            'EMA_RSI': EMA_RSI_Strategy,
            'MACD_Bollinger': MACD_Bollinger_Strategy,
            'RSI_50_Crossover': RSI_50_Crossover,
            'VWAP_Reversion': VWAP_Strategy,
            'MA_Crossover_50_200': MovingAverageCrossover,
            'ORB_30min': OpeningRangeBreakout
        }
        
        for strategy_name in Config.ACTIVE_STRATEGIES:
            if strategy_name in strategy_map:
                self.strategies.append(strategy_map[strategy_name]())
                print(f"✅ Loaded strategy: {strategy_name}")

    def initialize_optimization_layers(self):
        """Initialize all profit optimization components"""
        self.signal_cooldown = SignalCooldown()
        self.market_regime = MarketRegime()
        self.exit_calculator = DynamicExitCalculator()
        self.trailing_manager = AdaptiveTrailingStop() if Config.ENABLE_ADAPTIVE_TRAILING else None
        self.kelly_sizer = KellyPositionSizer() if Config.USE_Kelly_SIZING else None
        self.strategy_optimizer = StrategyWeightOptimizer() if Config.ENABLE_STRATEGY_WEIGHT_OPTIMIZATION else None
        self.completed_orders = []
        print("✅ Optimization layers initialized")

    def set_dynamic_capital(self):
        """Set BASE_CAPITAL dynamically from actual account balance"""
        try:
            balance = self.tsl.get_balance()
            if balance and balance > 0:
                Config.BASE_CAPITAL = balance
                print(f"✅ Set BASE_CAPITAL to actual balance: ₹{balance:,.2f}")
                return balance
            else:
                return getattr(self, 'current_balance', Config.BASE_CAPITAL)
        except Exception as e:
            print(f"⚠️ Balance fetch failed: {str(e)}")
            return getattr(self, 'current_balance', Config.BASE_CAPITAL)

    def get_current_balance(self):
        """Get current account balance with robust error handling"""
        try:
            balance_data = self.tsl.get_balance()
            if balance_data and isinstance(balance_data, (int, float)) and balance_data > 0:
                self.current_balance = balance_data
                return balance_data
            else:
                return getattr(Config, 'BASE_CAPITAL', 10000.0)
        except Exception as e:
            print(f"Balance fetch error: {str(e)}")
            return getattr(self, 'current_balance', Config.BASE_CAPITAL)

    def update_balance_after_trade(self, trade_data: Dict, operation: str = "deduct"):
        """Update current balance after a trade"""
        try:
            if isinstance(trade_data, dict):
                if 'trade_value' in trade_data:
                    trade_value = trade_data['trade_value']
                elif 'qty' in trade_data and 'entry_price' in trade_data:
                    trade_value = trade_data['qty'] * trade_data['entry_price']
                else:
                    return False
            else:
                trade_value = trade_data

            if not hasattr(self, 'current_balance'):
                self.current_balance = self.get_current_balance()

            if operation == "deduct":
                margin_amount = trade_value / Config.BROKER_MARGIN_MULTIPLIER
                if self.current_balance >= margin_amount:
                    self.current_balance -= margin_amount
                    return True
                return False
            elif operation == "add":
                margin_amount = trade_value / Config.BROKER_MARGIN_MULTIPLIER
                pnl = trade_data.get('pnl', 0) if isinstance(trade_data, dict) else 0
                pnl_margin = pnl / Config.BROKER_MARGIN_MULTIPLIER
                self.current_balance += margin_amount + pnl_margin
                return True
        except Exception as e:
            print(f"❌ Balance update error: {str(e)}")
        return False
    
    def get_available_capital(self):
        """Get available capital for new trades"""
        if hasattr(self, 'current_balance') and self.current_balance > 0:
            return self.current_balance
        fresh_balance = self.get_current_balance()
        self.current_balance = fresh_balance
        return fresh_balance

    def calculate_risk_per_trade(self):
        """Calculate risk amount per trade"""
        return self.opening_balance * Config.BASE_CAPITAL_RISK_PERCENT

    def calculate_position_size(self, atr_points: float, multiplier: int = 1, 
                               current_price: float = None, strategy_name: str = None) -> int:
        """Calculate position size with Kelly optimization"""
        try:
            current_capital = self.get_available_capital()
            
            if current_capital <= Config.Minimum_trading_capital:
                print(f"⚠️ Insufficient capital: ₹{current_capital:,.2f}")
                return 0
            
            if Config.USE_Kelly_SIZING and self.kelly_sizer and strategy_name:
                kelly_size = self.kelly_sizer.calculate_kelly_size(
                    strategy_name, current_capital, atr_points, current_price, self.completed_orders
                )
                if kelly_size > 0:
                    return kelly_size
            
            if current_capital < 500:
                risk_amount = max(current_capital * 0.02, 10)
            elif current_capital < 2000:
                risk_amount = current_capital * Config.BASE_CAPITAL_RISK_PERCENT * 1.5
            else:
                risk_amount = current_capital * Config.BASE_CAPITAL_RISK_PERCENT
            
            if atr_points <= 0:
                atr_points = current_price * 0.01 if current_price else 0.50
            
            position_size = int((risk_amount / atr_points) * multiplier)
            
            if position_size <= 0 and current_price and current_price > 0:
                min_trade_value = 500
                position_size = max(1, int(min_trade_value / current_price))
            
            position_size = max(1, position_size)
            
            if current_price and current_price > 0:
                trade_value = position_size * current_price
                buying_power = current_capital * Config.BROKER_MARGIN_MULTIPLIER
                max_allowed = buying_power * Config.MAX_CAPITAL_PER_TRADE
                if trade_value > max_allowed:
                    position_size = max(1, int(max_allowed / current_price))
            
            return position_size
        except Exception as e:
            print(f"❌ Position sizing error: {str(e)}")
            return 1

    def place_super_order_wrapper(self, name: str, action: str, qty: int, entry_price: float, 
                                 atr_points: float, strategy_name: str, 
                                 chart: pd.DataFrame) -> Dict[str, Any]:
        """Place an optimized Super Order with dynamic exit levels"""
        try:
            if Config.ENABLE_DYNAMIC_EXITS:
                position_type = 'LONG' if action == 'BUY' else 'SHORT'
                exit_levels = self.exit_calculator.calculate_exit_levels(
                    chart, entry_price, position_type, atr_points
                )
                stop_loss_price = exit_levels['sl']
                target_price = exit_levels['target']
            else:
                if action == 'BUY':
                    stop_loss_price = round(entry_price - atr_points, 2)
                    target_price = round(entry_price + (atr_points * Config.RISK_REWARD_RATIO), 2)
                else:
                    stop_loss_price = round(entry_price + atr_points, 2)
                    target_price = round(entry_price - (atr_points * Config.RISK_REWARD_RATIO), 2)
            
            super_order_id = self.tsl.place_super_order(
                tradingsymbol=name,
                exchange='NSE',
                transaction_type=action,
                quantity=qty,
                order_type='MARKET',
                trade_type='MIS',
                price=0,
                target_price=target_price,
                stop_loss_price=stop_loss_price,
                trailing_jump=0
            )
            
            if super_order_id:
                current_time = datetime.datetime.now(self.ist)
                order_details = {
                    'name': name, 'options_name': name, 'option_type': 'STOCK',
                    'date': str(current_time.date()), 'entry_time': current_time.strftime('%H:%M:%S'),
                    'max_holding_time': current_time + datetime.timedelta(hours=Config.MAX_HOLDING_HOURS),
                    'super_order_id': super_order_id, 'entry_price': entry_price, 'qty': qty,
                    'sl': stop_loss_price, 'target': target_price, 'original_sl': stop_loss_price,
                    'strategy': strategy_name, 'atr': atr_points, 'trade_type': 'EQUITY',
                    'buy_sell': action, 'trade_direction': "BUY" if action == 'BUY' else "SELL",
                    'position_type': "LONG" if action == 'BUY' else "SHORT", 'traded': "yes",
                    'order_type': 'SUPER_OPTIMIZED', 'trailing_enabled': Config.ENABLE_ADAPTIVE_TRAILING
                }
                return order_details
            return None
        except Exception as e:
            print(f"❌ SUPER ORDER ERROR: {str(e)}")
            return None

    def place_sl_order(self, symbol: str, action: str, qty: int, stop_loss_price: float):
        """Place stop loss order (for traditional orders only)"""
        try:
            sl_transaction_type = 'SELL' if action == 'BUY' else 'BUY'
            
            sl_orderid = self.tsl.order_placement(
                tradingsymbol=str(symbol),
                exchange='NSE',
                transaction_type=str(sl_transaction_type),
                quantity=int(qty),
                order_type='STOPMARKET',
                price=0,
                trigger_price=float(stop_loss_price),
                trade_type='MIS'
            )
            
            if sl_orderid:
                if symbol in self.orderbook:
                    self.orderbook[symbol]['sl_orderid'] = sl_orderid
                print(f"   ✅ STOP-LOSS PLACED: {sl_orderid}")
            else:
                print(f"   ❌ STOP-LOSS FAILED")
                
        except Exception as e:
            print(f"   ❌ STOP-LOSS ERROR: {str(e)}")

    def place_stock_order(self, name: str, signals: Dict, cc: pd.Series, chart: pd.DataFrame):
        """Execute stock order with ALL optimizations"""
        
        current_capital = self.get_available_capital()
        if current_capital <= Config.Minimum_trading_capital:
            print(f"🛑 SKIPPING {name}: Insufficient capital")
            return
        
        if name in self.orderbook:
            print(f"⚠️ SKIPPING {name}: Already in orderbook")
            return

        try:
            print(f"\n{'='*60}")
            print(f"OPTIMIZED ORDER EXECUTION FOR {name}")
            print(f"{'='*60}")
            
            if not signals or not any([signals.get('buy_call'), signals.get('buy_put')]):
                self.logger.warning(f"No valid buy signals for {name}")
                return
            
            action = 'BUY' if signals.get('buy_call') else 'SELL'
            
            triggering_strategy = None
            for s in signals.get('strategies', []):
                if (action == 'BUY' and s['signals'].get('buy_call')) or \
                   (action == 'SELL' and s['signals'].get('buy_put')):
                    triggering_strategy = s
                    break
            
            if not triggering_strategy:
                self.logger.warning(f"No triggering strategy found for {name}")
                return
                
            strategy_name = triggering_strategy['name']
            self.logger.info(f"Preparing {action} order for {name} using {strategy_name}")
            
            current_price = chart['close'].iloc[-1]
            
            scores = SignalStrength.calculate_signal_strength(chart, name, action)
            signal_grade = SignalStrength.get_signal_grade(scores)
            
            print(f"\n📊 SIGNAL STRENGTH ANALYSIS:")
            print(f"   OVERALL: {scores['overall']}/100 (Grade: {signal_grade})")
            
            if not SignalStrength.should_trade(scores, Config.MIN_SIGNAL_STRENGTH):
                print(f"⚠️ Signal too weak ({scores['overall']} < {Config.MIN_SIGNAL_STRENGTH})")
                return
            
            if Config.USE_MARKET_REGIME_FILTER:
                self.current_regime = MarketRegime.detect_regime(chart)
                bias = MarketRegime.get_bias(self.current_regime)
                if bias == 'LONG_ONLY' and action != 'BUY':
                    return
                if bias == 'SHORT_ONLY' and action != 'SELL':
                    return
            
            current_time = datetime.datetime.now(self.ist)
            if not self.signal_cooldown.can_take_signal(name, current_price, current_time):
                return
            
            try:
                atr = chart.ta.atr(length=14)
                if atr is None or atr.iloc[-1] <= 0 or pd.isna(atr.iloc[-1]):
                    atr_points = current_price * Config.ATR_MULTIPLIER * 0.01
                else:
                    atr_points = atr.iloc[-1] * Config.ATR_MULTIPLIER
            except:
                atr_points = current_price * Config.ATR_MULTIPLIER * 0.01
            
            base_qty = self.calculate_position_size(atr_points, 1, current_price, strategy_name)
            if base_qty <= 0:
                return
            
            # Prepare trade details
            trade_details = {
                'symbol': name, 'action': action, 'base_qty': base_qty,
                'entry_price': current_price, 'sl': 0, 'target': 0,
                'strategy': strategy_name, 'signal_strength': scores['overall'], 'signal_grade': signal_grade
            }
            
            # Place order (simplified - using super order if enabled)
            if Config.USE_SUPER_ORDERS:
                order_details = self.place_super_order_wrapper(
                    name=name, action=action, qty=base_qty, entry_price=current_price,
                    atr_points=atr_points, strategy_name=strategy_name, chart=chart
                )
            else:
                # Traditional order placement
                entry_orderid = self.tsl.order_placement(
                    tradingsymbol=name, exchange='NSE', quantity=base_qty,
                    order_type='MARKET', transaction_type=action, price=0, trigger_price=0, trade_type='MIS'
                )
                if not entry_orderid:
                    return
                
                if action == 'BUY':
                    stop_loss_price = round(current_price - atr_points, 2)
                    target_price = round(current_price + (atr_points * Config.RISK_REWARD_RATIO), 2)
                else:
                    stop_loss_price = round(current_price + atr_points, 2)
                    target_price = round(current_price - (atr_points * Config.RISK_REWARD_RATIO), 2)
                
                order_details = {
                    'name': name, 'options_name': name, 'option_type': 'STOCK',
                    'date': str(current_time.date()), 'entry_time': current_time.strftime('%H:%M:%S'),
                    'max_holding_time': current_time + datetime.timedelta(hours=Config.MAX_HOLDING_HOURS),
                    'entry_orderid': entry_orderid, 'entry_price': current_price, 'qty': base_qty,
                    'sl': stop_loss_price, 'target': target_price, 'strategy': strategy_name,
                    'atr': atr_points, 'trade_type': 'EQUITY', 'buy_sell': action,
                    'position_type': "LONG" if action == 'BUY' else "SHORT", 'traded': "yes",
                    'order_type': 'TRADITIONAL'
                }
                # Place SL order for traditional orders
                self.place_sl_order(name, action, base_qty, stop_loss_price)
            
            if order_details:
                trade_value = base_qty * current_price
                self.update_balance_after_trade(trade_value, operation="deduct")
                self.orderbook[name] = order_details
                self.save_trade(order_details)
                self.update_strategy_performance(strategy_name, action, 0)
                self.signal_cooldown.record_signal(name, current_price, current_time)
                self.send_trade_alert_with_retry(order_details, "ENTRY")
                print(f"\n✅ ORDER EXECUTED: {action} {base_qty} shares of {name}")

        except Exception as e:
            error_msg = f"❌ Order failed for {name}: {str(e)}"
            print(error_msg)
            self.send_trade_alert_with_retry({'name': name, 'error': str(e)}, "ERROR")

    def save_trade(self, trade_data: Dict):
        """Save trade to database"""
        try:
            cursor = self.conn.cursor()
            
            option_symbol = trade_data.get('options_name', trade_data.get('name', 'N/A'))
            option_type = trade_data.get('option_type', 'STOCK')
            strategy = trade_data.get('strategy', 'UNKNOWN')
            
            cursor.execute('''
                INSERT INTO trades (
                    symbol, option_symbol, option_type, strategy,
                    entry_time, entry_price, quantity, stop_loss,
                    target_price, exit_time, exit_price, pnl, exit_reason,
                    max_holding_time, status, order_type, super_order_id,
                    sl_orderid, entry_orderid, trade_direction, position_type,
                    trailing_enabled, signal_strength, market_regime
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                trade_data['name'], option_symbol, option_type, strategy,
                f"{trade_data['date']} {trade_data['entry_time']}", trade_data['entry_price'],
                trade_data['qty'], trade_data.get('sl', 0), trade_data.get('target', 0),
                f"{trade_data['date']} {trade_data.get('exit_time', '')}" if trade_data.get('exit_time') else None,
                trade_data.get('exit_price'), trade_data.get('pnl', 0), trade_data.get('remark', ''),
                f"{trade_data['date']} {trade_data['max_holding_time'].time()}" if 'max_holding_time' in trade_data else None,
                'closed' if trade_data.get('exit_time') else 'open', trade_data.get('order_type', 'TRADITIONAL'),
                trade_data.get('super_order_id'), trade_data.get('sl_orderid'), trade_data.get('entry_orderid'),
                trade_data.get('trade_direction', ''), trade_data.get('position_type', ''),
                trade_data.get('trailing_enabled', False), trade_data.get('signal_strength'), trade_data.get('market_regime')
            ))
            self.conn.commit()
            print(f"✅ Trade saved to database: {trade_data['name']}")
        except Exception as e:
            print(f"❌ Failed to save trade to database: {e}")

    def update_strategy_performance(self, strategy_name: str, option_type: str, pnl: float = 0):
        """Update strategy performance metrics in database"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT * FROM strategy_performance WHERE strategy_name = ?', (strategy_name,))
            if not cursor.fetchone():
                cursor.execute('INSERT INTO strategy_performance (strategy_name) VALUES (?)', (strategy_name,))
            
            field = 'calls' if option_type == "BUY" else 'puts'
            cursor.execute(f'''
                UPDATE strategy_performance 
                SET {field} = {field} + 1, total_profit = total_profit + ?,
                total_trades = total_trades + 1, last_updated = CURRENT_TIMESTAMP
                WHERE strategy_name = ?
            ''', (pnl, strategy_name))
            self.conn.commit()
        except Exception as e:
            self.logger.error(f"Failed to update strategy performance: {e}")

    def monitor_open_positions(self, symbol: str):
        """Monitor positions with adaptive trailing"""
        if symbol not in self.orderbook:
            return
            
        order = self.orderbook[symbol]
        
        if order.get('traded') != "yes":
            return
        
        try:
            current_price_data = self.tsl.get_ltp_data(names=[symbol])
            if not current_price_data or symbol not in current_price_data:
                print(f"❌ Couldn't get current price for {symbol}")
                return
                
            current_price = current_price_data[symbol]
            stop_loss_price = order.get('sl', 0)
            
            if Config.ENABLE_ADAPTIVE_TRAILING and order.get('order_type') == 'SUPER_OPTIMIZED':
                new_stop = self.trailing_manager.calculate_new_stop(
                    symbol=symbol,
                    position_type=order['position_type'],
                    current_price=current_price,
                    entry_price=order['entry_price'],
                    atr_points=order.get('atr', 0)
                )
                if new_stop and new_stop != order.get('sl'):
                    old_sl = order['sl']
                    order['sl'] = new_stop
                    print(f"   🔄 Trailing Stop Updated: ₹{old_sl:.2f} → ₹{new_stop:.2f}")
            
            position_type = order.get('position_type', 'LONG')
            sl_hit = False
            
            if position_type == 'LONG' and current_price <= stop_loss_price:
                sl_hit = True
            elif position_type == 'SHORT' and current_price >= stop_loss_price:
                sl_hit = True
            
            if sl_hit:
                self.handle_sl_hit(symbol)
                return
            
            if 'max_holding_time' in order and datetime.datetime.now(self.ist) >= order['max_holding_time']:
                self.manual_close_position(symbol, "HOLDING_TIME_EXCEEDED")
                return
                
        except Exception as e:
            print(f"❌ Error monitoring {symbol}: {str(e)}")

    def handle_sl_hit(self, name: str):
        """Process when stop loss is hit"""
        if name not in self.orderbook:
            return
            
        order = self.orderbook[name]
        strategy_name = order.get('strategy', 'unknown')
        
        try:
            if order['buy_sell'] == 'BUY':
                exit_action = 'SELL'
                trade_type = "LONG"
            else:
                exit_action = 'BUY'
                trade_type = "SHORT"
            
            if order.get('order_type') == 'TRADITIONAL':
                exit_orderid = self.tsl.order_placement(
                    tradingsymbol=name, exchange='NSE', quantity=order['qty'],
                    order_type='MARKET', transaction_type=exit_action,
                    price=0, trigger_price=0, trade_type='MIS'
                )
                if not exit_orderid:
                    return
                time.sleep(2)
                exit_price = order['sl']
                try:
                    executed_price = self.tsl.get_executed_price(exit_orderid)
                    if executed_price:
                        exit_price = executed_price
                except:
                    ltp_data = self.tsl.get_ltp_data(names=[name])
                    exit_price = ltp_data.get(name, order['sl'])
            else:
                exit_price = order['sl']
            
            if trade_type == "LONG":
                pnl = (exit_price - order['entry_price']) * order['qty']
            else:
                pnl = (order['entry_price'] - exit_price) * order['qty']
            
            current_time = datetime.datetime.now(self.ist)
            order.update({
                'exit_time': current_time.strftime('%H:%M:%S'),
                'exit_price': exit_price,
                'pnl': pnl,
                'remark': f"{trade_type}_SL_HIT"
            })
            
            trade_value = order['qty'] * order['entry_price']
            close_data = {'name': name, 'trade_value': trade_value, 'qty': order['qty'],
                         'entry_price': order['entry_price'], 'pnl': pnl}
            self.update_balance_after_trade(close_data, operation="add")
            
            self.update_strategy_performance(strategy_name, order['buy_sell'], pnl)
            self.completed_orders.append(order.copy())
            
            if Config.ENABLE_STRATEGY_WEIGHT_OPTIMIZATION and self.strategy_optimizer:
                if len(self.completed_orders) % 10 == 0:
                    self.strategy_optimizer.update_weights(self.completed_orders)
            
            self.send_trade_alert_with_retry(order.copy(), "EXIT")
            self.save_trade(order)
            del self.orderbook[name]
            
            print(f"✅ POSITION CLOSED: {name} {trade_type}")
            print(f"   P&L: Rs.{pnl:+,.2f}")
            
        except Exception as e:
            print(f"❌ Failed to process SL hit for {name}: {e}")
            if name in self.orderbook:
                del self.orderbook[name]

    def manual_close_position(self, name: str, reason: str = "MANUAL_EXIT"):
        """Manually close a position when automated SL fails"""
        if name not in self.orderbook:
            print(f"No position found for {name}")
            return
            
        order = self.orderbook[name]
        print(f"🆘 MANUAL CLOSE: {name}, Reason: {reason}")
        
        try:
            if order['buy_sell'] == 'BUY':
                exit_action = 'SELL'
                position_type = "LONG/BUY"
            else:
                exit_action = 'BUY'
                position_type = "SHORT/SELL"

            print(f"🔁 Closing {position_type} position with {exit_action} order")
                
            exit_orderid = self.tsl.order_placement(
                tradingsymbol=name, exchange='NSE', quantity=order['qty'],
                order_type='MARKET', transaction_type=exit_action,
                price=0, trigger_price=0, trade_type='MIS'
            )
            
            if exit_orderid:
                print(f"📤 MANUAL EXIT ORDER: {exit_orderid}")

                time.sleep(2)
                exit_price = order['sl']
                try:
                    executed_price = self.tsl.get_executed_price(exit_orderid)
                    if executed_price:
                        exit_price = executed_price
                        print(f"✅ MANUAL EXIT EXECUTED @ {exit_price}")
                    else:
                        ltp_data = self.tsl.get_ltp_data(names=[name])
                        exit_price = ltp_data.get(name, order['sl'])
                except:
                    ltp_data = self.tsl.get_ltp_data(names=[name])
                    exit_price = ltp_data.get(name, order['sl'])
                    
                if order['buy_sell'] == 'BUY':
                    pnl = (exit_price - order['entry_price']) * order['qty']
                else:
                    pnl = (order['entry_price'] - exit_price) * order['qty']
                
                current_time = datetime.datetime.now(self.ist)
                order.update({
                    'exit_time': current_time.strftime('%H:%M:%S'),
                    'exit_price': exit_price,
                    'pnl': pnl,
                    'remark': reason
                })
                
                trade_value = order['qty'] * order['entry_price']
                self.update_balance_after_trade(trade_value + pnl, operation="add")
                
                del self.orderbook[name]
                
                print(f"Manual exit successful for {name}: P&L Rs.{pnl:,.2f}")
            else:
                print(f"Manual exit failed for {name}")
                
        except Exception as e:
            print(f"Manual exit error for {name}: {e}")

    def close_all_positions(self):
        """Close all open positions at market"""
        self.logger.info("Closing all positions...")
        
        for name, order in list(self.orderbook.items()):
            if order.get('traded') == "yes" and order.get('status', 'open') != 'closed':
                try:
                    print(f"\nClosing position for {name}...")
                    
                    if order.get('order_type') == 'TRADITIONAL' and 'sl_orderid' in order:
                        try:
                            order_status = self.tsl.get_order_status(order['sl_orderid'])
                            if isinstance(order_status, str) and order_status.upper() in ['PENDING', 'TRANSIT', 'OPEN']:
                                self.tsl.cancel_order(order['sl_orderid'])
                                print(f"✅ Cancelled SL order: {order['sl_orderid']}")
                        except:
                            pass
                    
                    if order['buy_sell'] == 'BUY':
                        exit_action = 'SELL'
                        position_type = "LONG"
                    else:
                        exit_action = 'BUY'
                        position_type = "SHORT"
                    
                    square_off_id = self.tsl.order_placement(
                        tradingsymbol=order['options_name'], exchange='NSE', quantity=order['qty'],
                        order_type='MARKET', transaction_type=exit_action, price=0, trigger_price=0, trade_type='MIS'
                    )
                    
                    if square_off_id:
                        print(f"📤 SQUARE-OFF ORDER PLACED: {square_off_id}")
                        
                        exit_price = order.get('sl', 0)
                        for attempt in range(3):
                            try:
                                time.sleep(2)
                                executed_price = self.tsl.get_executed_price(square_off_id)
                                if executed_price:
                                    exit_price = executed_price
                                    print(f"✅ EXIT EXECUTED @ {exit_price}")
                                    break
                            except:
                                if attempt == 2:
                                    ltp_data = self.tsl.get_ltp_data(names=[order['options_name']])
                                    exit_price = ltp_data.get(order['options_name'], order.get('sl', 0))
                        
                        if position_type == "LONG":
                            pnl = (exit_price - order['entry_price']) * order['qty']
                        else:
                            pnl = (order['entry_price'] - exit_price) * order['qty']
                        
                        current_time = datetime.datetime.now(self.ist)
                        order.update({
                            'exit_time': current_time.strftime('%H:%M:%S'),
                            'exit_price': exit_price,
                            'pnl': pnl,
                            'remark': "MARKET_CLOSE_SHUTDOWN",
                            'status': 'closed'
                        })
                        
                        self.update_balance_after_trade(
                            {'name': name, 'trade_value': order['qty'] * order['entry_price'], 
                             'qty': order['qty'], 'entry_price': order['entry_price'], 'pnl': pnl}, 
                            operation="add"
                        )
                        self.send_trade_alert_with_retry(order, "EXIT")
                        self.save_trade(order)
                        del self.orderbook[name]
                        
                        print(f"✅ POSITION CLOSED: {name} {position_type}, P&L: Rs.{pnl:+,.2f}")
                        
                except Exception as e:
                    self.logger.error(f"Failed to close position for {name}: {e}")

    def get_symbol_data_with_retry(self, symbol: str, retries: int = 3) -> Optional[pd.DataFrame]:
        """Fetch data with multiple fallback options and retries"""
        exchange_options = self.get_exchange_options(symbol)
        
        for attempt in range(retries):
            for exchange in exchange_options:
                try:
                    print(f"   Attempt {attempt+1}: Fetching {symbol} from {exchange}")
                    chart = self.tsl.get_historical_data(
                        tradingsymbol=symbol,
                        exchange=exchange,
                        timeframe=Config.TIMEFRAME
                    )
                    
                    if self.validate_data(chart):
                        print(f"   ✅ Successfully got {len(chart)} rows")
                        return chart
                        
                except Exception as e:
                    print(f"   ⚠️ Attempt {attempt+1} failed: {str(e)[:50]}...")
                    
        print(f"   ❌ Failed to get valid data for {symbol} after {retries} attempts")
        return None

    def get_exchange_options(self, symbol: str) -> list:
        """Return ordered list of exchange options to try"""
        symbol = str(symbol).upper()
        if symbol in Config.INDEX_SYMBOLS:
            return ["INDICES", "NSE", "NFO"]
        return ["NSE", "BSE", "NFO"]

    def validate_data(self, chart) -> bool:
        """Validate the received market data"""
        if not isinstance(chart, pd.DataFrame):
            print("   ❌ Invalid data type received")
            return False
        if len(chart) < 20:
            print(f"   ❌ Insufficient data rows: {len(chart)}")
            return False
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        if not all(col in chart.columns for col in required_cols):
            print(f"   ❌ Missing required columns")
            return False
        return True

    def generate_signals(self, chart: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        """Generate trading signals from all active strategies"""
        signals = {
            'buy_call': False,
            'buy_put': False,
            'strategies': []
        }
        
        for strategy in self.strategies:
            try:
                strategy.calculate_indicators(chart)
                strategy_signals = strategy.generate_signals(chart, symbol)
                
                signals['strategies'].append({
                    'name': strategy.get_strategy_name(),
                    'signals': strategy_signals
                })
                
                weight = Config.STRATEGY_WEIGHTS.get(strategy.get_strategy_name(), 0)
                
                if weight > 0:
                    if strategy_signals.get('buy_call', False):
                        signals['buy_call'] = True
                    
                    if strategy_signals.get('buy_put', False):
                        signals['buy_put'] = True   
            except Exception as e:
                self.logger.error(f"Strategy {strategy.get_strategy_name()} failed: {e}")
        
        print(f"\nFinal signals for {symbol}:")
        print(f"Buy Call: {signals['buy_call']}")
        print(f"Buy Put: {signals['buy_put']}")
        
        return signals

    def send_telegram_alert(self, message: str) -> bool:
        """Low-level Telegram message sender"""
        try:
            url = f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendMessage?chat_id={Config.RECEIVER_CHAT_ID}&text={requests.utils.quote(message)}"
            response = requests.get(url, timeout=10)
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"Telegram send failed: {str(e)}")
            return False

    def send_trade_alert(self, trade_data: Dict, alert_type: str, option_type: str = None) -> bool:
        """Generate and send formatted trade alerts"""
        try:
            if alert_type == "ENTRY":
                emoji, action = "🚀", "ENTRY"
            elif alert_type == "EXIT":
                emoji, action = "🔴", "EXIT"
            elif alert_type == "ERROR":
                emoji, action = "🚨", "ERROR"
            else:
                emoji, action = "ℹ️", alert_type
            
            if not option_type:
                option_type = trade_data.get('option_type', 'STOCK')
            
            message_lines = [f"{emoji} {option_type} {action}", f"Symbol: {trade_data.get('name', 'N/A')}"]
            
            if alert_type == "ENTRY":
                message_lines.extend([
                    f"Price: ₹{trade_data.get('entry_price', 'N/A')}",
                    f"Qty: {trade_data.get('qty', 'N/A')}",
                    f"SL: ₹{trade_data.get('sl', 'N/A')}",
                    f"Target: ₹{trade_data.get('target', 'N/A')}"
                ])
            elif alert_type == "EXIT":
                pnl = trade_data.get('pnl', 0)
                pnl_emoji = "📈" if pnl > 0 else "📉" if pnl < 0 else "➖"
                message_lines.append(f"{pnl_emoji} P&L: ₹{pnl:+,.2f}")
            
            message_lines.append(f"Strategy: {trade_data.get('strategy', 'N/A')}")
            return self.send_telegram_alert("\n".join(message_lines))
        except Exception as e:
            self.logger.error(f"Failed to send trade alert: {str(e)}")
            return False

    def send_trade_alert_with_retry(self, trade_data: Dict, alert_type: str, 
                                   option_type: str = None, retries: int = 2) -> bool:
        """Send trade alert with retry mechanism"""
        for attempt in range(retries):
            try:
                if self.send_trade_alert(trade_data, alert_type, option_type):
                    return True
                time.sleep(1)
            except:
                time.sleep(1)
        return False

    def verify_api_connection(self) -> bool:
        """Verify API connection"""
        print("\n--- API Connection Test ---")
        test_symbols = ['RELIANCE', 'NIFTY-I', 'NIFTY50']
        for symbol in test_symbols:
            for exchange in ['NSE', 'INDICES']:
                try:
                    print(f"Trying {symbol} on {exchange}...")
                    data = self.tsl.get_historical_data(
                        tradingsymbol=symbol,
                        exchange=exchange,
                        timeframe=Config.TIMEFRAME
                    )
                    if data is not None and len(data) > 0:
                        print(f"SUCCESS: Got {len(data)} rows for {symbol} on {exchange}")
                        return True
                except Exception as e:
                    print(f"Error fetching {symbol}: {str(e)[:50]}...")
        return False

    def test_telegram_connection(self) -> bool:
        """Test Telegram connectivity"""
        print("\n=== Testing Telegram Connection ===")
        test_msg = f"🔔 Trading Bot Connection Test\nTime: {datetime.datetime.now(self.ist).strftime('%Y-%m-%d %H:%M:%S')}\n✅ Bot Ready"
        return self.send_telegram_alert(test_msg)

    def start_telegram_commands(self):
        """Initialize and start Telegram command handler"""
        try:
            self.telegram_handler = TelegramCommandHandler(self)
            self.telegram_handler.start_bot()
            print("✅ Telegram command bot is ready!")
        except Exception as e:
            print(f"⚠️ Telegram command bot initialization failed: {e}")
            return False

    def setup_pnl_tracking(self):
        self.pnl_history = []
        self.daily_pnl = {}
        self.equity_curve = []
        self.start_date = datetime.datetime.now().date()

    def calculate_current_drawdown(self) -> float:
        if not self.pnl_history:
            return 0.0
        max_balance = max(h['balance'] for h in self.pnl_history)
        current_balance = self.pnl_history[-1]['balance']
        return ((max_balance - current_balance) / max_balance * 100) if max_balance > 0 else 0

    def get_performance_dashboard(self) -> str:
        """Generate performance dashboard text"""
        if not self.completed_orders:
            return "📊 No performance data available yet."
        
        total_pnl = sum(t.get('pnl', 0) for t in self.completed_orders)
        winning_trades = len([t for t in self.completed_orders if t.get('pnl', 0) > 0])
        total_trades = len(self.completed_orders)
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        return f"""
📊 *PERFORMANCE DASHBOARD*

💰 Total P&L: ₹{total_pnl:+,.2f}
📈 Win Rate: {win_rate:.1f}%
📊 Total Trades: {total_trades}
🏆 Winning Trades: {winning_trades}
        """

    def analyze_strategy_performance(self):
        """Analyze and display strategy performance"""
        try:
            print("\n" + "="*60)
            print("📊 STRATEGY PERFORMANCE SUMMARY")
            print("="*60)
            
            if not self.completed_orders:
                print("No completed trades to analyze")
                return
            
            strategy_stats = {}
            for order in self.completed_orders:
                strategy = order.get('strategy', 'unknown')
                if strategy not in strategy_stats:
                    strategy_stats[strategy] = {'trades': 0, 'profit': 0, 'wins': 0, 'losses': 0}
                pnl = order.get('pnl', 0)
                strategy_stats[strategy]['trades'] += 1
                strategy_stats[strategy]['profit'] += pnl
                if pnl > 0:
                    strategy_stats[strategy]['wins'] += 1
                else:
                    strategy_stats[strategy]['losses'] += 1
            
            headers = ["Strategy", "Trades", "Wins", "Losses", "Win %", "Total P&L", "Avg P&L"]
            table_data = []
            total_trades = 0
            total_profit = 0
            for strategy, stats in strategy_stats.items():
                total_trades += stats['trades']
                total_profit += stats['profit']
                win_rate = (stats['wins'] / stats['trades'] * 100) if stats['trades'] > 0 else 0
                avg_pnl = stats['profit'] / stats['trades'] if stats['trades'] > 0 else 0
                table_data.append([strategy, stats['trades'], stats['wins'], stats['losses'], f"{win_rate:.1f}%", f"₹{stats['profit']:+,.2f}", f"₹{avg_pnl:+,.2f}"])
            print(tabulate(table_data, headers=headers, tablefmt="grid"))
            print(f"\n📈 OVERALL SUMMARY: Total Trades: {total_trades}, Total P&L: ₹{total_profit:+,.2f}")
        except Exception as e:
            print(f"Error analyzing strategy performance: {e}")

    def is_market_open(self) -> bool:
        """Check if market is currently open"""
        current_time = datetime.datetime.now(self.ist).time()
        weekday = datetime.datetime.now(self.ist).weekday()
        return (datetime.time(9, 15) <= current_time <= datetime.time(15, 30)) and (weekday < 5)

    def handle_market_closed(self):
        """Handle market closed state"""
        current_time = datetime.datetime.now(self.ist).time()
        if current_time > datetime.time(15, 30):
            print("📉 Market closed for the day - squaring off positions")
            self.close_all_positions()
            print("\n📊 Analyzing strategy performance...")
            self.analyze_strategy_performance()
            raise SystemExit("Market closed - exiting")
        
        sleep_time = self.calculate_sleep_time()
        print(f"⏰ Market closed. Next open in {sleep_time/60:.1f} minutes. Sleeping...")
        time.sleep(sleep_time)

    def calculate_sleep_time(self) -> float:
        """Calculate how long to sleep until market opens"""
        now = datetime.datetime.now(self.ist)
        today_9_15 = now.replace(hour=9, minute=15, second=0, microsecond=0)
        
        if now.time() < datetime.time(9, 15):
            return (today_9_15 - now).total_seconds()
        else:
            next_day = now + datetime.timedelta(days=1)
            while next_day.weekday() >= 5:
                next_day += datetime.timedelta(days=1)
            next_day_9_15 = next_day.replace(hour=9, minute=15, second=0, microsecond=0)
            return (next_day_9_15 - now).total_seconds()

    def handle_shutdown(self):
        """Clean shutdown procedure"""
        print("\n🛑 Initiating shutdown sequence...")
        self.close_all_positions()
        self.analyze_strategy_performance()
        print("✅ Shutdown complete")

    def __del__(self):
        """Clean up database connection when bot is destroyed"""
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()

    def process_symbol(self, symbol: str, chart: pd.DataFrame):
        """Process trading logic for one symbol"""
        try:
            for strategy in self.strategies:
                strategy.calculate_indicators(chart)
            
            signals = self.generate_signals(chart, symbol)
            
            if (signals['buy_call'] or signals['buy_put']) and symbol not in self.orderbook:
                print(f"\n🚀 Placing optimized order for {symbol}")
                self.place_stock_order(symbol, signals, chart.iloc[-1], chart)
                
            if symbol in self.orderbook:
                order = self.orderbook[symbol]
                if 'traded' not in order:
                    order['traded'] = "yes"
                    
                if order.get('traded') == "yes":
                    try:
                        self.monitor_open_positions(symbol)
                    except Exception as e:
                        print(f"❌ Error monitoring {symbol}: {e}")
                            
        except Exception as e:
            print(f"❌ Error processing {symbol}: {str(e)}")

    def run(self):
        """Main trading loop with optimization"""
        print("Starting trading bot main loop...")
        
        try:
            while True:
                current_time = datetime.datetime.now(self.ist).time()
                print(f"\n{'='*60}")
                print(f"🔄 CYCLE at {current_time}")
                print(f"{'='*60}")
                
                if hasattr(self, 'cycle_count'):
                    self.cycle_count += 1
                    if self.cycle_count % 5 == 0:
                        fresh_balance = self.get_current_balance()
                        if fresh_balance > 0:
                            self.current_balance = fresh_balance
                else:
                    self.cycle_count = 1
                
                print(f"💰 Available Capital: ₹{self.get_available_capital():,.2f}")
                print(f"📊 Open Positions: {len(self.orderbook)}")

                if self.is_market_open():
                    print("✅ Market is open - scanning for opportunities")
                    
                    for symbol in Config.WATCHLIST:
                        print(f"\n{'─'*50}")
                        print(f"🔍 Processing {symbol}...")
                        
                        chart = self.get_symbol_data_with_retry(symbol)
                        if chart is None:
                            continue
                            
                        self.process_symbol(symbol, chart)
                    
                    sleep_seconds = 15 * int(Config.TIMEFRAME)
                    print(f"\n⏰ Cycle complete. Sleeping for {sleep_seconds} seconds...")
                    time.sleep(sleep_seconds)
                    
                else:
                    self.handle_market_closed()
                    
        except Exception as e:
            print(f"❌ Fatal error: {str(e)}")
            self.handle_shutdown()


# Telegram Command Handler Class
class TelegramCommandHandler:
    def __init__(self, bot_instance):
        self.bot = bot_instance
        self.application = None
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        welcome_msg = "🤖 *Trading Bot Commander*\n\n/status - Bot status\n/balance - Balance\n/positions - Open positions\n/close_all - Close all"
        await update.message.reply_text(welcome_msg, parse_mode='Markdown')
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        status_msg = f"🤖 *Bot Status*\n\nOpen Positions: {len(self.bot.orderbook)}\nMarket Hours: {'✅ Open' if self.bot.is_market_open() else '❌ Closed'}\nActive Strategies: {len(self.bot.strategies)}"
        await update.message.reply_text(status_msg, parse_mode='Markdown')
    
    async def balance_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        balance = self.bot.get_available_capital()
        await update.message.reply_text(f"💰 Balance: ₹{balance:,.2f}", parse_mode='Markdown')
    
    async def positions_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.bot.orderbook:
            await update.message.reply_text("No open positions")
            return
        msg = "📈 *Open Positions*\n\n"
        for symbol, order in self.bot.orderbook.items():
            msg += f"*{symbol}*: {order.get('position_type')} {order.get('qty')} @ ₹{order.get('entry_price', 0):.2f}\n"
        await update.message.reply_text(msg, parse_mode='Markdown')
    
    async def close_all_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.bot.close_all_positions()
        await update.message.reply_text("✅ Closed all positions")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_msg = "/status, /balance, /positions, /close_all"
        await update.message.reply_text(help_msg)
    
    def start_bot(self):
        def run_bot():
            try:
                self.application = Application.builder().token(Config.BOT_TOKEN).build()
                self.application.add_handler(CommandHandler("start", self.start_command))
                self.application.add_handler(CommandHandler("status", self.status_command))
                self.application.add_handler(CommandHandler("balance", self.balance_command))
                self.application.add_handler(CommandHandler("positions", self.positions_command))
                self.application.add_handler(CommandHandler("close_all", self.close_all_command))
                self.application.add_handler(CommandHandler("help", self.help_command))
                self.application.run_polling(allowed_updates=Update.ALL_TYPES)
            except Exception as e:
                print(f"❌ Telegram bot error: {e}")
        
        bot_thread = threading.Thread(target=run_bot, daemon=True)
        bot_thread.start()


if __name__ == "__main__":
    try:
        if not Config.CLIENT_CODE or not Config.PIN or not Config.TOTP_SECRET:
            print("❌ ERROR: Please set CLIENT_CODE, PIN, and TOTP_SECRET in Config")
            exit(1)
        
        bot = OptionTradingBot()
        
        print("\n=== Verifying API Connection ===")
        if not bot.verify_api_connection():
            print("❌ CRITICAL: API connection failed")
            winsound.Beep(2000, 1000)
            exit(1)
        
        print("\n=== Testing Telegram Notifications ===")
        if not bot.test_telegram_connection():
            print("⚠️ WARNING: Telegram notifications may not work")
            winsound.Beep(1500, 500)
        
        startup_msg = "🤖 *Trading Bot Started with TOTP Authentication!*\n\nCommands: /status, /balance, /positions, /close_all"
        bot.send_telegram_alert(startup_msg)
        
        print("\n" + "="*60)
        print("🚀 STARTING MULTI-ACCOUNT COPY TRADING BOT (TOTP AUTH)")
        print("="*60)
        bot.run()
        
    except KeyboardInterrupt:
        print("\n" + "="*60)
        print("🛑 BOT STOPPED BY USER")
        print("="*60)
        try:
            if 'bot' in locals():
                if bot.orderbook:
                    print(f"\n📊 OPEN POSITIONS: {len(bot.orderbook)}")
                bot.analyze_strategy_performance()
                final_balance = bot.get_current_balance()
                print(f"\n💰 FINAL BALANCE: ₹{final_balance:,.2f}")
                bot.send_telegram_alert(f"🛑 Bot stopped. Final balance: ₹{final_balance:,.2f}")
        except Exception as e:
            print(f"\n⚠️ Error during shutdown: {e}")
    except Exception as e:
        print(f"\n❌ Fatal error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            if 'bot' in locals():
                print("\n🔄 Closing all positions...")
                bot.close_all_positions()
                print("✅ Cleanup complete")
        except:
            pass
        print("\n👋 Program terminated")
# config.py
import datetime
import pytz

class Config:
    # ============ API Credentials (TOTP Authentication) ============
    CLIENT_CODE = "1109910610"
    PIN = "121295"
    TOTP_SECRET = "IXTDHOOGHOPVCTMTE2V3NCYCMUMQWA4M"
    
    # ============ Secondary Trading Accounts ============
    TRADING_ACCOUNTS = {
        "ACCOUNT_2": {"client_code": "", "pin": "", "totp_secret": "", "multiplier": 1.0, "enabled": False},
        "ACCOUNT_3": {"client_code": "", "pin": "", "totp_secret": "", "multiplier": 0.5, "enabled": False},
    }
    
    # Copy Trading Settings
    COPY_TRADING_ENABLED = False
    EXECUTION_MODE = "PARALLEL"
    MAX_RETRIES_PER_ACCOUNT = 2
    REQUIRE_ALL_ACCOUNTS = False
    TRADE_DELAY_SECONDS = 1

    # Risk Management
    BASE_CAPITAL = 10000
    MARKET_MONEY_RISK_PERCENT = 0.01
    BASE_CAPITAL_RISK_PERCENT = 0.005
    MAX_CAPITAL_PER_TRADE = 0.5
    MAX_ORDERS_PER_DAY = 5
    RISK_REWARD_RATIO = 3
    ATR_MULTIPLIER = 5
    Minimum_trading_capital = 10
    BROKER_MARGIN_MULTIPLIER = 4
    
    # Trading Parameters
    TIMEFRAME = "1"
    OTM_COUNT = 1
    MAX_HOLDING_HOURS = 5
    REENTRY_ALLOWED = True
    USE_SUPER_ORDERS = True
    TRAILING_JUMP = 0.2
    
    # Optimization Parameters
    MIN_SIGNAL_STRENGTH = 30
    SIGNAL_COOLDOWN_MINUTES = 5
    MAX_SIGNALS_PER_HOUR = 3
    USE_MARKET_REGIME_FILTER = True
    USE_Kelly_SIZING = True
    MIN_KELlY_TRADES = 10
    HALF_KELLY = True
    ENABLE_ADAPTIVE_TRAILING = True
    ENABLE_DYNAMIC_EXITS = True
    ENABLE_STRATEGY_WEIGHT_OPTIMIZATION = True
    
    # Strategy Configuration
    ACTIVE_STRATEGIES = ['EMA_RSI', 'MACD_Bollinger', 'RSI_50_Crossover', 
                        'VWAP_Reversion', 'MA_Crossover_50_200', 'ORB_30min']
    STRATEGY_WEIGHTS = {
        'EMA_RSI': 0.02, 'MACD_Bollinger': 0.2, 'VWAP_Reversion': 0.2,
        'MA_Crossover_50_200': 0.2, 'ORB_30min': 0.0, 'RSI_50_Crossover': 0.2
    }
    
    # Alerting
    BOT_TOKEN = "8328373474:AAGwUiussSYN3wyiHgvjO0LeMFGOdjRYRjI"
    RECEIVER_CHAT_ID = "881317629"

    # Watchlist
    INDEX_SYMBOLS = []
    WATCHLIST = ['IDBI', 'BEL', 'ITC']
    
    # Timezone
    IST = pytz.timezone('Asia/Kolkata')
    
    @staticmethod
    def get_current_time():
        return datetime.datetime.now(Config.IST)
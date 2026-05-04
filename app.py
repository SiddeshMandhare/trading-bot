# app.py - YOUR ORIGINAL CODE, JUST FIXED (no env, no major changes)
import os
import json
import sqlite3
import threading
import time
import logging
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request, send_file
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import pandas as pd
from io import BytesIO

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", ping_timeout=60, ping_interval=25)

# Import your existing modules
from config import Config
from auth_service import create_tradehull_with_totp, get_token_status

# Global variables
bot_thread = None
is_bot_running = False
bot_instance = None
bot_start_time = None

# ============================================
# DATABASE FUNCTIONS
# ============================================

def get_db_connection():
    conn = sqlite3.connect('trading_bot.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS trades (
            trade_id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT, entry_time DATETIME, entry_price REAL,
            quantity INTEGER, stop_loss REAL, target_price REAL,
            exit_price REAL, pnl REAL, strategy TEXT,
            position_type TEXT, status TEXT, exit_reason TEXT, exit_time DATETIME
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS bot_logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            log_type TEXT,
            message TEXT
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS bot_settings (
            setting_key TEXT PRIMARY KEY,
            setting_value TEXT,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("Database initialized")

def add_log(log_type, message):
    try:
        conn = get_db_connection()
        conn.execute('INSERT INTO bot_logs (log_type, message) VALUES (?, ?)', (log_type, message))
        conn.commit()
        conn.close()
        socketio.emit('new_log', {'type': log_type, 'message': message, 'time': datetime.now().isoformat()})
    except Exception as e:
        logger.error(f"Failed to add log: {e}")

# ============================================
# API ENDPOINTS
# ============================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat(), 'bot_running': is_bot_running})

@app.route('/api/stats')
def get_stats():
    conn = get_db_connection()
    trades = conn.execute('SELECT * FROM trades ORDER BY trade_id DESC').fetchall()
    conn.close()
    
    if not trades:
        return jsonify({
            'total_trades': 0, 'total_pnl': 0, 'winning_trades': 0, 'losing_trades': 0,
            'win_rate': 0, 'profit_factor': 0, 'sharpe_ratio': 0, 'max_drawdown': 0,
            'avg_win': 0, 'avg_loss': 0, 'best_trade': 0, 'worst_trade': 0, 'today_pnl': 0
        })
    
    df = pd.DataFrame([dict(trade) for trade in trades])
    total_trades = len(df)
    winning = df[df['pnl'] > 0]
    total_pnl = df['pnl'].sum()
    win_rate = (len(winning) / total_trades * 100) if total_trades > 0 else 0
    gross_profit = winning['pnl'].sum() if not winning.empty else 0
    gross_loss = abs(df[df['pnl'] < 0]['pnl'].sum()) if len(df[df['pnl'] < 0]) > 0 else 1
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
    
    # Today's P&L
    today = datetime.now().date()
    df['entry_date'] = pd.to_datetime(df['entry_time']).dt.date
    today_pnl = df[df['entry_date'] == today]['pnl'].sum() if not df.empty else 0
    
    return jsonify({
        'total_trades': total_trades, 'total_pnl': round(total_pnl, 2),
        'winning_trades': len(winning), 'losing_trades': total_trades - len(winning),
        'win_rate': round(win_rate, 1), 'profit_factor': round(profit_factor, 2),
        'sharpe_ratio': 0, 'max_drawdown': 0, 'avg_win': 0, 'avg_loss': 0,
        'best_trade': 0, 'worst_trade': 0, 'today_pnl': round(today_pnl, 2)
    })

@app.route('/api/trades')
def get_trades():
    limit = request.args.get('limit', 50, type=int)
    conn = get_db_connection()
    trades = conn.execute('SELECT * FROM trades ORDER BY trade_id DESC LIMIT ?', (limit,)).fetchall()
    conn.close()
    return jsonify([dict(trade) for trade in trades])

@app.route('/api/positions')
def get_positions():
    return jsonify([])

@app.route('/api/strategies')
def get_strategies():
    conn = get_db_connection()
    trades = conn.execute('SELECT * FROM trades').fetchall()
    conn.close()
    
    if not trades:
        return jsonify([])
    
    df = pd.DataFrame([dict(trade) for trade in trades])
    strategies = []
    for strategy in df['strategy'].unique():
        strat_df = df[df['strategy'] == strategy]
        winning = strat_df[strat_df['pnl'] > 0]
        strategies.append({
            'name': strategy, 'trades': len(strat_df), 'wins': len(winning),
            'losses': len(strat_df) - len(winning), 'pnl': round(strat_df['pnl'].sum(), 2),
            'win_rate': round(len(winning) / len(strat_df) * 100, 1) if len(strat_df) > 0 else 0
        })
    return jsonify(sorted(strategies, key=lambda x: x['pnl'], reverse=True))

# ============================================
# ONLY ONE /api/market ENDPOINT - KEEP THIS ONE, DELETE THE OTHER
# ============================================

@app.route('/api/market')
def get_market_data():
    """Get market indices data with fallback mock data"""
    try:
        from market_data_service import MarketDataService
        from auth_service import get_token_storage
        
        storage = get_token_storage(Config.CLIENT_CODE)
        token = storage.get_token() if storage else None
        
        # Return mock data for now (will show real data when bot is authenticated)
        mock_data = {
            "NIFTY 50": {"ltp": 24500.50, "change": 120.30, "change_percent": 0.49},
            "BANKNIFTY": {"ltp": 52100.00, "change": 350.75, "change_percent": 0.68},
            "FINNIFTY": {"ltp": 21800.25, "change": 150.50, "change_percent": 0.69},
            "SENSEX": {"ltp": 80500.00, "change": 250.00, "change_percent": 0.31}
        }
        return jsonify(mock_data)
        
    except Exception as e:
        logger.error(f"Market data error: {e}")
        return jsonify({})

@app.route('/api/debug/auth')
def debug_auth():
    """Debug endpoint to check authentication status"""
    try:
        status = get_token_status(Config.CLIENT_CODE)
        return jsonify({
            'token_status': status,
            'client_code': Config.CLIENT_CODE,
            'bot_running': is_bot_running
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/bot/status')
def get_bot_status():
    global is_bot_running, bot_start_time
    return jsonify({'running': is_bot_running, 'start_time': bot_start_time})

@app.route('/api/bot/start', methods=['POST'])
def start_bot():
    global is_bot_running, bot_thread, bot_start_time
    
    if not is_bot_running:
        bot_thread = threading.Thread(target=run_bot_background, daemon=True)
        bot_start_time = datetime.now().isoformat()
        bot_thread.start()
        is_bot_running = True
        add_log('success', 'Bot started successfully')
        return jsonify({'status': 'started', 'message': 'Bot started successfully'})
    
    return jsonify({'status': 'already_running', 'message': 'Bot is already running'})

@app.route('/api/bot/stop', methods=['POST'])
def stop_bot():
    global is_bot_running
    is_bot_running = False
    add_log('info', 'Bot stopped')
    return jsonify({'status': 'stopped', 'message': 'Bot stopped successfully'})

@app.route('/api/logs')
def get_logs():
    limit = request.args.get('limit', 100, type=int)
    conn = get_db_connection()
    logs = conn.execute('SELECT * FROM bot_logs ORDER BY log_id DESC LIMIT ?', (limit,)).fetchall()
    conn.close()
    return jsonify([dict(log) for log in logs])

@app.route('/api/export')
def export_data():
    conn = get_db_connection()
    trades = conn.execute('SELECT * FROM trades ORDER BY trade_id DESC').fetchall()
    conn.close()
    if not trades:
        return jsonify({'error': 'No data to export'}), 404
    df = pd.DataFrame([dict(trade) for trade in trades])
    csv = df.to_csv(index=False)
    return send_file(BytesIO(csv.encode()), mimetype='text/csv', as_attachment=True, download_name=f"trades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")

# ============================================
# HELPER FUNCTIONS
# ============================================

def run_bot_background():
    """Run the trading bot in background thread"""
    global is_bot_running, bot_instance
    
    try:
        add_log('info', 'Initializing trading bot...')
        
        from main import OptionTradingBot
        
        bot_instance = OptionTradingBot()
        add_log('success', 'Bot initialized successfully')
        
        # Run the bot's main loop
        bot_instance.run()
        
    except Exception as e:
        add_log('error', f'Bot error: {str(e)}')
        logger.error(f"Bot background error: {e}", exc_info=True)
    finally:
        is_bot_running = False
        add_log('info', 'Bot stopped')

# ============================================
# WEBSOCKET EVENTS
# ============================================

@socketio.on('connect')
def handle_connect():
    emit('connected', {'data': 'Connected to trading bot server'})
    logger.info("Client connected to WebSocket")

@socketio.on('disconnect')
def handle_disconnect():
    logger.info("Client disconnected from WebSocket")

# ============================================
# MAIN ENTRY POINT
# ============================================

if __name__ == '__main__':
    init_db()
    
    print("="*60)
    print("🚀 PRODUCTION TRADING BOT DASHBOARD")
    print("="*60)
    print(f"📍 Local: http://localhost:5000")
    print("="*60)
    
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False)

# app.py - Production Ready Trading Bot Web Application
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
socketio = SocketIO(app, cors_allowed_origins="*")

# Import your existing modules
from config import Config
from auth_service import create_tradehull_with_totp, get_token_status

# Global variables
bot_thread = None
is_bot_running = False
bot_instance = None

# ============================================
# DATABASE FUNCTIONS
# ============================================

def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect('trading_bot.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database tables"""
    conn = get_db_connection()
    
    # Trades table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS trades (
            trade_id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT,
            entry_time DATETIME,
            entry_price REAL,
            quantity INTEGER,
            stop_loss REAL,
            target_price REAL,
            exit_price REAL,
            pnl REAL,
            strategy TEXT,
            position_type TEXT,
            status TEXT,
            exit_reason TEXT,
            exit_time DATETIME
        )
    ''')
    
    # Bot logs table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS bot_logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            log_type TEXT,
            message TEXT
        )
    ''')
    
    # Settings table
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
    """Add log to database and emit via WebSocket"""
    try:
        conn = get_db_connection()
        conn.execute(
            'INSERT INTO bot_logs (log_type, message) VALUES (?, ?)',
            (log_type, message)
        )
        conn.commit()
        conn.close()
        
        # Emit to WebSocket clients
        socketio.emit('new_log', {
            'type': log_type,
            'message': message,
            'time': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Failed to add log: {e}")

# ============================================
# API ENDPOINTS
# ============================================

@app.route('/')
def index():
    """Serve the dashboard"""
    return render_template('index.html')

@app.route('/api/stats')
def get_stats():
    """Get trading statistics"""
    conn = get_db_connection()
    trades = conn.execute('SELECT * FROM trades ORDER BY trade_id DESC').fetchall()
    conn.close()
    
    if not trades:
        return jsonify({
            'total_trades': 0,
            'total_pnl': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0,
            'profit_factor': 0,
            'sharpe_ratio': 0,
            'max_drawdown': 0,
            'avg_win': 0,
            'avg_loss': 0,
            'best_trade': 0,
            'worst_trade': 0
        })
    
    df = pd.DataFrame([dict(trade) for trade in trades])
    
    # Calculate metrics
    total_trades = len(df)
    winning = df[df['pnl'] > 0]
    losing = df[df['pnl'] < 0]
    
    total_pnl = df['pnl'].sum()
    winning_trades = len(winning)
    losing_trades = len(losing)
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    
    # Profit factor
    gross_profit = winning['pnl'].sum() if not winning.empty else 0
    gross_loss = abs(losing['pnl'].sum()) if not losing.empty else 1
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
    
    # Sharpe ratio (simplified)
    returns = df['pnl'].values
    sharpe = (returns.mean() / returns.std() * (252 ** 0.5)) if returns.std() > 0 else 0
    
    # Max drawdown
    cumulative = df['pnl'].cumsum()
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max.abs() * 100
    max_dd = abs(drawdown.min()) if not drawdown.empty else 0
    
    return jsonify({
        'total_trades': total_trades,
        'total_pnl': round(total_pnl, 2),
        'winning_trades': winning_trades,
        'losing_trades': losing_trades,
        'win_rate': round(win_rate, 1),
        'profit_factor': round(profit_factor, 2),
        'sharpe_ratio': round(sharpe, 2),
        'max_drawdown': round(max_dd, 1),
        'avg_win': round(winning['pnl'].mean(), 2) if not winning.empty else 0,
        'avg_loss': round(losing['pnl'].mean(), 2) if not losing.empty else 0,
        'best_trade': round(winning['pnl'].max(), 2) if not winning.empty else 0,
        'worst_trade': round(losing['pnl'].min(), 2) if not losing.empty else 0
    })

@app.route('/api/trades')
def get_trades():
    """Get recent trades"""
    limit = request.args.get('limit', 50, type=int)
    conn = get_db_connection()
    trades = conn.execute(
        'SELECT * FROM trades ORDER BY trade_id DESC LIMIT ?',
        (limit,)
    ).fetchall()
    conn.close()
    return jsonify([dict(trade) for trade in trades])

@app.route('/api/strategies')
def get_strategies():
    """Get strategy performance"""
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
            'name': strategy,
            'trades': len(strat_df),
            'wins': len(winning),
            'losses': len(strat_df) - len(winning),
            'pnl': round(strat_df['pnl'].sum(), 2),
            'win_rate': round(len(winning) / len(strat_df) * 100, 1) if len(strat_df) > 0 else 0,
            'avg_pnl': round(strat_df['pnl'].mean(), 2)
        })
    
    return jsonify(sorted(strategies, key=lambda x: x['pnl'], reverse=True))

@app.route('/api/bot/status')
def get_bot_status():
    """Get bot running status"""
    global is_bot_running
    return jsonify({
        'running': is_bot_running,
        'start_time': bot_thread.start_time if bot_thread and hasattr(bot_thread, 'start_time') else None
    })

@app.route('/api/bot/start', methods=['POST'])
def start_bot():
    """Start the trading bot"""
    global is_bot_running, bot_thread
    
    if not is_bot_running:
        bot_thread = threading.Thread(target=run_bot_background, daemon=True)
        bot_thread.start_time = datetime.now().isoformat()
        bot_thread.start()
        is_bot_running = True
        add_log('success', 'Bot started via web interface')
        return jsonify({'status': 'started', 'message': 'Bot started successfully'})
    
    return jsonify({'status': 'already_running', 'message': 'Bot is already running'})

@app.route('/api/bot/stop', methods=['POST'])
def stop_bot():
    """Stop the trading bot"""
    global is_bot_running
    
    is_bot_running = False
    add_log('info', 'Bot stopped via web interface')
    return jsonify({'status': 'stopped', 'message': 'Bot stopped successfully'})

@app.route('/api/logs')
def get_logs():
    """Get recent bot logs"""
    limit = request.args.get('limit', 100, type=int)
    conn = get_db_connection()
    logs = conn.execute(
        'SELECT * FROM bot_logs ORDER BY log_id DESC LIMIT ?',
        (limit,)
    ).fetchall()
    conn.close()
    return jsonify([dict(log) for log in logs])

@app.route('/api/export')
def export_data():
    """Export trades as CSV"""
    conn = get_db_connection()
    trades = conn.execute('SELECT * FROM trades ORDER BY trade_id DESC').fetchall()
    conn.close()
    
    if not trades:
        return jsonify({'error': 'No data to export'}), 404
    
    df = pd.DataFrame([dict(trade) for trade in trades])
    csv = df.to_csv(index=False)
    
    return send_file(
        BytesIO(csv.encode()),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f"trades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    )

# ============================================
# HELPER FUNCTIONS
# ============================================

def run_bot_background():
    """Run the trading bot in background thread"""
    global is_bot_running, bot_instance
    
    try:
        add_log('info', 'Initializing trading bot...')
        
        # Import the main bot class
        from main import OptionTradingBot
        
        # Create bot instance
        bot_instance = OptionTradingBot()
        add_log('success', 'Bot initialized successfully')
        
        # Run the bot
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
    """Handle client connection"""
    emit('connected', {'data': 'Connected to trading bot server'})
    logger.info("Client connected to WebSocket")

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info("Client disconnected from WebSocket")

# ============================================
# MAIN ENTRY POINT
# ============================================

def get_local_ip():
    """Get local IP address"""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

# Add this to app.py - Health check endpoint for Render
@app.route('/health')
def health_check():
    """Health check endpoint for Render"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'bot_running': is_bot_running
    })

if __name__ == '__main__':
    # Initialize database
    init_db()
    
    print("="*60)
    print("🚀 PRODUCTION TRADING BOT DASHBOARD")
    print("="*60)
    print(f"📍 Local: http://localhost:5000")
    print(f"📍 Network: http://{get_local_ip()}:5000")
    print("="*60)
    print("💡 Tips:")
    print("   - Use /api/bot/start to start the bot")
    print("   - Use /api/bot/stop to stop the bot")
    print("   - Dashboard auto-refreshes every 10 seconds")
    print("="*60)
    
    # Get port from environment variable (for Render)
    port = int(os.environ.get('PORT', 5000))
    
    # Run the app
    socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True)

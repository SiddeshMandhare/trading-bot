# app.py - COMPLETE REPLACEMENT FILE
import os
import threading
import logging
from datetime import datetime
from flask import Flask, render_template, jsonify, request, send_file
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import pandas as pd
from io import BytesIO

from unified_data_service import data_service
from config import Config
from auth_service import create_tradehull_with_totp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key')
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Global variables
bot_thread = None
is_bot_running = False
bot_instance = None

# ============================================
# MAIN ROUTES
# ============================================

@app.route('/')
def index():
    """Main dashboard"""
    return render_template('index.html')

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'bot_running': is_bot_running
    })

# ============================================
# UNIFIED API ENDPOINTS - ALL DATA FROM ONE SOURCE
# ============================================

@app.route('/api/all-data')
def get_all_data():
    """Get ALL data in one request - Most efficient!"""
    return jsonify(data_service.get_all_data())

@app.route('/api/market')
def get_market_data():
    """Get market data only"""
    return jsonify(data_service.get_market_data())

@app.route('/api/stats')
def get_stats():
    """Get statistics only"""
    return jsonify(data_service.get_stats())

@app.route('/api/trades')
def get_trades():
    """Get recent trades"""
    limit = request.args.get('limit', 50, type=int)
    return jsonify(data_service.get_trades(limit))

@app.route('/api/strategies')
def get_strategies():
    """Get strategy performance"""
    return jsonify(data_service.data_cache.get('strategies', []))

@app.route('/api/positions')
def get_positions():
    """Get open positions"""
    return jsonify(data_service.data_cache.get('positions', []))

@app.route('/api/bot/status')
def get_bot_status():
    """Get bot status"""
    return jsonify({
        'running': is_bot_running,
        'start_time': bot_instance.start_time if bot_instance else None
    })

@app.route('/api/bot/start', methods=['POST'])
def start_bot():
    global is_bot_running, bot_thread, bot_instance
    
    if not is_bot_running:
        from main import OptionTradingBot
        
        def run_bot():
            global is_bot_running, bot_instance
            try:
                bot_instance = OptionTradingBot()
                data_service.set_bot_instance(bot_instance)
                bot_instance.run()
            except Exception as e:
                logger.error(f"Bot error: {e}")
            finally:
                is_bot_running = False
        
        bot_thread = threading.Thread(target=run_bot, daemon=True)
        bot_thread.start()
        is_bot_running = True
        
        return jsonify({'status': 'started', 'message': 'Bot started'})
    
    return jsonify({'status': 'already_running', 'message': 'Bot is already running'})

@app.route('/api/bot/stop', methods=['POST'])
def stop_bot():
    global is_bot_running
    is_bot_running = False
    return jsonify({'status': 'stopped', 'message': 'Bot stopped'})

@app.route('/api/export')
def export_data():
    """Export trades to CSV"""
    trades = data_service.get_trades(limit=1000)
    if not trades:
        return jsonify({'error': 'No data to export'}), 404
    
    df = pd.DataFrame(trades)
    csv = df.to_csv(index=False)
    return send_file(
        BytesIO(csv.encode()),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f"trades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    )

# ============================================
# WEBSOCKET FOR REAL-TIME UPDATES
# ============================================

@socketio.on('connect')
def handle_connect():
    """Send initial data on connect"""
    emit('connected', {'data': 'Connected'})
    emit('data_update', data_service.get_all_data())
    logger.info("Client connected")

@socketio.on('request_update')
def handle_update_request():
    """Send latest data when requested"""
    emit('data_update', data_service.get_all_data())

# ============================================
# MAIN
# ============================================

if __name__ == '__main__':
    print("="*60)
    print("🚀 TRADING BOT DASHBOARD WITH UNIFIED DATA SERVICE")
    print("="*60)
    print(f"📍 Dashboard: http://localhost:5000")
    print(f"📊 All data endpoint: http://localhost:5000/api/all-data")
    print("="*60)
    
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False)

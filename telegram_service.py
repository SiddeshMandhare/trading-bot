# telegram_service.py
import threading
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

class TelegramService:
    def __init__(self, bot_token: str, chat_id: str, bot_instance):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.bot = bot_instance
        self.application = None
        
    def send_alert(self, message: str) -> bool:
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage?chat_id={self.chat_id}&text={message}"
            response = requests.get(url, timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"Telegram send failed: {e}")
            return False
    
    def start_command_handler(self):
        def run_bot():
            try:
                self.application = Application.builder().token(self.bot_token).build()
                self.application.add_handler(CommandHandler("status", self.status_command))
                self.application.add_handler(CommandHandler("balance", self.balance_command))
                self.application.add_handler(CommandHandler("positions", self.positions_command))
                self.application.add_handler(CommandHandler("watchlist", self.watchlist_command))
                self.application.add_handler(CommandHandler("add_symbol", self.add_symbol_command))
                self.application.add_handler(CommandHandler("remove_symbol", self.remove_symbol_command))
                self.application.add_handler(CommandHandler("close_all", self.close_all_command))
                self.application.add_handler(CommandHandler("help", self.help_command))
                self.application.run_polling(allowed_updates=Update.ALL_TYPES)
            except Exception as e:
                print(f"Telegram bot error: {e}")
        
        thread = threading.Thread(target=run_bot, daemon=True)
        thread.start()
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        from config import Config
        status_msg = f"🤖 Bot Status\n\nOpen Positions: {len(self.bot.orderbook)}\nMarket Hours: {'Open' if self.bot.is_market_open() else 'Closed'}\nWatchlist: {', '.join(Config.WATCHLIST)}"
        await update.message.reply_text(status_msg)
    
    async def balance_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        balance = self.bot.get_available_capital()
        await update.message.reply_text(f"💰 Balance: ₹{balance:,.2f}")
    
    async def positions_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.bot.orderbook:
            await update.message.reply_text("No open positions")
            return
        msg = "📈 Open Positions\n\n"
        for symbol, order in self.bot.orderbook.items():
            msg += f"{symbol}: {order.get('position_type')} {order.get('qty')} @ ₹{order.get('entry_price', 0):.2f}\n"
        await update.message.reply_text(msg)
    
    async def watchlist_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        from config import Config
        msg = "Watchlist:\n" + "\n".join(Config.WATCHLIST)
        await update.message.reply_text(msg)
    
    async def add_symbol_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        from config import Config
        args = context.args
        if args:
            symbol = args[0].upper()
            if symbol not in Config.WATCHLIST:
                Config.WATCHLIST.append(symbol)
                await update.message.reply_text(f"✅ Added {symbol} to watchlist")
            else:
                await update.message.reply_text(f"⚠️ {symbol} already in watchlist")
    
    async def remove_symbol_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        from config import Config
        args = context.args
        if args:
            symbol = args[0].upper()
            if symbol in Config.WATCHLIST:
                Config.WATCHLIST.remove(symbol)
                await update.message.reply_text(f"✅ Removed {symbol} from watchlist")
            else:
                await update.message.reply_text(f"⚠️ {symbol} not in watchlist")
    
    async def close_all_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.bot.close_all_positions()
        await update.message.reply_text("✅ Closed all positions")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_msg = """📚 *Available Commands*

/info - Bot information
/status - Bot status
/balance - Account balance
/positions - Open positions
/watchlist - View watchlist
/add_symbol SYMBOL - Add symbol to watchlist
/remove_symbol SYMBOL - Remove symbol from watchlist
/close_all - Close all positions

*Examples:*
/add_symbol RELIANCE
/remove_symbol ITC"""
        await update.message.reply_text(help_msg, parse_mode='Markdown')
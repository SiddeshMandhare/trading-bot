# multi_account_manager.py - Multi-Account Copy Trading Manager
import concurrent.futures
import time
import datetime
from collections import defaultdict
from typing import Dict, List
from config import Config
from auth_service import create_tradehull_with_totp

class MultiAccountTradingManager:
    """Manages multiple trading accounts for copy trading with TOTP authentication"""
    
    def __init__(self, primary_bot):
        self.primary_bot = primary_bot
        self.accounts = {}
        self.account_connections = {}
        self.order_history = defaultdict(list)
        self.account_balances = {}
        self.account_pnl = defaultdict(float)
        
    def initialize_accounts(self):
        """Initialize all trading accounts using TOTP authentication"""
        print("\n" + "="*60)
        print("🔗 INITIALIZING MULTI-ACCOUNT TRADING SYSTEM (TOTP + PIN)")
        print("="*60)
        
        # Initialize Primary Account
        try:
            primary_api = create_tradehull_with_totp(
                Config.CLIENT_CODE, 
                Config.PIN, 
                Config.TOTP_SECRET
            )
            
            if primary_api:
                self.accounts["PRIMARY"] = {
                    'api': primary_api,
                    'name': "PRIMARY",
                    'multiplier': 1.0,
                    'enabled': True,
                    'client_code': Config.CLIENT_CODE
                }
                self.account_connections["PRIMARY"] = True
                print(f"✅ PRIMARY ACCOUNT initialized: {Config.CLIENT_CODE}")
            else:
                print(f"❌ PRIMARY ACCOUNT failed to initialize")
                self.account_connections["PRIMARY"] = False
                
        except Exception as e:
            print(f"❌ PRIMARY ACCOUNT failed: {e}")
            self.account_connections["PRIMARY"] = False
        
        # Initialize Secondary Accounts
        for acc_name, acc_config in Config.TRADING_ACCOUNTS.items():
            if acc_config.get('enabled', False) and acc_config.get('client_code'):
                if acc_config.get('totp_secret') and acc_config.get('pin'):
                    try:
                        acc_api = create_tradehull_with_totp(
                            acc_config['client_code'],
                            acc_config['pin'],
                            acc_config['totp_secret']
                        )
                        
                        if acc_api:
                            self.accounts[acc_name] = {
                                'api': acc_api,
                                'name': acc_name,
                                'multiplier': acc_config.get('multiplier', 1.0),
                                'enabled': True,
                                'client_code': acc_config['client_code']
                            }
                            self.account_connections[acc_name] = True
                            print(f"✅ {acc_name} initialized: {acc_config['client_code']}")
                        else:
                            print(f"❌ {acc_name} failed")
                            
                    except Exception as e:
                        print(f"❌ {acc_name} failed: {e}")
                else:
                    print(f"⚠️ {acc_name}: Missing TOTP configuration")
        
        # Update balances
        self.update_all_balances()
        
        print("\n" + "="*60)
        print(f"📊 TOTAL ACTIVE ACCOUNTS: {len([a for a in self.accounts.values() if a['enabled']])}")
        print("="*60)
        
    def update_all_balances(self):
        """Update balances for all accounts"""
        for acc_name, account in self.accounts.items():
            if account['enabled']:
                try:
                    balance = account['api'].get_balance()
                    if balance and balance > 0:
                        self.account_balances[acc_name] = balance
                    else:
                        self.account_balances[acc_name] = 0
                except:
                    self.account_balances[acc_name] = 0
                    
    def get_primary_api(self):
        """Get primary account API for signals"""
        return self.accounts.get("PRIMARY", {}).get('api')
    
    def execute_on_all_accounts(self, trade_details: Dict) -> Dict:
        """Execute a trade on all enabled accounts"""
        results = {
            'successful': [],
            'failed': [],
            'details': {},
            'total_qty': 0,
            'total_value': 0
        }
        
        if not Config.COPY_TRADING_ENABLED:
            print("📋 Copy trading is disabled. Only primary account will trade.")
            return self.execute_on_single_account("PRIMARY", trade_details)
        
        print(f"\n{'='*60}")
        print(f"🔄 COPY TRADING: Executing on {len(self.accounts)} accounts")
        print(f"   Symbol: {trade_details['symbol']}")
        print(f"   Action: {trade_details['action']}")
        print(f"   Base Qty: {trade_details['base_qty']}")
        print(f"{'='*60}")
        
        if Config.EXECUTION_MODE == "PARALLEL":
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(self.accounts)) as executor:
                future_to_account = {
                    executor.submit(self.execute_on_single_account, acc_name, trade_details): acc_name
                    for acc_name, account in self.accounts.items() if account['enabled']
                }
                for future in concurrent.futures.as_completed(future_to_account):
                    acc_name = future_to_account[future]
                    try:
                        result = future.result()
                        results['details'][acc_name] = result
                        if result.get('success'):
                            results['successful'].append(acc_name)
                            results['total_qty'] += result.get('qty', 0)
                            results['total_value'] += result.get('value', 0)
                        else:
                            results['failed'].append(acc_name)
                    except Exception as e:
                        results['failed'].append(acc_name)
                        results['details'][acc_name] = {'success': False, 'error': str(e)}
        else:
            for acc_name, account in self.accounts.items():
                if account['enabled']:
                    result = self.execute_on_single_account(acc_name, trade_details)
                    results['details'][acc_name] = result
                    if result.get('success'):
                        results['successful'].append(acc_name)
                        results['total_qty'] += result.get('qty', 0)
                        results['total_value'] += result.get('value', 0)
                    else:
                        results['failed'].append(acc_name)
                    
                    if Config.TRADE_DELAY_SECONDS > 0:
                        time.sleep(Config.TRADE_DELAY_SECONDS)
        
        return results
    
    def execute_on_single_account(self, account_name: str, trade_details: Dict) -> Dict:
        """Execute trade on a single account with retry logic"""
        account = self.accounts.get(account_name)
        if not account or not account['enabled']:
            return {'success': False, 'error': f'Account {account_name} not enabled'}
        
        adjusted_qty = max(1, int(trade_details['base_qty'] * account['multiplier']))
        adjusted_value = adjusted_qty * trade_details['entry_price']
        
        current_balance = self.account_balances.get(account_name, 0)
        margin_required = adjusted_value / Config.BROKER_MARGIN_MULTIPLIER
        
        if current_balance < margin_required and account_name != "PRIMARY":
            print(f"⚠️ {account_name}: Insufficient balance")
            if Config.REQUIRE_ALL_ACCOUNTS:
                return {'success': False, 'error': 'Insufficient balance', 'account': account_name}
        
        for attempt in range(Config.MAX_RETRIES_PER_ACCOUNT):
            try:
                print(f"   📤 {account_name}: Placing {trade_details['action']} order for {adjusted_qty} shares")
                
                if Config.USE_SUPER_ORDERS:
                    order_id = account['api'].place_super_order(
                        tradingsymbol=trade_details['symbol'],
                        exchange='NSE',
                        transaction_type=trade_details['action'],
                        quantity=adjusted_qty,
                        order_type='MARKET',
                        trade_type='MIS',
                        price=0,
                        target_price=trade_details['target'],
                        stop_loss_price=trade_details['sl'],
                        trailing_jump=0
                    )
                else:
                    order_id = account['api'].order_placement(
                        tradingsymbol=trade_details['symbol'],
                        exchange='NSE',
                        quantity=adjusted_qty,
                        price=0,
                        trigger_price=0,
                        order_type='MARKET',
                        transaction_type=trade_details['action'],
                        trade_type='MIS'
                    )
                
                if order_id:
                    if account_name != "PRIMARY":
                        self.account_balances[account_name] = current_balance - margin_required
                    
                    self.order_history[account_name].append({
                        'order_id': order_id,
                        'trade_details': trade_details,
                        'qty': adjusted_qty,
                        'timestamp': datetime.datetime.now()
                    })
                    
                    print(f"   ✅ {account_name}: Order placed! ID: {order_id}")
                    
                    return {
                        'success': True,
                        'order_id': order_id,
                        'qty': adjusted_qty,
                        'value': adjusted_value,
                        'account': account_name,
                        'multiplier': account['multiplier']
                    }
                else:
                    print(f"   ❌ {account_name}: Order failed (attempt {attempt + 1})")
                    
            except Exception as e:
                print(f"   ❌ {account_name}: Error - {str(e)} (attempt {attempt + 1})")
                if attempt == Config.MAX_RETRIES_PER_ACCOUNT - 1:
                    return {'success': False, 'error': str(e), 'account': account_name}
                time.sleep(1)
        
        return {'success': False, 'error': 'Max retries exceeded', 'account': account_name}
    
    def get_accounts_status(self) -> str:
        """Get formatted status of all accounts"""
        self.update_all_balances()
        
        status = "🏦 *MULTI-ACCOUNT STATUS*\n\n"
        status += f"📋 *Copy Trading:* {'✅ ENABLED' if Config.COPY_TRADING_ENABLED else '❌ DISABLED'}\n"
        status += f"⚡ *Execution Mode:* {Config.EXECUTION_MODE}\n\n"
        status += "*Accounts:*\n"
        
        total_balance = 0
        for acc_name, account in self.accounts.items():
            if account['enabled']:
                balance = self.account_balances.get(acc_name, 0)
                total_balance += balance
                status += f"\n*{acc_name}* {'(Primary)' if acc_name == 'PRIMARY' else ''}\n"
                status += f"  • Status: 🟢 Active\n"
                status += f"  • Balance: ₹{balance:,.2f}\n"
                status += f"  • Multiplier: {account['multiplier']}x\n"
        
        status += f"\n💰 *Total Combined Balance:* ₹{total_balance:,.2f}"
        return status
    
    def toggle_copy_trading(self, enabled: bool):
        """Enable or disable copy trading"""
        Config.COPY_TRADING_ENABLED = enabled
        status = "ENABLED" if enabled else "DISABLED"
        print(f"📋 Copy Trading {status}")
        if hasattr(self.primary_bot, 'send_telegram_alert'):
            self.primary_bot.send_telegram_alert(f"📋 Copy Trading {status}")
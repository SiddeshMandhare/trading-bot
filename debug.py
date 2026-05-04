# debug.py - Run this to test components
import os
import sys
import json
import requests
from datetime import datetime

def test_all_components():
    print("="*60)
    print("TRADING BOT DIAGNOSTIC TOOL")
    print("="*60)
    
    # Test 1: Config
    print("\n1. Testing Configuration...")
    try:
        from config import Config
        print(f"   ✅ Client Code: {Config.CLIENT_CODE[:5]}...")
        print(f"   ✅ TOTP Secret: {'Set' if Config.TOTP_SECRET else 'MISSING'}")
        print(f"   ✅ Watchlist: {Config.WATCHLIST}")
    except Exception as e:
        print(f"   ❌ Config error: {e}")
    
    # Test 2: Authentication
    print("\n2. Testing Authentication...")
    try:
        from auth_service import verify_authentication
        result = verify_authentication()
        if result.get('authenticated'):
            print(f"   ✅ Authentication successful")
            print(f"   ✅ Balance: ₹{result.get('balance', 0):,.2f}")
        else:
            print(f"   ❌ Authentication failed: {result.get('error')}")
    except Exception as e:
        print(f"   ❌ Auth error: {e}")
    
    # Test 3: Market Data
    print("\n3. Testing Market Data...")
    try:
        from market_data_service import MarketDataService
        from auth_service import create_tradehull_with_totp
        from config import Config
        
        tsl = create_tradehull_with_totp(Config.CLIENT_CODE, Config.PIN, Config.TOTP_SECRET)
        if tsl:
            mds = MarketDataService(tsl)
            data = mds.get_index_prices()
            for name, values in data.items():
                print(f"   {name}: ₹{values.get('ltp', 0):,.2f}")
        else:
            print("   ❌ Could not create Tradehull instance")
    except Exception as e:
        print(f"   ❌ Market data error: {e}")
    
    # Test 4: Database
    print("\n4. Testing Database...")
    try:
        import sqlite3
        conn = sqlite3.connect('trading_bot.db')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM trades")
        count = cursor.fetchone()[0]
        print(f"   ✅ Database connected, {count} trades recorded")
        conn.close()
    except Exception as e:
        print(f"   ❌ Database error: {e}")
    
    print("\n" + "="*60)
    print("Diagnostic complete!")
    print("="*60)

if __name__ == "__main__":
    test_all_components()

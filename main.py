import time
import os
import MetaTrader5 as mt5
from dotenv import load_dotenv
from services.mt5_client import fetch_price_history, initialize_mt5, shutdown_mt5, get_gold_price, place_order, get_account_info
from strategies.simple_ma import trade_decision
from utils.logger import log

# Load credentials from .env
load_dotenv()
LOGIN = int(os.getenv("LOGIN"))
PASSWORD = os.getenv("PASSWORD")
SERVER = os.getenv("SERVER")

log.info("🚀 Starting Gold Auto-Trading Bot...")
log.info("🔌 Attempting to connect to MetaTrader 5...")

if not initialize_mt5(login=LOGIN, password=PASSWORD, server=SERVER):
    log.error("❌ MT5 initialization failed. Check login, password, or terminal state.")
    exit(1)

log.info("✅ Connected to MT5 successfully.")


account = get_account_info()
if account:
    log.info(f"👤 Account Balance: {account['balance']} {account['currency']}")
    log.info(f"📈 Free Margin: {account['margin_free']}")
    log.info(f"📊 Leverage: {account['leverage']}x")


price_history = fetch_price_history("XAUUSD", count=200, timeframe=mt5.TIMEFRAME_M5)
log.info(f"📚 Loaded {len(price_history)} historical prices for strategy seed.")
log.info("⏳ Starting price monitoring loop every 60 seconds...")

try:
    while True:
        price = get_gold_price()
        if price:
            log.info(f"📉 Live Gold Price (XAUUSD Ask): {price}")
            price_history.append(price)

            if len(price_history) > 100:
                price_history.pop(0)

            decision = trade_decision(price_history)
            log.info(f"📊 Strategy Decision: {decision}")

            if decision in ["BUY", "SELL"]:
                log.info(f"📤 Placing {decision} order at price: {price}")
                result = place_order("XAUUSD", decision)
                log.info(f"✅ Order placed result: {result}")
            else:
                log.info("⏱ Waiting for signal...")

        else:
            log.warning("⚠️ Could not fetch gold price from MT5")

        log.info("🔁 Sleeping for 60 seconds...\n")
        time.sleep(60)

except KeyboardInterrupt:
    log.info("🛑 Bot stopped manually via keyboard.")

finally:
    shutdown_mt5()
    log.info("🔒 MT5 connection closed.")

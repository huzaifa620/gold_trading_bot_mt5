import time
import os
import MetaTrader5 as mt5
from dotenv import load_dotenv
import pandas as pd
from services.mt5_client import (
    fetch_price_history,
    initialize_mt5,
    shutdown_mt5,
    get_account_info,
    place_order,
    close_all_trades,
)
from strategies.supertrend_strategy import trade_decision
from utils.risk import calculate_lot_size
from utils.trade_logger import log_trade

load_dotenv()
LOGIN = int(os.getenv("LOGIN"))
PASSWORD = os.getenv("PASSWORD")
SERVER = os.getenv("SERVER")

symbol = "XAUUSD"

print("🚀 Starting Gold Bot...")
if not initialize_mt5(login=LOGIN, password=PASSWORD, server=SERVER):
    print("❌ MT5 initialization failed.")
    exit(1)

account = get_account_info()
if account:
    balance = account["balance"]
else:
    print("❌ Could not fetch account info.")
    exit(1)

current_trend = None  # "BUY" or "SELL"

try:
    while True:
        df = fetch_price_history(symbol, count=100, timeframe=mt5.TIMEFRAME_M5)
        if df is None or df.empty or len(df) < 30:
            print("⚠️ Not enough price data.")
            time.sleep(60)
            continue

        current_price = df["close"].iloc[-1]
        signal, stop_loss_price = trade_decision(df)

        if signal in ["BUY", "SELL"] and stop_loss_price:
            if current_trend and signal != current_trend:
                print(f"🔄 Trend changed: closing all {current_trend} trades.")
                close_all_trades(opposite=signal)

            sl_distance = abs(current_price - stop_loss_price)
            volume = calculate_lot_size(
                sl_points=sl_distance, price=current_price, balance=balance
            )

            print(
                f"📥 Signal: {signal} | Price: {current_price:.2f} | SL: {stop_loss_price:.2f} | Volume: {volume}"
            )

            result = place_order(
                symbol, signal, volume=volume, sl_points=sl_distance, tp_points=0
            )
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                print(f"✅ {signal} order placed.")
                current_trend = signal

                # Log to CSV
                log_trade(
                    order_type=signal,
                    price=current_price,
                    stop_loss=stop_loss_price,
                    lot_size=volume,
                    order_id=result.order,
                    balance=balance,
                )
            else:
                print(f"❌ Failed to place order: {result}")

        else:
            print("⏱ No valid signal. Waiting...")

        print("🕒 Next market check in 60 seconds...\n" + "-" * 50)
        time.sleep(60)

except KeyboardInterrupt:
    print("🛑 Bot stopped manually.")
finally:
    shutdown_mt5()
    print("🔒 Disconnected from MT5.")

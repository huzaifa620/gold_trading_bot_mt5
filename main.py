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
    close_one_trade,
    get_open_positions,
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
        df = fetch_price_history(symbol, count=100, timeframe=mt5.TIMEFRAME_M1)
        if df is None or df.empty or len(df) < 30:
            print("⚠️ Not enough price data.")
            time.sleep(60)
            continue

        current_price = df["close"].iloc[-1]
        signal, stop_loss_price = trade_decision(df)

        # After signal and stop_loss_price are received
        if signal in ["BUY", "SELL"] and stop_loss_price:
            opposite_type = (
                mt5.POSITION_TYPE_SELL if signal == "BUY" else mt5.POSITION_TYPE_BUY
            )
            opposite_trades = get_open_positions(symbol=symbol, order_type=signal)

            if opposite_trades:
                side = "SELL" if opposite_type == mt5.POSITION_TYPE_SELL else "BUY"
                print(f"🔁 {len(opposite_trades)} open {side} trades. Closing one...")
                success = close_one_trade(symbol=symbol, target_type=opposite_type)
                if not success:
                    print("🔁 Retrying to close...")
                    time.sleep(2)
                    close_one_trade(symbol=symbol, target_type=opposite_type)
            else:
                print("✅ No opposite trades to close. Placing new order...")
                sl_distance = abs(current_price - stop_loss_price)
                if sl_distance <= 0:
                    print("⚠️ Invalid SL distance.")
                    continue

                volume = calculate_lot_size(sl_points=sl_distance)
                if volume <= 0:
                    print("⚠️ Lot size too small. Skipping order.")
                    continue

                print(
                    f"📥 Signal: {signal} | Price: {current_price:.2f} | SL: {stop_loss_price:.2f} | Volume: {volume:.2f}"
                )
                result = place_order(
                    symbol, signal, volume=volume, sl_points=sl_distance, tp_points=0
                )

                if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                    print(f"✅ {signal} order placed.")
                    current_trend = signal
                    log_trade(
                        order_type=signal,
                        price=current_price,
                        stop_loss=stop_loss_price,
                        lot_size=volume,
                        order_id=result.order,
                        balance=balance,
                    )
                else:
                    print(f"❌ Order failed: {result}")

        else:
            print("⏱ No valid signal. Waiting...")

        print("🕒 Next market check in 60 seconds...")
        print("-" * 50 + "\n")
        time.sleep(60)

except KeyboardInterrupt:
    print("🛑 Bot stopped manually.")
finally:
    shutdown_mt5()
    print("🔒 Disconnected from MT5.")

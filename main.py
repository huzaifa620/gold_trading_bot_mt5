import time
import os
import MetaTrader5 as mt5
from dotenv import load_dotenv

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

print("\n🚀 Starting Gold Bot...")
print("-" * 60)

# Initialize connection to MT5
if not initialize_mt5(login=LOGIN, password=PASSWORD, server=SERVER):
    print("❌ MT5 initialization failed.")
    exit(1)

account = get_account_info()
if not account:
    print("❌ Could not fetch account info.")
    shutdown_mt5()
    exit(1)

balance = account["balance"]
print(f"📈 Account Balance: ${balance:.2f}")

current_trend = None  # BUY or SELL

try:
    while True:
        df = fetch_price_history(symbol, count=100, timeframe=mt5.TIMEFRAME_M1)
        if df is None or df.empty or len(df) < 30:
            print("⚠️ Not enough price data. Retrying in 60s.")
            time.sleep(60)
            continue

        current_price = df["close"].iloc[-1]
        signal, stop_loss_price = trade_decision(df)

        if signal and stop_loss_price:
            opposite_type = (
                mt5.POSITION_TYPE_SELL if signal == "BUY" else mt5.POSITION_TYPE_BUY
            )
            opposite_trades = get_open_positions(symbol=symbol)

            # Close opposite positions first
            to_close = [pos for pos in opposite_trades if pos.type == opposite_type]
            if to_close:
                print(f"🔁 {len(to_close)} opposite trades found. Closing one...")
                success = close_one_trade(symbol=symbol, target_type=opposite_type)
                if not success:
                    print("❌ Failed to close. Retrying in 2s.")
                    time.sleep(2)
                    close_one_trade(symbol=symbol, target_type=opposite_type)
                time.sleep(1)
            else:
                print("✅ No opposite trades. Proceeding with new order...")

            sl_distance = abs(current_price - stop_loss_price)
            if sl_distance <= 0:
                print("⚠️ Invalid SL distance. Skipping.")
                time.sleep(60)
                continue

            sl_distance = max(sl_distance, 1.0)  # minimum enforced SL
            volume = calculate_lot_size(sl_points=sl_distance)

            if volume <= 0:
                print("⚠️ Invalid lot size. Skipping.")
                time.sleep(60)
                continue

            print(
                f"📥 Placing {signal} order | Price: {current_price:.2f} | SL: {stop_loss_price:.2f} | Vol: {volume:.2f}"
            )
            result = place_order(
                symbol, signal, volume=volume, sl_points=sl_distance, tp_points=0
            )

            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                print(f"✅ Order placed successfully: #{result.order}")
                log_trade(
                    order_type=signal,
                    price=current_price,
                    stop_loss=sl_distance,
                    lot_size=volume,
                    order_id=result.order,
                    balance=balance,
                )
                current_trend = signal
            else:
                print(
                    f"❌ Order placement failed: {result.retcode} - {result.comment if result else 'No result'}"
                )
        else:
            print("⏱ No valid signal this cycle.")

        print("🕒 Waiting 60s for next check...")
        print("-" * 50 + "\n")
        time.sleep(60)

except KeyboardInterrupt:
    print("🛑 Bot stopped manually.")

finally:
    shutdown_mt5()
    print("🔒 Disconnected from MT5.")

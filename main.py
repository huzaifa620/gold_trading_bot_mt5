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

# Initialize MT5 connection
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

current_trend = None

try:
    while True:
        df = fetch_price_history(symbol, count=100, timeframe=mt5.TIMEFRAME_M1)
        if df is None or df.empty or len(df) < 30:
            print("⚠️ Not enough price data. Retrying in 60s.")
            time.sleep(60)
            continue

        current_price = df["close"].iloc[-1]
        signal, stop_loss_price, take_profit_points = trade_decision(df)

        if signal and stop_loss_price and take_profit_points:
            opposite_type = "SELL" if signal == "BUY" else "BUY"
            opposite_trades = get_open_positions(
                symbol=symbol, order_type=opposite_type
            )

            if opposite_trades:
                print(
                    f"🔁 {len(opposite_trades)} opposite trades found. Closing one..."
                )
                success = close_one_trade(
                    symbol=symbol, target_type=opposite_trades[0].type
                )
                if not success:
                    print("❌ Failed to close. Retrying in 2s.")
                    time.sleep(2)
                    close_one_trade(symbol=symbol, target_type=opposite_trades[0].type)
                time.sleep(1)
            else:
                print("✅ No opposite trades. Proceeding with new order...")

            sl_distance = abs(current_price - stop_loss_price)
            sl_distance = max(sl_distance, 1.0)  # Enforce minimum SL distance

            volume = calculate_lot_size(sl_points=sl_distance)
            if volume <= 0:
                print("⚠️ Invalid lot size. Skipping.")
                time.sleep(60)
                continue

            print(
                f"📥 Placing {signal} order | Entry: {current_price:.2f} | SL: {stop_loss_price:.2f} | TP: {take_profit_points:.2f} pts | Vol: {volume:.2f}"
            )
            result = place_order(
                symbol,
                signal,
                volume=volume,
                sl_points=sl_distance,
                tp_points=take_profit_points,
            )

            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                print(f"✅ Order placed successfully: #{result.order}")
                log_trade(
                    order_type=signal,
                    price=current_price,
                    stop_loss=stop_loss_price,
                    take_profit=(
                        current_price + take_profit_points
                        if signal == "BUY"
                        else current_price - take_profit_points
                    ),
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

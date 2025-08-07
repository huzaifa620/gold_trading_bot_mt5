import csv
import os
import time
from datetime import datetime

LOG_FILE = "trades_log.csv"

LOG_FIELDS = [
    "timestamp",
    "order_type",
    "price",
    "stop_loss",
    "take_profit",
    "lot_size",
    "order_id",
    "balance",
    "status",  # OPEN or CLOSED
    "close_price",  # Set when CLOSED
    "close_time",  # Set when CLOSED
    "profit_loss",  # Calculated on close
    "close_reason",  # e.g. TP Hit, Signal Flip
]


# Retry decorator for file writing (handles locked file errors)
def retry_on_file_lock(func):
    def wrapper(*args, **kwargs):
        retries = 5
        delay = 1  # seconds
        for attempt in range(retries):
            try:
                return func(*args, **kwargs)
            except PermissionError:
                log(f"🔒 File locked. Retrying ({attempt + 1}/{retries})...")
                time.sleep(delay)
        log("❌ Failed to access log file after multiple attempts.")

    return wrapper


@retry_on_file_lock
def initialize_log():
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, mode="w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=LOG_FIELDS)
            writer.writeheader()


@retry_on_file_lock
def log_trade(order_type, price, stop_loss, take_profit, lot_size, order_id, balance):
    initialize_log()

    entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "order_type": order_type,
        "price": round(price, 2),
        "stop_loss": round(stop_loss, 2),
        "take_profit": round(take_profit, 2),
        "lot_size": round(lot_size, 2),
        "order_id": order_id,
        "balance": round(balance, 2),
        "status": "OPEN",
        "close_price": "",
        "close_time": "",
        "profit_loss": "",
        "close_reason": "",
    }

    with open(LOG_FILE, mode="a", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=LOG_FIELDS)
        writer.writerow(entry)


@retry_on_file_lock
def close_trade(order_id, close_price, reason="Closed"):
    if not os.path.exists(LOG_FILE):
        log("⚠️ Log file not found. Cannot update trade.")
        return

    updated = False
    rows = []

    with open(LOG_FILE, mode="r", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row["order_id"] == str(order_id) and row["status"] == "OPEN":
                entry_price = float(row["price"])
                lot_size = float(row["lot_size"])
                order_type = row["order_type"]

                # Calculate profit/loss for XAUUSD (1 lot = 100 oz)
                if order_type == "BUY":
                    profit_loss = (close_price - entry_price) * 100 * lot_size
                else:
                    profit_loss = (entry_price - close_price) * 100 * lot_size

                row["status"] = "CLOSED"
                row["close_price"] = round(close_price, 2)
                row["close_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                row["profit_loss"] = round(profit_loss, 2)
                row["close_reason"] = reason
                updated = True

            rows.append(row)

    if updated:
        with open(LOG_FILE, mode="w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=LOG_FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        log(
            f"📘 Trade {order_id} closed. P/L: {round(profit_loss, 2)} USD | Reason: {reason}"
        )
    else:
        log(f"⚠️ Trade {order_id} not found or already closed.")


def log(message: str, save_to_file=True):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    full_msg = f"[{timestamp}] {message}"
    print(full_msg)
    if save_to_file:
        with open("gold_bot.log", "a", encoding="utf-8") as f:
            f.write(full_msg + "\n")


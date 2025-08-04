import csv
import os
from datetime import datetime

LOG_FILE = "trades_log.csv"
LOG_FIELDS = [
    "timestamp",
    "order_type",
    "price",
    "stop_loss",
    "lot_size",
    "order_id",
    "balance",
    "status",  # OPEN or CLOSED
    "close_price",  # set when CLOSED
    "close_time",  # set when CLOSED
]


def initialize_log():
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, mode="w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=LOG_FIELDS)
            writer.writeheader()


def log_trade(
    order_type,
    price,
    stop_loss,
    lot_size,
    order_id=None,
    balance=None,
):
    initialize_log()
    with open(LOG_FILE, mode="a", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=LOG_FIELDS)
        writer.writerow(
            {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "order_type": order_type,
                "price": round(price, 2),
                "stop_loss": round(stop_loss, 2) if stop_loss else "",
                "lot_size": lot_size,
                "order_id": order_id or "",
                "balance": round(balance, 2) if balance else "",
                "status": "OPEN",
                "close_price": "",
                "close_time": "",
            }
        )


def close_trade(order_id, close_price):
    """
    Marks the given order as CLOSED in the CSV and logs close price and time.
    """
    if not os.path.exists(LOG_FILE):
        print("⚠️ Log file not found. Cannot update trade.")
        return

    updated = False
    rows = []

    with open(LOG_FILE, mode="r", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row["order_id"] == str(order_id) and row["status"] == "OPEN":
                row["status"] = "CLOSED"
                row["close_price"] = round(close_price, 2)
                row["close_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                updated = True
            rows.append(row)

    if updated:
        with open(LOG_FILE, mode="w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=LOG_FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        print(f"✅ Trade {order_id} marked as CLOSED.")
    else:
        print(f"⚠️ Trade {order_id} not found or already closed.")

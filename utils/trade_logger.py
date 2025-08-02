import csv
import os
from datetime import datetime

LOG_FILE = "trades_log.csv"


def initialize_log():
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, mode="w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(
                [
                    "timestamp",
                    "order_type",
                    "price",
                    "stop_loss",
                    "lot_size",
                    "order_id",
                ]
            )


def log_trade(order_type, price, stop_loss, lot_size, order_id=None):
    initialize_log()
    with open(LOG_FILE, mode="a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(
            [
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                order_type,
                round(price, 2),
                round(stop_loss, 2) if stop_loss else "",
                lot_size,
                order_id or "",
            ]
        )

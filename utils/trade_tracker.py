import json
import os
from datetime import datetime

TRACKER_FILE = "last_trade.json"

def load_last_trade_time():
    if os.path.exists(TRACKER_FILE):
        with open(TRACKER_FILE, "r") as f:
            data = json.load(f)
            return datetime.fromisoformat(data.get("last_trade_time"))
    return None

def save_last_trade_time(dt):
    with open(TRACKER_FILE, "w") as f:
        json.dump({"last_trade_time": dt.isoformat()}, f)

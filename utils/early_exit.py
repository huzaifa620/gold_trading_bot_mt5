import pandas as pd
import MetaTrader5 as mt5


def should_exit_early(symbol, direction, bars=3, timeframe=mt5.TIMEFRAME_M1):
    # Fetch candles for analysis
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, bars + 5)
    if rates is None or len(rates) < bars + 5:
        return False

    closes = [bar["close"] for bar in rates]
    opens = [bar["open"] for bar in rates]

    # 1️⃣ Check if last `bars` candles go against trade direction
    if direction == "BUY":
        candles_against = all(closes[i] < opens[i] for i in range(-bars, 0))
    else:  # SELL
        candles_against = all(closes[i] > opens[i] for i in range(-bars, 0))

    if not candles_against:
        return False  # Price not consistently against us

    # 2️⃣ Confirm EMA5 cross
    df = pd.DataFrame(rates)
    df["ema5"] = df["close"].ewm(span=5, adjust=False).mean()
    latest_close = df["close"].iloc[-1]
    latest_ema5 = df["ema5"].iloc[-1]

    if direction == "BUY" and latest_close < latest_ema5:
        return True
    if direction == "SELL" and latest_close > latest_ema5:
        return True

    return False

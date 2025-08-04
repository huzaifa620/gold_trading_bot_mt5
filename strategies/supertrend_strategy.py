import pandas as pd
from ta.volatility import AverageTrueRange
from ta.trend import EMAIndicator


def calculate_supertrend(df, atr_period=10, multiplier=3):
    df = df.copy()
    atr = AverageTrueRange(
        high=df["high"], low=df["low"], close=df["close"], window=atr_period
    ).average_true_range()
    hl2 = (df["high"] + df["low"]) / 2

    df["upper_band"] = hl2 + (multiplier * atr)
    df["lower_band"] = hl2 - (multiplier * atr)
    df["supertrend"] = pd.Series(index=df.index, dtype="float64")
    in_uptrend = True

    for i in range(1, len(df)):
        curr_close = df["close"][i]
        if in_uptrend and curr_close < df["lower_band"][i]:
            in_uptrend = False
            print(f"🔻 Supertrend switched to SELL at index {i}")
        elif not in_uptrend and curr_close > df["upper_band"][i]:
            in_uptrend = True
            print(f"🔺 Supertrend switched to BUY at index {i}")

        df.at[i, "supertrend"] = (
            df["lower_band"][i] if in_uptrend else df["upper_band"][i]
        )

    df["in_uptrend"] = df["close"] > df["supertrend"]
    return df


def trade_decision(df: pd.DataFrame) -> tuple:
    if len(df) < 30:
        print("⚠️ Not enough data for decision-making.")
        return "WAIT", None

    df = calculate_supertrend(df)
    df["ema5"] = EMAIndicator(close=df["close"], window=5).ema_indicator()
    df["ema20"] = EMAIndicator(close=df["close"], window=20).ema_indicator()

    latest = df.iloc[-1]
    trend = "BUY" if latest["in_uptrend"] else "SELL"
    ema_signal = "BUY" if latest["ema5"] > latest["ema20"] else "SELL"

    print(f"📉 Supertrend Direction: {trend}")
    print(f"📈 EMA Crossover Signal: {ema_signal}")

    if trend == "BUY" and ema_signal == "BUY":
        print("✅ Final Decision: BUY")
        return "BUY", latest["supertrend"]
    elif trend == "SELL" and ema_signal == "SELL":
        print("✅ Final Decision: SELL")
        return "SELL", latest["supertrend"]
    else:
        print("⏸ Final Decision: WAIT (No confirmation)")
        return "WAIT", None

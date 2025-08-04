import pandas as pd


def calculate_atr(df, period):
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift()).abs()
    low_close = (df["low"] - df["close"].shift()).abs()

    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr


def calculate_supertrend(df, period=10, multiplier=3):
    atr = calculate_atr(df, period)
    hl2 = (df["high"] + df["low"]) / 2
    upperband = hl2 + (multiplier * atr)
    lowerband = hl2 - (multiplier * atr)

    supertrend = [False] * len(df)
    in_uptrend = True

    for i in range(1, len(df)):
        if df["close"][i] > upperband[i - 1]:
            in_uptrend = True
        elif df["close"][i] < lowerband[i - 1]:
            in_uptrend = False
        else:
            if in_uptrend and lowerband[i] < lowerband[i - 1]:
                lowerband[i] = lowerband[i - 1]
            if not in_uptrend and upperband[i] > upperband[i - 1]:
                upperband[i] = upperband[i - 1]

        supertrend[i] = in_uptrend

    df["supertrend"] = supertrend
    df["supertrend_upper"] = upperband
    df["supertrend_lower"] = lowerband

    return df


def calculate_ema(df, period):
    return df["close"].ewm(span=period, adjust=False).mean()


def trade_decision(df):
    df = calculate_supertrend(df)
    ema5 = calculate_ema(df, 5)
    ema20 = calculate_ema(df, 20)

    latest_close = df["close"].iloc[-1]
    in_uptrend = df["supertrend"].iloc[-1]
    ema5_latest = ema5.iloc[-1]
    ema20_latest = ema20.iloc[-1]

    print(
        f"📊 Price: {latest_close:.2f} | EMA5: {ema5_latest:.2f} | EMA20: {ema20_latest:.2f} | Trend: {'UP' if in_uptrend else 'DOWN'}"
    )

    # EMA + Supertrend confirmation
    if in_uptrend and ema5_latest > ema20_latest:
        sl = df["supertrend_lower"].iloc[-1]
        print(f"✅ BUY signal confirmed. Stop loss at {sl:.2f}")
        return "BUY", sl
    elif not in_uptrend and ema5_latest < ema20_latest:
        sl = df["supertrend_upper"].iloc[-1]
        print(f"✅ SELL signal confirmed. Stop loss at {sl:.2f}")
        return "SELL", sl
    else:
        print("❌ Signal rejected due to EMA mismatch with trend.")
        return None, None

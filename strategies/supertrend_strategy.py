import pandas as pd


def calculate_atr(df, period):
    """Calculate Average True Range (ATR) for volatility measurement."""
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift()).abs()
    low_close = (df["low"] - df["close"].shift()).abs()

    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()


def calculate_supertrend(df, period=10, multiplier=3):
    """Calculate SuperTrend indicator."""
    atr = calculate_atr(df, period)
    hl2 = (df["high"] + df["low"]) / 2
    upperband = hl2 + (multiplier * atr)
    lowerband = hl2 - (multiplier * atr)

    supertrend = [False] * len(df)
    in_uptrend = True

    for i in range(1, len(df)):
        if df["close"].iloc[i] > upperband.iloc[i - 1]:
            in_uptrend = True
        elif df["close"].iloc[i] < lowerband.iloc[i - 1]:
            in_uptrend = False
        else:
            if in_uptrend and lowerband.iloc[i] < lowerband.iloc[i - 1]:
                lowerband.iloc[i] = lowerband.iloc[i - 1]
            if not in_uptrend and upperband.iloc[i] > upperband.iloc[i - 1]:
                upperband.iloc[i] = upperband.iloc[i - 1]

        supertrend[i] = in_uptrend

    df["supertrend"] = supertrend
    df["supertrend_upper"] = upperband
    df["supertrend_lower"] = lowerband
    df["atr"] = atr

    return df


def calculate_ema(df, period):
    return df["close"].ewm(span=period, adjust=False).mean()


tp_rules = [
    (2.0, 2.5),
    (1.5, 2.0),
    (1.0, 1.5),
    (0.7, 1.2),
    (0.0, 1.0),
]


def get_dynamic_tp_multiplier(atr, sl_distance):
    """Calculate dynamic TP multiplier based on ATR and SL distance."""
    if sl_distance <= 0:
        return 1.0
    ratio = atr / sl_distance
    for threshold, multiplier in tp_rules:
        if ratio >= threshold:
            return multiplier
    return 1.0


def calculate_adx(df, period=14):
    df = df.copy()
    df["tr"] = df[["high", "low", "close"]].apply(
        lambda x: max(
            x["high"] - x["low"],
            abs(x["high"] - x["close"]),
            abs(x["low"] - x["close"]),
        ),
        axis=1,
    )

    df["+dm"] = df["high"].diff()
    df["-dm"] = df["low"].diff()

    df["+dm"] = df["+dm"].where((df["+dm"] > df["-dm"]) & (df["+dm"] > 0), 0.0)
    df["-dm"] = df["-dm"].where((df["-dm"] > df["+dm"]) & (df["-dm"] > 0), 0.0)

    atr = df["tr"].rolling(window=period).mean()
    plus_di = 100 * (df["+dm"].rolling(window=period).mean() / atr)
    minus_di = 100 * (df["-dm"].rolling(window=period).mean() / atr)
    dx = 100 * (abs(plus_di - minus_di) / (plus_di + minus_di)).fillna(0)

    adx = dx.rolling(window=period).mean()
    df["adx"] = adx

    return df


def trade_decision(df, atr_period=14, adx_threshold=20):
    """Make trade decision based on SuperTrend, EMA, and ADX filter."""
    df = calculate_supertrend(df, period=atr_period)
    df["ema5"] = calculate_ema(df, 5)
    df["ema20"] = calculate_ema(df, 20)
    df = calculate_adx(df, period=atr_period)

    if len(df) < atr_period + 2:
        print("⚠️ Not enough data for decision.")
        return None, None, None

    latest = df.iloc[-1]
    close_price = latest["close"]
    ema5 = latest["ema5"]
    ema20 = latest["ema20"]
    atr = df["atr"].iloc[-5:].mean()
    in_uptrend = latest["supertrend"]
    adx = latest["adx"]

    print(
        f"📊 Price: {close_price:.2f} | EMA5: {ema5:.2f} | EMA20: {ema20:.2f} | ATR: {atr:.2f} | ADX: {adx:.2f} | Trend: {'UP' if in_uptrend else 'DOWN'}"
    )

    if pd.isna(atr) or atr < 0.1:
        print("⚠️ ATR too small. Skipping trade.")
        return None, None, None

    if pd.isna(adx) or adx < adx_threshold:
        print(f"🚫 ADX too low ({adx:.2f}) — skipping due to sideways market.")
        return None, None, None

    if in_uptrend and ema5 > ema20:
        sl_price = latest["supertrend_lower"]
        sl_distance = close_price - sl_price
        tp_multiplier = get_dynamic_tp_multiplier(atr, sl_distance) * 1.5
        tp_points = tp_multiplier * atr
        print(f"✅ BUY signal confirmed | SL: {sl_price:.2f} | TP: {tp_points:.2f}")
        return "BUY", sl_price, tp_points

    elif not in_uptrend and ema5 < ema20:
        sl_price = latest["supertrend_upper"]
        sl_distance = sl_price - close_price
        tp_multiplier = get_dynamic_tp_multiplier(atr, sl_distance) * 1.5
        tp_points = tp_multiplier * atr
        print(f"✅ SELL signal confirmed | SL: {sl_price:.2f} | TP: {tp_points:.2f}")
        return "SELL", sl_price, tp_points

    print("❌ Signal rejected due to EMA mismatch with trend.")
    return None, None, None

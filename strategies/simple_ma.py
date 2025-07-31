
def trade_decision(price_history: list[float]) -> str:
    if len(price_history) < 10:
        return "WAIT"

    current = price_history[-1]
    ma_10 = sum(price_history[-10:]) / 10
    print(f"Current Price: {current}, 10-Period MA: {ma_10}, Buy Target: {ma_10 * 0.99}, Sell Target: {ma_10 * 1.01}")
    if current > ma_10 * 1.01:
        return "SELL"
    elif current < ma_10 * 0.99:
        return "BUY"
    else:
        return "WAIT"

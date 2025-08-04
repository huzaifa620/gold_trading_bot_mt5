import MetaTrader5 as mt5
from MetaTrader5 import copy_rates_from_pos, TIMEFRAME_M1
import pandas as pd

from utils.trade_logger import close_trade


def initialize_mt5(login: int, password: str, server: str) -> bool:
    return mt5.initialize(server=server, login=login, password=password)


def shutdown_mt5():
    mt5.shutdown()


def get_gold_price():
    try:
        symbol = "XAUUSD"
        tick = mt5.symbol_info_tick(symbol)._asdict()
        print(f"Current tick for {symbol}: {tick}")
        return tick["ask"] if tick else None
    except Exception as e:
        print(f"Error getting gold price: {e}")
        return None


def place_order(
    symbol: str,
    action: str,
    volume: float = 0.01,
    sl_points: float = 100.0,
    tp_points: float = 200.0,
):
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None or not symbol_info.visible:
        print(f"⚠️ Symbol {symbol} not found or not visible.")
        return None

    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        print(f"⚠️ Failed to fetch tick for {symbol}")
        return None

    price = tick.ask if action == "BUY" else tick.bid
    deviation = 20
    point = symbol_info.point

    # Get broker-defined minimum stop level (converted from points to price distance)
    stop_level = symbol_info.trade_stops_level * point
    min_distance = max(stop_level, 0.5)  # fallback if stop level is zero

    # Compute SL and TP from input point values
    sl = price - sl_points if action == "BUY" else price + sl_points
    tp = price + tp_points if action == "BUY" else price - tp_points

    # Ensure SL and TP meet minimum distance requirement
    if action == "BUY":
        if (price - sl) < min_distance:
            sl = price - min_distance
        if (tp - price) < min_distance:
            tp = price + min_distance
    else:  # SELL
        if (sl - price) < min_distance:
            sl = price + min_distance
        if (price - tp) < min_distance:
            tp = price - min_distance

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": mt5.ORDER_TYPE_BUY if action == "BUY" else mt5.ORDER_TYPE_SELL,
        "price": price,
        "sl": round(sl, 2),
        "tp": round(tp, 2),
        "deviation": deviation,
        "magic": 234000,
        "comment": "AutoTrade via Bot",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"❌ Order failed: {result.retcode} - {result.comment}")
        print(f"❌ Full response: {result}")
    else:
        print(f"✅ Order placed successfully! Order ID: {result.order}")

    return result


def fetch_price_history(symbol="XAUUSD", count=100, timeframe=TIMEFRAME_M1):
    rates = copy_rates_from_pos(symbol, timeframe, 0, count)
    if rates is None or len(rates) == 0:
        print(f"❌ Failed to fetch historical rates for {symbol}")
        return []

    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    return df[["time", "open", "high", "low", "close", "tick_volume"]]


def get_account_info():
    account = mt5.account_info()
    if account is None:
        print("❌ Failed to get account info")
        return None
    return {
        "balance": account.balance,
        "equity": account.equity,
        "margin_free": account.margin_free,
        "leverage": account.leverage,
        "currency": account.currency,
    }


def close_all_trades(opposite="SELL", symbol="XAUUSD"):
    """
    Closes all open positions in the opposite direction to the new signal.
    For example, if signal is "SELL", it will close all existing BUY trades.
    """
    position_type = (
        mt5.POSITION_TYPE_BUY if opposite == "SELL" else mt5.POSITION_TYPE_SELL
    )

    positions = mt5.positions_get(symbol=symbol)

    if positions is None or len(positions) == 0:
        print("⚠️ No open positions to close.")
        return

    for pos in positions:
        position_type = "BUY" if pos.type == mt5.ORDER_TYPE_BUY else "SELL"

        if opposite and position_type != opposite:
            print(
                f"⏩ Skipping {position_type} position as it doesn't match '{opposite}' signal."
            )
            continue

        close_type = (
            mt5.ORDER_TYPE_SELL
            if pos.type == mt5.ORDER_TYPE_BUY
            else mt5.ORDER_TYPE_BUY
        )
        price = (
            mt5.symbol_info_tick(symbol).bid
            if close_type == mt5.ORDER_TYPE_SELL
            else mt5.symbol_info_tick(symbol).ask
        )

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": pos.volume,
            "type": close_type,
            "price": price,
            "deviation": 20,
            "magic": 234000,
            "comment": "Auto-close via trend reversal",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            print(f"✅ Closed {position_type} position | Order ID: {result.order}")
            close_trade(order_id=pos.ticket, close_price=price)
        else:
            print(
                f"❌ Failed to close {position_type} position: {result.retcode} - {result.comment}"
            )

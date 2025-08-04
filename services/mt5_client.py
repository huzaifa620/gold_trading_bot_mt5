import csv
import os
import MetaTrader5 as mt5
from MetaTrader5 import copy_rates_from_pos, TIMEFRAME_M1
import pandas as pd

from utils.trade_logger import LOG_FILE, close_trade


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


def close_all_trades(opposite_type="SELL", symbol="XAUUSD"):
    """
    Closes all open trades that are opposite to the current signal (BUY/SELL).
    """
    close_type = mt5.ORDER_TYPE_SELL if opposite_type == "BUY" else mt5.ORDER_TYPE_BUY
    target_position_type = (
        mt5.POSITION_TYPE_BUY if opposite_type == "SELL" else mt5.POSITION_TYPE_SELL
    )

    positions = mt5.positions_get(symbol=symbol)
    print(f"🔍 Found {len(positions)} open positions for {symbol}.")
    if not positions:
        print("⚠️ No open positions to close.")
        return

    for pos in positions:
        if pos.type != target_position_type:
            print(
                f"⏩ Skipping position #{pos.ticket} | Type: {pos.type} (Not matching target)"
            )
            continue

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
            print(
                f"✅ Closed position #{pos.ticket} | Volume: {pos.volume} at price {price}"
            )
            close_trade(order_id=pos.ticket, close_price=price)
        else:
            print(
                f"❌ Failed to close position #{pos.ticket} | Retcode: {result.retcode} - {result.comment}"
            )


def get_open_positions(symbol="XAUUSD", order_type=None):
    """
    Fetch all open positions for the specified symbol.
    """
    positions = mt5.positions_get(symbol=symbol)
    if positions is None:
        return []
    if order_type is not None:
        return [pos for pos in positions if pos.type == order_type]
    return list(positions)


def close_one_trade(symbol="XAUUSD", target_type=mt5.POSITION_TYPE_BUY):
    """
    Closes one trade of the specified position type (BUY/SELL).
    Returns the closed order ticket ID or None if nothing was closed.
    """
    print(
        f"🔍 Attempting to close one {'BUY' if target_type == mt5.POSITION_TYPE_BUY else 'SELL'} trade for {symbol}..."
    )

    positions = get_open_positions(symbol)
    print(f"📊 Found {len(positions)} open position(s) for {symbol}.")

    for pos in positions:
        print(
            f"➡️ Checking position #{pos.ticket}: type={pos.type}, volume={pos.volume}"
        )
        if pos.type == target_type:
            print(f"🛑 Match found: Preparing to close position #{pos.ticket}...")

            close_type = (
                mt5.ORDER_TYPE_SELL
                if pos.type == mt5.POSITION_TYPE_BUY
                else mt5.ORDER_TYPE_BUY
            )
            price = (
                mt5.symbol_info_tick(symbol).bid
                if close_type == mt5.ORDER_TYPE_SELL
                else mt5.symbol_info_tick(symbol).ask
            )
            print(
                f"💰 Close order type: {'SELL' if close_type == mt5.ORDER_TYPE_SELL else 'BUY'}, Price: {price}"
            )

            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": pos.volume,
                "type": close_type,
                "price": price,
                "deviation": 20,
                "magic": 234000,
                "comment": "Auto-close single opposite",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
                "position": pos.ticket,
            }

            print(f"📤 Sending close request for position #{pos.ticket}...")
            result = mt5.order_send(request)

            if result.retcode == mt5.TRADE_RETCODE_DONE:
                print(f"✅ Successfully closed trade #{pos.ticket} (type: {pos.type})")
                return pos.ticket
            else:
                print(
                    f"❌ Failed to close trade #{pos.ticket}: Retcode={result.retcode}, Comment='{result.comment}'"
                )
        else:
            print(
                f"⏭️ Skipping position #{pos.ticket}, not a {'BUY' if target_type == mt5.POSITION_TYPE_BUY else 'SELL'}."
            )

    print(
        f"⚠️ No {'BUY' if target_type == mt5.POSITION_TYPE_BUY else 'SELL'} trades were closed."
    )
    return None

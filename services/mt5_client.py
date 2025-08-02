import MetaTrader5 as mt5
from MetaTrader5 import copy_rates_from_pos, TIMEFRAME_M1
import pandas as pd


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

    price = (
        mt5.symbol_info_tick(symbol).ask
        if action == "BUY"
        else mt5.symbol_info_tick(symbol).bid
    )
    deviation = 20

    sl = price - sl_points if action == "BUY" else price + sl_points
    tp = price + tp_points if action == "BUY" else price - tp_points

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
    if positions is None:
        print("❌ Failed to retrieve positions.")
        return

    for pos in positions:
        if pos.type == position_type:
            ticket = pos.ticket
            volume = pos.volume
            price = (
                mt5.symbol_info_tick(symbol).bid
                if pos.type == mt5.POSITION_TYPE_BUY
                else mt5.symbol_info_tick(symbol).ask
            )

            close_type = (
                mt5.ORDER_TYPE_SELL
                if pos.type == mt5.POSITION_TYPE_BUY
                else mt5.ORDER_TYPE_BUY
            )

            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type": close_type,
                "position": ticket,
                "price": price,
                "deviation": 20,
                "magic": 234000,
                "comment": "Auto-close on trend reversal",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }

            result = mt5.order_send(request)
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                print(
                    f"✅ Closed trade {ticket} ({'BUY' if pos.type == 0 else 'SELL'}) at price {price}"
                )
            else:
                print(f"❌ Failed to close trade {ticket}: {result}")

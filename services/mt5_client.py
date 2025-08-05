import MetaTrader5 as mt5
import pandas as pd

from utils.trade_logger import close_trade


def initialize_mt5(login, password, server):
    mt5.shutdown()
    if not mt5.initialize():
        print("❌ Failed to initialize MetaTrader 5.")
        return False
    authorized = mt5.login(login, password=password, server=server)
    if authorized:
        print("✅ Successfully connected to MT5 account.")
    else:
        print("❌ Login failed. Check credentials.")
    return authorized


def shutdown_mt5():
    mt5.shutdown()
    print("🔒 MT5 connection closed.")


def get_account_info():
    acc = mt5.account_info()
    if acc:
        print(
            f"💰 Account Info - Balance: {acc.balance}, Equity: {acc.equity}, Leverage: {acc.leverage}"
        )
        return {"balance": acc.balance, "equity": acc.equity, "leverage": acc.leverage}
    print("❌ Could not retrieve account info.")
    return None


def fetch_price_history(symbol, count=300, timeframe=mt5.TIMEFRAME_M5):
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, count)
    if rates is None:
        print("❌ Failed to fetch price data.")
        return None
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    df.set_index("time", inplace=True)
    return df


def place_order(symbol, signal, volume, sl_points, tp_points=0):
    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        print("❌ Failed to retrieve current price.")
        return None

    symbol_info = mt5.symbol_info(symbol)
    if not symbol_info:
        print("❌ Failed to retrieve symbol info.")
        return None

    digits = symbol_info.digits
    price = tick.ask if signal == "BUY" else tick.bid
    order_type = mt5.ORDER_TYPE_BUY if signal == "BUY" else mt5.ORDER_TYPE_SELL

    sl_price = price - sl_points if signal == "BUY" else price + sl_points
    tp_price = price + tp_points if signal == "BUY" else price - tp_points

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": order_type,
        "price": round(price, digits),
        "sl": round(sl_price, digits),
        "tp": round(tp_price, digits),
        "deviation": 20,
        "magic": 234000,
        "comment": "Supertrend Signal Entry",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)

    if result.retcode == mt5.TRADE_RETCODE_DONE:
        print(
            f"✅ {signal} order placed | Price: {round(price, digits)} | SL: {round(sl_price, digits)} | TP: {round(tp_price, digits)} | Volume: {volume:.2f}"
        )
    else:
        print(f"❌ Order failed: {result.retcode} - {result.comment}")

    return result


def get_open_positions(symbol, order_type=None):
    positions = mt5.positions_get(symbol=symbol)
    if positions is None:
        print("⚠️ No open positions found.")
        return []

    if order_type:
        target_type = (
            mt5.POSITION_TYPE_BUY if order_type == "BUY" else mt5.POSITION_TYPE_SELL
        )
        filtered = [p for p in positions if p.type == target_type]
        print(f"🔍 Found {len(filtered)} open {order_type} positions for {symbol}.")
        return filtered

    print(f"🔍 Found {len(positions)} total open positions for {symbol}.")
    return positions


def close_all_trades(opposite_type, symbol="XAUUSD"):
    close_type = mt5.ORDER_TYPE_SELL if opposite_type == "BUY" else mt5.ORDER_TYPE_BUY
    target_position_type = (
        mt5.POSITION_TYPE_BUY if opposite_type == "SELL" else mt5.POSITION_TYPE_SELL
    )
    positions = mt5.positions_get(symbol=symbol)
    if not positions:
        print(f"📭 No open positions to close for {symbol}")
        return

    for pos in positions:
        if pos.type != target_position_type:
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
            "comment": "Close on signal flip",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
            "position": pos.ticket,
        }

        result = mt5.order_send(request)
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            print(f"✅ Closed position #{pos.ticket} at price {price}")
            close_trade(
                order_id=pos.ticket, close_price=price, reason="Mass Close - New Signal"
            )
        else:
            print(f"❌ Failed to close position #{pos.ticket}: {result.comment}")


def close_one_trade(symbol, target_type):
    positions = mt5.positions_get(symbol=symbol)
    if not positions:
        print("⚠️ No open positions found.")
        return False

    for pos in positions:
        if pos.type != target_type:
            continue

        close_type = (
            mt5.ORDER_TYPE_SELL
            if target_type == mt5.POSITION_TYPE_BUY
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
            "comment": "Auto-close one trade",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
            "position": pos.ticket,
        }

        result = mt5.order_send(request)
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            print(f"✅ Closed position #{pos.ticket} at {price:.2f}")
            close_trade(
                order_id=pos.ticket,
                close_price=price,
                reason="Trend Reversal - Signal Flip",
            )
            return True
        else:
            print(f"❌ Failed to close #{pos.ticket}: {result.comment}")
            return False

    print("⚠️ No matching trade to close.")
    return False

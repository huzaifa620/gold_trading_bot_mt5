import MetaTrader5 as mt5
from MetaTrader5 import copy_rates_from_pos, TIMEFRAME_M1

def initialize_mt5(login: int, password: str, server: str) -> bool:
    return mt5.initialize(server=server, login=login, password=password)

def shutdown_mt5():
    mt5.shutdown()

def get_gold_price():
    try:
        symbol = "XAUUSD"
        tick = mt5.symbol_info_tick(symbol)._asdict()
        print(f"Current tick for {symbol}: {tick}")
        return tick['ask'] if tick else None
    except Exception as e:
        print(f"Error getting gold price: {e}")
        return None

def place_order(symbol: str, action: str, volume: float = 0.1):
    order_type = mt5.ORDER_TYPE_BUY if action == "BUY" else mt5.ORDER_TYPE_SELL
    price = mt5.symbol_info_tick(symbol).ask if action == "BUY" else mt5.symbol_info_tick(symbol).bid

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": order_type,
        "price": price,
        "deviation": 20,
        "magic": 234000,
        "comment": f"gold_{action.lower()}",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    return mt5.order_send(request)


def fetch_price_history(symbol="XAUUSD", count=100, timeframe=TIMEFRAME_M1):
    """
    Fetch historical close prices for the given symbol and timeframe.
    Returns a list of closing prices.
    """
    rates = copy_rates_from_pos(symbol, timeframe, 0, count)
    if rates is None:
        print(f"❌ Failed to fetch historical rates for {symbol}")
        return []
    return [bar['close'] for bar in rates]


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
        "currency": account.currency
    }

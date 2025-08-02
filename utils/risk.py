def calculate_lot_size(sl_points: float, price: float, balance: float, risk_dollars: float = 5.0) -> float:
    """
    Calculates lot size based on a fixed dollar risk per trade.

    Parameters:
    - sl_points: The stop-loss distance in price (e.g., $10)
    - price: Current price of XAUUSD
    - balance: Account balance (not directly used here but can be in future)
    - risk_dollars: Max amount to risk per trade (default $5)

    Returns:
    - volume (lot size) between 0.01 and 1.0
    """
    if sl_points <= 0:
        return 0.01  # default minimum if invalid SL

    # For XAUUSD, 1 lot = 100 oz → $1 move = $100 per lot
    dollars_per_lot_per_point = 100
    volume = risk_dollars / (sl_points * dollars_per_lot_per_point)

    # Clamp between 0.01 and 1.0 lots
    return round(min(max(volume, 0.01), 1.0), 2)

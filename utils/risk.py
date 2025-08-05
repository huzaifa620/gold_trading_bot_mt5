import math

def calculate_lot_size(sl_points, risk_dollars=5.0):
    if sl_points <= 0:
        return 0.01  # fallback safety minimum

    # Raw unrounded lot size
    raw_lot = risk_dollars / (sl_points * 100)

    # Round down to nearest 0.01 to stay under max risk
    lot = math.floor(raw_lot * 100) / 100

    # Enforce broker limits (min 0.01, max 1.0 lot)
    lot = max(min(lot, 1.0), 0.01)

    return round(lot, 2)

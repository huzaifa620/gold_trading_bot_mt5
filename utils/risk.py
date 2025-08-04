def calculate_lot_size(sl_points, risk_dollars=5.0):
    if sl_points <= 0:
        return 0.01

    volume = risk_dollars / (sl_points * 100)
    return round(min(max(volume, 0.01), 1.0), 2)

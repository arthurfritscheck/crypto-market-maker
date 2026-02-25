class InventoryStrategy:
    def __init__(self):
        self.symbol = 'BTC-PERPETUAL'
        self.position_size = 1000
        self.spread = 0.0002       # 0.02% spread
        self.max_inventory = 50000
        self.skew_factor = 0.00005 # price skew per $1 of inventory
        self.price_update_threshold = 1.0 # only update quotes if mid-price moves > $1

    def calculate_quotes(self, current_inventory, mid_price):
        """Calculates fair value bids and asks based on inventory skew."""
        price_skew = current_inventory * self.skew_factor
        target_bid = mid_price * (1 - self.spread) - price_skew
        target_ask = mid_price * (1 + self.spread) - price_skew
        
        return target_bid, target_ask, price_skew
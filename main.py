import asyncio
import ccxt.pro as ccxt
import os
import time
from dotenv import load_dotenv
from database import DatabaseLogger
from strategy import InventoryStrategy

class ExecutionEngine:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv('DERIBIT_API_KEY')
        self.api_secret = os.getenv('DERIBIT_API_SECRET')
        
        # instantiate modules
        self.strategy = InventoryStrategy()
        self.db = DatabaseLogger()
        
        # state management
        self.last_mid_price = 0.0
        self.current_inventory = 0
        self.base_currency = self.strategy.symbol.split('-')[0] # splits 'BTC-PERPETUAL' into ['BTC', 'PERPETUAL'] and grabs the first part

        # PnL trackers
        self.initial_equity = None
        self.cumulative_pnl = 0.0
        self.unrealized_pnl = 0.0
        
        self.exchange = ccxt.deribit({
            'apiKey': self.api_key,
            'secret': self.api_secret,
            'enableRateLimit': True,
        })
        self.exchange.set_sandbox_mode(True)

    async def log_trades_background_task(self):
        """Runs concurrently to fetch and pass trades to the database module."""
        while True:
            try:
                await asyncio.sleep(30)
                since_time = self.exchange.milliseconds() - (60 * 60 * 1000)
                trades = await self.exchange.fetch_my_trades(self.strategy.symbol, since=since_time, limit=50)
                
                # pass the raw data to the database module
                new_count = self.db.log_trades(trades)
                
                if new_count > 0:
                    print(f"[DB LOG] Logged {new_count} new trade(s)")
            except Exception as e:
                print(f"[DB ERROR] Logging error: {e}")

    async def watch_fills_background_task(self):
        "Updates inventory in real-time whenever a fill is detected"
        while True:
            try:
                trades = await self.exchange.watch_my_trades(self.strategy.symbol)

                for trade in trades:
                    if trade['side'] == 'buy':
                        self.current_inventory += trade['amount']
                    else:
                        self.current_inventory -= trade['amount']
                    
                    print(f"[FILL] {trade['side'].upper()} {trade['amount']} @ {trade['price']} | New inventory: {self.current_inventory}")
        
            except Exception as e:
                print(f"[FILLS ERROR] {e}")
                await asyncio.sleep(1)

    async def update_inventory_background_task(self):
        """Reconciles inventory with exchange every 5 seconds as fallback""" # in case of missed fills, partial fills, starting state with open position from previous sessions
        while True:
            await asyncio.sleep(5)
            try:
                # fetch current position (inventory)
                positions = await self.exchange.fetch_positions([self.strategy.symbol])
                
                if len(positions) > 0:
                    self.current_inventory = positions[0]['contracts'] if len(positions) > 0 else 0
                    self.unrealized_pnl = positions[0].get('unrealizedPnl', 0.0)
                else:
                    self.current_inventory = 0
                    self.unrealized_pnl = 0.0

                # fetch account balance (PnL)
                balance = await self.exchange.fetch_balance()
                if self.base_currency in balance:
                    current_total_equity = balance[self.base_currency]['total']
                    if self.initial_equity is None:
                        self.initial_equity = current_total_equity
                    self.cumulative_pnl = current_total_equity - self.initial_equity
                else:
                    self.cumulative_pnl = 0.0
            
            except Exception as e:
                print(f"[API ERROR] failed to fetch inventory/balance: {e}")

    async def execute_quotes(self, target_bid, target_ask):
        params = {'postOnly': True}
        orders = []

        if self.current_inventory < self.strategy.max_inventory:
            orders.append(self.exchange.create_limit_buy_order(self.strategy.symbol, self.strategy.position_size, target_bid, params))
        
        if self.current_inventory > -self.strategy.max_inventory:
            orders.append(self.exchange.create_limit_sell_order(self.strategy.symbol, self.strategy.position_size, target_ask, params))

        if orders:
            try:
                await asyncio.gather(*orders)
            except Exception as e:
                print(f"[EXECUTION ERROR] Order failed: {e}")

    async def run(self):
        if not self.api_key or not self.api_secret:
            print("ERROR: API Keys not found in .env file.")
            return
        
        print(f"--- Starting Engine on {self.strategy.symbol} ---")
        self.db.init_db()
        asyncio.create_task(self.log_trades_background_task())
        asyncio.create_task(self.watch_fills_background_task())
        asyncio.create_task(self.update_inventory_background_task())

        try:
            await self.exchange.cancel_all_orders(self.strategy.symbol)

            while True: 
                ticker = await self.exchange.watch_ticker(self.strategy.symbol)
                mid_price = (ticker['bid'] + ticker['ask']) / 2

                if abs(mid_price - self.last_mid_price) >= self.strategy.price_update_threshold:
                    start_time = time.perf_counter()

                    # ask the Strategy module for the quotes
                    target_bid, target_ask, price_skew = self.strategy.calculate_quotes(self.current_inventory, mid_price)

                    upnl_usd = self.unrealized_pnl * mid_price
                    cumulative_usd = self.cumulative_pnl * mid_price

                    print(f"\n--- Market Move Detected ---")
                    print(f"Session PnL: {self.cumulative_pnl:+.5f} {self.base_currency} (${cumulative_usd:+.2f})")
                    print(f"Open uPnL:   {self.unrealized_pnl:+.5f} {self.base_currency} (${upnl_usd:+.2f})")
                    print(f"Inv: {self.current_inventory} | Mid: {mid_price:.2f} | Skew: {price_skew:.2f}")
                    print(f"Qt: Bid {target_bid:.2f} | Ask {target_ask:.2f}")

                    await asyncio.gather(
                        self.exchange.cancel_all_orders(self.strategy.symbol),
                        self.execute_quotes(target_bid, target_ask)
                    )

                    self.last_mid_price = mid_price
                    print(f"Execution Latency: {(time.perf_counter() - start_time) * 1000:.2f} ms")

        except asyncio.CancelledError:
            print("\nShutting down now...")
        except Exception as e:
            print(f"\nERROR in main loop: {e}")
        finally:
            print("Closing exchange connections...")
            await self.exchange.cancel_all_orders(self.strategy.symbol)
            await self.exchange.close()

if __name__ == "__main__":
    bot = ExecutionEngine()
    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        print("\nEngine stopped manually by user.")
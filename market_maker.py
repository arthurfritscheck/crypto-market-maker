import asyncio
import ccxt.async_support as ccxt
import os
from dotenv import load_dotenv

# load key and secrets
load_dotenv()

API_KEY = os.getenv('DERIBIT_API_KEY')
API_SECRET = os.getenv('DERIBIT_API_SECRET')
SYMBOL = 'BTC-PERPETUAL'

# CONFIGURATION
POSITION_SIZE = 1000
SPREAD = 0.0002 # 0.02% spread
MAX_INVENTORY = 50000
SKEW_FACTOR = 0.00005 # how aggresively we move price per $1 of inventory 

async def run_bot():
    if not API_KEY or not API_SECRET:
        print("ERROR: API Keys not found.")
        return
    
    print(f"--- Starting market maker on {SYMBOL} ---")
    print("Press Ctrl+C to stop.")

    # Initialize exchange
    exchange = ccxt.deribit({
        'apiKey': API_KEY,
        'secret': API_SECRET,
        'enableRateLimit': True,
    })
    exchange.set_sandbox_mode(True) # connect to testnet

    try:
        while True: 
            # cancel all existing orders
            await exchange.cancel_all_orders(SYMBOL)

            # fetch market data and position
            ticker = await exchange.fetch_ticker(SYMBOL)
            balance = await exchange.fetch_balance()

            # get current invnetory in USDT
            positions = await exchange.fetch_positions([SYMBOL])
            current_inventory = 0
            if len(positions) > 0: 
                current_inventory = positions[0]['contracts']

            best_bid = ticker['bid']
            best_ask = ticker['ask']
            mid_price = (best_bid + best_ask) / 2

            # calculate skew --> skew = inventory * skew factor

            price_skew = current_inventory * SKEW_FACTOR

            # calculate skewed quotes
            target_bid = mid_price * (1 - SPREAD) - price_skew
            target_ask = mid_price * (1 + SPREAD) - price_skew

            print(f"Inv: {current_inventory} | Mid: {mid_price:.2f} | Skew: {price_skew:.2f}")
            print(f"Qt: Bid {target_bid:.2f} | Ask {target_ask:.2f}")

            # risk checks
            params = {'postOnly': True}
            orders_to_place = []

            # only buy if not max long
            if current_inventory < MAX_INVENTORY:
                orders_to_place.append(exchange.create_limit_buy_order(SYMBOL, POSITION_SIZE, target_bid, params))
            else:
                print("Max long inventory! Stopping buys now.")
            
            # only sell if not max short
            if current_inventory > -MAX_INVENTORY:
                orders_to_place.append(exchange.create_limit_sell_order(SYMBOL, POSITION_SIZE, target_ask, params))
            else:
                print("Max short inventory! Stopping sells now.")

            # execute safe orders
            if orders_to_place:
                try:
                    await asyncio.gather(*orders_to_place) # unpack list
                except Exception as e:
                    print(f"Order error: {e}")

            await asyncio.sleep(5)

    except KeyboardInterrupt:
        print("\nStopping bot gracefully...")

    except Exception as e:
        print(f"\nCRITICAL ERROR: {e}")
    finally:
        await exchange.close()

if __name__ == "__main__":
    asyncio.run(run_bot())
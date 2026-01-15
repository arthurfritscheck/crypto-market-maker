import asyncio
import ccxt.async_support as ccxt
import os
from dotenv import load_dotenv

# load key and secrets
load_dotenv()

API_KEY = os.getenv('DERIBIT_API_KEY')
API_SECRET = os.getenv('DERIBIT_API_SECRET')
SYMBOL = 'BTC-PERPETUAL'
POSITION_SIZE = 10000
SPREAD = 0.0005

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

            # get real time price
            ticker = await exchange.fetch_ticker(SYMBOL)
            best_bid = ticker['bid']
            best_ask = ticker['ask']
            mid_price = (best_bid + best_ask) / 2

            # calculate our prices
            my_bid_price = mid_price * (1 - SPREAD)
            my_ask_price = mid_price * (1 + SPREAD)

            print(f"Stats: Market Mid: {mid_price:.2f} | My Spread: {(my_ask_price - my_bid_price):.2f}")

            params = {'postOnly': True}

            # use asyncio.gather to send both orders at the exact same time
            try:
                await asyncio.gather(
                    exchange.create_limit_buy_order(SYMBOL, POSITION_SIZE, my_bid_price, params),
                    exchange.create_limit_sell_order(SYMBOL, POSITION_SIZE, my_ask_price, params)
                )
                print(f" -> ORDERS PLACED: Buy @ {my_bid_price:.2f} | Sell @ {my_ask_price:.2f}")
            except Exception as e:
                print(f" -> Order failed: {e}")

            print("-" * 30)

            await asyncio.sleep(5)

    except KeyboardInterrupt:
        print("\nStopping bot gracefully...")

    except Exception as e:
        print(f"\nCRITICAL ERROR: {e}")
    finally:
        await exchange.close()

if __name__ == "__main__":
    asyncio.run(run_bot())
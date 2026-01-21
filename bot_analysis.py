import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# CONFIG
DB_FILE = "trading_data.db"

def analyze():
    # load data
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM trades ORDER BY timestamp ASC", conn)
    conn.close()

    if df.empty:
        print("No trades found in database!")
        return

    # process data
    # convert milliseconds to readable date
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    # calculate directional size (buy = +size, sell = -size)
    df['signed_amount'] = df.apply(lambda x: x['amount'] if x['side'].lower() == 'buy' else -x['amount'], axis=1)
    
    # calculate cumulative inventory (holdings over time)
    df['inventory'] = df['signed_amount'].cumsum()

    # plotting
    print(f"Analyzing {len(df)} trades...")
    
    plt.figure(figsize=(12, 6))
    
    # draw inventory line
    plt.plot(df['datetime'], df['inventory'], label='Inventory (USD)', color='#1f77b4', linewidth=2)
    
    # add a zero line (the target)
    plt.axhline(y=0, color='r', linestyle='--', alpha=0.5, label='Target (0)')
    
    # formatting
    plt.title("Market Maker Performance: Inventory Mean Reversion", fontsize=14)
    plt.ylabel("Inventory Position ($)", fontsize=12)
    plt.xlabel("Time", fontsize=12)
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # time formatting
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    plt.gcf().autofmt_xdate()

    # save chart
    plt.savefig("inventory_chart.png")
    print("Success: Chart saved as 'inventory_chart.png'")

if __name__ == "__main__":
    analyze()
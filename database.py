import sqlite3

class DatabaseLogger:
    def __init__(self, db_file='trading_data.db'):
        self.db_file = db_file

    def init_db(self):
        """Set up the SQLite database to track trade executions."""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id TEXT PRIMARY KEY,
                timestamp INTEGER,
                symbol TEXT,
                side TEXT,
                price REAL, 
                amount REAL, 
                fee REAL, 
                liquidity TEXT
            )
        ''')
        conn.commit()
        conn.close()
        print(f"----- Database '{self.db_file}' initialized -----")

    def log_trades(self, trades):
        """Receives a list of trades from the engine and saves them to the DB."""
        if not trades:
            return 0

        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        new_count = 0

        for trade in trades:
            trade_data = (
                trade['id'],          
                trade['timestamp'],
                trade['symbol'],
                trade['side'],        
                trade['price'],
                trade['amount'],
                trade['fee']['cost'] if trade.get('fee') else 0,
                trade['takerOrMaker'] 
            )

            cursor.execute('''
                INSERT OR IGNORE INTO trades
                (id, timestamp, symbol, side, price, amount, fee, liquidity)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?)
            ''', trade_data)

            if cursor.rowcount > 0:
                new_count += 1

        conn.commit()
        conn.close()
        return new_count
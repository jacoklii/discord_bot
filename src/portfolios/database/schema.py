import sqlite3 as sq

db_path = 'portfolio.db'
def create_portfolio_schema(db_path):
    conn = sq.connect(db_path)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS portfolios (
                portfolio_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                initial_balance REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

    conn.commit()
    cur.close()
    conn.close()

def create_transaction_schema(db_path):
    conn = sq.connect(db_path)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
                transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                portfolio_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                operation TEXT NOT NULL,
                shares INTEGER NOT NULL,
                price_per_share REAL NOT NULL,
                total_price REAL NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (portfolio_id) REFERENCES portfolios(portfolio_id)
                )
            ''')

    conn.commit()
    cur.close()
    conn.close()

def create_balance_schema(db_path):
    conn = sq.connect(db_path)
    cur = conn.cursor()

    cur.execute('''
                CREATE TABLE IF NOT EXISTS balances (
                balance_id INTEGER PRIMARY KEY AUTOINCREMENT,
                portfolio_id INTEGER NOT NULL,
                balance REAL NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (portfolio_id) REFERENCES portfolios(portfolio_id)
                )
            ''')

    conn.commit()
    cur.close()
    conn.close()


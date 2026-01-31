import sqlite3 as sq

def create_database_schema(conn):
    cur = conn.cursor()

    try:
        portfolio_schema = '''
                    CREATE TABLE IF NOT EXISTS portfolios (
                    portfolio_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    initial_balance REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                '''

        cur.execute(portfolio_schema)

        transaction_schema = '''
                    CREATE TABLE IF NOT EXISTS transactions (
                    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    portfolio_id INTEGER NOT NULL,
                    symbol TEXT NOT NULL,
                    sector TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    shares INTEGER NOT NULL,
                    price_per_share REAL NOT NULL,
                    total_price REAL NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (portfolio_id) REFERENCES portfolios(portfolio_id)
                    )
                '''

        cur.execute(transaction_schema)

        balance_schema = '''
                    CREATE TABLE IF NOT EXISTS balances (
                    balance_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    portfolio_id INTEGER NOT NULL,
                    balance REAL NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (portfolio_id) REFERENCES portfolios(portfolio_id)
                    )
                '''

        cur.execute(balance_schema)

        conn.commit()
    except sq.Error as e:
        return f'Error creating database schema: {e}'
    except Exception as e:
        return f'Unexpected error: {e}'

    cur.close()


import os
import sqlite3 as sq

DB_DIR = 'src/portfolios/database'
PORTFOLIO_DB_DIR = os.path.join(DB_DIR, 'portfolios.db')

os.makedirs(DB_DIR, exist_ok=True)

def get_portfolio_connection():
    """Get connetion to database."""
    conn = sq.connect(PORTFOLIO_DB_DIR)
    
    return conn

def initialize_database():
    """Initialize the database with schema and return a connection."""
    from src.portfolios.database.schema import create_database_schema
    
    conn = get_portfolio_connection()
    create_database_schema(conn)
    return conn




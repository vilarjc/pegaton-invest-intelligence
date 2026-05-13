import os
import sqlite3
import requests
from dotenv import load_dotenv
import logging

load_dotenv()
API_KEY = os.getenv('TWELVEDATA_API_KEY')

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Symbols to track: usar SPY como proxy del S&P 500, EUR/USD, BTC/USD
SYMBOLS = {
    'SPY': 'SPY',
    'EUR/USD': 'EUR/USD',
    'BTC/USD': 'BTC/USD',
}

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'pegaton.db')

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS precios_ohlcv (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            simbolo TEXT NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume REAL,
            UNIQUE(timestamp, simbolo)
        )
    ''')
    conn.commit()
    conn.close()
    logger.info(f"DB ready at {DB_PATH}")

def fetch_and_store(symbol, td_symbol):
    url = f'https://api.twelvedata.com/time_series?symbol={td_symbol}&interval=1day&outputsize=1&apikey={API_KEY}'
    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code != 200:
            logger.error(f"HTTP {resp.status_code} for {td_symbol}")
            return
        data = resp.json()
        if data.get('status') == 'error':
            logger.error(f"API error for {td_symbol}: {data.get('message')}")
            return
        values = data.get('values')
        if not values:
            logger.warning(f"No values for {td_symbol}")
            return
        v = values[0]
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            INSERT OR REPLACE INTO precios_ohlcv (timestamp, simbolo, open, high, low, close, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            v['datetime'], symbol,
            float(v['open']), float(v['high']), float(v['low']), float(v['close']),
            float(v.get('volume', 0) or 0)
        ))
        conn.commit()
        conn.close()
        logger.info(f"{symbol}: {v['datetime']} close={v['close']}")
    except Exception as e:
        logger.error(f"Error fetching {td_symbol}: {e}", exc_info=True)

def main():
    logger.info("Starting price ingestion…")
    init_db()
    for sym, td_sym in SYMBOLS.items():
        fetch_and_store(sym, td_sym)
    logger.info("Price ingestion done.")

if __name__ == "__main__":
    main()

"""Fetch 200 days of historical OHLCV data for all tracked symbols."""
import os, sqlite3, requests, time, logging
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv('TWELVEDATA_API_KEY')
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SYMBOLS_TD = {'SPY': 'SPY', 'EUR/USD': 'EUR/USD', 'BTC/USD': 'BTC/USD'}
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

def fetch_historical(td_symbol, outputsize=200):
    """Fetch historical daily data."""
    url = f'https://api.twelvedata.com/time_series?symbol={td_symbol}&interval=1day&outputsize={outputsize}&apikey={API_KEY}'
    resp = requests.get(url, timeout=20)
    if resp.status_code != 200:
        logger.error(f"HTTP {resp.status_code} for {td_symbol}")
        return []
    data = resp.json()
    if data.get('status') == 'error':
        logger.error(f"API error for {td_symbol}: {data.get('message')}")
        return []
    return data.get('values', [])

def store_data(symbol, values):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    inserted = 0
    for v in reversed(values):  # oldest first
        try:
            c.execute('''
                INSERT OR IGNORE INTO precios_ohlcv (timestamp, simbolo, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (v['datetime'], symbol,
                  float(v['open']), float(v['high']), float(v['low']), float(v['close']),
                  float(v.get('volume', 0) or 0)))
            inserted += 1
        except Exception as e:
            logger.warning(f"Error inserting {v.get('datetime')}: {e}")
    conn.commit()
    conn.close()
    return inserted

def main():
    logger.info("Fetching historical price data (200 days)...")
    init_db()
    for symbol, td_sym in SYMBOLS_TD.items():
        logger.info(f"Fetching {td_sym}...")
        values = fetch_historical(td_sym, 200)
        if values:
            count = store_data(symbol, values)
            logger.info(f"  {symbol}: {count} records stored")
        else:
            logger.warning(f"  {symbol}: no data")
        time.sleep(1)  # rate limit courtesy
    logger.info("Historical data ingestion complete.")

if __name__ == "__main__":
    main()

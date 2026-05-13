#!/usr/bin/env python3
"""Incremental price ingestion - only fetches data not yet in database."""
import os, sqlite3, requests, time, logging
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv('TWELVEDATA_API_KEY')
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SYMBOLS = {'SPY': 'SPY', 'EUR/USD': 'EUR/USD', 'BTC/USD': 'BTC/USD'}
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'pegaton.db')

def get_latest_date(symbol):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT MAX(timestamp) FROM precios_ohlcv WHERE simbolo = ?", (symbol,))
    row = c.fetchone()
    conn.close()
    return row[0] if row and row[0] else None

def store_data(symbol, values):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    inserted = 0
    for v in reversed(values):
        try:
            c.execute('INSERT OR IGNORE INTO precios_ohlcv (timestamp, simbolo, open, high, low, close, volume) VALUES (?,?,?,?,?,?,?)',
                (v['datetime'], symbol, float(v['open']), float(v['high']), float(v['low']), float(v['close']), float(v.get('volume',0) or 0)))
            inserted += 1
        except: pass
    conn.commit()
    conn.close()
    return inserted

def main():
    logger.info("Incremental price ingestion...")
    for symbol, td_sym in SYMBOLS.items():
        latest = get_latest_date(symbol)
        if latest:
            # Fetch since latest date minus 2 days (overlap for safety)
            start = (datetime.strptime(latest[:10], '%Y-%m-%d') - timedelta(days=2)).strftime('%Y-%m-%d')
            url = f'https://api.twelvedata.com/time_series?symbol={td_sym}&interval=1day&outputsize=500&apikey={API_KEY}'
        else:
            url = f'https://api.twelvedata.com/time_series?symbol={td_sym}&interval=1day&outputsize=200&apikey={API_KEY}'
        try:
            resp = requests.get(url, timeout=20)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('values'):
                    count = store_data(symbol, data['values'])
                    logger.info(f"  {symbol}: {count} nuevos registros")
            time.sleep(1)
        except Exception as e:
            logger.error(f"  {symbol}: {e}")
    logger.info("Incremental ingestion done.")

if __name__ == '__main__':
    main()

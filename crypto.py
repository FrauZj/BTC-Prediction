import yfinance as yf
from datetime import datetime, timedelta
import pandas as pd
import json
import os
import argparse
import sys

# Configuration
OUTPUT_FOLDER = "data"
JSON_FILENAME = "btc_prices.json"
MAX_DAYS = 30
VALID_INTERVALS = ['15m', '30m', '1h', '4h', '1d']


def fetch_and_save_btc_data(days=7, interval='1h'):
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    if days <= 0 or days > MAX_DAYS:
        print(f"Invalid days count. Max {MAX_DAYS}")
        return False

    if interval not in VALID_INTERVALS:
        print(f"Invalid interval. Valid: {', '.join(VALID_INTERVALS)}")
        return False

    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)

    ticker_btc = "BTC-USD"
    print(f"[Crypto] Fetching {ticker_btc} for last {days} days ({interval})...")

    try:
        data_btc = yf.download(
            ticker_btc,
            start=start_time.strftime('%Y-%m-%d'),
            end=end_time.strftime('%Y-%m-%d'),
            interval=interval,
            auto_adjust=True,
            progress=False
        )

        if data_btc.empty:
            print("[Crypto] Failed to download data (DataFrame empty).")
            return False

        # Format data for JSON
        vector_value = data_btc[['Close']].reset_index()
        vector_value.columns = ['time', 'price']

        # Handle timezone if present
        if vector_value['time'].dt.tz is not None:
            vector_value['time'] = vector_value['time'].dt.tz_convert(None)

        vector_value['time'] = vector_value['time'].dt.strftime('%Y-%m-%d %H:%M:%S')
        vector_value['price'] = vector_value['price'].round(2)
        vector_price = vector_value.to_dict('records')

        file_path = os.path.join(OUTPUT_FOLDER, JSON_FILENAME)

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(vector_price, f, ensure_ascii=False, indent=4)

        print(f"[Crypto] Saved {len(vector_price)} records to {file_path}")
        return True

    except Exception as e:
        print(f"[Crypto] Error: {e}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download historical BTC-USD prices")
    parser.add_argument('--days', type=int, default=7, help=f'Days to download (Max {MAX_DAYS})')
    parser.add_argument('--interval', type=str, default='1h', help=f'Interval: {", ".join(VALID_INTERVALS)}')

    args = parser.parse_args()

    success = fetch_and_save_btc_data(args.days, args.interval)
    if not success:
        sys.exit(1)
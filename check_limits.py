import ccxt
import os
from dotenv import load_dotenv

def check_limits():
    load_dotenv()
    symbol = os.getenv('SYMBOL', 'BNB/USDT')

    exchange = ccxt.binance({
        'options': {'defaultType': 'future'}
    })

    try:
        markets = exchange.load_markets()
        if symbol in markets:
            market = markets[symbol]
            print(f"--- Limits for {symbol} on Binance Futures ---")
            print(f"Minimum Amount (Coin): {market['limits']['amount']['min']}")
            print(f"Minimum Notional (USDT): {market['limits']['cost']['min']}")
            print(f"Amount Precision: {market['precision']['amount']}")
            print(f"Price Precision: {market['precision']['price']}")

            # Fetch current price to calculate real dollar minimum
            ticker = exchange.fetch_ticker(symbol)
            current_price = ticker['last']
            min_notional = market['limits']['cost']['min']
            min_amount_in_usdt = market['limits']['amount']['min'] * current_price

            print(f"Current Price: {current_price} USDT")
            print(f"Min Amount in USDT: {min_amount_in_usdt:.2f} USDT")
            print(f"Actual Min Order Size: {max(min_notional, min_amount_in_usdt):.2f} USDT")
        else:
            print(f"Symbol {symbol} not found.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_limits()

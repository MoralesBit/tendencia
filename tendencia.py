import time
import numpy as np
import requests
import pandas as pd
from binance.client import Client
import Telegram_bot as Tb

Pkey = ''
Skey = ''
client = Client(api_key=Pkey, api_secret=Skey)

def get_trading_symbols():
    """Obtiene la lista de símbolos de futuros de Binance que están disponibles para trading"""
    futures_info = client.futures_exchange_info()
    symbols = [symbol['symbol'] for symbol in futures_info['symbols'] if symbol['status'] == "TRADING"]
    coins_to_remove = [
        "DOGEUSDT", "AXSUSDT", "ETHBTC", "USDCUSDT", "BNBBTC", "ETHUSDT", 
        "BTCDOMUSDT", "BTCUSDT_230929", "XEMUSDT", "BLUEBIRDUSDT", 
        "ETHUSDT_231229", "DOGEUSDT", "LITUSDT", "ETHUSDT_230929", 
        "BTCUSDT_231229", "ETCUSDT"
    ]
    return [symbol for symbol in symbols if symbol not in coins_to_remove]

def calculate_indicators(symbol, interval):
    klines = client.futures_klines(symbol=symbol, interval=interval, limit=1000)
    df = pd.DataFrame(klines)
    if df.empty:
        return None
    df.columns = [
        'Open time', 'Open', 'High', 'Low', 'Close', 'Volume', 
        'Close time', 'Quote asset volume', 'Number of trades', 
        'Taker buy base asset volume', 'Taker buy quote asset volume', 'Ignore'
    ]
    df['Open time'] = pd.to_datetime(df['Open time'], unit='ms')
    df = df.set_index('Open time')

    df[['Open', 'High', 'Low', 'Close', 'Volume']] = df[['Open', 'High', 'Low', 'Close', 'Volume']].astype(float)

    df['ema200'] = df['Close'].ewm(span=200, adjust=False).mean()
    df['ema59'] = df['Close'].ewm(span=59, adjust=False).mean()

    df['dist_ema'] = df['ema200'] - df['ema59']
    df['dist_price'] = df['Close'] - df['ema200']

    # Calcular ROC manualmente
    period = 288
    df['roc'] = ((df['Close'] / df['Close'].shift(period)) - 1) * 100
    df['roc_long'] = np.where(df['roc'].shift(-1) > 5, 1, 0)
    df['roc_short'] = np.where(df['roc'].shift(-1) < -5, 1, 0)

    return df.tail(3)

def run_strategy():
    """Ejecuta la estrategia de trading para cada símbolo en la lista de trading"""
    symbols = get_trading_symbols()

    for symbol in symbols:
        print(symbol)

        try:
            df = calculate_indicators(symbol, interval=Client.KLINE_INTERVAL_5MINUTE)
            if df is None:
                continue

            print(df['dist_ema'].iloc[-2])
            print(df['dist_price'].iloc[-2])

            if df['roc_long'].iloc[-2] == 1:
                if df['dist_price'].iloc[-2] >= 2.6 and df['dist_ema'].iloc[-2] >= 0.4:
                    message = f"🟢 {symbol} \n💵 Precio: {df['Close'].iloc[-2]}"
                    Tb.telegram_send_message(message)

                    Tendencia_Long = {
                        "name": "FISHING LONG",
                        "secret": "0kivpja7tz89",
                        "side": "buy",
                        "symbol": symbol,
                        "open": {
                            "price": float(df['Close'].iloc[-2])
                        }
                    }
                    requests.post('https://hook.finandy.com/OVz7nTomirUoYCLeqFUK', json=Tendencia_Long)

            if df['roc_short'].iloc[-2] == 1:
                if df['dist_price'].iloc[-2] <= -2.6 and df['dist_ema'].iloc[-2] <= -0.4:
                    message = f"🔴 {symbol} \n💵 Precio: {df['Close'].iloc[-2]}"
                    Tb.telegram_send_message(message)

                    Tendencia_short = {
                        "name": "FISHING SHORT",
                        "secret": "azsdb9x719",
                        "side": "sell",
                        "symbol": symbol,
                        "open": {
                            "price": float(df['Close'].iloc[-2])
                        }
                    }
                    requests.post('https://hook.finandy.com/q-1NIQZTgB4tzBvSqFUK', json=Tendencia_short)

        except Exception as e:
            print(f"Error en el símbolo {symbol}: {e}")

while True:
    current_time = time.time()
    seconds_to_wait = 300 - current_time % 300
    time.sleep(seconds_to_wait)
    run_strategy()

import support_keys as keys
import datetime as datetime
import numpy as np
from binance.client import Client
import pandas as pd
import math

client = Client(api_key=keys.binance_api_key_out, api_secret=keys.binance_api_secret_out)

def spot_last_price():
    return pd.DataFrame(client.get_all_tickers())

def last_price():
    return pd.DataFrame(client.futures_ticker())

def spot_list():
    return pd.DataFrame(client.get_exchange_info()['symbols'])['symbol'].to_list()

def round_up(n, decimals=0):
    multiplier = 10 ** decimals
    return math.ceil(n * multiplier) / multiplier

def format_float(num):
    return np.format_float_positional(num, trim='-')

def futures_klines_df(symbol, kline_size, df):
    df_len = len(df)
    if df_len > 1:

        data_prev = df
        try:
            inicio = int(data_prev['timestamp'].iloc[-1].timestamp()*1000)+60*60*5*1000
        except:
            inicio = int(data_prev['timestamp'].iloc[-1])
        data_prev.drop(data_prev.tail(1).index, inplace=True)

    else:
        inicio = int((datetime(2020, 2, 1).timestamp())) * 1000

    klines = client.futures_klines(symbol=symbol, interval=kline_size, startTime=inicio)

    new_data = pd.DataFrame(klines,
                            columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time',
                                     'quote_av', 'trades', 'tb_base_av', 'tb_quote_av', 'ignore'])
    new_data['open'] = new_data['open'].astype(float)
    new_data['high'] = new_data['high'].astype(float)
    new_data['low'] = new_data['low'].astype(float)
    new_data['close'] = new_data['close'].astype(float)
    new_data['timestamp'] = pd.to_datetime(new_data['timestamp']-(5*60*60*1000),unit='ms')


    if df_len > 1:
        data = data_prev
        data = data.append(new_data)
        data.reset_index(inplace=True, drop=True)
    else:
        data = new_data

    return data
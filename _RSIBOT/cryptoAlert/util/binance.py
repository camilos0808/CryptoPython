import util.keys as keys
import datetime as datetime
from binance.client import Client
import pandas as pd
import math

client = Client(api_key=keys.api_bot, api_secret=keys.secret_bot)

# FUTURES UTIL


def futures_list():
    df = pd.DataFrame(client.futures_exchange_info()['symbols'])
    symbols = df.loc[df['contractType'] == 'PERPETUAL']['symbol'].tolist()
    return symbols


def futures_klines(symbol, kline_size):
    klines = client.futures_klines(symbol=symbol, interval=kline_size, limit=200)

    new_data = pd.DataFrame(klines,
                            columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time',
                                     'quote_av', 'trades', 'tb_base_av', 'tb_quote_av', 'ignore'])

    new_data['close'] = new_data['close'].astype(float)

    return new_data


def futures_balance():
    df = pd.DataFrame(client.futures_account_balance())
    df.set_index('asset', inplace=True)
    df['balance'] = df['balance'].astype(float)
    df['withdrawAvailable'] = df['withdrawAvailable'].astype(float)

    return df


def futures_open_trades():
    par = pd.DataFrame(client.futures_position_information())
    par.loc[:, 'unRealizedProfit'] = par.loc[:, 'unRealizedProfit'].astype(float)
    par.loc[:, 'positionAmt'] = par.loc[:, 'positionAmt'].astype(float)
    open = par[par.loc[:, 'unRealizedProfit'] != 0].copy()

    return open


# SPOT UTIL

def spot_list():
    df = pd.DataFrame(client.get_exchange_info()['symbols'])['symbol']

    df = df[(df.str.endswith('USDT')) & ((~df.str.contains('DOWN')) &
                                         (~df.str.contains('UP')) &
                                         (~df.str.contains('BEAR')) &
                                         (~df.str.contains('BULL')))].copy()

    return df


# a = spot_list()


def spot_klines(symbol, klines_size):
    klines = client.get_klines(symbol=symbol, interval=klines_size, limit=200)

    new_data = pd.DataFrame(klines,
                            columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time',
                                     'quote_av', 'trades', 'tb_base_av', 'tb_quote_av', 'ignore'])

    new_data['close'] = new_data['close'].astype(float)

    return new_data


def spot_balance():
    df = pd.DataFrame(client.get_account()['balances'])
    df.set_index('asset', inplace=True)
    df['free'] = df['free'].astype(float)
    df['locked'] = df['locked'].astype(float)

    return df


def spot_open_trades(df):
    df = df.loc[df['locked'] != 0].copy()
    return df


# MORE METHODS
def change_leverage(symbol, leverage):
    client.futures_change_leverage(leverage=leverage, symbol=symbol)


def margin_type(symbol, marginType):
    type = {
        0: 'CROSSED',
        1: 'ISOLATED'}
    type = type[marginType]
    try:
        client.futures_change_margin_type(symbol=symbol, marginType=type)
    except:
        pass


def symbol_info():
    symbol_info = client.futures_exchange_info()['symbols']
    df = pd.DataFrame(symbol_info)
    return df


def free_quantity():
    ffqu = float(client.futures_account_balance()[0]['balance'])

    return ffqu


def round_up(n, decimals=0):
    multiplier = 10 ** decimals
    return math.ceil(n * multiplier) / multiplier


def q_buy(symbol, symbol_info, price, usdt):
    pr = symbol_info[symbol_info['symbol'] == symbol]['quantityPrecision'].values[0]
    q_buy = float(usdt) / float(price)
    order_quantity = round_up(q_buy, pr)
    return order_quantity, order_quantity * float(price)


def buy_order(symbol, side, quantity, leverage):
    side_list = {
        1: 'BUY',
        -1: 'SELL'}
    side_c = side_list[side]
    order = client.futures_create_order(symbol=symbol, side=side_c, type='MARKET', quantity=quantity)
    id = order['orderId']
    order = client.futures_get_order(symbol=symbol, orderId=id)
    close = float(order['avgPrice'])
    usdt = float(order['cumQuote']) / leverage
    time_b = float(order['time'])

    return usdt, close, time_b

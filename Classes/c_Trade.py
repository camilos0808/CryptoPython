import support_keys as keys
from binance.client import Client
import math
import pandas as pd
import threading
import datetime as dt
from support_sendTGM import telegram_bot_sendtext_test
from Classes.c_BinanceWebSocket import BinanceWebSocket
import numpy as np
import matplotlib.pyplot as plt
from decimal import Decimal
from Classes.c_Symbol import Symbol
from os.path import join

client = Client(api_key=keys.binance_api_key_out, api_secret=keys.binance_api_secret_out)
side_d = {
    1: 'BUY',
    -1: 'SELL'}

''''
Auxiliary Methods
'''


def margin_type(symbol, marginType):
    type = {
        0: 'CROSSED',
        1: 'ISOLATED'}
    type = type[marginType]
    try:
        client.futures_change_margin_type(symbol=symbol, marginType=type)
    except:
        pass


def effective_trade_info_dict(exchange,order, oco=False):
    if oco:
        order_one = order['orderReports'][0]
        order_two = order['orderReports'][1]

        if order_one['type'].find('STOP') >= 0:
            stop_order = order_one
            maker_order = order_two
        else:
            stop_order = order_two
            maker_order = order_one

        stop_id = stop_order['orderId']
        maker_id = maker_order['orderId']
        maker_price = maker_order['price']
        price = stop_order['price']
        quantity = stop_order['origQty']
        stop_price = stop_order['stopPrice']

        return {
            'status': 'OPEN',
            'stopId': stop_id,
            'makerId': maker_id,
            'qty': quantity,
            'price': maker_price,
            'stopPrice': stop_price,
            'limitPrice': price}

    else:
        if exchange == 'SPOT':
            price = float(order['fills'][0]['price'])
            id = order['orderId']
            time = float(order['transactTime'])
            quantity = float(order['executedQty'])
            return {
                'entry': True,
                'orderId': id,
                'price': price,
                'quantity': quantity,
                'baseQty': quantity * price,
                'time': time,
                'order': order}
        else:
            price = float(order['avgPrice'])
            id = order['orderId']
            time = float(order['time'])
            quantity = float(order['executedQty'])
            return {
                'entry': True,
                'orderId': id,
                'price': price,
                'quantity': quantity,
                'baseQty': quantity * price,
                'time': time,
                'order': order}


class Futures_Trade:
    SIDE_DICT = {
        1: 'BUY',
        -1: 'SELL'}

    def __init__(self, side, symbol, leverage, trade_type, margin, **kwargs):

        self.symbol = Symbol(symbol)
        if not self.symbol.futures_exists():
            raise ValueError('not available in FUTURES')
        self.side = side
        self.margin = margin
        self.leverage = leverage
        self.quantity = self.quantity_init(kwargs)
        self.status = 'OPEN'
        self.ws_on = False
        self.trade_type = trade_type
        self.entry_info = []
        self.sell_info = []
        self.entry_time = dt.datetime.now()
        margin_type(symbol, margin)
        client.futures_change_leverage(leverage=self.leverage, symbol=self.symbol)

    def quantity_init(self, kwargs: dict):
        if 'quantity' in kwargs.keys():

            qty = kwargs['quantity']*self.leverage

        elif ('usdt' in kwargs.keys()) and ('lastPrice' in kwargs.keys()):
            base_quantity = kwargs['usdt']
            if type(kwargs['lastPrice']) != float:
                kwargs['lastPrice'] = float(kwargs['lastPrice'])

            qty = self.symbol.futures_correct_quantity(base_quantity*self.leverage / kwargs['lastPrice'])

        else:
            raise ValueError('Not possible to calculate %s quantity' % self.symbol.name)

        return qty

    def enter_trade(self, **kwargs):

        trade_type = self.trade_type
        if trade_type == 'LIMIT':
            order = client.futures_create_order(symbol=self.symbol, type=trade_type, side=self.SIDE_DICT[self.side],
                                                quantity=self.quantity, timeInForce='GTC',
                                                price=kwargs['price'])
        elif trade_type == 'MARKET':
            self.status = 'POSITION'
            order = client.futures_create_order(symbol=self.symbol, type=trade_type, side=self.SIDE_DICT[self.side],
                                                quantity=self.quantity)

        elif trade_type == 'STOP' | trade_type == 'TAKE_PROFIT_MARKET':
            order = client.futures_create_order(symbol=self.symbol, type=trade_type, side=self.SIDE_DICT[self.side],
                                                quantity=self.quantity, stopPrice=kwargs['stopPrice'],
                                                price=kwargs['price'])

        elif trade_type == 'STOP_MARKET' | trade_type == 'TAKE_PROFIT':
            self.status = 'POSITION'
            order = client.futures_create_order(symbol=self.symbol, type=trade_type, side=self.SIDE_DICT[self.side],
                                                stopPrice=kwargs['stopPrice'])

        elif trade_type == ' TRAILING_STOP_MARKET':
            order = client.futures_create_order(symbol=self.symbol, type=trade_type, side=self.SIDE_DICT[self.side],
                                                callbackRate=kwargs['callbackRate'])

        else:
            raise Exception('TRADE TYPE incorrecto')

        order = client.futures_get_order(orderId=order['orderId'], symbol=self.symbol)

        self.entry_info.append(effective_trade_info_dict('FUTURES',order))
        self.message()

    def start_websocket(self, price):

        if not self.ws_on:
            self.ws_on = True
            self.ws = BinanceWebSocket(symbol=self.symbol, timeframe='1h', wallet='FUTURES', price=price)
            p = threading.Thread(target=self.ws.ws.run_forever)
            p.start()

    def stop_websocket(self):
        if self.ws_on:
            self.ws.ws.close()
            self.ws_on = False

    def message(self):

        t = {
            1: 'LONG',
            -1: 'SHORT'}
        s = {
            1: '📈',
            -1: '📉'}
        msg = '🤑💰 TRADE ALERT 💰🤑 \n ---------------------------\n\n'
        wallet = '💡EXCHANGE: BINANCE FUTURES\n\n'
        coin = '🔣SYMBOL: {}\n\n'.format(self.symbol)
        type_str = '{}TYPE: {}\n\n'.format(s[self.side], t[self.side])
        price_str = '✅PRICE: {}\n\n'.format(self.entry_info[0]['price'])

        msg = msg + wallet + coin + type_str + price_str

        telegram_bot_sendtext_test(msg)

    def change_entry(self, new_entry):
        last_status = self.check_status()
        if last_status == 'OPEN':
            if self.trade_type == 'LIMIT':
                client.futures_cancel_order(symbol=self.symbol, orderId=self.id)
                order = client.futures_create_order(symbol=self.symbol, type=self.trade_type, side=side_d[self.side],
                                                    quantity=self.quantity, timeInForce='GTC',
                                                    price=new_entry)
                self.id = order['orderId']
                self.time = float(order['updateTime'])

            else:
                print('Not Running yet for that type of trade')

        else:
            print('POSITION ENTERED OR CLOSED')

    def set_take_profit_order(self, prc):

        tp_price = self.entry_info[0]['price'] * (1 + self.side * prc)
        correct_price = self.symbol.futures_correct_price(tp_price)
        order = client.futures_create_order(symbol=self.symbol, type='LIMIT', side=side_d[-1*self.side],
                                            quantity=self.quantity, timeInForce='GTC',price=correct_price)
        print('DONE')

    def check_status(self):
        if self.status == 'POSITION':
            positions = pd.DataFrame(client.futures_position_information())
            position = len(positions[(positions['positionAmt'].astype(float) == self.quantity) & (
                    positions['symbol'] == self.symbol)])
            if position == 0:
                self.status = 'CLOSED'
        elif self.status == 'OPEN':
            order = client.futures_get_order(orderId=self.id, symbol=self.symbol)
            if float(order['avgPrice']) != 0:
                self.status == 'OPEN'

        return self.status


class Spot_Trade:
    SIDE_DICT = {
        1: 'BUY',
        -1: 'SELL'}

    def __init__(self, symbol, side, trade_type, **kwargs):
        self.symbol = Symbol(symbol)
        self.quantity = self.quantity_init(kwargs)
        self.side = side
        self.status = 'OPEN'
        self.ws_on = False
        self.trade_type = trade_type
        self.entry_info = []
        self.sell_info = []
        self.entry_time = dt.datetime.now()

    def quantity_init(self, kwargs: dict):
        if 'quantity' in kwargs.keys():

            qty = kwargs['quantity']

        elif ('usdt' in kwargs.keys()) and ('lastPrice' in kwargs.keys()):

            if self.symbol.name[-1] == 'C':

                if 'BTCUSDT_lp' in kwargs.keys():
                    self.priceBTC = kwargs['BTCUSDT_lp']
                    btc_tb = kwargs['usdt'] / kwargs['BTCUSDT_lp']
                    base_quantity = btc_tb
                else:
                    raise ValueError('%s needs BTCUSDT last price to calculate quantity of trade' % self.symbol.name)
            elif self.symbol.name[-1] == 'T':

                self.priceBTC = kwargs['lastPrice']

                base_quantity = kwargs['usdt']

            else:
                raise ValueError('Not possible to calculate %s quantity' % self.symbol.name)

            if type(kwargs['lastPrice']) != float:
                kwargs['lastPrice'] = float(kwargs['lastPrice'])

            qty = self.symbol.spot_correct_quantity(base_quantity / kwargs['lastPrice'])

        else:
            raise ValueError('Not possible to calculate %s quantity' % self.symbol.name)

        return qty

    def enter_trade(self, **kwargs):

        if self.trade_type == 'LIMIT':
            if isinstance(kwargs['price'], float):

                crc_prc = self.symbol.spot_correct_price(kwargs['price'])
            else:
                crc_prc = self.symbol.spot_correct_price(float(kwargs['price']))

            order = client.create_order(symbol=self.symbol, type=self.trade_type, side=self.SIDE_DICT[self.side],
                                        quantity=self.quantity, timeInForce='GTC', price=crc_prc)

        elif self.trade_type == 'MARKET':
            self.status = 'POSITION'
            try:
                order = client.create_order(symbol=self.symbol, type=self.trade_type, side=self.SIDE_DICT[self.side],
                                            quantity=self.quantity)
            except Exception as e:
                print(e)
                print(self.symbol)
                print(dt.datetime.now())
                self.custom_message('Error on buying %s' % self.symbol)
                exit()

            self.entry_info.append(effective_trade_info_dict('SPOT',order))
            self.message()

    def start_websocket(self, price):

        if not self.ws_on:
            self.ws_on = True
            self.ws = BinanceWebSocket(symbol=self.symbol, timeframe='1h', wallet='SPOT', price=price)
            p = threading.Thread(target=self.ws.ws.run_forever)
            p.start()

    def stop_websocket(self):
        if self.ws_on:
            self.ws.ws.close()
            self.ws_on = False

    def custom_message(self, message):

        telegram_bot_sendtext_test(message)

    def message(self):

        msg = '🤑💰 TRADE ALERT 💰🤑 \n ------------------------\n\n'
        wallet = '💡EXCHANGE: BINANCE SPOT\n\n'
        coin = '🔣SYMBOL: {}\n\n'.format(self.symbol)
        price_str = '✅PRICE: {}\n\n'.format(self.entry_info[0]['price'])
        # usdt_str = '💸USDT: {}\n\n'.format(round(self.usdt, 2))

        msg = msg + wallet + coin + price_str  # + usdt_str

        telegram_bot_sendtext_test(msg)

    def OCO_order(self, qty, maker_price, stop_price, slprice):

        order = client.create_oco_order(symbol=self.symbol, side=self.SIDE_DICT[-1 * self.side], quantity=qty,
                                        price=maker_price,
                                        stopPrice=stop_price, stopLimitPrice=slprice, stopLimitTimeInForce='GTC')
        return order

    def scaling_correction(self, qty_list, prc_list, st):

        if len(qty_list) != len(prc_list):
            raise TypeError('list of different Size')

        price_sp = self.symbol.spot_correct_price(self.entry_info[0]['price'] * (1 - self.side * st))
        price_sl = self.symbol.spot_correct_price(self.entry_info[0]['price'] * (1 - self.side * st))

        qty = np.array(qty_list) * float(self.quantity)
        prc = (1 + np.array(prc_list)) * float(self.entry_info[0]['price'])
        qty_corrected = np.array(list(map(self.symbol.spot_correct_quantity, qty)))
        qty_calc = list(map(float, qty_corrected))
        if sum(qty_calc) != float(self.quantity):
            qty_corrected[-1] = float(Decimal(self.quantity.__str__()) - Decimal(sum(qty_calc[:-1]).__str__()))
            qty_calc = list(map(float, qty_corrected))
        prc_corrected = np.array(list(map(self.symbol.spot_correct_price, prc)))

        min_qty = float(self.symbol.spot_min_quantity(min(float(price_sl), float(price_sp))))

        if not all(np.array(qty_calc) >= min_qty):
            raise ValueError('STOP LOSS ORDER BELOW MIN_NOMINAL')

        return [[price_sl, price_sp, prc_corrected[i], qty_corrected[i]] for i in range(prc_corrected.__len__())]

    def set_scaling_OCO_sell(self, scal_obj):

        for scal_odr in scal_obj:
            order = self.OCO_order(scal_odr[3], scal_odr[2], scal_odr[1], scal_odr[0])

            self.sell_info.append(effective_trade_info_dict('SPOT',order, oco=True))

        print('DONE')

    def init_scaling_OCO_sell(self):

        number_entries = self.sell_info.__len__()
        current_sell_index = 0

        while True:
            current_sell_id = self.sell_info[current_sell_index]['makerId']
            status = self.check_status(current_sell_id)
            if status == 'FILLED':
                current_sell_index += 1
                index_left = [i for i in range(current_sell_index, number_entries)]
                if len(index_left) > 0:
                    for i in index_left:
                        cancel_id = self.sell_info[i]['makerId']
                        client.cancel_order(symbol=self.symbol.name, orderId=cancel_id)

                        qty = self.sell_info[i]['qty']
                        maker_price = self.sell_info[i]['price']
                        new_sp = (float(self.sell_info[i - 1]['price']) - float(self.entry_info[0]['price'])) * 0.6 \
                                 + float(self.entry_info[0]['price'])
                        sp = self.symbol.spot_correct_price(new_sp)
                        sl = sp

                        order = self.OCO_order(qty, maker_price, sp, sl)
                        self.sell_info[i] = effective_trade_info_dict(order, oco=True)

                else:
                    break
            elif status == 'CANCELED':
                break

    def change_entry(self, new_entry):
        last_status = self.check_status()
        if last_status == 'OPEN':
            if self.trade_type == 'LIMIT':
                client.cancel_order(symbol=self.symbol, orderId=self.id)
                order = client.create_order(symbol=self.symbol, type=self.trade_type, side=self.SIDE_DICT[self.side],
                                            quantity=self.quantity, timeInForce='GTC',
                                            price=new_entry)
                self.id = order['orderId']
                self.time = float(order['updateTime'])

            else:
                print('Not Running yet for that type of trade')

        else:
            print('POSITION ENTERED OR CLOSED')

    def check_status(self, id):
        order = client.get_order(symbol=self.symbol.name, orderId=id)
        status = order['status']

        return status

    def market_sell(self):
        h = input('y/n')
        if h == 'y':
            order = client.create_order(symbol=self.symbol, side=self.SIDE_DICT[-1 * self.side], type='MARKET',
                                        quantity=self.quantity)
            print('done')
            self.sell_info.append(effective_trade_info_dict('SPOT',order))

    def set_take_profit_order(self, prc):
        tp_price = self.entry_info[0]['price'] * (1 + self.side * prc)
        correct_price = self.symbol.spot_correct_price(tp_price)
        order = client.create_order(symbol=self.symbol, type='LIMIT', side=-1 * self.SIDE_DICT[self.side],
                                    quantity=self.quantity, timeInForce='GTC', price=correct_price)

# symbol = 'ETHBTC'
# usdt = 30
# side = 1
# df = pd.DataFrame(client.get_all_tickers())
# df.set_index('symbol', inplace=True)
# lastPrice = float(df.at[symbol, 'price'])
# BTC_lp = float(df.at['BTCUSDT', 'price'])
# a = Spot_Trade(symbol=symbol, side=side, trade_type='MARKET', usdt=usdt, lastPrice=lastPrice, BTCUSDT_lp=BTC_lp)
# # a.enter_trade()
# # a.market_sell()
# a.entry_info.append({'price': lastPrice})
# scal_obj = a.scaling_correction([0.2, 0.4, 0.3], [0.04, 0.1, 0.2], 0.04)
# a.set_scaling_OCO_sell(scal_obj)
# a.init_scaling_OCO_sell()
# a = 1
symbol = 'BTCUSDT'
price = 55073.85
#
# trade = Futures_Trade(symbol=symbol, lastPrice=price, side=1, leverage=1,
#                                       trade_type='MARKET',
#                                       margin=1, usdt=5.5)
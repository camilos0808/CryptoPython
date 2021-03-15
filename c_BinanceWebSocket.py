import json, websocket
import datetime as dt
import numpy as np
from json import JSONEncoder


class BinanceWebSocket:

    def __init__(self, symbol, timeframe,wallet, price):
        self.symbol = symbol
        self.entry_price = price
        self.fprices = []
        self.start_time = dt.datetime.now()
        self.sell = False
        self.stop_time = dt.datetime.fromtimestamp(0)
        if wallet == 'FUTURES':
            self.socket = 'wss://fstream.binance.com/ws/{}@kline_{}'.format(self.symbol.lower(),timeframe)
        elif wallet == 'SPOT':
            self.socket = 'wss://stream.binance.com:9443/ws/{}@kline_{}'.format(self.symbol.lower(), timeframe)
        self.ws = websocket.WebSocketApp(self.socket,
                                         on_message=lambda ws, msg: self.on_message(ws, msg),
                                         on_close=lambda ws: self.on_close(ws))

    def on_message(self, ws, message):
        my_dict = json.loads(message)
        print(float(my_dict['k']['c']), my_dict['k']['x'])
        self.fprices.append([float(my_dict['k']['c']), my_dict['k']['x']])

    def on_close(self, ws):
        self.stop_time = dt.datetime.now()
        print('Stream Closed.')

    def to_JSON(self):
        return {
            'symbol': self.symbol, 'fprices': self.fprices, 'start_time': self.start_time.__str__(),
            'stop_time': self.stop_time.__str__(), 'socket': self.socket,
            self.__class__.__name__: True}

def decode_binancewebsocket(dct):
    if BinanceWebSocket.__name__ in dct:
        return BinanceWebSocket()


# class BinanceWebSocketEnconder(JSONEncoder):
#
#     def default(self, o: BinanceWebSocket):
#
#         return {
#             'price': o.price, 'symbol': o.symbol, 'side': o.side, 'fprices': o.fprices, 'leverage': o.leverage,
#             'start_time': o.start_time.__str__(), 'stop_time': o.stop_time.__str__(), 'socket': o.socket, o.__class__.__name__: True}

a = BinanceWebSocket('ETHUSDT','1h','SPOT',343)


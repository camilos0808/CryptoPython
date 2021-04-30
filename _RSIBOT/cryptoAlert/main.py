import ta.momentum as momentum
import datetime as dt
import pandas as pd
from util.telegram import telegram_bot_sendtext
import util.binance as bu




def RSI(klines):
    rsi = momentum.rsi(klines['close'], n=14)

    return rsi.iloc[-1], klines['close'].iloc[-1]


def activate_alert(symbol, RSI, db: dict):
    alert = True
    if RSI < 50: side = 1
    else: side = -1
    if symbol in db.keys():
        rsi_old = db[symbol]['RSI']

        if (dt.datetime.now() - db[symbol]['hora']).total_seconds() / 60 < 60:
            if side*(rsi_old-RSI) < 3:
                alert = False

    return alert


class Klines_db:
    def __init__(self, klines, exchange):
        if exchange == 'SPOT':
            self.symbols = bu.spot_list()
        elif exchange == 'FUTURES':
            self.symbols = bu.futures_list()
        else:
            raise ValueError('Exchange not valid')

        self.klines = klines
        self.exchange = exchange

    def get_klines(self, symbol):
        if self.exchange == 'SPOT':
            return bu.spot_klines(symbol, self.klines)
        else:
            return bu.futures_klines(symbol, self.klines)

    def get_last_rsi(self, symbol):
        rsi, price = RSI(self.get_klines(symbol))
        return rsi, price


def message(exchange, coins, db,klines):

    msg = '📢️ *ALERTA({})*\n ----------------------------\n'.format(klines)
    wallet = 'Las siguientes cryptomonedas en *BINANCE {}* presentan un volumen que ha activado una alerta ' \
             'de RSI. *Operar con precaución*:\n\n'.format(exchange)

    msg = msg + wallet

    df = pd.DataFrame(coins).transpose()
    df_longs = df.loc[df['type'] == 1].copy().sort_values(by='rsi',ascending=False)
    df_shorts = df.loc[df['type'] == -1].copy().sort_values(by='rsi',ascending=False)

    if df_longs.__len__() != 0:
        msg_longs = '*Oportunidad de Largos*\n'
        for row in df_longs.iterrows():
            symbol = row[0]
            rsi = row[1]['rsi']
            add_str = 'RSI: *{}* --> ${}\n'.format(rsi, symbol)
            msg_longs += add_str
            db[symbol] = {
                'RSI': rsi,
                'hora': dt.datetime.now()}
        msg += msg_longs + '\n'
    if df_shorts.__len__() != 0:
        msg_short = '*Oportunidad de Cortos*\n'
        for row in df_shorts.iterrows():
            symbol = row[0]
            rsi = row[1]['rsi']
            add_str = 'RSI: *{}* --> ${}\n'.format(rsi, symbol)
            msg_short += add_str
            db[symbol] = {
                'RSI': rsi,
                'hora': dt.datetime.now()}
        msg += msg_short

    telegram_bot_sendtext(msg)

class RSIBOT:
    SIDE = {
        'long': 1,
        'short': -1}

    def __init__(self, klines, exchange):
        self.db = Klines_db(klines, exchange)
        self.exchange = exchange

    def init(self, min_rsi, max_rsi, long=True, short=True):
        db = {}
        while True:
            coins = {}
            for symbol in self.db.symbols:
                last_rsi, last_price = self.db.get_last_rsi(symbol)
                # print(symbol, round(last_rsi))

                if last_rsi < min_rsi and long:  # REVISA SI RSI ACTUAL ES MENOR AL RSI MINIMO PARA COMPRA
                    trade_type = RSIBOT.SIDE['long']
                elif last_rsi > max_rsi and short:
                    trade_type = RSIBOT.SIDE['short']
                else:
                    trade_type = 0

                if trade_type != 0 and activate_alert(symbol, round(last_rsi), db):
                    coins[symbol] = {
                        'type': trade_type,
                        'rsi': round(last_rsi)}

            if coins.__len__() > 0:
                message(self.exchange, coins, db,self.db.klines)


klines = '15m'

a = RSIBOT(klines, 'FUTURES')
a.init(30, 70)

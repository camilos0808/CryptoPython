from _PumpBOT.binance_util import spot_last_price
from _PumpBOT.util import minute_boolean as mb
from time import sleep
import os
import pandas as pd
import json
import numpy as np
import datetime as dt
from Classes.c_Trade import Spot_Trade
import pathlib


class CoinHistoric:

    def __init__(self, symbol, max_number, **kwargs):
        self.symbol = symbol
        if 'historic' in kwargs.keys():
            self.historic = kwargs['historic']
        else:
            self.historic = []
        self.max = max_number

    def add(self, value):
        if value != 0:
            if self.historic.__len__() >= self.max:
                self.historic.pop(0)
                self.historic.append(value)
                # print('added')
            else:
                self.historic.append(value)
                # print('added')
        # else:
        #     print('Value equal 0')

    def mean(self):
        if self.historic.__len__() != 0:
            return sum([abs(ele) for ele in self.historic]) / (self.historic.__len__())

    def len(self):
        return self.historic.__len__()

    def json_encode(self):
        return {'symbol': self.symbol, 'max_number': self.max, 'historic': self.historic, self.__class__.__name__: True}

    @staticmethod
    def json_decode(ch):
        if CoinHistoric.__name__ in ch:
            return CoinHistoric(symbol=ch['symbol'], max_number=ch['max_number'], historic=ch['historic'])


class Historic:
    INIT = os.path.join(pathlib.Path().absolute(), '_DB')

    def __init__(self, seconds, max_numbers, wallet='SPOT', **kwargs):
        self.wallet = wallet
        self.seconds = seconds
        self.max = max_numbers
        if 'symbols' in kwargs.keys():
            self.symbols = kwargs['symbols']
        else:
            self.symbols = {}

    def add_coin(self, symbol):
        if symbol not in self.symbols.keys():
            self.symbols[symbol] = CoinHistoric(symbol, self.max)
            print('Added {}'.format(symbol))
        else:
            print('Already exists')

    def verify_coin(self, symbol):
        if symbol in self.symbols.keys():
            return True
        else:
            return False

    def add_historic(self, lp_series: pd.Series):
        for symbol, change in lp_series.items():
            if self.verify_coin(symbol):
                self.symbols[symbol].add(change)
            else:
                self.add_coin(symbol)
                self.symbols[symbol].add(change)

    def mean_series(self):
        if self.symbols.__len__() != 0:
            prev_dict = {}
            for symbol, historic in self.symbols.items():
                if historic.len() > self.max / 2:
                    prev_dict[symbol] = historic.mean()
                else:
                    prev_dict[symbol] = np.nan

            return pd.Series(prev_dict)
        else:
            return pd.Series()

    def json_encode(self):
        all_dict = {}

        for symbol, historic in self.symbols.items():
            all_dict[symbol] = historic.json_encode()

        dict_to_dump = {'seconds': self.seconds, 'max_number': self.max, 'symbols': all_dict, 'wallet': self.wallet,
                        self.__class__.__name__: True}

        folder = 'seconds_{}'.format(self.seconds.__str__())

        file_name = 'DB_{}.json'.format(self.seconds.__str__())

        with open(os.path.join(Historic.INIT, folder, file_name), 'w') as f:
            json.dump(dict_to_dump, f)

        # print('DONE')

    @staticmethod
    def json_decode(seconds, wallet):

        file_name = 'DB_{}.json'.format(seconds)
        folder = 'seconds_{}'.format(seconds)
        directory = os.path.join(Historic.INIT, folder, file_name)
        if os.path.exists(directory):
            with open(directory, 'r') as json_file:
                h = json.load(json_file)

            if Historic.__name__ in h.keys():
                ch_dict = {}
                for symbols, ch in h['symbols'].items():
                    ch_dict[symbols] = CoinHistoric.json_decode(ch)

                return Historic(seconds=h['seconds'], max_numbers=h['max_number'], symbols=ch_dict, wallet=h['wallet'])
        else:
            print('No DB with {} seconds'.format(seconds))

            raise Exception('No such File')


class PumpAllBot:
    INIT = Historic.INIT
    file_name = {'SPOT': 'pPumps.JSON', 'FUTURES': 'fpPumps.JSON'}

    def __init__(self, seconds, max_columns=1000, wallet='SPOT', **kwargs):
        self.wallet = wallet
        self.seconds = seconds
        self.max = max_columns
        self.trade = np.nan
        folder = 'seconds_{}'.format(seconds)
        self.trade_dir = os.path.join(PumpAllBot.INIT, folder, 'trades_s{}'.format(seconds))

        if os.path.exists(self.trade_dir):
            self.trades = pd.read_json(self.trade_dir)
            self.usdt = self.trades['susdt'].iloc[-1]
        elif 'usdt' in kwargs.keys():
            self.trades = pd.DataFrame()
            self.usdt = kwargs['usdt']
        else:
            raise ValueError('No File, Enter initial usdt')

        try:
            self.database = Historic.json_decode(self.seconds, self.wallet)
        except Exception as e:
            print(e)
            self.database = Historic(seconds=self.seconds, max_numbers=self.max)
        self.iter = 0
        try:
            with open(os.path.join(PumpAllBot.INIT, PumpAllBot.file_name[self.wallet])) as fp:
                self.pPumps = json.load(fp)
        except:
            self.pPumps = {}

    def init(self):
        # pd.options.display.float_format = '{:.2f}'.format
        dumped_coins = []
        while True:
            self.iter += 1
            try:
                prc_change = self.change()
            except:
                sleep(60)
                continue

            prc_series = (prc_change['price'].astype(float) / prc_change['f_price'].astype(float) - 1) * 100
            prc_series = prc_series[~prc_series.index.isin(dumped_coins)].copy()
            self.database.add_historic(prc_series)
            self.encode_db()
            historic_mean = self.database.mean_series()

            relative_prc = (prc_series / historic_mean).dropna().sort_values(ascending=False)
            if relative_prc.__len__() != 0:
                top_prc = list(relative_prc.head(1).to_dict().items())[0]
                dumped_coins = list(relative_prc[relative_prc < - 40].copy().index)

                symbol = top_prc[0]
                val = round(top_prc[1], ndigits=2)
                time = dt.datetime.now()

            # print(symbol, val)
                if val > 20:

                    if mb(time):
                        lp = float(prc_change['f_price'][symbol])
                        lp_btcusdt = float(prc_change['f_price']['BTCUSDT'])
                        self.make_trade(symbol, lp, lp_btcusdt)

                    print(symbol, val)
                    self.pPumps[time.timestamp()] = {'symbol': symbol, 'rate': val, 'seconds': self.seconds,
                                                     'available': self.database.symbols[symbol].len()}
                    self.save_pPumps()
                    if isinstance(self.trade, Spot_Trade):
                        break

    def change(self):
        lp_df = spot_last_price().set_index('symbol')
        lp_df = lp_df[((lp_df.index.str.endswith('USDT')) | (lp_df.index.str.endswith('BTC'))) & (
            ~lp_df.index.str.contains('DOWN')) & (~lp_df.index.str.contains('UP')) & (
                          ~lp_df.index.str.contains('BEAR')) & (~lp_df.index.str.contains('BULL'))].copy() \
            .rename(columns={'price': 'f_price'})
        sleep(self.seconds)
        lp2_df = spot_last_price().set_index('symbol')

        return lp_df.join(lp2_df)

    def encode_db(self):
        if int(self.iter / 100) == self.iter / 100:
            self.database.json_encode()
            print('saved')

    def make_trade(self, symbol, lp, lp_btcusdt):

        self.trade = Spot_Trade(symbol=symbol, side=1, trade_type='MARKET', usdt=self.usdt, lastPrice=lp,
                                BTCUSDT_lp=lp_btcusdt)
        self.trade.enter_trade()
        scal_obj = self.trade.scaling_correction([0.3, 0.4, 0.3], [0.12, 0.3, 0.5], 0.05)
        self.trade.set_scaling_OCO_sell(scal_obj)
        # self.trade.init_scaling_OCO_sell()
        # df = self.trade.trade_to_df()
        # self.trades = pd.concat([self.trades, df])
        # self.trades.to_json(self.trade_dir)

    def save_pPumps(self):
        with open(os.path.join(PumpAllBot.INIT, PumpAllBot.file_name[self.wallet]), 'w') as fp:
            json.dump(self.pPumps, fp)
        print('PUMPED')

    def visualize_df(self):
        df = pd.DataFrame(self.pPumps).transpose()
        df.reset_index(inplace=True, drop=False)
        df['index'] = pd.to_datetime(df['index'], unit='s') - dt.timedelta(hours=5)

        return df

    def entry_alert(self):
        INIT = r'C:\Users\PC\PythonProjects\Crypto\_ChatBOT\_PumpBOT\_Files'
        DIR = os.path.join(INIT, '_f.json')
        exists = os.path.exists(DIR)
        while not exists:
            exists = os.path.exists(DIR)


sleep_seconds = 0.5
init = PumpAllBot(sleep_seconds, usdt=30, wallet='SPOT')
init.init()

import math
from pandas import read_json
import pathlib
from os.path import join

''''
Auxiliary Methods
'''


def correct_decimals(tickers):
    formatted_tickers = '{0:.10f}'.format(tickers)
    decimals = formatted_tickers.find('1') - formatted_tickers.find('.')

    return decimals


def math_ceil(quantity, decimals):
    corrected_qty = (math.ceil(quantity * (10 ** decimals)) / (10 ** decimals))
    return corrected_qty


def scientific_notation(corrected_qty, decimals):
    qty_scientific_not = corrected_qty.__str__().find('-')
    if qty_scientific_not != -1:
        new_cted_qty = "{:0.0{}f}".format(corrected_qty, decimals)
    else:
        new_cted_qty = corrected_qty

    return new_cted_qty.__str__()

'''
Classes
'''

class Symbol:

    STICKERS = read_json(join(pathlib.Path().absolute().parent,'_DB\\spot_tickers.json'))
    FTICKERS = read_json(join(pathlib.Path().absolute().parent,'_DB\\futures_tickers.json'))

    def __init__(self, symbol):
        if symbol in Symbol.STICKERS.index:
            self.__name = symbol
            self.__spot_tickers = Symbol.STICKERS.loc[symbol, :].copy()
        else:
            raise ValueError('%s not in BINANCE' % symbol)

    def __str__(self):
        return self.__name

    @property
    def name(self):
        return self.__name

    @property
    def tickers(self):
        return self.__spot_tickers

    def spot_min_quantity(self, last_price):
        return self.spot_correct_quantity(self.__spot_tickers['MIN_NOTIONAL'] / last_price)

    def spot_correct_quantity(self, quantity):
        lot_size = self.__spot_tickers['LOT_SIZE']
        decimals = correct_decimals(lot_size)
        if decimals == -1:
            decimals = 0

        corrected_qty = scientific_notation(math_ceil(quantity, decimals), decimals)

        return corrected_qty

    def spot_correct_price(self, price):
        price_size = self.__spot_tickers['PRICE_FILTER']
        decimals = correct_decimals(price_size)
        if decimals == -1:
            decimals = 0

        corrected_price = scientific_notation(math_ceil(price, decimals), decimals)

        return corrected_price

    def futures_exists(self):
        return self.__name in Symbol.FTICKERS.index


new_symbol = Symbol('ETHBTC')

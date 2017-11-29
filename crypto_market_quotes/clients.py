from trading_api_wrappers import SURBTC, Kraken, Bitfinex, CryptoMKT

class ExchangeClient(object):
    def __init__(self):
        pass

    @staticmethod
    def get_quote(orderbook, quote_max_accumulated):
        results = []
        for operation_type in ('bids', 'asks'):
            quoted_accumulated = 0
            base_accumulated = 0
            for entry in orderbook[operation_type]:
                quote_expent = entry[0] * entry[1]
                if quote_max_accumulated > quoted_accumulated + quote_expent:
                    quoted_accumulated += quote_expent
                    base_accumulated += entry[0]
                else:
                    remaining_quote = quote_max_accumulated - quoted_accumulated
                    quoted_accumulated += remaining_quote
                    base_accumulated += remaining_quote/entry[1]
                    break
            if quoted_accumulated != quote_max_accumulated:
                results.append(None)
            else:
                results.append(quoted_accumulated/base_accumulated)
        return results

    @staticmethod
    def base_standarize_orderbook(raw_orderbook, get_row):
        orderbook = {}
        orderbook['bids'] = sorted(
            [[float(entry_el) for entry_el in get_row(entry)] for entry in raw_orderbook['bids']],
            key=lambda x: x[1], reverse=True
        )
        orderbook['asks'] = sorted(
            [[float(entry_el) for entry_el in get_row(entry)] for entry in raw_orderbook['asks']],
            key=lambda x: x[1], reverse=False
        )
        return orderbook


class SurbtcClient(ExchangeClient):
    client = SURBTC.Public()

    @staticmethod
    def get_pair_mapping(base, quote):
        return base + '-' + quote

    @classmethod
    def standarize_orderbook(cls, raw_orderbook):
        return cls.base_standarize_orderbook(
            raw_orderbook, lambda entry: (entry.amount, entry.price)
        )


    def get_orderbook(self, base, quote):
        market = self.get_pair_mapping(base, quote)
        tmp_orderbook = self.client.order_book(market)
        orderbook = {}
        orderbook['bids'] = tmp_orderbook.bids
        orderbook['asks'] = tmp_orderbook.asks
        return self.standarize_orderbook(orderbook)

class KrakenClient(ExchangeClient):
    client = Kraken.Public()

    @staticmethod
    def get_pair_mapping(base, quote):
        currency_mapping = {
            'btc': 'XXBT',
            'eth': 'XETH',
            'bch': 'BCH',
            'usd': 'ZUSD',
            'eur': 'ZEUR'
        }
        if base == 'bch':
            pair = currency_mapping[base]+currency_mapping[quote][1:]
        else:
            pair = currency_mapping[base]+currency_mapping[quote]
        return pair

    @classmethod
    def standarize_orderbook(cls, raw_orderbook):
        return cls.base_standarize_orderbook(
            raw_orderbook, lambda entry: (entry[1], entry[0])
        )

    def get_orderbook(self, base, quote):
        market = self.get_pair_mapping(base, quote)
        orderbook = self.client.order_book(market)['result'][market]
        return self.standarize_orderbook(orderbook)


class BitfinexClient(ExchangeClient):
    client = Bitfinex.Public()

    @staticmethod
    def get_pair_mapping(base, quote):
        return base + quote

    @classmethod
    def standarize_orderbook(cls, raw_orderbook):
        return cls.base_standarize_orderbook(
            raw_orderbook, lambda entry: (entry['amount'], entry['price'])
        )

    def get_orderbook(self, base, quote):
        market = self.get_pair_mapping(base, quote)
        orderbook = self.client.order_book(market)
        return self.standarize_orderbook(orderbook)


class CryptoMKTClient(ExchangeClient):
    client = CryptoMKT.Public()

    @staticmethod
    def get_pair_mapping(base, quote):
        return base + quote

    @classmethod
    def standarize_orderbook(cls, raw_orderbook):
        return cls.base_standarize_orderbook(
            raw_orderbook, lambda entry: (entry.amount, entry.price)
        )

    def get_orderbook(self, base, quote):
        market = self.get_pair_mapping(base, quote)
        orderbook = {}
        orderbook['bids'] = self.client.order_book(market, 'buy')[0]
        orderbook['asks'] = self.client.order_book(market, 'sell')[0]
        return self.standarize_orderbook(orderbook)

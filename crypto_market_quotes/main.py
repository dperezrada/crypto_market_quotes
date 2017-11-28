import sys
from datetime import datetime, timezone

import yaml
from crypto_market_quotes.clients import SurbtcClient, KrakenClient

def get_client(exchange):
    if exchange.lower() == 'surbtc':
        return SurbtcClient()
    elif exchange.lower() == 'kraken':
        return KrakenClient()
    else:
        raise

def build_markets(config):
    exchanges_markets = {}
    for exchange in config['exchanges'].keys():
        exchanges_markets[exchange] = []
        exchange_data = config['exchanges'][exchange]
        for base in exchange_data['base']:
            for quote in exchange_data['quote']:
                if base != quote:
                    exchanges_markets[exchange].append((base, quote))
    return exchanges_markets


CONVERTION_FIAT_RATE = {
    'clp': 643,
    'eur': 0.84,
    'cop': 3012,
    'pen': 3.24,
    'btc': 0.00010,
    'usd': 1
}



QUOTE_AMOUNTS_USD = [0.01, 100, 500, 1000, 5000, 10000, 50000, 100000, 500000, 1000000]

def main():
    config = yaml.load(open("config.yml").read())

    exchanges_markets = build_markets(config)

    exchanges = exchanges_markets.keys()
    if len(sys.argv) > 1:
        exchange = sys.argv[1].lower()
        exchanges = [exchange, ]

    for exchange in exchanges:
        client = get_client(exchange)
        for base, quote in exchanges_markets[exchange]:
            orderbook = client.get_orderbook(base, quote)
            for amount in QUOTE_AMOUNTS_USD:
                quote_amount = amount * CONVERTION_FIAT_RATE[quote]
                quote_bid, quote_ask = client.get_quote(orderbook, quote_amount)
                quote_bid = quote_bid if quote_bid else '-'
                quote_ask = quote_ask if quote_ask else '-'
                print('\t'.join([
                    str(row_el) for row_el in [
                        datetime.now(timezone.utc).isoformat(" "),
                        exchange, base, quote, amount, quote_bid, quote_ask
                    ]
                ]))

if __name__ == '__main__':
    main()

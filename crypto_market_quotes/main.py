import sys
from crypto_market_quotes.clients import surbtcClient

def get_client(exchange):
    if exchange.lower() == 'surbtc':
        return surbtcClient()
    else:
        raise

convertion_fiat_rate = {
    'clp': 643,
    'eur': 0.84,
    'cop': 3012,
    'pen': 3.24,
}

def main():
    exchange = sys.argv[1]
    client = get_client(exchange)
    base = 'btc'
    quote = 'clp'
    quote_amount = 1000 * convertion_fiat_rate[quote]
    quote_bid, quote_ask = client.get_quote(base, quote, quote_amount)



if __name__ == '__main__':
    main()

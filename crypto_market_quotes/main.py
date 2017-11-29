import os
import sys
import uuid
from datetime import datetime, timezone

import yaml
from crypto_market_quotes.clients import SurbtcClient, KrakenClient, BitfinexClient, CryptoMKTClient
from trading_api_wrappers import CoinDesk
from google.cloud import bigquery

def get_client(exchange):
    if exchange.lower() == 'surbtc':
        return SurbtcClient()
    elif exchange.lower() == 'kraken':
        return KrakenClient()
    elif exchange.lower() == 'bitfinex':
        return BitfinexClient()
    elif exchange.lower() == 'cryptomkt':
        return CryptoMKTClient()
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
    'ars': 0.057,
    'brl': 0.31,
    'btc': 0.00010,
    'usd': 1
}

def get_fiat_usd_rate(currency):
    coindesk = CoinDesk()
    if currency in ['btc']:
        return 1.0/coindesk.rate('usd').current()
    elif currency in ['usd']:
        return 1
    else:
        usd = coindesk.rate('usd').current()
        target = coindesk.rate(currency).current()
        return target / usd




QUOTE_AMOUNTS_USD = [0.01, 100, 500, 1000, 5000, 10000, 50000, 100000, 500000, 1000000]
DATASET_ID = 'crypto_market_quotes'
TABLE_ID = 'bid_ask'

def get_bigquery_client():
    bigquery_client = bigquery.Client()
    dataset_ref = bigquery_client.dataset(DATASET_ID)
    today = datetime.now(timezone.utc).isoformat().split('T')[0].replace('-', '')
    table_ref = dataset_ref.table(TABLE_ID+'$'+today)
    table = bigquery_client.get_table(table_ref)
    return bigquery_client, table

def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config = yaml.load(open(os.path.join(current_dir, "..", "config.yml")).read())

    exchanges_markets = build_markets(config)

    exchanges = exchanges_markets.keys()
    if len(sys.argv) > 1:
        exchange = sys.argv[1].lower()
        exchanges = [exchange, ]
    DEV = False
    if os.environ.get('DEV'):
        DEV = True

    for currency in CONVERTION_FIAT_RATE:
        try:
            CONVERTION_FIAT_RATE[currency] = get_fiat_usd_rate(currency)
        except:
            pass
    if not DEV:
        bigquery_client, table = get_bigquery_client()

    for exchange in exchanges:
        client = get_client(exchange)
        for base, quote in exchanges_markets[exchange]:
            try:
                orderbook = client.get_orderbook(base, quote)
            except:
                continue
            datetime_ = datetime.now(timezone.utc).isoformat().split('+')[0]
            bq_rows = []
            for amount in QUOTE_AMOUNTS_USD:
                quote_amount = amount * CONVERTION_FIAT_RATE[quote]
                quote_bid, quote_ask = client.get_quote(orderbook, quote_amount)
                row = [
                    str(uuid.uuid4()), str(datetime_), exchange, base,
                    quote, amount, quote_bid, quote_ask
                ]

                row[6] = quote_bid if quote_bid else '-1'
                row[7] = quote_ask if quote_ask else '-1'
                bq_rows.append(row)
                print('\t'.join([str(row_el) for row_el in row]))

            if not DEV:
                errors = bigquery_client.create_rows(
                    table, bq_rows, row_ids=[row_el[0] for row_el in bq_rows]
                )
                if errors:
                    print(errors, file=sys.stderr)

if __name__ == '__main__':
    main()

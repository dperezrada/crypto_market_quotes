import os
import sys
import uuid
import argparse
from datetime import datetime, timezone

import yaml
from trading_api_wrappers import CoinDesk, SURBTC, Kraken, Bitfinex, CryptoMKT
from google.cloud import bigquery

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
CONVERTION_FIAT_LASTUPDATE = {}

DEV = True if os.environ.get('DEV') else False
QUOTE_AMOUNTS_USD = [0.01, 100, 500, 1000, 5000, 10000, 50000, 100000, 500000, 1000000]
DATASET_ID = 'crypto_market_quotes'

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG = yaml.load(open(os.path.join(CURRENT_DIR, "..", "config.yml")).read())
AUTHKEYS = yaml.load(open(os.path.join(CURRENT_DIR, "..", "authkeys.yml")).read())

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

def build_currencies(config):
    exchanges_currencies = {}
    for exchange in config['exchanges'].keys():
        exchanges_currencies[exchange] = []
        exchange_data = config['exchanges'][exchange]
        for base in exchange_data['base']:
            exchanges_currencies[exchange].append(base)
        for quote in exchange_data['quote']:
            if quote not in exchanges_currencies:
                exchanges_currencies[exchange].append(quote)
    return exchanges_currencies

EXCHANGES_MARKETS = build_markets(CONFIG)
EXCHANGES_CURRENCIES = build_currencies(CONFIG)


def get_client(exchange, authkeys=None):
    key = None
    secret = None
    if authkeys is not None:
        try:
            key = authkeys[exchange]['API_KEY']
            secret = authkeys[exchange]['API_SECRET']
        except:
            pass
    if exchange.lower() == 'surbtc':
        return SURBTC.Standard(key=key, secret=secret)
    elif exchange.lower() == 'kraken':
        return Kraken.Standard()
    elif exchange.lower() == 'bitfinex':
        return Bitfinex.Standard()
    elif exchange.lower() == 'cryptomkt':
        return CryptoMKT.Standard()
    else:
        raise


def get_fiat_usd_rate(currency):
    coindesk = CoinDesk()
    if currency == 'btc':
        return 1.0/coindesk.rate('usd').current()
    elif currency == 'usd':
        return 1
    else:
        usd = coindesk.rate('usd').current()
        target = coindesk.rate(currency).current()
        return target / usd

def get_bigquery_client(table_id):
    if DEV:
        return None, None
    bigquery_client = bigquery.Client()
    dataset_ref = bigquery_client.dataset(DATASET_ID)
    today = datetime.now(timezone.utc).isoformat().split('T')[0].replace('-', '')
    table_ref = dataset_ref.table(table_id+'$'+today)
    table = bigquery_client.get_table(table_ref)
    return bigquery_client, table

def get_quote_base_orderbooks(client, exchange, base, quote):
    try:
        orderbook = client.get_orderbook(base, quote)
    except:
        return []
    datetime_ = datetime.now(timezone.utc).isoformat().split('+')[0]
    rows = []
    for amount in QUOTE_AMOUNTS_USD:
        quote_amount = amount * CONVERTION_FIAT_RATE[quote]
        quote_bid, quote_ask = client.get_quote(orderbook, quote_amount)
        row = [
            str(uuid.uuid4()), str(datetime_), exchange, base,
            quote, amount, quote_bid or '-1', quote_ask or '-1'
        ]
        rows.append(row)
    return rows


def calculate_rates():
    for currency in CONVERTION_FIAT_RATE:
        try:
            CONVERTION_FIAT_RATE[currency] = get_fiat_usd_rate(currency)
            CONVERTION_FIAT_LASTUPDATE[currency] = datetime.now(timezone.utc).isoformat().split('+')[0]
        except:
            pass

def save(rows, bigquery_client=None, table=None, add_id=False):
    if add_id:
        rows = [
            [str(uuid.uuid4()),] + list(row)
            for row in rows
        ]

    if bigquery_client and table:
        errors = bigquery_client.create_rows(
            table, rows, row_ids=[row_el[0] for row_el in rows]
        )
        if errors:
            print(errors, file=sys.stderr)
    for row in rows:
        print('\t'.join([str(row_el).lower() if row_el is not None else '-' for row_el in row]))

def get_exchanges(exchanges_markets, exchange=None):
    if exchange:
        return [exchange,]
    return exchanges_markets.keys()

def save_bid_ask(exchanges):
    calculate_rates()
    bigquery_client, table = get_bigquery_client('bid_ask')

    for exchange in exchanges:
        client = get_client(exchange, AUTHKEYS)
        for base, quote in EXCHANGES_MARKETS[exchange]:
            order_books = get_quote_base_orderbooks(client, exchange, base, quote)
            save(order_books, bigquery_client, table=table)

def save_all_withdrawals(exchanges):
    bigquery_client, table = get_bigquery_client('withdrawal')

    for exchange in exchanges:
        client = get_client(exchange, AUTHKEYS)
        for currency in EXCHANGES_CURRENCIES[exchange]:
            withdrawals = client.get_withdrawals(currency)
            save(withdrawals, bigquery_client, table=table)

def save_all_deposits(exchanges):
    bigquery_client, table = get_bigquery_client('deposit')

    for exchange in exchanges:
        client = get_client(exchange, AUTHKEYS)
        for currency in EXCHANGES_CURRENCIES[exchange]:
            deposits = client.get_deposits(currency)
            save(deposits, bigquery_client, table=table, add_id=True)

def save_currency_rates():
    calculate_rates()
    bigquery_client, table = get_bigquery_client('currency_rate')
    rows = []
    for fiat_currency in CONVERTION_FIAT_RATE:
        if CONVERTION_FIAT_LASTUPDATE.get(fiat_currency) is None:
            continue
        rows.append([
            CONVERTION_FIAT_LASTUPDATE[fiat_currency],
            fiat_currency,
            CONVERTION_FIAT_RATE[fiat_currency],
        ])

    save(rows, bigquery_client, table=table, add_id=True)

def save_all_orders(exchanges):
    bigquery_client, table = get_bigquery_client('orders')

    for exchange in exchanges:
        client = get_client(exchange, AUTHKEYS)
        for base, quote in EXCHANGES_MARKETS[exchange]:
            orders = client.get_orders(base, quote, state='traded')
            save(orders, bigquery_client, table=table, add_id=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "process_type",
        type=str,
        choices=['currency_rates', 'bid_ask', 'withdrawals', 'deposits', 'orders']
    )
    parser.add_argument("-e", "--exchange", type=str)
    args = parser.parse_args()
    exchanges = get_exchanges(EXCHANGES_MARKETS, args.exchange)

    process_t = args.process_type
    if process_t == 'currency_rates':
        save_currency_rates()
    elif process_t == 'bid_ask':
        save_bid_ask(exchanges)
    elif process_t == 'withdrawals':
        save_all_withdrawals(exchanges)
    elif process_t == 'deposits':
        save_all_deposits(exchanges)
    elif process_t == 'orders':
        save_all_orders(exchanges)


if __name__ == '__main__':
    main()

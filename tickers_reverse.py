import json


def get_pool_id_from_ticker_file():
    with open('tickers.json', 'r') as ticker_file:
        tickers = json.load(ticker_file)
    new_dict = {}
    with open('tickers_reverse.json', 'w') as reverse_f:
        new_dict['tickers'] = {}
        for pool_id in tickers['tickers']:
            new_dict['tickers'][tickers['tickers'][pool_id]] = pool_id
        json.dump(new_dict, reverse_f)


get_pool_id_from_ticker_file()
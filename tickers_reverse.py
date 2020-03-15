import json


def get_pool_id_from_ticker_file():
    with open('tickers.json', 'r') as ticker_file:
        tickers = json.load(ticker_file)
    with open('tickers_reverse.json', 'w') as reverse_f:
        reverse_dic = {}
        for k, v in tickers['tickers'].items():
            reverse_dic[v] = reverse_dic.get(v, [])
            reverse_dic[v].append(k)
        json.dump(reverse_dic, reverse_f)


get_pool_id_from_ticker_file()
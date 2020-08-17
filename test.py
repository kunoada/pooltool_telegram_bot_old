import json



with open('tickers.json', 'r') as f:
    data = json.load(f)
    with open('tickers_reverse.json', 'r') as ticker:
        tickers = json.load(ticker)
    with open('tickers_reverse.json', 'w') as reverse_f:
        reverse_dic = {}
        for pool in data:
            reverse_dic[data[pool]['ticker'].upper()] = reverse_dic.get(data[pool]['ticker'].upper(), [])
            reverse_dic[data[pool]['ticker'].upper()].append(pool)

        final_dic = {}
        for ticker in reverse_dic:
            if ticker not in tickers:
                tickers[ticker] = tickers.get(ticker, [])
                for pool_id in reverse_dic[ticker]:
                    tickers[ticker].append(pool_id)
            else:
                for pool_id in reverse_dic[ticker]:
                    if pool_id not in tickers[ticker]:
                        tickers[ticker].append(pool_id)

        # for k, v in data['tickers'].items():
        #     reverse_dic[v] = reverse_dic.get(v, [])
        #     reverse_dic[v].append(k)
        json.dump(tickers, reverse_f)
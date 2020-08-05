from dbhelper import DBHelper
import json

db = DBHelper()

with open('tickers_new.json', 'r') as pools:
    pools = json.load(pools)
    for pool in pools:
        print(pool, " ", pools[pool]['ticker'])
        db.update_poolid(pool, pools[pool]['ticker'])

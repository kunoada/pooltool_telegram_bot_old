import json
import requests
import time
import urllib
import threading

import boto3
import pprint
from os import environ

from si_prefix import si_format
from dbhelper import DBHelper

db = DBHelper()

TOKEN = open('token', 'r').read()
URL = "https://api.telegram.org/bot{}/".format(TOKEN)

environ["AWS_PROFILE"] = "bot_iam"
client = boto3.client('sts')
session = boto3.Session(profile_name='bot_iam')
sqs = boto3.client('sqs')
queue_url = 'https://sqs.us-west-2.amazonaws.com/637019325511/pooltoolevents.fifo'

current_epoch = 0

lightning = '⚡'
fire = '🔥'
moneyBag = '💰'
pickaxe = '⛏'
swords = '⚔'
throphy = '🏆'
annoyed = '😤'
warning = '⚠'
alert = '‼'
like = '👍'


def get_url(url):
    try:
        response = requests.get(url)
    except requests.exceptions.RequestException as e:
        return ''
    content = response.content.decode("utf8")
    return content


def get_json_from_url(url):
    content = get_url(url)
    if content == '':
        return
    js = json.loads(content)
    return js


def get_updates(offset=None):
    url = URL + "getUpdates"
    if offset:
        url += "?offset={}".format(offset)
    url += "?timeout={}".format(100)
    js = get_json_from_url(url)
    return js


def get_last_update_id(updates):
    update_ids = []
    for update in updates["result"]:
        update_ids.append(int(update["update_id"]))
    return max(update_ids)


def handle_updates(updates):
    for update in updates["result"]:
        print(update)
        if 'text' not in update["message"]:
            continue
        text = update["message"]["text"].upper()
        chat = update["message"]["chat"]["id"]
        tickers = db.get_tickers(chat)
        if text == "/DELETE":
            if not tickers:
                send_message("No TICKERs added", chat)
                continue
            keyboard = build_keyboard(tickers)
            send_message("Select an item to delete", chat, keyboard)
        elif text == "/START":
            message = "Welcome to PoolTool Bot!\n" \
                      "\n" \
                      "Please enter the TICKER of the pool(s) you want to follow\n" \
                      "\n" \
                      "Example: KUNO\n" \
                      "\n" \
                      "In order to remove a TICKER from the list, you have two options:\n" \
                      "1. Enter the TICKER again\n" \
                      "2. Enter \"/DELETE\" to get a list with possible TICKERs to delete\n" \
                      "\n" \
                      "This pooltool bot was created for pooltool by KUNO stakepool"
            send_message(message, chat)
        elif text.startswith("/"):
            continue
        elif 3 > len(text) or len(text) > 5:
            message = "A TICKER needs to be between 3-5 letters!"
            send_message(message, chat)
        elif text in tickers:
            db.delete_item(chat, text)
            tickers = db.get_tickers(chat)
            message = "List of pools you watch:\n\n" + "\n".join(tickers)
            send_message(message, chat)
        else:
            pool_id = get_pool_id_from_ticker_file(text)
            if pool_id == '':
                pool_id = get_pool_id_from_ticker_url(text)
            if pool_id == '':
                message = "This is not a valid TICKER!"
                send_message(message, chat)
                continue
            elif pool_id == 'error':
                message = "There was an error, please try again"
                send_message(message, chat)
                continue
            db.add_item(chat, text)
            data = update_livestats(pool_id)
            db.update_items(chat, text, pool_id, data[0], data[1])
            tickers = db.get_tickers(chat)
            message = "List of pools you watch:\n\n" + "\n".join(tickers)
            send_message(message, chat)


def get_last_chat_id_and_text(updates):
    num_updates = len(updates["result"])
    last_update = num_updates - 1
    text = updates["result"][last_update]["message"]["text"]
    chat_id = updates["result"][last_update]["message"]["chat"]["id"]
    return (text, chat_id)


def build_keyboard(items):
    keyboard = [[item] for item in items]
    reply_markup = {"keyboard":keyboard, "one_time_keyboard": True}
    return json.dumps(reply_markup)


def send_message(text, chat_id, reply_markup=None):
    text = urllib.parse.quote_plus(text)
    url = URL + "sendMessage?text={}&chat_id={}&parse_mode=Markdown".format(text, chat_id)
    if reply_markup:
        url += "&reply_markup={}".format(reply_markup)
    get_url(url)


def get_pool_id_from_ticker_file(ticker):
    with open('tickers.json', 'r') as ticker_file:
        tickers = json.load(ticker_file)
    for pool_id in tickers['tickers']:
        if tickers['tickers'][pool_id] == ticker:
            return pool_id
    return ''


def get_pool_id_from_ticker_url(ticker):
    url_pool_ids = 'https://pooltool.s3-us-west-2.amazonaws.com/8e4d2a3/tickers.json'
    try:
        r = requests.get(url_pool_ids)
        data = r.json()
    except requests.exceptions.RequestException as e:
        return 'error'
    for pool_id in data['tickers']:
        if data['tickers'][pool_id] == ticker:
            return pool_id
    return ''


def get_ticker_from_pool_id(pool_id):
    with open('tickers.json', 'r') as ticker_file:
        tickers = json.load(ticker_file)
    if pool_id in tickers['tickers']:
        return tickers['tickers'][pool_id]
    return 'UNKNOWN'


def get_livestats(pool_id):
    url_livestats = f'https://pooltool.s3-us-west-2.amazonaws.com/8e4d2a3/pools/{pool_id}/livestats.json'
    try:
        r = requests.get(url_livestats)
        data = r.json()
    except requests.exceptions.RequestException as e:
        return ''
    return data


def update_livestats(pool_id):
    data = get_livestats(pool_id)
    if data == '':
        return (0, 0, 0)
    return (round(int(data['livestake'])/1000000), data['epochblocks'], data['lastBlockEpoch'])


def get_stats():
    url_stats = 'https://pooltool.s3-us-west-2.amazonaws.com/stats/stats.json'
    try:
        r = requests.get(url_stats)
        data = r.json()
    except requests.exceptions.RequestException as e:
        return ''
    return data


def get_current_epoch():
    data = get_stats()
    if data == '':
        return 0
    return data['currentepoch']


def get_rewards_data(pool_id, epoch):
    url_rewards = f'https://pooltool.s3-us-west-2.amazonaws.com/8e4d2a3/pools/{pool_id}/rewards_{epoch}.json'
    try:
        r = requests.get(url_rewards)
        data = r.json()
    except requests.exceptions.RequestException as e:
        return ''
    return data


def update_rewards(pool_id, epoch):
    data = get_rewards_data(pool_id, epoch)
    if data == '':
        return (0, 0)
    return (data['rewards']['value_for_stakers'], data['rewards']['value_taxed'])


def get_competitive(pool_id, epoch):
    url_competitive = f'https://pooltool.s3-us-west-2.amazonaws.com/8e4d2a3/pools/{pool_id}/byepoch/{epoch}/winloss.json'
    try:
        r = requests.get(url_competitive)
        data = r.json()
    except requests.exceptions.RequestException as e:
        return ''
    return data


def update_competitive_win_loss(pool_id, epoch):
    data = get_competitive(pool_id, epoch)
    if data == '':
        return (0, 0)
    return (data['w'], data['l'])


def check_delegation_changes(chat_id, ticker, delegations, new_delegations):
    if delegations != new_delegations:
        db.update_delegation(chat_id, ticker, new_delegations)
        if delegations > new_delegations:
            message = f'{ticker}\n' \
                      f'- {si_format(delegations - new_delegations, precision=2)} ADA! Your delegations has decreased to: {si_format(new_delegations, precision=2)} ADA'
            send_message(message, chat_id)
        elif delegations < new_delegations:
            message = f'{ticker}\n' \
                      f'+ {si_format(new_delegations - delegations, precision=2)} ADA! Your delegations has increased to: {si_format(new_delegations, precision=2)} ADA'
            send_message(message, chat_id)


def check_blocks_minted(chat_id, ticker, blocks_minted, new_blocks_minted, new_last_block_epoch):
    if new_last_block_epoch == current_epoch:
        if new_blocks_minted > blocks_minted:
            db.update_blocks_minted(chat_id, ticker, new_blocks_minted)
            message = f'{ticker}\n New block minted! Total blocks minted this epoch: {new_blocks_minted}'
            send_message(message, chat_id)
    else:
        db.update_blocks_minted(chat_id, ticker, 0)


def handle_notifier():
    global current_epoch
    chat_ids = list(set(db.get_chat_ids()))

    epoch = get_current_epoch()
    if current_epoch < epoch:
        for chat_id in chat_ids:
            tickers = db.get_tickers(chat_id)
            for ticker in tickers:
                pool_id , delegations , blocks_minted = db.get_items(chat_id , ticker)
                wins, losses = update_competitive_win_loss(pool_id, current_epoch)
                rewards_stakers, rewards_tax = update_rewards(pool_id, current_epoch)
                message = f'{ticker}\n ' \
                          f'🔥Epoch {current_epoch} stats:🔥\n' \
                          f'\n' \
                          f'💰Live stake {si_format(delegations, precision=2)}\n' \
                          f'⛏Blocks minted: {blocks_minted}\n' \
                          f'⚔Slot battles: {wins}/{wins + losses}\n' \
                          f'\n' \
                          f'Stakers rewards {si_format(rewards_stakers/1000000, precision=2)}\n' \
                          f'Tax rewards {si_format(rewards_tax / 1000000, precision=2)}'
                send_message(message , chat_id)
        current_epoch = epoch

    for chat_id in chat_ids:
        tickers = db.get_tickers(chat_id)
        for ticker in tickers:
            pool_id, delegations, blocks_minted = db.get_items(chat_id, ticker)
            new_delegations, new_blocks_minted, new_last_block_epoch = update_livestats(pool_id)
            if new_last_block_epoch == 0:
                continue
            check_delegation_changes(chat_id, ticker, delegations, new_delegations)
            check_blocks_minted(chat_id, ticker, blocks_minted, new_blocks_minted, new_last_block_epoch)


def start_telegram_update_handler():
    last_update_id = None
    while True:
        updates = get_updates(last_update_id)
        if updates is not None:
            if len(updates["result"]) > 0:
                last_update_id = get_last_update_id(updates) + 1
                handle_updates(updates)
        time.sleep(0.5)


def get_aws_event():
    response = sqs.receive_message(
        QueueUrl=queue_url,
        AttributeNames=[
            'SentTimestamp'
        ],
        MaxNumberOfMessages=1,
        MessageAttributeNames=[
            'All'
        ],
        # VisibilityTimeout=0,
        WaitTimeSeconds=20
    )
    if 'Messages' in response:
        if len(response['Messages']) > 0:
            return response['Messages'][0]
    return ''


def delete_aws_event_from_queue(receipt_handle):
    sqs.delete_message(
        QueueUrl=queue_url,
        ReceiptHandle=receipt_handle
    )


def handle_battle(data):
    def what_battle_type(players):
        slot_check = ''
        for player in players:
            if slot_check == '':
                slot_check = player['slot']
            else:
                if slot_check != player['slot']:
                    return 'Height'
        return 'Slot'

    def who_battled(players):
        tickers = []
        for player in players:
            tickers.append(get_ticker_from_pool_id(player['pool']))
        return ' vs '.join(tickers)

    players = data['players']
    height = data['height']
    battle_type = what_battle_type(players)
    competitors = who_battled(players)
    for player in data['players']:
        if player['pool'] == data['winner']:
            chat_ids = db.get_chat_ids_from_poolid(player['pool'])
            for chat_id in chat_ids:
                ticker = db.get_ticker_from_poolid(player['pool'])[0]
                message = f'{ticker}\n' \
                          f'{swords}{battle_type} battle!\n' \
                          f'At height: {height}\n' \
                          f'{competitors}\n' \
                          f'...\n' \
                          f'You won! {throphy}\n' \
                          f'https://pooltool.io/competitive'
                send_message(message, chat_id)
        else:
            chat_ids = db.get_chat_ids_from_poolid(player['pool'])
            for chat_id in chat_ids:
                ticker = db.get_ticker_from_poolid(player['pool'])[0]
                message = f'{ticker}\n' \
                          f'{swords}{battle_type} battle!\n' \
                          f'At height: {height}\n' \
                          f'{competitors}\n' \
                          f'...\n' \
                          f'You lost! {annoyed}\n' \
                          f'https://pooltool.io/competitive'
                send_message(message, chat_id)


def handle_wallet_poolchange(data):
    with open('wallet_poolchange', 'w') as f:
        f.write(json.dumps(data))


def handle_wallet_newpool(data):
    with open('wallet_newpool', 'w') as f:
        f.write(json.dumps(data))


def handle_block_minted(data):
    pool_id = data['pool']
    nbe = data['nbe']
    chat_ids = db.get_chat_ids_from_poolid(pool_id)
    for chat_id in chat_ids:
        ticker = db.get_ticker_from_poolid(pool_id)[0]
        message = f'{ticker}\n' \
                  f'{pickaxe}New block minted! Total blocks minted this epoch: {nbe}'
        send_message(message, chat_id)
        db.update_blocks_minted(chat_id, ticker, nbe)


def handle_stake_change(data):
    with open('stake_change', 'w') as f:
        f.write(json.dumps(data))

    pool_id = data['pool']
    chat_ids = db.get_chat_ids_from_poolid(pool_id)
    if chat_ids:
        ticker = db.get_ticker_from_poolid(pool_id)[0]
        for chat_id in chat_ids:
            pool_id, delegations, blocks_minted = db.get_items(chat_id, ticker)
            new_delegations, new_blocks_minted, new_last_block_epoch = update_livestats(pool_id)
            if new_last_block_epoch == 0:
                continue
            check_delegation_changes(chat_id, ticker, delegations, new_delegations)


def handle_block_adjustment(data):
    pool_id = data['pool']
    chat_ids = db.get_chat_ids_from_poolid(pool_id)
    for chat_id in chat_ids:
        ticker = db.get_ticker_from_poolid(pool_id)[0]
        message = f'{ticker}\n' \
                  f'{warning}Block adjustment{warning}\n' \
                  f"Total blocks this epoch has changed from {data['old_epoch_blocks']} to {data['new_epoch_blocks']}\n" \
                  f"More info:\n" \
                  f"https://pooltool.io/"
        send_message(message, chat_id)
        db.update_blocks_minted(chat_id, ticker, data['new_epoch_blocks'])


def handle_sync_change(data):
    pool_id = data['pool']
    chat_ids = db.get_chat_ids_from_poolid(pool_id)
    for chat_id in chat_ids:
        ticker = db.get_ticker_from_poolid(pool_id)[0]
        if not data['new_status']:
            message = f'{ticker}\n' \
                      f'{alert}Pool is out of sync{alert}'
            send_message(message, chat_id)
        else:
            message = f'{ticker}\n' \
                      f'{like}Pool is back in sync{like}'
            send_message(message, chat_id)


def check_for_new_epoch():
    global current_epoch
    epoch = get_current_epoch()

    if current_epoch < epoch:
        chat_ids = list(set(db.get_chat_ids()))
        for chat_id in chat_ids:
            tickers = db.get_tickers(chat_id)
            for ticker in tickers:
                pool_id , delegations , blocks_minted = db.get_items(chat_id , ticker)
                wins, losses = update_competitive_win_loss(pool_id, current_epoch)
                rewards_stakers, rewards_tax = update_rewards(pool_id, current_epoch)
                message = f'{ticker}\n ' \
                          f'🔥Epoch {current_epoch} stats:🔥\n' \
                          f'\n' \
                          f'💰Live stake {si_format(delegations, precision=2)}\n' \
                          f'⛏Blocks minted: {blocks_minted}\n' \
                          f'⚔Slot battles: {wins}/{wins + losses}\n' \
                          f'\n' \
                          f'Stakers rewards {si_format(rewards_stakers/1000000, precision=2)}\n' \
                          f'Tax rewards {si_format(rewards_tax / 1000000, precision=2)}'
                send_message(message , chat_id)
        current_epoch = epoch


def start_telegram_notifier():
    ## On start init..
    global current_epoch
    current_epoch = get_current_epoch()
    ##
    periodic_new_epoch_check = time.time()
    while True:
        event = get_aws_event()
        if event != '':
            delete_aws_event_from_queue(event['ReceiptHandle'])
            body = json.loads(event['Body'])
            data = body['data']
            if body['type'] == 'battle':
                handle_battle(data)
                continue
            elif body['type'] == 'wallet_poolchange':
                handle_wallet_poolchange(data)
                continue
            elif body['type'] == 'wallet_newpool':
                handle_wallet_newpool(data)
                continue
            elif body['type'] == 'block_minted':
                handle_block_minted(data)
                continue
            elif body['type'] == 'stake_change':
                handle_stake_change(data)
                continue
            elif body['type'] == 'block_adjustment':
                handle_block_adjustment(data)
                continue
            elif body['type'] == 'sync_change':
                handle_sync_change(data)
                continue

        if time.time() - periodic_new_epoch_check > 10*60: # Check every 10 min
            check_for_new_epoch()
            periodic_new_epoch_check = time.time()
        time.sleep(0.5)


def main():
    db.setup()
    updates_handler = threading.Thread(target=start_telegram_update_handler)
    notifier = threading.Thread(target=start_telegram_notifier)

    updates_handler.start()
    notifier.start()


if __name__ == '__main__':
    main()
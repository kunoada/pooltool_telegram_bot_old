import json
import requests
import time
import urllib
import threading
import math

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

options_string_builder = {}

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
link = '🔗'
globe = '🌐'
tools = '🛠'
chains = '⛓'
brick = '🧱'
meat = '🥩'
flyingMoney = '💸'
clock = '⏱'
arrowDown = '🔻'
arrowUp = '🔺'
star = '⭐'
dice = '🎲'


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


def handle_start(chat):
    message = f"{globe}Welcome to PoolTool Bot!{globe}\n" \
              "\n" \
              "Please enter the TICKER of the pool(s) you want to follow\n" \
              "\n" \
              "Example: KUNO\n" \
              "\n" \
              "In order to remove a TICKER from the list, you have two options:\n" \
              "1. Enter the TICKER again\n" \
              "2. Enter \"/DELETE\" to get a list with possible TICKERs to delete\n" \
              "\n" \
              "For more information, enter \"/HELP\"\n" \
              "\n" \
              "This pooltool bot was created for pooltool by KUNO stakepool\n" \
              "\n" \
              "*NOTE: This Bot is not case sensitive! text in upper- and lower case work!*"
    send_message(message, chat)


def handle_help(chat):
    message = "*Add/Remove pool:*\n" \
              "Enter ticker of the pool, this will both add the pool to the list or delete if it is already on the list\n" \
              "\n" \
              "Example: KUNO\n" \
              "\n" \
              "\n" \
              "*Options for each pool:*\n" \
              "You can enable/disable/silent each specific notification you want for each pool on your list\n" \
              "\n" \
              "/OPTION \\[POOL TICKER]\n" \
              "\n" \
              "For more info about using option, enter /OPTION"
    send_message(message, chat)


def handle_option_help(chat):
    message = "*Change or see current options for a pool:*\n" \
              "\n" \
              "Usage: /OPTION \\[POOL TICKER]\n" \
              "Example: /OPTION KUNO"
    send_message(message, chat)


def on_ticker_valid(ticker, number, chat, pool_id):
    # db.add_item(chat, ticker)
    db.add_new_pool(pool_id[number], ticker)
    db.add_new_user_pool(chat, pool_id[number], ticker)
    # tickers = db.get_tickers(chat)
    tickers = db.get_tickers_from_chat_id(chat)
    message = "List of pools you watch:\n\n" + "\n".join(tickers)
    send_message(message, chat)
    # data = update_livestats(pool_id[number])
    # db.update_items(chat, f'{ticker}', pool_id[number], data[0], data[1])


def handle_duplicate_ticker(text, chat, pool_id):
    if len(text) > 1:
        try:
            number = int(text[1])
            if number < len(pool_id) and number >= 0:
                text = f'{text[0]} {text[1]}'
                on_ticker_valid(text, number, chat, pool_id)
            else:
                raise Exception("Assuming number doesn't fit the provided listing!")
        except:
            message = "Something went wrong!"
            send_message(message, chat)
            return
    else:
        count = 0
        pool_ids = ''
        for pool in pool_id:
            pool_ids = pool_ids + f'{count}. {pool}\n'
            count += 1
        message = "There's more than one pool with this ticker!\n" \
                  "\n" \
                  f"{pool_ids}\n" \
                  f"Please specify which pool you want listed, eg.\n" \
                  f"{text[0]} x, where x is the listing number"
        send_message(message, chat)


def handle_new_ticker(text, chat):
    text = text.split(' ')
    pool_id = get_pool_id_from_ticker_file(text[0])

    if pool_id is None:
        message = "This is not a valid TICKER!"
        send_message(message, chat)
        return
    elif len(pool_id) > 1:
        handle_duplicate_ticker(text, chat, pool_id)
    else:
        on_ticker_valid(text[0], 0, chat, pool_id)


def validate_option_usage(chat, text, tickers):
    options = ['BLOCK_MINTED', 'BATTLE', 'SYNC_STATUS', 'BLOCK_ADJUSTMENT', 'STAKE_CHANGE']
    if len(text) == 4:
        if not text[0] == "/OPTION":
            message = 'Option is not the first argument'
            send_message(message, chat)
            return False
        if not text[1] in tickers:
            message = 'Ticker is not in your list of pools'
            send_message(message, chat)
            return False
        if not text[2] in options:
            message = 'Unknown option type'
            send_message(message, chat)
            return False
        try:
            value = int(text[3])
        except Exception as e:
            message = 'Value is not a number'
            send_message(message, chat)
            return False
        if not 0 <= value <= 1:
            message = 'Value should be either, 0 or 1'
            send_message(message, chat)
            return False
    else:
        return False
    return True


# def validate_option_get(chat, text, tickers):
#     if len(text) == 3:
#         if not text[0] == "/OPTION":
#             message = 'Option is not the first argument'
#             send_message(message, chat)
#             return False
#         if not text[1] in tickers:
#             message = 'Ticker is not in your list of pools'
#             send_message(message, chat)
#             return False
#         if not text[2] == 'GET':
#             message = 'Unknown option type'
#             send_message(message, chat)
#             return False
#     else:
#         return False
#     return True


def convert_option_value(value):
    if value == 1:
        return 'On'
    elif value == 2:
        return 'Silent'
    else:
        return 'Off'


def get_current_options(chat, text):
    if len(text) > 1:
        options_string = f'\\[ {text[1]} ] Options:\n' \
                         f'\n' \
                         f"block\\_minted: {convert_option_value(db.get_option(chat, text[1], 'block_minted'))}\n" \
                         f"battle: {convert_option_value(db.get_option(chat, text[1], 'battle'))}\n" \
                         f"sync\\_status: {convert_option_value(db.get_option(chat, text[1], 'sync_status'))}\n" \
                         f"block\\_adjustment: {convert_option_value(db.get_option(chat, text[1], 'block_adjustment'))}\n" \
                         f"stake\\_change: {convert_option_value(db.get_option(chat, text[1], 'stake_change'))}"
        return options_string
    return ''


def validate_option_type(type):
    options = ['SEE OPTIONS', 'BLOCK_MINTED', 'BATTLE', 'SYNC_STATUS', 'BLOCK_ADJUSTMENT', 'STAKE_CHANGE']
    if type in options:
        return True
    return False


def send_option_type(chat):
    options = ['SEE OPTIONS', 'BLOCK_MINTED', 'BATTLE', 'SYNC_STATUS', 'BLOCK_ADJUSTMENT', 'STAKE_CHANGE']
    keyboard = build_keyboard(options)
    send_message('Select option to change', chat, keyboard)


def validate_option_state(type):
    states = ['ENABLE', 'DISABLE', 'SILENT']
    if type in states:
        return True
    return False


def send_option_state(chat):
    states = ['ENABLE', 'DISABLE', 'SILENT']
    keyboard = build_keyboard(states)
    send_message('Select new state', chat, keyboard)


def handle_option(chat, text, tickers):
    text = text.split(' ')
    if text[0] == '/OPTION':
        if len(text) == 2:
            if text[1] in tickers:
                options_string_builder[chat] = {}
                options_string_builder[chat]['string'] = ' '.join(text)
                options_string_builder[chat]['next'] = 'option_type'
                send_option_type(chat)
            else:
                message = 'Ticker is not in your list of pools'
                send_message(message, chat)
        elif len(text) == 3:
            ticker = ' '.join([text[1], text[2]])
            if ticker in tickers:
                options_string_builder[chat] = {}
                options_string_builder[chat]['string'] = ' '.join(text)
                options_string_builder[chat]['next'] = 'option_type'
                send_option_type(chat)
            else:
                message = 'Ticker is not in your list of pools'
                send_message(message, chat)
        else:
            message = "To many arguments!"
            send_message(message, chat)


def adjust_string_if_duplicate(text):
    list = text.split(' ')
    if len(list) > 2:
        if list[2].isdigit():  # Assuming we work with a duplicate ticker
            new_list = []
            if len(list) == 4:
                new_list.extend([list[0], ' '.join([list[1], list[2]]), list[3]])
            elif len(list) == 5:
                new_list.extend([list[0], ' '.join([list[1], list[2]]), list[3], list[4]])
            return new_list
    return list


def update_option(chat, text):
    db.update_option(chat, text[1], text[2], text[3])


def handle_next_option_step(chat, text):
    next_step = options_string_builder[chat]['next']
    if next_step == 'option_type':
        if validate_option_type(text):
            if text == 'SEE OPTIONS':
                message = get_current_options(chat, adjust_string_if_duplicate(options_string_builder[chat]['string']))
                if not message == '':
                    send_message(message, chat, remove_keyboard(True))
                del options_string_builder[chat]
                return
            options_string_builder[chat]['string'] = ' '.join([options_string_builder[chat]['string'], text])
            options_string_builder[chat]['next'] = 'option_state'
            send_option_state(chat)
        else:
            message = "Not a possible option type, try again!"
            send_message(message, chat)
            send_option_type(chat)
    elif next_step == 'option_state':
        if validate_option_state(text):
            if text == 'ENABLE':
                options_string_builder[chat]['string'] = ' '.join([options_string_builder[chat]['string'], '1'])
            elif text == 'DISABLE':
                options_string_builder[chat]['string'] = ' '.join([options_string_builder[chat]['string'], '0'])
            elif text == 'SILENT':
                options_string_builder[chat]['string'] = ' '.join([options_string_builder[chat]['string'], '2'])
            update_option(chat, adjust_string_if_duplicate(options_string_builder[chat]['string']))
            message = get_current_options(chat, adjust_string_if_duplicate(options_string_builder[chat]['string']))
            send_message(message, chat)
            del options_string_builder[chat]
        else:
            message = "Not a possible option state, try again!"
            send_message(message, chat)
            send_option_state(chat)


def handle_updates(updates):
    if 'result' in updates:
        for update in updates["result"]:
            if 'message' in update:
                print(update)
                if 'text' not in update["message"]:
                    continue
                text = update["message"]["text"].upper()
                chat = update["message"]["chat"]["id"]
                tickers = db.get_tickers_from_chat_id(chat)
                if chat in options_string_builder:
                    handle_next_option_step(chat, text)
                    continue
                if text == "/DELETE":
                    if not tickers:
                        send_message("No TICKERs added", chat)
                        continue
                    keyboard = build_keyboard(tickers)
                    send_message("Select pool to delete", chat, keyboard)
                elif text == "/START":
                    handle_start(chat)
                    if 'first_name' in update["message"]["text"]:
                        name = update["message"]["text"]["first_name"]
                        try:
                            db.add_user(chat, name)
                        except Exception as e:
                            print('Assuming user is already added')
                elif text == "/HELP":
                    handle_help(chat)
                elif "/OPTION" in text:
                    if text == "/OPTION":
                        handle_option_help(chat)
                    else:
                        handle_option(chat, text, tickers)
                elif text.startswith("/"):
                    continue
                elif text in tickers:
                    db.delete_user_pool(chat, text)
                    # db.delete_item(chat, text)
                    tickers = db.get_tickers_from_chat_id(chat)
                    # tickers = db.get_tickers(chat)
                    message = "List of pools you watch:\n\n" + "\n".join(tickers)
                    send_message(message, chat)
                else:
                    handle_new_ticker(text, chat)


def get_last_chat_id_and_text(updates):
    num_updates = len(updates["result"])
    last_update = num_updates - 1
    text = updates["result"][last_update]["message"]["text"]
    chat_id = updates["result"][last_update]["message"]["chat"]["id"]
    return (text, chat_id)


def build_keyboard(items):
    keyboard = [[item] for item in items]
    reply_markup = {"keyboard": keyboard, "one_time_keyboard": True}
    return json.dumps(reply_markup)


def remove_keyboard(boolean):
    remove_keyboard_reply = {"RemoveKeyboard": boolean}
    return json.dumps(remove_keyboard_reply)


def send_message(text, chat_id, reply_markup=None, silent=None, disable_web_preview=None):
    text = urllib.parse.quote_plus(text)
    url = URL + "sendMessage?text={}&chat_id={}&parse_mode=Markdown".format(text, chat_id)
    if reply_markup:
        url += "&reply_markup={}".format(reply_markup)
    if silent:
        url += f"&disable_notification={silent}"
    if disable_web_preview:
        url += f"&disable_web_page_preview={disable_web_preview}"
    get_url(url)


def get_pool_id_from_ticker_file(ticker):
    with open('tickers_reverse.json', 'r') as ticker_file:
        tickers = json.load(ticker_file)
    return tickers.get(ticker)


def get_pool_id_from_ticker_url(ticker):
    url_pool_ids = 'https://pooltool.s3-us-west-2.amazonaws.com/8e4d2a3/tickers.json'
    try:
        r = requests.get(url_pool_ids)
        if r.ok:
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


def get_new_ticker_file():
    time.sleep(60)
    url_ticker = 'https://pooltool.s3-us-west-2.amazonaws.com/8e4d2a3/tickers.json'
    try:
        r = requests.get(url_ticker)
        if r.ok:
            return r.json()
    except requests.exceptions.RequestException as e:
        return 'error'


def get_livestats(pool_id):
    url_livestats = f'https://pooltool.s3-us-west-2.amazonaws.com/8e4d2a3/pools/{pool_id}/livestats.json'
    try:
        r = requests.get(url_livestats)
        if r.ok:
            data = r.json()
        else:
            data = ''
    except requests.exceptions.RequestException as e:
        return ''
    return data


def update_livestats(pool_id):
    data = get_livestats(pool_id)
    if data == '' or 'livestake' not in data or 'epochblocks' not in data or 'lastBlockEpoch' not in data:
        return (0, 0, 0)
    return (round(int(data['livestake']) / 1000000), data['epochblocks'], data['lastBlockEpoch'])


def get_stats():
    url_stats = 'https://pooltool.s3-us-west-2.amazonaws.com/stats/stats.json'
    try:
        r = requests.get(url_stats)
        if r.ok:
            data = r.json()
        else:
            data = ''
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
        if r.ok:
            data = r.json()
        else:
            data = ''
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
        if r.ok:
            data = r.json()
        else:
            data = ''
    except requests.exceptions.RequestException as e:
        return ''
    return data


def update_competitive_win_loss(pool_id, epoch):
    data = get_competitive(pool_id, epoch)
    if data == '':
        return (0, 0)
    return (data['w'], data['l'])


def set_prefix(number):
    if number < 1000:
        return number
    else:
        return si_format(number, precision=2)


def check_delegation_changes(chat_id, ticker, delegations, new_delegations, message_type):
    if delegations > new_delegations:
        message = f'\\[ {ticker} ] Stake decreased 💔\n' \
                  f'-{set_prefix(delegations - new_delegations)}\n' \
                  f'Livestake: {set_prefix(new_delegations)}'
        if message_type == 2:
            send_message(message, chat_id, silent=True)
        else:
            send_message(message, chat_id)
    elif delegations < new_delegations:
        message = f'\\[ {ticker} ] Stake increased 💚\n' \
                  f'+{set_prefix(new_delegations - delegations)}\n' \
                  f'Livestake: {set_prefix(new_delegations)}'
        if message_type == 2:
            send_message(message, chat_id, silent=True)
        else:
            send_message(message, chat_id)


def start_telegram_update_handler():
    last_update_id = None
    while True:
        updates = get_updates(last_update_id)
        if updates is not None:
            if updates['ok']:
                if len(updates["result"]) > 0:
                    last_update_id = get_last_update_id(updates) + 1
                    handle_updates(updates)
        time.sleep(0.5)


def get_aws_event():
    try:
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
    except:
        return ''
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

    def which_slot(players):
        slots = []
        for player in players:
            slots.append(player['slot'])
        return ' vs '.join(slots)

    players = data['players']
    height = data['height']
    battle_type = what_battle_type(players)
    competitors = who_battled(players)
    slots = which_slot(players)
    for player in data['players']:
        if player['pool'] == data['winner']:
            chat_ids = db.get_chat_ids_from_pool_id(player['pool'])
            for chat_id in chat_ids:
                ticker = db.get_ticker_from_pool_id(player['pool'])[0]
                message_type = db.get_option(chat_id, ticker, 'battle')
                if message_type:
                    message = f'\\[ {ticker} ] You won! {throphy}\n' \
                              f'\n' \
                              f'{swords}{battle_type} battle: {competitors}\n' \
                              f'{clock} Slot: {slots}\n'\
                              f'{brick} Height: {height}\n' \
                              f'\n' \
                              f'https://pooltool.io/competitive'
                    if message_type == 2:
                        send_message(message, chat_id, silent=True, disable_web_preview=True)
                    else:
                        send_message(message, chat_id, disable_web_preview=True)
        else:
            chat_ids = db.get_chat_ids_from_pool_id(player['pool'])
            for chat_id in chat_ids:
                ticker = db.get_ticker_from_pool_id(player['pool'])[0]
                message_type = db.get_option(chat_id, ticker, 'battle')
                if message_type:
                    message = f'\\[ {ticker} ] You lost! {annoyed}\n' \
                              f'\n' \
                              f'{swords} {battle_type} battle: {competitors}\n' \
                              f'{brick} Height: {height}\n' \
                              f'\n' \
                              f'https://pooltool.io/competitive'
                    if message_type == 2:
                        send_message(message, chat_id, silent=True, disable_web_preview=True)
                    else:
                        send_message(message, chat_id, disable_web_preview=True)


def handle_wallet_poolchange(data):
    with open('wallet_poolchange', 'w') as f:
        f.write(json.dumps(data))
    pool_id = data['pool']
    if 'ticker' in data['change']:
        new_ticker = data['change']['ticker']['new_value']
        db.update_ticker(pool_id, new_ticker)


def handle_wallet_newpool(data):
    with open('tickers.json', 'w') as f:
        data = get_new_ticker_file()
        if data != 'error':
            json.dump(data, f)
        with open('tickers_reverse.json', 'w') as reverse_f:
            reverse_dic = {}
            for k, v in data['tickers'].items():
                reverse_dic[v] = reverse_dic.get(v, [])
                reverse_dic[v].append(k)
            json.dump(reverse_dic, reverse_f)


def handle_block_minted(data):
    with open('block_minted', 'w') as f:
        f.write(json.dumps(data))

    pool_id = data['pool']
    nbe = data['nbe']
    height = data['height']
    epoch = data['epoch']
    slot = data['slot']
    chat_ids = db.get_chat_ids_from_pool_id(pool_id)
    for chat_id in chat_ids:
        ticker = db.get_ticker_from_pool_id(pool_id)[0]
        message_type = db.get_option(chat_id, ticker, 'block_minted')
        if message_type:
            message = f'\\[ {ticker} ] New block! {fire}\n' \
                      f'\n' \
                      f'{brick} Height: {height}\n' \
                      f'{clock} Slot: {epoch}.{slot}\n' \
                      f'{tools} Total blocks: {nbe}'
            if message_type == 2:
                send_message(message, chat_id, silent=True)
            else:
                send_message(message, chat_id)


def handle_stake_change(data):
    with open('stake_change', 'w') as f:
        f.write(json.dumps(data))

    pool_id = data['pool']
    chat_ids = db.get_chat_ids_from_pool_id(pool_id)
    if chat_ids:
        ticker = db.get_ticker_from_pool_id(pool_id)[0]
        for chat_id in chat_ids:
            message_type = db.get_option(chat_id, ticker, 'stake_change')
            if message_type:
                check_delegation_changes(chat_id, ticker, data['old_stake'] / 1000000, data['livestake'] / 1000000, message_type)


def handle_block_adjustment(data):
    pool_id = data['pool']
    chat_ids = db.get_chat_ids_from_pool_id(pool_id)
    current_epoch = get_current_epoch()
    for chat_id in chat_ids:
        ticker = db.get_ticker_from_pool_id(pool_id)[0]
        message_type = db.get_option(chat_id, ticker, 'block_adjustment')
        if message_type:
            message = f'\\[ {ticker} ] Block adjustment{warning}\n' \
                      f'\n' \
                      f"Total blocks has changed: {data['old_epoch_blocks']} to {data['new_epoch_blocks']}\n" \
                      f"Epoch: {current_epoch}\n" \
                      f"\n" \
                      f"More info:\n" \
                      f"https://pooltool.io/"
            if message_type == 2:
                send_message(message, chat_id, silent=True)
            else:
                send_message(message, chat_id)


def handle_sync_status(data):
    pool_id = data['pool']
    chat_ids = db.get_chat_ids_from_pool_id(pool_id)
    for chat_id in chat_ids:
        ticker = db.get_ticker_from_pool_id(pool_id)[0]
        message_type = db.get_option(chat_id, ticker, 'sync_status')
        if message_type:
            if not data['new_status']:
                message = f'\\[ {ticker} ] Out of sync {alert}'
                if message_type == 2:
                    send_message(message, chat_id, silent=True)
                else:
                    send_message(message, chat_id)
            else:
                message = f'\\[ {ticker} ] Back in sync {like}'
                if message_type == 2:
                    send_message(message, chat_id, silent=True)
                else:
                    send_message(message, chat_id)


def handle_epoch_summary(data):
    pool_id = data['pool']
    delegations = data['liveStake'] / 1000000
    rewards_stakers = data['value_for_stakers'] / 1000000
    rewards_tax = data['value_taxed'] / 1000000
    blockstake = data['blockstake'] / 1000000
    last_epoch = data['epoch']
    wins = data['w']
    losses = data['l']
    blocks_minted = int(data['blocks'])
    epoch_slots = data['epochSlots']
    if epoch_slots:
        if blocks_minted == epoch_slots and epoch_slots > 0:
            blocks_created_text = f'/{epoch_slots} {star}'
        else:
            blocks_created_text = f'/{epoch_slots}'
    else:
        blocks_created_text = ''

    if blockstake:
        current_ros = round((math.pow((rewards_stakers / blockstake) + 1, 365) - 1) * 100, 2)
    else:
        current_ros = 0

    chat_ids = db.get_chat_ids_from_pool_id(pool_id)
    for chat_id in chat_ids:
        ticker = db.get_ticker_from_pool_id(pool_id)[0]
        message = f'\\[ {ticker} ] Epoch {last_epoch} stats {globe}\n' \
                  f'\n' \
                  f'{meat} Live stake {set_prefix(delegations)}\n' \
                  f"{tools} Blocks created: {blocks_minted}{blocks_created_text}\n" \
                  f'{swords} Slot battles: {wins}/{wins + losses}\n' \
                  f'\n' \
                  f'{moneyBag} Stakers rewards: {set_prefix(rewards_stakers)} ADA\n' \
                  f'{flyingMoney} Tax rewards: {set_prefix(round(rewards_tax))} ADA\n' \
                  f'\n' \
                  f'Current ROS: {current_ros}%\n' \
                  f'\n' \
                  f'More info at:\n' \
                  f'https://pooltool.io/pool/{pool_id}/'
        send_message(message, chat_id)


def handle_slot_loaded(data):
    pool_id = data['poolid']
    epoch = data['epoch']
    slots_assigned = data['epochSlots']
    last_epoch_validated = data['verifiedPreviousEpoch']
    chat_ids = db.get_chat_ids_from_pool_id(pool_id)
    for chat_id in chat_ids:
        ticker = db.get_ticker_from_pool_id(pool_id)[0]
        # if db.get_option(chat_id, ticker, 'sync_status'):
        message = f'\\[ {ticker} ] Epoch {epoch} {dice}\n' \
                  f'\n' \
                  f'Blocks assigned: {slots_assigned}\n' \
                  f'Last epoch validated: {last_epoch_validated}'
        send_message(message, chat_id)


def start_telegram_notifier():
    while True:
        event = get_aws_event()
        if event != '':
            delete_aws_event_from_queue(event['ReceiptHandle'])
            body = json.loads(event['Body'])
            data = body['data']
            if body['type'] == 'battle':
                handle_battle(data)
                continue
            if body['type'] == 'wallet_poolchange':
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
                handle_sync_status(data)
                continue
            elif body['type'] == 'epoch_summary':
                handle_epoch_summary(data)
                continue
            elif body['type'] == 'slots_loaded':
                handle_slot_loaded(data)

        time.sleep(0.5)


def main():
    db.setup()

    updates_handler = threading.Thread(target=start_telegram_update_handler)
    notifier = threading.Thread(target=start_telegram_notifier)

    updates_handler.start()
    notifier.start()

    while True:
        if not updates_handler.is_alive():
            updates_handler = threading.Thread(target=start_telegram_update_handler)
            updates_handler.start()
        if not notifier.is_alive():
            notifier = threading.Thread(target=start_telegram_notifier)
            notifier.start()
        time.sleep(5*60)


if __name__ == '__main__':
    main()

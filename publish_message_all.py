import urllib
import requests

from dbhelper import DBHelper

TOKEN = open('token', 'r').read()
URL = "https://api.telegram.org/bot{}/".format(TOKEN)


def get_url(url):
    try:
        response = requests.get(url)
    except requests.exceptions.RequestException as e:
        return ''
    content = response.content.decode("utf8")
    return content


def send_message(text, chat_id, reply_markup=None):
    text = urllib.parse.quote_plus(text)
    url = URL + "sendMessage?text={}&chat_id={}&parse_mode=Markdown".format(text, chat_id)
    if reply_markup:
        url += "&reply_markup={}".format(reply_markup)
    get_url(url)


message = '🌐NEW FEATURE!🌐'

db = DBHelper()

chat_ids = list(set(db.get_chat_ids()))
for chat_id in chat_ids:
    send_message(message, chat_id)
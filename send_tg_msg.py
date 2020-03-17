import urllib
import requests

TOKEN = open('token_pooltool', 'r').read()
URL = "https://api.telegram.org/bot{}/".format(TOKEN)
chat_id = 488598281


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


message = f'\\[ hej ] Block adjustment'
send_message(message, chat_id)
from dbhelper import DBHelper

db = DBHelper()

chat_ids = list(set(db.get_chat_ids()))

print(len(chat_ids))
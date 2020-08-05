import sqlite3


class DBHelper:

    def __init__(self, dbname="telegram.sqlite"):
        self.dbname = dbname
        self.conn = sqlite3.connect(dbname, check_same_thread=False)

    def setup(self):
        tblstmt = "CREATE TABLE IF NOT EXISTS items (chat_id INTEGER, ticker TEXT, pool_id text, " \
                  "delegations integer default 0 ,blocks_minted integer default 0)"
        itemidx = "CREATE UNIQUE INDEX IF NOT EXISTS itemIndex ON items (chat_id,ticker)"
        self.conn.execute(tblstmt)
        self.conn.execute(itemidx)
        
        tblstmt = "CREATE TABLE IF NOT EXISTS users (chat_id integer PRIMARY KEY, username text )"        
        self.conn.execute(tblstmt)

        tblstmt = "CREATE TABLE IF NOT EXISTS pools(pool_id , ticker TEXT," \
                  "delegations integer default 0, blocks_minted integer default 0," \
                  "PRIMARY KEY (pool_id,ticker))"
        self.conn.execute(tblstmt)
        
        tblstmt = "CREATE TABLE IF NOT EXISTS user_pool (chat_id integer , pool_id TEXT ,ticker TEXT , block_minted integer default 1, " \
                  "battle integer default 1 , sync_status integer default 1, block_adjustment integer default 1, "\
                  "stake_change integer default 1, epoch_summary integer default 1," \
                  "PRIMARY KEY (chat_id,pool_id,ticker) " \
                  "FOREIGN KEY (chat_id) REFERENCES users(chat_id) " \
                  "FOREIGN KEY (pool_id,ticker) REFERENCES pools(pool_id,ticker)) "
        self.conn.execute(tblstmt)
        self.conn.commit()

        try:
            self.migrate_db()
        except Exception as err:
            print("Assuming db is already migrated")

        try:
            self.new_userpool_columns()
        except Exception as err:
            print("Assuming new columns is already migrated")

        try:
            self.new_userpool_column_threshold()
        except Exception as err:
            print("Assuming threshold columns is already migrated")

    def get_chat_ids(self):
        stmt = "SELECT chat_id FROM users"
        args = ()
        return [x[0] for x in self.conn.execute(stmt, args)]

    def add_user(self, chat_id, username):
        stmt = "INSERT INTO users (chat_id, username) VALUES (?, ?)"
        args = (chat_id, username)
        self.conn.execute(stmt, args)
        self.conn.commit()

    def update_username(self, chat_id, username):
        stmt = "UPDATE users SET username = (?) WHERE chat_id = (?)"
        args = (chat_id, username)
        self.conn.execute(stmt, args)
        self.conn.commit()

    def add_new_pool(self, pool_id, ticker):
        if not self.does_pool_ticker_exist(pool_id, ticker):
            stmt = "INSERT INTO pools (pool_id, ticker) VALUES (?, ?)"
            args = (pool_id, ticker)
            self.conn.execute(stmt, args)
            self.conn.commit()

    def does_pool_ticker_exist(self, pool_id, ticker):
        stmt = "SELECT count(*) FROM pools WHERE pool_id = (?) AND ticker = (?)"
        args = (pool_id, ticker)
        return [x[0] for x in self.conn.execute(stmt, args)][0]

    def get_option(self, chat_id, ticker, option_type):
        stmt = f"SELECT {option_type} FROM user_pool WHERE chat_id = (?) AND ticker = (?)"
        args = (chat_id, ticker)
        try:
            return [x[0] for x in self.conn.execute(stmt, args)][0]
        except Exception as e:
            print(f'Could not get options for: {chat_id}, {ticker}, {option_type}')

    def update_option(self, chat_id, ticker, option_type, value):
        stmt = f"UPDATE user_pool SET {option_type} = (?) WHERE chat_id = (?) AND ticker = (?)"
        args = (value, chat_id, ticker)
        self.conn.execute(stmt, args)
        self.conn.commit()

    def get_chat_ids_from_pool_id(self, pool_id):
        stmt = "SELECT chat_id FROM user_pool WHERE pool_id = (?)"
        args = (pool_id,)
        return [x[0] for x in self.conn.execute(stmt, args)]

    def get_ticker_from_pool_id(self, pool_id):
        stmt = "SELECT ticker FROM pools WHERE pool_id = (?)"
        args = (pool_id,)
        return [x[0] for x in self.conn.execute(stmt, args)]

    def get_tickers_from_chat_id(self, chat_id):
        stmt = "SELECT ticker FROM user_pool WHERE chat_id = (?)"
        args = (chat_id,)
        return [x[0] for x in self.conn.execute(stmt, args)]

    def add_new_user_pool(self, chat_id, pool_id, ticker):
        stmt = "INSERT INTO user_pool (chat_id, pool_id, ticker) VALUES (?, ?, ?)"
        args = (chat_id, pool_id, ticker)
        self.conn.execute(stmt, args)
        self.conn.commit()

    def delete_user_pool(self, chat_id, ticker):
        stmt = "DELETE FROM user_pool WHERE chat_id = (?) AND ticker = (?)"
        args = (chat_id, ticker)
        self.conn.execute(stmt, args)
        self.conn.commit()

    def update_ticker(self, pool_id, new_ticker):
        stmt = f"UPDATE pools SET ticker = (?) WHERE pool_id = (?)"
        args = (new_ticker, pool_id)
        self.conn.execute(stmt, args)

        stmt = f"UPDATE user_pool SET ticker = (?) WHERE pool_id = (?)"
        args = (new_ticker, pool_id)
        self.conn.execute(stmt, args)

        self.conn.commit()

    def update_poolid(self, new_pool_id, ticker):
        stmt = f"UPDATE pools SET pool_id = (?) WHERE ticker = (?)"
        args = (new_pool_id, ticker)
        self.conn.execute(stmt, args)

        stmt = f"UPDATE user_pool SET pool_id = (?) WHERE ticker = (?)"
        args = (new_pool_id, ticker)
        self.conn.execute(stmt, args)

        self.conn.commit()

    def new_userpool_columns(self):
        stmt = "ALTER TABLE user_pool ADD epoch_summary INTEGER DEFAULT 1"
        self.conn.execute(stmt)
        stmt = "ALTER TABLE user_pool ADD slot_loaded INTEGER DEFAULT 1"
        self.conn.execute(stmt)
        self.conn.commit()

    def new_userpool_column_threshold(self):
        stmt = "ALTER TABLE user_pool ADD stake_change_threshold INTEGER DEFAULT 0"
        self.conn.execute(stmt)
        self.conn.commit()

    def new_user_columns(self):
        stmt = "ALTER TABLE users ADD string_builder TEXT"
        self.conn.execute(stmt)
        self.conn.commit()

    def migrate_db(self):
        stmt = "insert into users (chat_id) select distinct(chat_id) from items"
        self.conn.execute(stmt)
        stmt = "insert into pools (pool_id, ticker) select distinct pool_id, ticker from items"
        self.conn.execute(stmt)
        stmt = "insert into user_pool (chat_id,pool_id, ticker) select distinct chat_id, pool_id, ticker from items"
        self.conn.execute(stmt)
        self.conn.commit()

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
                  "stake_change integer default 1," \
                  "PRIMARY KEY (chat_id,pool_id,ticker) " \
                  "FOREIGN KEY (chat_id) REFERENCES users(chat_id) " \
                  "FOREIGN KEY (pool_id,ticker) REFERENCES pools(pool_id,ticker)) "
        self.conn.execute(tblstmt)
        self.conn.commit()
        # self.migrate_db()

    def add_user(self, chat_id, username):
        stmt = "INSERT INTO users (chat_id, username) VALUES (?)"
        args = (chat_id, username)
        self.conn.execute(stmt, args)
        self.conn.commit()

    def add_chat_id(self, chat_id):
        stmt = "INSERT INTO users (chat_id) VALUES (?)"
        args = (chat_id)
        self.conn.execute(stmt, args)
        self.conn.commit()

    def does_pool_ticker_exist(self, pool_id, ticker):
        stmt = "SELECT pools WHERE pool_id = (?) AND ticker = (?)"
        args = (pool_id, ticker)
        return len([x[0] for x in self.conn.execute(stmt, args)])

    def add_item(self, chat_id, ticker):
        try:
            stmt = "INSERT INTO items (chat_id, ticker) VALUES (?, ?)"
            args = (chat_id, ticker)
            self.conn.execute(stmt, args)
            self.conn.commit()
        except sqlite3.Error:
            print("Failed to add new record.")

    def delete_item(self, chat_id, ticker):
        stmt = "DELETE FROM items WHERE chat_id = (?) AND ticker = (?)"
        args = (chat_id, ticker )
        self.conn.execute(stmt, args)
        self.conn.commit()

    def get_chat_ids(self):
        stmt = "SELECT chat_id FROM items"
        args = ()
        return [x[0] for x in self.conn.execute(stmt, args)]

    def get_chat_ids_from_poolid(self, pool_id):
        stmt = "SELECT chat_id FROM items WHERE pool_id = (?)"
        args = (pool_id,)
        return [x[0] for x in self.conn.execute(stmt, args)]

    def get_ticker_from_poolid(self, pool_id):
        stmt = "SELECT ticker FROM items WHERE pool_id = (?)"
        args = (pool_id,)
        return [x[0] for x in self.conn.execute(stmt, args)]

    def get_tickers(self, chat_id):
        stmt = "SELECT ticker FROM items WHERE chat_id = (?)"
        args = (chat_id,)
        return [x[0] for x in self.conn.execute(stmt, args)]

    def get_items(self, chat_id, ticker):
        stmt = "SELECT pool_id, delegations, blocks_minted FROM items WHERE chat_id = (?) AND ticker = (?)"
        args = (chat_id, ticker)
        for x in self.conn.execute(stmt, args):
            x = x
        return x

    def update_items(self, chat_id, ticker, pool_id, delegations, blocks_minted):
        stmt = "UPDATE items SET pool_id = (?), delegations = (?), blocks_minted = (?)" \
               "WHERE chat_id = (?) AND ticker = (?)"
        args = (pool_id, delegations, blocks_minted, chat_id, ticker)
        self.conn.execute(stmt, args)
        self.conn.commit()

    def update_delegation(self, chat_id, ticker, delegations):
        stmt = "UPDATE items SET delegations = (?) WHERE chat_id = (?) AND ticker = (?)"
        args = (delegations, chat_id, ticker)
        self.conn.execute(stmt, args)
        self.conn.commit()

    def update_blocks_minted(self, chat_id, ticker, blocks_minted):
        stmt = "UPDATE items SET blocks_minted = (?) WHERE chat_id = (?) AND ticker = (?)"
        args = (blocks_minted, chat_id, ticker)
        self.conn.execute(stmt, args)
        self.conn.commit()

    def update_pool_id(self, chat_id, ticker, pool_id):
        stmt = "UPDATE items SET pool_id = (?) WHERE chat_id = (?) AND ticker = (?)"
        args = (pool_id, chat_id, ticker)
        self.conn.execute(stmt, args)
        self.conn.commit()

    def migrate_db(self):
        stmt = "insert into users (chat_id) select distinct(chat_id) from items"
        self.conn.execute(stmt)
        stmt = "insert into pools (pool_id, ticker) select distinct pool_id, ticker from items"
        self.conn.execute(stmt)
        stmt = "insert into user_pool (chat_id,pool_id, ticker) select distinct chat_id, pool_id, ticker from items"
        self.conn.execute(stmt)

        self.conn.commit()
    

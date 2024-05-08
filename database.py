import asyncio
import aiosqlite


class Database:
    def __init__(self, loop: asyncio.AbstractEventLoop):
        self.conn, self.loop = None, loop
        self.test_mode = False  # Set to True to print while testing



    # CONNESSIONI E GESTIONI BASSO LIVELLO
    async def connect(self):
        self.conn = await aiosqlite.connect('data/maindb.db', loop=self.loop)
        await self.execute("CREATE TABLE IF NOT EXISTS last (`ID` INTEGER PRIMARY KEY AUTOINCREMENT , `chat_id` BIGINT NOT NULL, `lastid` BIGINT NOT NULL DEFAULT 0);", [], commit=True)
        return self.conn

    async def execute(self, sql: str, values: tuple, commit: bool = False, fetch: int = 0):
        # If no connection is established, connect
        if not self.conn:
            await self.connect()
            await asyncio.sleep(0.1)

        # Test mode, print sql and values
        if self.test_mode:
            print(sql, values)

        # Execute the query
        try:
            cursor = await self.conn.cursor()
        except aiosqlite.ProgrammingError:
            await self.connect()
            cursor = await self.conn.cursor()

        try:
            executed = await cursor.execute(sql, values)
        except aiosqlite.ProgrammingError:
            await self.connect()
            executed = await cursor.execute(sql, values)


        # If fetch is True, return the result
        fetch = await cursor.fetchone() if fetch == 1 else cursor.rowcount if fetch == 2 else await cursor.fetchall() if fetch == 3 else None


        # Commit Db
        if commit:
            await self.conn.commit()

        return fetch

    async def close(self):
        await self.conn.close()



    # GESTIONE INSERIMENTI | ELIMINAZIONI
    async def addids(self, chat_id: int):
        fc = await self.execute('SELECT * FROM last WHERE chat_id = ?', (chat_id,), fetch=1)
        if not fc:
            await self.execute('INSERT INTO last (chat_id) VALUES (?)', (chat_id,), commit=True)
        query='CREATE TABLE IF NOT EXISTS `'+str(chat_id)+'` (`user_id` BIGINT PRIMARY KEY, `reputation` BIGINT DEFAULT 0);'
        fc = await self.execute(query, [], commit=True)
        return True if not fc else False

    async def getLastmsg(self, chat_id: int):
        return await self.execute('SELECT lastid FROM last WHERE chat_id = ?', (chat_id,), fetch=1)

    

    async def generaNuoviRep(self, chat_id, user_id):
        await self.execute(f'INSERT OR IGNORE INTO `{chat_id}` (user_id) VALUES (?)', (user_id, ), commit=True)

    async def updateLastmsg(self, lastmsg: int, chat_id: int):
        await self.execute('UPDATE last SET lastid = ? WHERE chat_id = ?', (lastmsg, chat_id, ), commit=True)

    async def updateReputazione(self, rep: int, chat_id: int, user_id: int):
        await self.execute(f'UPDATE `{chat_id}` SET reputation = ? WHERE user_id = ?', (rep, user_id, ), commit=True)

    async def getReputazione(self, chat_id: int, user_id: int):
        return await self.execute(f'SELECT reputation FROM `{chat_id}` WHERE user_id = ?', (user_id,), fetch=1)

    async def top10rep(self, chat_id: int):
        return await self.execute(f'SELECT user_id, reputation FROM `{chat_id}` ORDER BY reputation DESC LIMIT 10', [], fetch=3)

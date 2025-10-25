import aiosqlite
from config import DATABASE

class DBInterface:
    def __init__(self):
        self.db = None
        self.path = DATABASE["path"]

    async def open(self):
        try:
            self.db = await aiosqlite.connect(self.path)
            await self._setup()
        except Exception as e:
            return f"DB Failed to open: {e}"

    async def __aenter__(self):
        await self.open()

    async def close(self):
        if self.db:
            await self.db.close()
            self.db = None
        return True

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def _execute(self, statement: str) -> aiosqlite.Cursor | None:
        if self.db is None:
            return None
        cursor = await self.db.execute(statement)
        return cursor
    
    async def _commit(self) -> bool | None:
        if self.db is None:
            return None
        return await self.db.commit() == True

    async def _setup(self):
        cur = await self._execute('SELECT name FROM sqlite_master WHERE name ="Bins"')
        if cur and await cur.fetchone() is None:
            query = '''
            CREATE TABLE Bins (
                BinID INTEGER NOT NULL,
                Barcode VARCHAR(20) NOT NULL,
                PRIMARY KEY (BinID)
            );'''
            await cur.execute(query)
        cur = await self._execute('SELECT name FROM sqlite_master WHERE name ="Cards"')
        if cur and await cur.fetchone() is None:
            query = '''
            CREATE TABLE Cards (
                CardID INTEGER NOT NULL,
                BinID INTEGER NOT NULL,
                Position INTEGER NOT NULL,
                Data TEXT,
                PRIMARY KEY (CardID),
                FOREIGN KEY (BinID) REFERENCES Bins(BinID)
            );'''
            await cur.execute(query)

    async def check_barcode(self, barcode: str):
        cur = await self._execute(f'SELECT BinID FROM Bins WHERE Barcode ="{barcode}"')
        if cur:
            ret = await cur.fetchone()
            if ret:
                return ret[0]
        return None

    async def add_barcode(self, barcode: str):
        query = f'INSERT INTO Bins (Barcode) VALUES ({barcode});'
        await self._execute(query)
        await self._commit()


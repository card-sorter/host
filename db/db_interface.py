import asyncio

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
        return self

    async def close(self):
        # Close DB connection.
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
        return bool(await self.db.commit())

    async def _setup(self):
        query = '''
        CREATE TABLE NOT EXISTS Bins (
            BinID INTEGER NOT NULL,
            PRIMARY KEY (BinID)
        );'''
        await self._execute(query)
        query = '''
        CREATE TABLE IF NOT EXISTS Cards (
            CardID INTEGER NOT NULL,
            BinID INTEGER NOT NULL,
            Position INTEGER NOT NULL,
            Data TEXT,
            PRIMARY KEY (CardID),
            FOREIGN KEY (BinID) REFERENCES Bins(BinID)
        );'''
        await self._execute(query)
        query = '''
        CREATE TABLE IF NOT EXISTS Barcodes (
            Barcode VARCHAR NOT NULL,
            BinID INTEGER,
            PRIMARY KEY (Barcode)
            FOREIGN KEY (BinID) REFERENCES Bins(BinID)
        )
        '''
        await self._execute(query)

    async def check_barcode(self, barcode: str):
        cur = await self._execute(
            f"SELECT Barcode, BinID FROM Barcodes WHERE Barcode ='{barcode}'"
        )
        if cur:
            ret = await cur.fetchone()
            if ret:
                return ret[0]
        return None

    async def add_barcode(self, barcode: str):
        query = f"INSERT INTO Barcodes (Barcode) VALUES ('{barcode}');"
        await self._execute(query)
        await self._commit()


async def main():
    async with DBInterface() as db:
        print(await db.check_barcode("abc"))

if __name__ == "__main__":
    asyncio.run(main())

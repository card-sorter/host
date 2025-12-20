import db.db_interface
import asyncio

            
async def run():
    await db.db_interface.main()

if __name__ == "__main__":
    asyncio.run(run())
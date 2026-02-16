import hardware.hal
import asyncio

            
async def run():
    await hardware.hal.main()

if __name__ == "__main__":
    asyncio.run(run())
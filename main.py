from queue_manager import command_queue, event_queue
from controller import controller
from api import websocket
import asyncio
from common import CommandEvent


async def ainput(prompt: str) -> str:
    return await asyncio.to_thread(input, prompt)

async def runner():
    controllertask = asyncio.create_task(controller.run_forever())
    webservertask = asyncio.create_task(websocket.run_and_wait())
    await asyncio.sleep(1)
    while True:
        user_message = await ainput("send command")
        if user_message == "quit":
            break
        command_queue.put_nowait(CommandEvent(user_message))
        
    webservertask.cancel()
    try:
        await webservertask
    except asyncio.CancelledError:
        print('webserver stopped')

    controllertask.cancel()
    try:
        await controllertask
    except asyncio.CancelledError:
        print('controller stopped')

if __name__ == "__main__":
    asyncio.run(runner())
from queue_manager import command_queue, event_queue
from controller import controller
from api import websocket
import asyncio
from common import CommandEvent

async def runner():
    controllertask = asyncio.create_task(controller.run_forever())
    webservertask = asyncio.create_task(websocket.run_and_wait())
    message = ""
    while message != "quit":
        user_message = input("send command")
        if user_message != "quit":
            command_queue.put_nowait(CommandEvent(user_message))

if __name__ == "__main__":
    asyncio.run(runner())
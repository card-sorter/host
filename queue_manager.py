import asyncio
import common

command_queue: asyncio.Queue[common.Event] = asyncio.Queue()
event_queue: asyncio.Queue[common.Event] = asyncio.Queue()


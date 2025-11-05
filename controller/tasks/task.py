import asyncio
from common import *
from db.db_interface import DBInterface
from hardware.hal import HAL


class TaskContext:
    def __init__(self, hal: HAL, event_queue: asyncio.Queue, database:DBInterface):
        self.hal: HAL = hal
        self.bins = self.hal.bins
        self.default_bins = self.hal.default_bins
        self._event_queue: asyncio.Queue = event_queue
        self.database = database
        pass

    def emit(self, event: Event):
        self._event_queue.put_nowait(event)


class TaskController:
    def __init__(self, ctx: TaskContext):
        self.ctx = ctx
        self.name:str = ""
        self.description:str = ""

    async def run(self):
        pass

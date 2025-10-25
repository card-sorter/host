import asyncio
from common import *
from hardware.hal import HAL


class TaskContext:
    def __init__(self, hal: HAL, event_queue: asyncio.Queue):
        self.hal: HAL = hal
        self.bins = self.hal.bins
        self._event_queue: asyncio.Queue = event_queue
        pass

    def emit(self, event: Event):
        self._event_queue.put_nowait(event)


class TaskController:
    def __init__(self, ctx: TaskContext):
        self.ctx = ctx

    async def run(self):
        pass

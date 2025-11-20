import asyncio

from queue_manager import command_queue, event_queue
from importlib import import_module
from config import *
from common import *
import os


class Controller:
    def __init__(self):
        self._state = ""
        self._tasks = []


    def _load_tasks(self):
        self._modules = []
        for task in TASKS:
            path = "controller.tasks." + task["module"]
            self._modules.append(import_module(path))

    async def loop(self):
        while True:
            command = await command_queue.get()


if __name__ == "__main__":
    controller = Controller()
    controller._load_tasks()

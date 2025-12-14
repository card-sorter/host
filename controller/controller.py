import asyncio
from queue_manager import command_queue, event_queue
from common import StateEvent, ErrorEvent, States
from controller.routes import ROUTES
from config import TASKS
from importlib import import_module


class Controller:
    def __init__(self):
        self.state = States.IDLE
        self._tasks = []
        self._current = None


    def _load_tasks(self):
        self._modules = []
        for task in TASKS:
            path = "controller.tasks." + task["module"]
            self._modules.append(import_module(path))


    async def on_state_change(self, message: str | None = None):
        print(States(self.state).name)
        event_queue.put_nowait(StateEvent(States(self.state).name, message))


    async def set_state(self, new_state: str, message: str | None = None):
        if self.state != new_state:
            self.state = new_state
            await self.on_state_change(message)
            return True
        return False

    async def on_command(self, command):
        handler = ROUTES.get((command.value or "").strip().lower())
        if handler:
            await handler(self, command)
        else:
            event_queue.put_nowait(ErrorEvent(f"route {command.value} not found"))

    async def run(self):
        await self.on_state_change("Host ready")
        while True:
            cmd_event = await command_queue.get()
            await self.on_command(cmd_event)

async def run_forever():
    controller = Controller()
    asyncio.create_task(controller.run())
    await asyncio.Event().wait()
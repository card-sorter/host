import asyncio
from controller.tasks.task import TaskContext
from db import db_interface
from queue_manager import command_queue, event_queue
from common import StateEvent, ErrorEvent, States
from controller.routes import ROUTES
from config import TASKS, DEFAULT_TASK
from importlib import import_module
from hardware.hal import HAL


class Controller:
    def __init__(self):
        self.state = States.IDLE
        self._tasks = []
        self.current_task = None
        self._hal = HAL()
        self._db = db_interface.DBInterface()


    def _load_tasks(self):
        self._tasks = []
        for task in TASKS:
            path = "controller.tasks." + task["module"]
            module = import_module(path)
            task_class = None
            if hasattr(module, '__all__') and module.__all__:
                class_name = module.__all__[0]
                task_class = getattr(module, class_name)
            self._tasks.append(task_class)
        print(self._tasks)

    async def start_task(self, tasknum = DEFAULT_TASK):
        print(f"Starting {TASKS[tasknum]["name"]}")
        await self._hal.open()
        self._hal.open_camera()
        ctx = TaskContext(self._hal, event_queue, self._db)
        task = self._tasks[tasknum](ctx)
        try: 
            await task.run()
        except:
            await self.set_state(new_state = States.FINISHED)
        await self._hal.close()


    async def on_state_change(self, message: str | None = None):
        print(States(self.state).name)
        event_queue.put_nowait(StateEvent(States(self.state).name, message))


    async def set_state(self, new_state, message: str | None = None):
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
        self._load_tasks()
        await self.on_state_change("Host ready")
        while True:
            cmd_event = await command_queue.get()
            await self.on_command(cmd_event)

async def run_forever():
    controller = Controller()
    asyncio.create_task(controller.run())
    await asyncio.Event().wait()
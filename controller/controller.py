import asyncio
import pkgutil
from controller.tasks.task import TaskContext, TaskController
from db import db_interface
from queue_manager import command_queue, event_queue
from common import StateEvent, ErrorEvent, States
from controller.routes import ROUTES
from config import DEFAULT_TASK
from importlib import import_module
from hardware.hal import HAL
import controller.tasks as _tasks_pkg


class Controller:
    def __init__(self):
        self.state = States.IDLE
        self._tasks = []
        self.current_task = None
        self._hal = HAL()
        self._db = db_interface.DBInterface()


    def _load_tasks(self):
        self._tasks = []
        for importer, modname, ispkg in pkgutil.iter_modules(_tasks_pkg.__path__):
            if modname == "task":
                continue
            module = import_module(f"controller.tasks.{modname}")
            task_class = None
            if hasattr(module, '__all__') and module.__all__:
                class_name = module.__all__[0]
                task_class = getattr(module, class_name)
            if task_class and issubclass(task_class, TaskController):
                name = getattr(module, 'TASK_NAME', modname)
                description = getattr(module, 'TASK_DESCRIPTION', '')
                self._tasks.append({
                    "name": name,
                    "description": description,
                    "class": task_class,
                })
        print(self._tasks)

    def _get_task(self, task_id=DEFAULT_TASK):
        if isinstance(task_id, int):
            return self._tasks[task_id]
        for t in self._tasks:
            if t["name"] == task_id:
                return t
        raise ValueError(f"Task '{task_id}' not found")

    async def start_task(self, task_id=DEFAULT_TASK):
        task_info = self._get_task(task_id)
        print(f"Starting {task_info['name']}")
        await self._hal.open()
        self._hal.open_camera()
        await self._db.open()
        ctx = TaskContext(self._hal, event_queue, self._db)
        task = task_info["class"](ctx)
        try: 
            await task.run()
        except Exception as e:
            print(e)
            await self.set_state(new_state = States.FINISHED)
        await self._hal.close()
        await self._db.close()
        await self.set_state(new_state = States.FINISHED)


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
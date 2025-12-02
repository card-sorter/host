import asyncio
from host.queue_manager import command_queue, event_queue
from host.common import StateEvent, ErrorEvent, STATES
from host.controller.routes import ROUTES


class Controller:
    def __init__(self):
        self.state = STATES["IDLE"]

    async def on_state_change(self, message: str | None = None):
        event_queue.put_nowait(StateEvent(self.state, message))

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

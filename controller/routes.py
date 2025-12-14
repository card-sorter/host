import asyncio
from common import States


async def start(controller, command):
    controller.current_task = asyncio.create_task(controller.start_task())
    await controller.set_state(States.RUNNING)


async def resume(controller, command):
    await controller.set_state(States.RUNNING)


async def stop(controller, command):
    await controller.set_state(States.PAUSED)


async def estop(controller, command):
    await controller.set_state(States.E_STOP)


async def reset(controller, command):
    await controller.set_state(States.RESET)
    await controller.set_state(States.IDLE)

ROUTES = {
    "start": start,
    "resume": resume,
    "stop": stop,
    "estop": estop,
    "reset": reset,
}
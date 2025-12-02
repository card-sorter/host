from host.common import STATES


async def start(controller, command):
    await controller.set_state(STATES["RUNNING"])


async def resume(controller, command):
    await controller.set_state(STATES["RUNNING"])


async def stop(controller, command):
    await controller.set_state(STATES["PAUSED"])


async def estop(controller, command):
    await controller.set_state(STATES["E_STOP"])


async def reset(controller, command):
    await controller.set_state(STATES["RESET"])
    await controller.set_state(STATES["IDLE"])

ROUTES = {
    "start": start,
    "resume": resume,
    "stop": stop,
    "estop": estop,
    "reset": reset,
}
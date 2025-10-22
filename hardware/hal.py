import asyncio
import config
from cnc_serial import SerialController
from common import Bin
import cv2

class HAL:
    def __init__(self, port=config.SERIAL_PORT, baud_rate=config.BAUD_RATE):
        self._connected = False
        self._serialController = SerialController(port=port, baud_rate=baud_rate)
        self._bins = [Bin(pos[0], pos[1], config.BIN_HEIGHT) for pos in config.BIN_POSITIONS]
        self._height = config.MOVEMENT_HEIGHT
        self._bottom_limit = config.BIN_BOTTOM_LIMIT
        self._camera = None

    @property
    def bins(self):
        return self._bins

    async def open(self):
        self._camera = cv2.VideoCapture(0)
        if not self._camera.isOpened():
            return "Webcam not connected"

        result = await self._serialController.open()
        if result.find("Connected"):
            self._connected = True
        return result

    async def _check_disconnection(self)->bool:
        return False

    async def _move_to_bin(self, target):
        command = f"G0 X{target.x} Y{target.y}"
        ret = await self._serialController.send_command(command, timeout=5)
        if ret == "Timeout":
            await self._check_disconnection()
        return ret

    async def _move_to_height(self, height):
        command = f"G0 Z{height}"
        ret = await self._serialController.send_command(command, timeout=5)
        return ret

    async def _lift_card(self):
        pass

    async def _drop_card(self):
        pass

    async def move_card(self, source, target):
        if self._connected:
            try:
                await self._move_to_bin(source)
                await self._lift_card()
                await self._move_to_bin(target)
                await self._drop_card()
                return True
            finally:
                pass
        return False

    async def scan_card(self, source, target):
        pass


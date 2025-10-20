import asyncio
import config
from cnc_serial import SerialController
from common import Bin

class HAL:
    def __init__(self, port=config.SERIAL_PORT, baud_rate=config.BAUD_RATE):
        self.serialController = SerialController(port=port, baud_rate=baud_rate)
        self.bins = [Bin(pos[0], pos[1], config.BIN_HEIGHT) for pos in config.BIN_POSITIONS]
        self.height = config.MOVEMENT_HEIGHT
        self.bottom_limit = config.BIN_BOTTOM_LIMIT
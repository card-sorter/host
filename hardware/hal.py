import asyncio
import config
from cnc_serial import SerialController

class HardwareHAL:
    def __init__(self, port=config.SERIAL_PORT, baud_rate=config.BAUD_RATE):
        self.serialController = SerialController(port=port, baud_rate=baud_rate)
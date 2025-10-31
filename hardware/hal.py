import asyncio
import random
import time

#import numpy as np

import config
from cnc_serial import SerialController
from common import Bin


class HAL:
    def __init__(self, port=config.SERIAL_PORT, baud_rate=config.BAUD_RATE):
        self._connected = False
        self._serialController = SerialController(port=port, baud_rate=baud_rate)
        self._bins = [Bin(pos[0], pos[1], config.BIN_HEIGHT) for pos in config.BIN_POSITIONS]
        self._height = config.MOVEMENT_HEIGHT
        self._bottom_limit = config.BIN_BOTTOM_LIMIT
        self._probe_safety_distance = config.PROBE_SAFETY_DISTANCE
        self._probe_feedrate = config.PROBE_FEEDRATE
        self._camera = None
        self._homed = False
        self._card_drop_offset = config.CARD_DROP_OFFSET
        self._card_lift_delay = config.CARD_LIFT_DELAY

    @property
    def bins(self):
        return self._bins

    async def open(self):
        # self._camera = cv2.VideoCapture(0)
        # if not self._camera.isOpened():
        #    return "Webcam not connected"

        result = await self._serialController.open()
        if result.find("Connected") > -1:
            self._connected = True
            return True
        return False

    async def close(self):
        await self._set_vacuum(False, True)
        await self._move_to_height(self._height)
        await self._set_vacuum(False, False)
        await self._serialController.close()
        self._connected = False

    async def _check_disconnection(self) -> bool:
        # TODO: handle random disconnects
        pass

    async def _send_command(self, command: str, find: str = "ok", delim="\n", timeout: int=5):
        if not self._homed:
            status = await self._serialController.home()
            self._homed = status == "ok"
            if not self._homed: return False
            await self._set_vacuum(True, False)
        ret = await self._serialController.send_command(command, timeout=timeout, delimiter=delim)
        if find not in ret:
            # TODO: error check
            return False
        return ret

    async def _move_to_bin(self, target: Bin) -> bool:
        command = f"G0 X{target.x} Y{target.y}"
        return await self._send_command(command)

    async def _move_to_height(self, height: float) -> bool:
        command = f"G0 Z{height}"
        return await self._send_command(command)

    async def _probe_height(self, bin: Bin) -> bool:
        height = bin.z + self._probe_safety_distance
        if not await self._move_to_height(height):
            return False
        timeout = abs(self._bottom_limit-height)/self._probe_feedrate*60 + 2
        data = await self._send_command(
            f"G38.2 Z{self._bottom_limit} F{self._probe_feedrate}",
            timeout=timeout,
            delim="ok\r\n"
        )
        if not data:
            return False
        if "PRB" in data:
            data = data.split(":")
            data = data[1].split(",")
            bin.set_z(float(data[2]))
        else:
            return False
        return True

    async def _set_vacuum(self, pump: bool, solenoid: bool) -> bool:
        if solenoid: command = "M4"
        else: command = "M3"
        if pump: command = command + " S1000"
        else: command = command + " S0"
        return await self._send_command(command)

    async def _lift_card(self, bin: Bin) -> bool:
        if not await self._probe_height(bin): return False
        if not await self._set_vacuum(True, False): return False
        if not await self._send_command(f"G01 Z{bin.z + 5} F500"): return False
        if not await self._send_command(f"G01 Z{bin.z + self._card_drop_offset} F2000"): return False
        #if not await self._send_command(f"G04 P{self._card_lift_delay}"): return False
        return await self._move_to_height(self._height)

    async def _drop_card(self, bin: Bin) -> bool:
        if not await self._probe_height(bin): return False
        if not await self._set_vacuum(True, True): return False
        if not await self._send_command("G04 P0.2"): return False
        if not await self._move_to_height(bin.z + self._card_drop_offset): return False
        if not await self._send_command("G04 P0.1"): return False
        return await self._move_to_height(self._height)

    async def move_card(self, source, target) -> bool:
        if self._connected:
            if not await self._move_to_bin(source): return False
            if not await self._lift_card(source): return False
            if not await self._move_to_bin(target): return False
            return await self._drop_card(target)
        return False

#    async def scan_card(self, source, target) -> None|np.ndarray:
#        pass

async def main():
    hal = HAL()
    print(await hal.open())
    print("connected")
    bins = hal.bins
    binlist = [1, 3]
    await hal.move_card(bins[1], bins[3])
    start = time.time()
    count = 50
    for i in range(count):
        print(await hal.move_card(bins[4], bins[binlist[i%2]]))
    await hal.close()
    end = time.time()
    print("average time per move:")
    print((end-start)/count)

if __name__ == "__main__":
    asyncio.run(main())

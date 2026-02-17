import asyncio
import time
from typing import final
import cv2
import numpy as np
import config
from hardware.cnc_serial import SerialController
from common import (
    Bin, HALError, ConnectionError, ProbeError, MotionError, CameraError, VacuumError,
)
from hardware.projector import Projector
from picamera2 import Picamera2


@final
class HAL:
    def __init__(self, port:str=config.SERIAL_PORT, baud_rate:int=config.BAUD_RATE):
        self._connected = False
        self._serialController = SerialController(port=port, baud_rate=baud_rate)
        self._bins = [Bin(pos[0], pos[1], config.BIN_HEIGHT) for pos in config.BIN_POSITIONS]
        self._camera_bin = config.CAMERA_BIN
        self._camera_height = config.CAMERA_HEIGHT
        self._height = config.MOVEMENT_HEIGHT
        self._bottom_limit = config.BIN_BOTTOM_LIMIT
        self._probe_safety_distance = config.PROBE_SAFETY_DISTANCE
        self._probe_feedrate = config.PROBE_FEEDRATE
        self._camera = None
        self._focused = True
        self._homed = False
        self._card_drop_offset = config.CARD_DROP_OFFSET
        self._card_lift_delay = config.CARD_LIFT_DELAY
        self.bin_max_len = 0
        self.projector = Projector(*config.WARP_INFO)
        self._event_queue = None

    @property
    def bins(self):
        return self._bins

    @property
    def default_bins(self):
        ret = list(self.bins)
        ret.pop(self._camera_bin)
        return ret

    async def open(self):
        """Open serial connection. Raises ConnectionError on failure."""
        await self._serialController.open()
        self._connected = True

    def open_camera(self):
        """Initialize camera. Raises CameraError on failure."""
        try:
            self._camera = Picamera2()
            cam_config = self._camera.create_still_configuration({'format': 'RGB888'})
            self._camera.configure(cam_config)
            self._camera.start()
            self._camera.set_controls(config.CAMERA_CONFIG)
        except Exception as e:
            raise CameraError(f"Failed to initialize camera: {e}") from e

    async def close(self):
        """Best-effort cleanup. Won't raise."""
        try:
            await self._set_vacuum(False, True)
            await self._move_to_height(self._height)
            await self._set_vacuum(False, False)
        except Exception:
            pass
        try:
            await self._serialController.close()
        except Exception:
            pass
        if self._camera:
            try:
                self._camera.stop()
                self._camera.close()
            except Exception:
                pass
        self._connected = False
        self._homed = False

    async def _ensure_homed(self):
        """Home the machine if not already homed. Raises HomingError on failure."""
        if not self._homed:
            await self._serialController.home()
            self._homed = True
            await self._send_command("G92 X0 Z0")
            await self._set_vacuum(True, False)

    async def _send_command(self, command: str, delim="\n", timeout: int|float=5) -> str:
        """Send a G-code command. Raises MotionError if GRBL doesn't respond 'ok'.
        Lets TimeoutError/ConnectionError propagate from serial layer."""
        await self._ensure_homed()
        ret = await self._serialController.send_command(command, timeout=timeout, delimiter=delim)
        if "ok" not in ret:
            raise MotionError(f"Command '{command}' failed: {ret}")
        return ret

    async def _move_to_bin(self, target: Bin):
        command = f"G0 X{target.x} Y{target.y}"
        await self._send_command(command)

    async def _move_to_height(self, height: float):
        command = f"G0 Z{height}"
        await self._send_command(command)

    async def _probe_height(self, bin: Bin):
        """Probe to find bin surface height. Raises ProbeError on failure."""
        height = bin.z + self._probe_safety_distance
        await self._move_to_height(height)
        try:
            data = await self._send_command(
                f"G38.2 Z{self._bottom_limit} F{self._probe_feedrate}",
                timeout=100,
                delim="ok\r\n"
            )
        except MotionError as e:
            raise ProbeError(f"Probe command failed: {e}") from e
        if "PRB" not in data:
            raise ProbeError(f"Probe response missing PRB data: {data}")
        try:
            parts = data.split(":")
            coords = parts[1].split(",")
            bin.set_z(float(coords[2]))
        except (IndexError, ValueError) as e:
            raise ProbeError(f"Malformed PRB response: {data}") from e

    async def _set_vacuum(self, pump: bool, solenoid: bool):
        """Control vacuum. Raises VacuumError on failure."""
        if solenoid: command = "M4"
        else: command = "M3"
        if pump: command = command + " S80"
        else: command = command + " S0"
        try:
            await self._send_command(command)
        except MotionError as e:
            raise VacuumError(f"Vacuum command failed: {e}") from e

    async def _lift_card(self, bin: Bin):
        await self._probe_height(bin)
        await self._set_vacuum(True, False)
        await self._send_command(f"G01 Z{bin.z + 5} F500")
        await self._send_command(f"G01 Z{bin.z + self._card_drop_offset} F2000")
        await self._move_to_height(self._height)

    async def _drop_card(self, bin: Bin):
        await self._probe_height(bin)
        await self._set_vacuum(True, True)
        await self._send_command("G04 P0.2")
        await self._move_to_height(bin.z + self._card_drop_offset)
        await self._send_command("G04 P0.1")
        await self._move_to_height(self._height)

    async def _safe_state(self):
        """Best-effort recovery: raise head, turn off vacuum. Won't raise."""
        try:
            await self._move_to_height(self._height)
        except Exception:
            pass
        try:
            await self._set_vacuum(False, False)
        except Exception:
            pass

    async def move_card(self, source, target):
        """Move a card from source bin to target bin.
        Raises HALError subclasses on failure after attempting safe-state recovery."""
        if not self._connected:
            raise ConnectionError("HAL not connected")
        try:
            await self._move_to_bin(source)
            await self._lift_card(source)
            await self._move_to_bin(target)
            await self._drop_card(target)
        except HALError:
            await self._safe_state()
            raise

    async def scan_card(self, source, target) -> np.ndarray:
        """Scan a card: pick up, photograph, place down. Returns the image.
        Raises HALError subclasses on failure, CameraError if no camera."""
        if not self._connected:
            raise ConnectionError("HAL not connected")
        if not self._camera:
            raise CameraError("Camera not initialized")
        try:
            await self._move_to_bin(source)
            await self._lift_card(source)
            await self._move_to_bin(self.bins[self._camera_bin])
            await self._move_to_height(self._camera_height)
            await self._send_command("G04 P0.5")
            if not self._focused:
                self._camera.autofocus_cycle()
            frame = self._camera.capture_array()
            frame = self.projector.project(frame)
            frame = cv2.resize(frame, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
            await self._move_to_height(self._height)
            await self._move_to_bin(target)
            await self._drop_card(target)
            return frame
        except HALError:
            await self._safe_state()
            raise


async def main():
    hal = HAL()
    print(hal.open_camera())
    print(await hal.open())
    print("connected")
    bins = hal.bins
    binlist = [2, 3]
    await hal.move_card(bins[2], bins[3])
    start = time.time()
    count = 50
    for i in range(count):
        await hal.move_card(bins[1], bins[binlist[i%2]])
    await hal.close()
    end = time.time()
    print("average time per move:")
    print((end-start)/count)

if __name__ == "__main__":
    asyncio.run(main())

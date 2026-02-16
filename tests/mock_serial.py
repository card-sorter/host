"""
Mock implementation of SerialController that simulates GRBL responses in-memory.
Drop-in replacement for hardware.cnc_serial.SerialController — no hardware needed.
"""

import asyncio
import re
from queue_manager import event_queue
from common import NotifyEvent, ErrorEvent


class MockSerialController:
    def __init__(self, port: str = "/dev/ttyACM0", baud_rate: int = 115200, debug: bool = False):
        self.port = port
        self._baud_rate = baud_rate
        self.debug = debug

        self._connected = False
        self._command_lock = None
        self._WCO = [0.0, 0.0, 0.0]

        # Simulated machine state
        self._pos = [0.0, 0.0, 0.0]  # X, Y, Z
        self._state = "Idle"
        self._homed = False
        self._spindle_mode = "M3"
        self._spindle_speed = 0

        # Error simulation flags
        self.simulate_timeout = False
        self.simulate_disconnect = False
        self.simulate_home_error = False

        # Command log for test assertions
        self.command_log: list[str] = []

    async def __aenter__(self):
        await self.open()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def open(self) -> str:
        self._command_lock = asyncio.Lock()

        if self.simulate_disconnect:
            event_queue.put_nowait(ErrorEvent(f"Error when connecting to {self.port}: simulated disconnect"))
            return f"Error when connecting to {self.port}: simulated disconnect"

        self._connected = True
        self._pos = [0.0, 0.0, 0.0]
        event_queue.put_nowait(NotifyEvent(f"Connected to {self.port}"))
        return f"Connected to {self.port}"

    async def close(self):
        if self._connected:
            self._connected = False
            event_queue.put_nowait(NotifyEvent(f"Disconnected from {self.port}."))

    async def send_command(self, command: str, delimiter: str = "\n", timeout: float = 30.0) -> str:
        if not self._connected:
            event_queue.put_nowait(ErrorEvent(f"Not connected to {self.port}"))
            return "Not Connected"

        async with self._command_lock:
            cmd = command.strip()
            self.command_log.append(cmd)

            if self.debug:
                print(f"MockSerial Command: {cmd}")

            if self.simulate_timeout:
                event_queue.put_nowait(ErrorEvent(f"Timeout on {self.port} when running {command}"))
                self._connected = False
                return "Timeout"

            if self.simulate_disconnect:
                self._connected = False
                return "Not Connected"

            return self._process_command(cmd)

    def _process_command(self, cmd: str) -> str:
        upper = cmd.upper()

        # Status query
        if cmd == "?":
            return self._build_status_response()

        # Homing
        if upper == "$H":
            if self.simulate_home_error:
                return "error:9\r\n"
            self._homed = True
            self._pos = [0.0, 0.0, 0.0]
            return "ok\r\n"

        # Unlock
        if upper == "$X":
            return "ok\r\n"

        # Set position (G92)
        if upper.startswith("G92"):
            self._apply_position_params(cmd)
            return "ok\r\n"

        # Rapid move (G0)
        if upper.startswith("G0 ") or upper == "G0":
            self._apply_position_params(cmd)
            return "ok\r\n"

        # Linear move (G01 / G1)
        if upper.startswith("G01") or upper.startswith("G1 "):
            self._apply_position_params(cmd)
            return "ok\r\n"

        # Dwell (G4 / G04)
        if upper.startswith("G4 ") or upper.startswith("G04"):
            return "ok\r\n"

        # Probe (G38.2)
        if upper.startswith("G38.2"):
            return self._handle_probe(cmd)

        # Spindle commands (M3/M4)
        if upper.startswith("M3") or upper.startswith("M4"):
            self._handle_spindle(cmd)
            return "ok\r\n"

        # Default: treat as ok
        return "ok\r\n"

    def _apply_position_params(self, cmd: str):
        x_match = re.search(r'[Xx]([-\d.]+)', cmd)
        y_match = re.search(r'[Yy]([-\d.]+)', cmd)
        z_match = re.search(r'[Zz]([-\d.]+)', cmd)
        if x_match:
            self._pos[0] = float(x_match.group(1))
        if y_match:
            self._pos[1] = float(y_match.group(1))
        if z_match:
            self._pos[2] = float(z_match.group(1))

    def _handle_probe(self, cmd: str) -> str:
        z_match = re.search(r'[Zz]([-\d.]+)', cmd)
        if z_match:
            target_z = float(z_match.group(1))
            # Simulate probe contact partway to target
            probe_z = (self._pos[2] + target_z) / 2
            self._pos[2] = probe_z
        return f"[PRB:{self._pos[0]:.3f},{self._pos[1]:.3f},{self._pos[2]:.3f}:1]\r\nok\r\n"

    def _handle_spindle(self, cmd: str):
        upper = cmd.upper()
        if upper.startswith("M4"):
            self._spindle_mode = "M4"
        else:
            self._spindle_mode = "M3"
        s_match = re.search(r'[Ss]([\d.]+)', cmd)
        if s_match:
            self._spindle_speed = float(s_match.group(1))
        else:
            self._spindle_speed = 0

    def _build_status_response(self) -> str:
        mpos = f"{self._pos[0]:.3f},{self._pos[1]:.3f},{self._pos[2]:.3f}"
        wco = f"{self._WCO[0]:.3f},{self._WCO[1]:.3f},{self._WCO[2]:.3f}"
        return f"<{self._state}|MPos:{mpos}|FS:0,0|WCO:{wco}>\r\n"

    async def get_position(self) -> dict | bool:
        pos = await self.send_command("?")
        if pos.find(">") == -1:
            return False
        ret = {}
        pos = pos.strip().strip("<>")
        parts = pos.split("|")
        ret["state"] = parts.pop(0)
        for part in parts:
            if ":" not in part:
                continue
            label, values = part.split(":", 1)
            if label in ["MPos", "FS", "WCO"]:
                ret[label] = list(map(float, values.split(",")))
            else:
                ret[label] = values
        if "WCO" in ret:
            self._WCO = ret["WCO"]
        ret["WPos"] = [m - w for m, w in zip(ret["MPos"], self._WCO)]
        return ret

    async def home(self):
        if not self._connected:
            event_queue.put_nowait(ErrorEvent(f"Not connected to {self.port}"))
            return None
        result = await self.send_command("$H\n")
        if result.find("ok\r\n") > -1:
            await self.send_command("G92 X0 Y0 Z0")
            return "ok"
        event_queue.put_nowait(ErrorEvent(f"Homing failed on {self.port}: {result}"))
        return result

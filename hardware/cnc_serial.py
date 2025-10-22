import asyncio
import serial
import config
from queue_manager import event_queue
from common import *


class SerialController:
    def __init__(self, port: str=config.SERIAL_PORT, baud_rate: int=config.BAUD_RATE):
        self.port = port
        self._baud_rate = baud_rate
        self._serial = None
        self._loop = asyncio.get_running_loop()
        self._rbuf = b''
        self._rbytes = 0
        self._wbuf = b''
        self._rfuture = None
        self._delimiter = None

    def _on_read(self):
        try:
            data = self._serial.read(self._serial.in_waiting)
            self._rbuf += data
            self._rbytes = len(self._rbuf)
            self._check_pending_read()
        except OSError as e:
            if e.errno == 5:
                self._loop.remove_reader(self._serial.fd)
                if self._rfuture:
                    self._rfuture.set_result("disconnected unexpectedly")
                self._serial.close()
                self._serial = None


    def _check_pending_read(self):
        future = self._rfuture
        if future is not None:
            # get data from buffer
            pos = self._rbuf.find(self._delimiter)
            if pos > -1:
                ret = self._rbuf[:(pos+len(self._delimiter))]
                self._rbuf = self._rbuf[(pos+len(self._delimiter)):]
                self._delimiter = self._rfuture = None
                future.set_result(ret)
                return future

    def _on_write(self):
        written = self._serial.write(self._wbuf)
        self._wbuf = self._wbuf[written:]
        if not self._wbuf:
            self._loop.remove_writer(self._serial.fd)

    async def _write(self, data):
        need_add_writer = not self._wbuf

        self._wbuf = self._wbuf + data
        if need_add_writer:
            self._loop.add_writer(self._serial.fd, self._on_write, None)
        return len(data)

    def _clear_buffer(self):
        self._serial.reset_input_buffer()
        self._rbuf = b""

    async def send_command(self, command: str, delimiter: bytes=b"\n", timeout: float=20.0)->str|None:
        """
        Send a command to GRBL.
        Will return a string including the delimiter upon command completion.
        Upon timeout, will return 'Timeout'.
        If not connected, will return None.
        """
        if self._serial is not None:
            while self._delimiter:
                await self._rfuture

            self._clear_buffer()
            self._rfuture = self._loop.create_future()
            self._delimiter = delimiter

            command = command.encode("utf-8")

            await self._write(command)

            try:
                ret = await asyncio.wait_for(self._rfuture, timeout)
                return ret
            except asyncio.TimeoutError:
                self._rfuture = None
                event_queue.put_nowait(ErrorEvent(f"Timeout on {self.port} when running {command}"))
                return "Timeout"
        event_queue.put_nowait(ErrorEvent(f"Not connected to {self.port}"))
        return None


    async def open(self)->str:
        """
        Open the connection to GRBL.
        Returns "Connected to {self.port}" if connection is successful.
        Will return "Connection timeout to {self.port}" if connection times out.
        Other errors include:
        "Serial error when connecting to {self.port}: {e}"
        "Error when connecting to {self.port}: {e}"
        """
        try:
            self._rfuture = self._loop.create_future()
            self._delimiter = config.GRBL_CONNECTION
            self._serial = serial.Serial(self.port, self._baud_rate)
            self._loop.add_reader(self._serial.fileno(), self._on_read, None)
            await asyncio.wait_for(self._rfuture, timeout=5.0)
            await self.send_command("$X\n")
            await asyncio.sleep(0.5)
            self._clear_buffer()
            event_queue.put_nowait(NotifyEvent(f"Connected to {self.port}"))
            return f"Connected to {self.port}"

        except asyncio.TimeoutError:
            event_queue.put_nowait(ErrorEvent(f"Timeout when connecting to {self.port}"))
            await self.close()
            return f"Connection timeout to {self.port}"

        except serial.serialutil.SerialException as e:
            event_queue.put_nowait(ErrorEvent(f"Serial error when connecting to {self.port}: {e}"))
            await self.close()
            return f"Serial error when connecting to {self.port}: {e}"

        except Exception as e:
            event_queue.put_nowait(ErrorEvent(f"Error when connecting to {self.port}: {e}"))
            await self.close()
            return f"Error when connecting to {self.port}: {e}"

    async def close(self):
        """
        Closes the GRBL connection.
        """
        if self._serial is not None:
            self._loop.remove_reader(self._serial.fd)
            self._serial.close()
            self._serial = None
            event_queue.put_nowait(NotifyEvent(f"Disconnected from {self.port}."))

    async def home(self):
        """
        Homes the CNC machine.
        Returns "ok" if homing successful.
        Returns the error from GRBL if there is an error.
        Returns None if not connected.
        """
        if self._serial is not None:
            result = await self.send_command("$H\n")
            if result.find(str(b"ok\r\n")) > -1:
                return "ok"
            event_queue.put_nowait(ErrorEvent(f"Homing failed on {self.port}: {result}"))
            return result
        event_queue.put_nowait(ErrorEvent(f"Not connected to {self.port}"))
        return None


async def main():
    controller = SerialController()
    print(await controller.open())
    print(await controller.home())
    print(await controller.send_command("?\n"))
    await controller.close()

if __name__ == "__main__":
    asyncio.run(main())
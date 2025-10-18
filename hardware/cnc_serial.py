import asyncio
import serial
import config
from queue_manager import event_queue
from common import *


class SerialController:
    def __init__(self, port=config.SERIAL_PORT, baud_rate=config.BAUD_RATE):
        self.port = port
        self._baud_rate = baud_rate
        self._serial = None
        self._loop = asyncio.get_event_loop()
        self._rbuf = b''
        self._rbytes = 0
        self._wbuf = b''
        self._rfuture = None
        self._delimiter = None

    def _on_read(self):
        data = self._serial.read(self._serial.in_waiting)
        self._rbuf += data
        self._rbytes = len(self._rbuf)
        print(self._rbuf)
        self._check_pending_read()

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

    async def open(self):
        try:
            self._rfuture = asyncio.Future()
            self._delimiter = b"Grbl 1.1h ['$' for help]\r\n"
            self._serial = serial.Serial(self.port, self._baud_rate)
            self._loop.add_reader(self._serial.fileno(), self._on_read)
            print("start")
            msg = await asyncio.wait_for(self._rfuture, timeout=5.0)
            print('Serial port opened')
            print(msg)
            event_queue.put_nowait(NotifyEvent(f"Connected to {self.port}"))

        except asyncio.TimeoutError:
            print("timeout")
            event_queue.put_nowait(ErrorEvent(f"Timeout when connecting to {self.port}"))

        except serial.serialutil.SerialException as e:
            print(e)
            """
            await asyncio.sleep(1)
            while self._serial.in_waiting:
                out = self._serial.readline().strip()
                print(out)
                if out.find(b"ok") > -1:
                    print('ok, connected')
                    event_queue.put_nowait(NotifyEvent(f"Connected to {self._port}."))
                elif out.find(b"Alarm") > -1:
                    print('Alarm')
                    event_queue.put_nowait(NotifyEvent(f"{self._port} in Alarm"))
                else:
                    self._serial.close()
                    self._serial = None
                    event_queue.put_nowait(ErrorEvent(out))
        except serial.SerialException as e:
            print(e)
            event_queue.put_nowait(ErrorEvent(e))
            self._serial.close()
            self._serial = None"""

    async def close(self):
        if self._serial is not None:
            self._serial.close()
            self._serial = None
            event_queue.put_nowait(NotifyEvent(f"Disconnected from {self.port}."))

    async def home(self):
        if self._serial is not None:
            self._serial.reset_input_buffer()
            self._serial.write(b"$X\n$H\n")
            while True:
                out = self._serial.readline().strip()
                if out.find(b"ok") > -1:
                    event_queue.put_nowait(NotifyEvent(f"{self.port} homing complete."))
                    break
                if out.find(b"error") > -1:
                    event_queue.put_nowait(ErrorEvent(out))
                    break

async def main():
    controller = SerialController()
    await controller.open()

if __name__ == "__main__":
    asyncio.run(main())
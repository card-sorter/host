# From https://stackoverflow.com/a/50774991
import asyncio
import sys

import serial


class AIOSerial:
    def __init__(self, serial, ioloop=None):
        self._serial = serial
        # Asynchronous I/O requires non-blocking devices
        self._serial.timeout = 0
        self._serial.write_timeout = 0

        if ioloop is not None:
            self.loop = ioloop
        else:
            self.loop = asyncio.get_running_loop()
        self.loop.add_reader(self._serial.fd, self._on_read)
        self._rbuf = b''
        self._rbytes = 0
        self._wbuf = b''
        self._rfuture = None
        self._delimiter = None

    def _on_read(self):
        data = self._serial.read(4096)
        self._rbuf += data
        self._rbytes = len(self._rbuf)
        self._check_pending_read()

    def _on_write(self):
        written = self._serial.write(self._wbuf)
        self._wbuf = self._wbuf[written:]
        if not self._wbuf:
            self.loop.remove_writer(self._serial.fd)

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

    async def read_until(self, delimiter=b'\n'):
        while self._delimiter:
            await self._rfuture

        self._delimiter = delimiter
        self._rfuture = asyncio.Future()
        #future = self._check_pending_read()
        return await self._rfuture

    async def readline(self):
        return await self.read_until()

    async def write(self, data):
        need_add_writer = not self._wbuf

        self._wbuf = self._wbuf + data
        if need_add_writer:
            self.loop.add_writer(self._serial.fd, self._on_write)
        return len(data)
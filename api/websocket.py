import asyncio
try:
    from typing import override
except ImportError:
    def override(func):
        return func
import tornado.websocket
from host.queue_manager import command_queue, event_queue
from host. common import *
from host.controller.controller import Controller

port = 8888
connections: set["WebSocket"] = set()


class WebSocket(tornado.websocket.WebSocketHandler):

    @override
    def open(self, *args: str, **kwargs: str) -> None:
        connections.add(self)
        _ = super().open()

    @override
    def check_origin(self, origin: str) -> bool:
        return True

    @override
    async def on_message(self, message: str | bytes) -> None:
        command_queue.put_nowait(CommandEvent(str(message)))

    @override
    def on_close(self) -> None:
        connections.discard(self)
        return super().on_close()


async def broadcaster():
    while True:
        message = await event_queue.get()
        dead_connections: list[WebSocket] = []
        for con in connections:
            try:
                await con.write_message(message.to_json)
            except tornado.websocket.WebSocketClosedError:
                dead_connections.append(con)
        for con in dead_connections:
            connections.discard(con)


async def run_and_wait():
    app = tornado.web.Application([
        (r"/socket", WebSocket),
        (r"/images/(.*)", tornado.web.StaticFileHandler, {
            "path": "images"
        })
    ])
    _ = app.listen(port)

    _ = asyncio.create_task(broadcaster())

    print("Server Running")

    _ = await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(run_and_wait())

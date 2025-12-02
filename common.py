import json
from typing import final

STATES = {
    "IDLE": "IDLE",
    "RUNNING": "RUNNING",
    "PAUSED": "PAUSED",
    "STOPPED": "STOPPED",
    "FINISHED": "FINISHED",
    "E_STOP": "E_STOP",
    "RESET": "RESET",

}


class Event:
    def __init__(self):
        self._type: str = "event"
        self._value: str | None = None

    @property
    def to_string(self):
        return str(self._value)

    @property
    def to_json(self):
        obj = {
            "type": self._type,
            "message": self._value
        }
        return json.dumps(obj)

    @property
    def type(self):
        return self._type

    @property
    def value(self):
        return self._value


@final
class CommandEvent(Event):
    def __init__(self, value: str):
        super().__init__()
        self._type = "command"
        self._value = value


@final
class NotifyEvent(Event):
    def __init__(self, value: str):
        super().__init__()
        self._type = "notify"
        self._value = value


@final
class ErrorEvent(Event):
    def __init__(self, value: str):
        super().__init__()
        self._type = "error"
        self._value = value


@final
class WarningEvent(Event):
    def __init__(self, value: str):
        super().__init__()
        self._type = "warning"
        self._value = value


@final
class StatusEvent(Event):
    def __init__(self, state: str, progress: float | int = 0, job_id=None, message: str | None = None):
        super().__init__()
        self._type = "status"
        self._state = state
        self._progress = max(0, min(100, progress))
        self._job_id = job_id
        self._value = message

    @property
    def to_json(self):
        obj = {
            "type": self._type,
            "state": self._state,
            "progress": self._progress,
            "job_id": self._job_id,
        }
        if self._value is not None:
            obj["message"] = self._value
        return json.dumps(obj)

    @property
    def state(self):
        return self._state

    @property
    def progress(self):
        return self._progress

    @property
    def job_id(self):
        return self._job_id


@final
class StateEvent(Event):
    def __init__(self, state: str, message: str | None = None):
        super().__init__()
        self._type = "state"
        self._state = state
        self._value = message or state

    @property
    def to_json(self):
        obj = {
            "type": self._type,
            "state": self._state,
            "message": self._value
        }
        return json.dumps(obj)

    @property
    def state(self):
        return self._state


class Card:
    def __init__(self) -> None:
        pass


class Bin(list[Card]):
    def __init__(self, x: float, y: float, z: float) -> None:
        super().__init__()
        self._x: float = x
        self._y: float = y
        self._z: float = z
        self.scanned: bool = False
        self.barcode: str = ""

    @property
    def empty(self):
        return self.scanned and len(self) == 0

    @property
    def x(self):
        return self._x

    @property
    def y(self):
        return self._y

    @property
    def z(self):
        return self._z

    def set_z(self, z: float):
        self._z = z

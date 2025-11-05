import json
from typing import final


class Event:
    def __init__(self):
        self._type:str = "event"
        self._value:str|None = None

    @property
    def to_string(self):
        return str(self._value)

    @property
    def to_json(self):
        obj = {
            "type":self._type,
            "message":self._value
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
    def __init__(self, value:str):
        super().__init__()
        self._type = "command"
        self._value = value

@final
class NotifyEvent(Event):
    def __init__(self, value:str):
        super().__init__()
        self._type = "notify"
        self._value = value

@final
class ErrorEvent(Event):
    def __init__(self, value:str):
        super().__init__()
        self._type = "error"
        self._value = value

@final
class WarningEvent(Event):
    def __init__(self, value:str):
        super().__init__()
        self._type = "warning"
        self._value = value


class Card:
    def __init__(self) -> None:
        pass

class Bin(list[Card]):
    def __init__(self, x:float, y:float, z:float) -> None:
        super().__init__()
        self._x:float = x
        self._y:float = y
        self._z:float = z
        self.scanned:bool = False
        self.barcode:str = ""

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

    def set_z(self, z:float):
        self._z = z

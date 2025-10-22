class Event:
    def __init__(self):
        self._type = "event"
        self._value = None

    def __str__(self):
        return str(self._value)

    @property
    def type(self):
        return self._type

    @property
    def value(self):
        return self._value


class CommandEvent(Event):
    def __init__(self, value):
        super().__init__()
        self._type = "command"
        self._value = value


class NotifyEvent(Event):
    def __init__(self, value):
        super().__init__()
        self._type = "notify"
        self._value = value


class ErrorEvent(Event):
    def __init__(self, value):
        super().__init__()
        self._type = "error"
        self._value = value


class WarningEvent(Event):
    def __init__(self, value):
        super().__init__()
        self._type = "warning"
        self._value = value


class Bin(list):
    def __init__(self, x, y, z):
        super().__init__()
        self._x = x
        self._y = y
        self._z = z
        self.barcode = ""

    @property
    def x(self):
        return self._x

    @property
    def y(self):
        return self._y

    @property
    def z(self):
        return self._z

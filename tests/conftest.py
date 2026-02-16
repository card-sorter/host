import sys
import os
import types
import unittest.mock

import pytest
import pytest_asyncio
import numpy as np

# Add project root to path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Stub out hardware-only modules before any project imports
for mod_name in ("libcamera", "libcamera.controls", "picamera2", "cv2", "serial"):
    if mod_name not in sys.modules:
        sys.modules[mod_name] = types.ModuleType(mod_name)

# libcamera.controls needs an AfModeEnum.Manual attribute
_controls = sys.modules["libcamera.controls"] if "libcamera.controls" in sys.modules else sys.modules.setdefault("libcamera.controls", types.ModuleType("libcamera.controls"))
_controls.AfModeEnum = types.SimpleNamespace(Manual=0)
# config.py imports `from libcamera import controls`
sys.modules["libcamera"].controls = _controls

# picamera2 needs a Picamera2 class
sys.modules["picamera2"].Picamera2 = type("Picamera2", (), {})

# cv2 needs remap and INTER_LINEAR and resize
_cv2 = sys.modules["cv2"]
_cv2.remap = lambda img, mx, my, interp: img
_cv2.INTER_LINEAR = 1
_cv2.INTER_AREA = 3
_cv2.resize = lambda img, dsize, **kw: img

from tests.mock_serial import MockSerialController
from hardware.hal import HAL


@pytest.fixture
def mock_serial():
    """Provides a fresh MockSerialController instance (not yet opened)."""
    return MockSerialController(port="/dev/ttyTEST")


@pytest_asyncio.fixture
async def connected_serial():
    """Provides a MockSerialController that is already open and connected."""
    controller = MockSerialController(port="/dev/ttyTEST")
    await controller.open()
    yield controller
    await controller.close()


class MockCamera:
    """Fake camera that returns a solid-color numpy array."""

    def __init__(self, width=200, height=150):
        self._frame = np.zeros((height, width, 3), dtype=np.uint8)

    def capture_array(self):
        return self._frame.copy()

    def start(self):
        pass

    def stop(self):
        pass

    def close(self):
        pass

    def set_controls(self, cfg):
        pass

    def autofocus_cycle(self):
        pass


class MockProjector:
    """Projector mock that returns the image unchanged."""

    def project(self, image):
        return image

    def crop(self, image):
        return image


@pytest.fixture
def mock_camera():
    return MockCamera()


@pytest.fixture
def mock_projector():
    return MockProjector()


@pytest_asyncio.fixture
async def hal():
    """HAL with MockSerialController injected, opened and ready for motion tests."""
    h = HAL.__new__(HAL)
    mock = MockSerialController(port="/dev/ttyTEST")
    # Replicate __init__ fields
    h._connected = False
    h._serialController = mock
    import config
    h._bins = [__import__('common').Bin(pos[0], pos[1], config.BIN_HEIGHT) for pos in config.BIN_POSITIONS]
    h._camera_bin = config.CAMERA_BIN
    h._camera_height = config.CAMERA_HEIGHT
    h._height = config.MOVEMENT_HEIGHT
    h._bottom_limit = config.BIN_BOTTOM_LIMIT
    h._probe_safety_distance = config.PROBE_SAFETY_DISTANCE
    h._probe_feedrate = config.PROBE_FEEDRATE
    h._camera = None
    h._focused = True
    h._homed = False
    h._card_drop_offset = config.CARD_DROP_OFFSET
    h._card_lift_delay = config.CARD_LIFT_DELAY
    h.bin_max_len = 0
    h.projector = MockProjector()

    await mock.open()
    h._connected = True
    yield h
    if mock._connected:
        await mock.close()


@pytest_asyncio.fixture
async def connected_hal(hal, mock_camera):
    """HAL with mock camera and projector attached, ready for scan tests."""
    hal._camera = mock_camera
    return hal

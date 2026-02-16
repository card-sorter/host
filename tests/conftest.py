import sys
import os
import pytest
import pytest_asyncio

# Add project root to path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tests.mock_serial import MockSerialController


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

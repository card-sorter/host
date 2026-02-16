"""Tests for hardware/hal.py — HAL layer with MockSerialController injected."""

import pytest
import numpy as np

import config
from common import Bin
from tests.mock_serial import MockSerialController


# ---------------------------------------------------------------------------
# TestHALConnection
# ---------------------------------------------------------------------------

class TestHALConnection:
    @pytest.mark.asyncio
    async def test_open_success(self):
        from hardware.hal import HAL
        h = HAL.__new__(HAL)
        mock = MockSerialController(port="/dev/ttyTEST")
        h._serialController = mock
        h._connected = False

        result = await h.open()

        assert result is True
        assert h._connected is True

    @pytest.mark.asyncio
    async def test_open_failure(self):
        from hardware.hal import HAL
        h = HAL.__new__(HAL)
        mock = MockSerialController(port="/dev/ttyTEST")
        mock.simulate_disconnect = True
        h._serialController = mock
        h._connected = False

        result = await h.open()

        assert result is False
        assert h._connected is False

    @pytest.mark.asyncio
    async def test_close(self, hal):
        assert hal._connected is True
        await hal.close()
        assert hal._connected is False
        assert hal._homed is False


# ---------------------------------------------------------------------------
# TestHALProperties
# ---------------------------------------------------------------------------

class TestHALProperties:
    def test_bins_count(self, hal):
        assert len(hal.bins) == len(config.BIN_POSITIONS)

    def test_bins_positions(self, hal):
        for i, (x, y) in enumerate(config.BIN_POSITIONS):
            assert hal.bins[i].x == x
            assert hal.bins[i].y == y

    def test_default_bins(self, hal):
        defaults = hal.default_bins
        assert len(defaults) == len(config.BIN_POSITIONS) - 1
        # Camera bin (index 0) should be excluded — remaining bins start at position index 1
        for i, b in enumerate(defaults):
            expected_x = config.BIN_POSITIONS[i + 1][0]
            assert b.x == expected_x


# ---------------------------------------------------------------------------
# TestHALMovement
# ---------------------------------------------------------------------------

class TestHALMovement:
    @pytest.mark.asyncio
    async def test_move_to_bin(self, hal):
        target = hal.bins[1]
        result = await hal._move_to_bin(target)
        assert result is True
        mock: MockSerialController = hal._serialController
        assert any(f"G0 X{target.x} Y{target.y}" in cmd for cmd in mock.command_log)

    @pytest.mark.asyncio
    async def test_move_to_height(self, hal):
        result = await hal._move_to_height(-10)
        assert result is True
        mock: MockSerialController = hal._serialController
        assert any("G0 Z-10" in cmd for cmd in mock.command_log)

    @pytest.mark.asyncio
    async def test_auto_home_on_first_command(self, hal):
        assert hal._homed is False
        await hal._send_command("G0 X0")
        mock: MockSerialController = hal._serialController
        assert "$H" in mock.command_log[0]
        assert hal._homed is True

    @pytest.mark.asyncio
    async def test_no_rehome_after_first(self, hal):
        await hal._send_command("G0 X0")  # triggers homing
        mock: MockSerialController = hal._serialController
        home_count_before = sum(1 for c in mock.command_log if "$H" in c)

        await hal._send_command("G0 X10")
        home_count_after = sum(1 for c in mock.command_log if "$H" in c)
        assert home_count_after == home_count_before


# ---------------------------------------------------------------------------
# TestHALProbing
# ---------------------------------------------------------------------------

class TestHALProbing:
    @pytest.mark.asyncio
    async def test_probe_height(self, hal):
        # Force homed so _send_command doesn't auto-home
        hal._homed = True
        b = hal.bins[1]
        original_z = b.z
        result = await hal._probe_height(b)
        assert result is True
        # Bin Z should have been updated from PRB response
        assert b.z != original_z

    @pytest.mark.asyncio
    async def test_probe_failure(self, hal):
        hal._homed = True
        b = hal.bins[1]
        mock: MockSerialController = hal._serialController
        # Simulate timeout during probe — mock returns "Timeout" which has no PRB
        mock.simulate_timeout = True
        result = await hal._probe_height(b)
        assert result is False


# ---------------------------------------------------------------------------
# TestHALVacuum
# ---------------------------------------------------------------------------

class TestHALVacuum:
    @pytest.mark.asyncio
    async def test_vacuum_pump_on_hold(self, hal):
        hal._homed = True
        await hal._set_vacuum(True, False)
        mock: MockSerialController = hal._serialController
        assert any("M3 S80" in cmd for cmd in mock.command_log)

    @pytest.mark.asyncio
    async def test_vacuum_release(self, hal):
        hal._homed = True
        await hal._set_vacuum(True, True)
        mock: MockSerialController = hal._serialController
        assert any("M4 S80" in cmd for cmd in mock.command_log)

    @pytest.mark.asyncio
    async def test_vacuum_off(self, hal):
        hal._homed = True
        await hal._set_vacuum(False, False)
        mock: MockSerialController = hal._serialController
        assert any("M3 S0" in cmd for cmd in mock.command_log)


# ---------------------------------------------------------------------------
# TestHALMoveCard
# ---------------------------------------------------------------------------

class TestHALMoveCard:
    @pytest.mark.asyncio
    async def test_move_card_success(self, hal):
        source = hal.bins[1]
        target = hal.bins[2]
        result = await hal.move_card(source, target)
        assert result is True

    @pytest.mark.asyncio
    async def test_move_card_not_connected(self, hal):
        hal._connected = False
        result = await hal.move_card(hal.bins[1], hal.bins[2])
        assert result is False

    @pytest.mark.asyncio
    async def test_move_card_command_sequence(self, hal):
        source = hal.bins[1]
        target = hal.bins[2]
        await hal.move_card(source, target)
        mock: MockSerialController = hal._serialController
        log = mock.command_log

        # Should contain: move to source, probe, vacuum, lift, move to target, probe, drop
        assert any(f"G0 X{source.x} Y{source.y}" in cmd for cmd in log)
        assert any(f"G0 X{target.x} Y{target.y}" in cmd for cmd in log)
        assert any("G38.2" in cmd for cmd in log)
        assert any("M3" in cmd or "M4" in cmd for cmd in log)


# ---------------------------------------------------------------------------
# TestHALScanCard
# ---------------------------------------------------------------------------

class TestHALScanCard:
    @pytest.mark.asyncio
    async def test_scan_card_returns_image(self, connected_hal):
        source = connected_hal.bins[1]
        target = connected_hal.bins[2]
        result = await connected_hal.scan_card(source, target)
        assert isinstance(result, np.ndarray)

    @pytest.mark.asyncio
    async def test_scan_card_no_camera(self, hal):
        assert hal._camera is None
        result = await hal.scan_card(hal.bins[1], hal.bins[2])
        assert result is False

    @pytest.mark.asyncio
    async def test_scan_card_command_sequence(self, connected_hal):
        source = connected_hal.bins[1]
        target = connected_hal.bins[2]
        camera_bin = connected_hal.bins[connected_hal._camera_bin]
        await connected_hal.scan_card(source, target)
        mock: MockSerialController = connected_hal._serialController
        log = mock.command_log

        # Should move to source, camera bin, then target
        assert any(f"G0 X{source.x} Y{source.y}" in cmd for cmd in log)
        assert any(f"G0 X{camera_bin.x} Y{camera_bin.y}" in cmd for cmd in log)
        assert any(f"G0 X{target.x} Y{target.y}" in cmd for cmd in log)
        # Should move to camera height
        assert any(f"G0 Z{config.CAMERA_HEIGHT}" in cmd for cmd in log)


# ---------------------------------------------------------------------------
# TestHALLiftDrop
# ---------------------------------------------------------------------------

class TestHALLiftDrop:
    @pytest.mark.asyncio
    async def test_lift_card(self, hal):
        hal._homed = True
        b = hal.bins[1]
        result = await hal._lift_card(b)
        assert result is True
        mock: MockSerialController = hal._serialController
        log = mock.command_log
        # Should contain: probe, vacuum (M3 S80), slow lift (G01), fast lift (G01), move up (G0 Z0)
        assert any("G38.2" in cmd for cmd in log)
        assert any("M3 S80" in cmd for cmd in log)
        assert any(cmd.startswith("G01") for cmd in log)
        assert any(f"G0 Z{hal._height}" in cmd for cmd in log)

    @pytest.mark.asyncio
    async def test_drop_card(self, hal):
        hal._homed = True
        b = hal.bins[2]
        result = await hal._drop_card(b)
        assert result is True
        mock: MockSerialController = hal._serialController
        log = mock.command_log
        # Should contain: probe, vacuum release (M4 S80), dwell, move up
        assert any("G38.2" in cmd for cmd in log)
        assert any("M4 S80" in cmd for cmd in log)
        assert any("G04" in cmd for cmd in log)
        assert any(f"G0 Z{hal._height}" in cmd for cmd in log)

"""Tests for hardware/hal.py — HAL layer with MockSerialController injected."""

import pytest
import numpy as np

import config
from common import (
    Bin, ConnectionError, HomingError, TimeoutError,
    ProbeError, CameraError, HALError,
)
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

        await h.open()

        assert h._connected is True

    @pytest.mark.asyncio
    async def test_open_failure(self):
        from hardware.hal import HAL
        h = HAL.__new__(HAL)
        mock = MockSerialController(port="/dev/ttyTEST")
        mock.simulate_disconnect = True
        h._serialController = mock
        h._connected = False

        with pytest.raises(ConnectionError):
            await h.open()
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
        await hal._move_to_bin(target)
        mock: MockSerialController = hal._serialController
        assert any(f"G0 X{target.x} Y{target.y}" in cmd for cmd in mock.command_log)

    @pytest.mark.asyncio
    async def test_move_to_height(self, hal):
        await hal._move_to_height(-10)
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

    @pytest.mark.asyncio
    async def test_ensure_homed_raises_homing_error(self, hal):
        mock: MockSerialController = hal._serialController
        mock.simulate_home_error = True
        with pytest.raises(HomingError):
            await hal._ensure_homed()


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
        await hal._probe_height(b)
        # Bin Z should have been updated from PRB response
        assert b.z != original_z

    @pytest.mark.asyncio
    async def test_probe_failure_timeout(self, hal):
        hal._homed = True
        b = hal.bins[1]
        mock: MockSerialController = hal._serialController
        # Simulate timeout during probe
        mock.simulate_timeout = True
        with pytest.raises(TimeoutError):
            await hal._probe_height(b)


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
        await hal.move_card(source, target)

    @pytest.mark.asyncio
    async def test_move_card_not_connected(self, hal):
        hal._connected = False
        with pytest.raises(ConnectionError):
            await hal.move_card(hal.bins[1], hal.bins[2])

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
        with pytest.raises(CameraError):
            await hal.scan_card(hal.bins[1], hal.bins[2])

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
        await hal._lift_card(b)
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
        await hal._drop_card(b)
        mock: MockSerialController = hal._serialController
        log = mock.command_log
        # Should contain: probe, vacuum release (M4 S80), dwell, move up
        assert any("G38.2" in cmd for cmd in log)
        assert any("M4 S80" in cmd for cmd in log)
        assert any("G04" in cmd for cmd in log)
        assert any(f"G0 Z{hal._height}" in cmd for cmd in log)


# ---------------------------------------------------------------------------
# TestHALSafeState
# ---------------------------------------------------------------------------

class TestHALSafeState:
    @pytest.mark.asyncio
    async def test_safe_state_does_not_raise(self, hal):
        """_safe_state should never raise, even if commands fail."""
        hal._homed = True
        mock: MockSerialController = hal._serialController
        mock.simulate_timeout = True
        # Should not raise
        await hal._safe_state()

    @pytest.mark.asyncio
    async def test_safe_state_attempts_recovery(self, hal):
        """_safe_state should try to raise head and turn off vacuum."""
        hal._homed = True
        await hal._safe_state()
        mock: MockSerialController = hal._serialController
        log = mock.command_log
        assert any(f"G0 Z{hal._height}" in cmd for cmd in log)
        assert any("M3 S0" in cmd for cmd in log)

    @pytest.mark.asyncio
    async def test_move_card_calls_safe_state_on_error(self, hal):
        """move_card should call _safe_state on HALError before re-raising."""
        hal._homed = True
        mock: MockSerialController = hal._serialController
        # Let the first few commands succeed, then fail on probe
        original_process = mock._process_command
        call_count = [0]
        def failing_process(cmd):
            call_count[0] += 1
            # Fail on probe command
            if cmd.upper().startswith("G38.2"):
                return "error:probe\r\n"
            return original_process(cmd)
        mock._process_command = failing_process

        with pytest.raises(ProbeError):
            await hal.move_card(hal.bins[1], hal.bins[2])


# ---------------------------------------------------------------------------
# TestHALTimeoutPropagation
# ---------------------------------------------------------------------------

class TestHALTimeoutPropagation:
    @pytest.mark.asyncio
    async def test_timeout_propagates_through_send_command(self, hal):
        hal._homed = True
        mock: MockSerialController = hal._serialController
        mock.simulate_timeout = True
        with pytest.raises(TimeoutError):
            await hal._send_command("G0 X10")

    @pytest.mark.asyncio
    async def test_connection_error_propagates(self, hal):
        hal._homed = True
        mock: MockSerialController = hal._serialController
        mock.simulate_disconnect = True
        with pytest.raises(ConnectionError):
            await hal._send_command("G0 X10")

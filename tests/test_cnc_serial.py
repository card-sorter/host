import asyncio
import pytest

from common import ConnectionError, TimeoutError, HomingError
from tests.mock_serial import MockSerialController

pytestmark = pytest.mark.asyncio


# ── Connection lifecycle ──────────────────────────────────────────────


class TestConnection:
    async def test_open_success(self, mock_serial):
        await mock_serial.open()
        assert mock_serial._connected is True

    async def test_open_twice(self, mock_serial):
        await mock_serial.open()
        await mock_serial.open()
        # Second open should still succeed (reinitializes)
        assert mock_serial._connected is True

    async def test_close(self, connected_serial):
        await connected_serial.close()
        assert connected_serial._connected is False

    async def test_close_when_not_connected(self, mock_serial):
        # Should not raise
        await mock_serial.close()
        assert mock_serial._connected is False

    async def test_context_manager(self):
        controller = MockSerialController(port="/dev/ttyTEST")
        async with controller:
            assert controller._connected is True
        assert controller._connected is False

    async def test_open_simulated_disconnect(self, mock_serial):
        mock_serial.simulate_disconnect = True
        with pytest.raises(ConnectionError):
            await mock_serial.open()
        assert mock_serial._connected is False


# ── Command sending ───────────────────────────────────────────────────


class TestSendCommand:
    async def test_send_command_ok(self, connected_serial):
        result = await connected_serial.send_command("G0 X50 Y0")
        assert result == "ok\r\n"

    async def test_send_command_strips_and_logs(self, connected_serial):
        await connected_serial.send_command("G0 X10\n")
        assert "G0 X10" in connected_serial.command_log

    async def test_send_command_not_connected(self, mock_serial):
        with pytest.raises(ConnectionError):
            await mock_serial.send_command("G0 X0")

    async def test_send_command_timeout(self, connected_serial):
        connected_serial.simulate_timeout = True
        with pytest.raises(TimeoutError):
            await connected_serial.send_command("G0 X0")
        # Connection should be closed after timeout
        assert connected_serial._connected is False

    async def test_send_command_various_gcodes(self, connected_serial):
        commands = [
            ("G0 X10 Y20", "ok\r\n"),
            ("G01 Z-5 F500", "ok\r\n"),
            ("G04 P0.2", "ok\r\n"),
            ("G92 X0 Y0 Z0", "ok\r\n"),
            ("M3 S80", "ok\r\n"),
            ("M4 S0", "ok\r\n"),
            ("$X", "ok\r\n"),
        ]
        for cmd, expected in commands:
            result = await connected_serial.send_command(cmd)
            assert result == expected, f"Command {cmd} returned {result!r}, expected {expected!r}"

    async def test_unknown_command_returns_ok(self, connected_serial):
        result = await connected_serial.send_command("G999")
        assert result == "ok\r\n"


# ── Homing ────────────────────────────────────────────────────────────


class TestHoming:
    async def test_home_success(self, connected_serial):
        await connected_serial.home()
        assert connected_serial._homed is True

    async def test_home_resets_position(self, connected_serial):
        await connected_serial.send_command("G0 X100 Y50 Z-20")
        await connected_serial.home()
        assert connected_serial._pos == [0.0, 0.0, 0.0]

    async def test_home_not_connected(self, mock_serial):
        with pytest.raises(ConnectionError):
            await mock_serial.home()

    async def test_home_failure(self, connected_serial):
        connected_serial.simulate_home_error = True
        with pytest.raises(HomingError):
            await connected_serial.home()


# ── Position queries ──────────────────────────────────────────────────


class TestGetPosition:
    async def test_get_position_idle(self, connected_serial):
        pos = await connected_serial.get_position()
        assert isinstance(pos, dict)
        assert pos["state"] == "Idle"
        assert "MPos" in pos
        assert "WPos" in pos
        assert "FS" in pos

    async def test_get_position_after_move(self, connected_serial):
        await connected_serial.send_command("G0 X50 Y25 Z-10")
        pos = await connected_serial.get_position()
        assert pos["MPos"] == [50.0, 25.0, -10.0]

    async def test_get_position_wpos_calculation(self, connected_serial):
        pos = await connected_serial.get_position()
        # With WCO=[0,0,0], WPos should equal MPos
        assert pos["WPos"] == pos["MPos"]

    async def test_get_position_wco_cached(self, connected_serial):
        pos = await connected_serial.get_position()
        assert "WCO" in pos
        assert connected_serial._WCO == pos["WCO"]

    async def test_get_position_not_connected(self, mock_serial):
        with pytest.raises(ConnectionError):
            await mock_serial.get_position()


# ── Position tracking ─────────────────────────────────────────────────


class TestPositionTracking:
    async def test_g0_updates_position(self, connected_serial):
        await connected_serial.send_command("G0 X100")
        assert connected_serial._pos[0] == 100.0

    async def test_g0_partial_axes(self, connected_serial):
        await connected_serial.send_command("G0 X10 Y20")
        assert connected_serial._pos == [10.0, 20.0, 0.0]

        await connected_serial.send_command("G0 Z-5")
        assert connected_serial._pos == [10.0, 20.0, -5.0]

    async def test_g92_sets_position(self, connected_serial):
        await connected_serial.send_command("G0 X100 Y200 Z-50")
        await connected_serial.send_command("G92 X0 Y0 Z0")
        assert connected_serial._pos == [0.0, 0.0, 0.0]

    async def test_g01_updates_position(self, connected_serial):
        await connected_serial.send_command("G01 Z-30 F500")
        assert connected_serial._pos[2] == -30.0

    async def test_probe_updates_position(self, connected_serial):
        await connected_serial.send_command("G0 Z0")
        result = await connected_serial.send_command("G38.2 Z-100 F500")
        assert "[PRB:" in result
        assert ":1]" in result
        # Z should be between 0 and -100 (midpoint = -50)
        assert connected_serial._pos[2] == -50.0


# ── Spindle / vacuum control ─────────────────────────────────────────


class TestSpindleControl:
    async def test_m3_pump_on(self, connected_serial):
        await connected_serial.send_command("M3 S80")
        assert connected_serial._spindle_mode == "M3"
        assert connected_serial._spindle_speed == 80

    async def test_m4_solenoid_on(self, connected_serial):
        await connected_serial.send_command("M4 S80")
        assert connected_serial._spindle_mode == "M4"
        assert connected_serial._spindle_speed == 80

    async def test_m3_pump_off(self, connected_serial):
        await connected_serial.send_command("M3 S0")
        assert connected_serial._spindle_speed == 0


# ── Command serialization ────────────────────────────────────────────


class TestConcurrency:
    async def test_concurrent_commands_serialized(self, connected_serial):
        """Multiple concurrent commands should all complete without errors."""
        commands = [f"G0 X{i * 10}" for i in range(10)]
        results = await asyncio.gather(
            *[connected_serial.send_command(cmd) for cmd in commands]
        )
        assert all(r == "ok\r\n" for r in results)
        assert len(connected_serial.command_log) == 10

    async def test_command_log_order(self, connected_serial):
        """Commands should be logged in order of execution."""
        await connected_serial.send_command("G0 X1")
        await connected_serial.send_command("G0 X2")
        await connected_serial.send_command("G0 X3")
        assert connected_serial.command_log == ["G0 X1", "G0 X2", "G0 X3"]


# ── Probe responses ──────────────────────────────────────────────────


class TestProbe:
    async def test_probe_response_format(self, connected_serial):
        await connected_serial.send_command("G0 X14 Y0 Z-25")
        result = await connected_serial.send_command("G38.2 Z-105 F500")
        assert result.startswith("[PRB:")
        assert ":1]" in result
        assert "ok\r\n" in result

    async def test_probe_contact_position(self, connected_serial):
        await connected_serial.send_command("G0 Z0")
        result = await connected_serial.send_command("G38.2 Z-100 F500")
        # Parse probe position from response
        import re
        match = re.search(r'\[PRB:([-\d.]+),([-\d.]+),([-\d.]+):1\]', result)
        assert match is not None
        probe_z = float(match.group(3))
        assert -100 < probe_z < 0  # Should be between start and target

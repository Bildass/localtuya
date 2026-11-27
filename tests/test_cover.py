"""Regression tests for local and device-reported cover movement."""

import asyncio
import time
from tempfile import TemporaryDirectory
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock, call, patch

from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

from custom_components.localtuya_bildass.cover import LocaltuyaCover


class CoverTest(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.hass = HomeAssistant(self.enterContext(TemporaryDirectory()))
        self.device = Mock(is_connecting=False, set_dp=AsyncMock())
        self.hass.loop.set_debug(False)
        self.offset = 0
        for name in ("monotonic", "time"):
            clock = getattr(time, name)
            self.enterContext(
                patch.object(time, name, lambda clock=clock: clock() + self.offset)
            )

    async def add_cover(self, mode="position", **options):
        config = {
            "id": 1,
            "friendly_name": "Test blind",
            "commands_set": "open_close_stop",
            "positioning_mode": mode,
            "position_inverted": False,
            "span_time": 100,
            **options,
        }
        entry = {"device_id": "blind", "entities": [config]}
        self.cover = LocaltuyaCover(self.device, entry, 1)
        self.cover.hass = self.hass
        self.cover.platform = Mock(platform_name="localtuya_bildass", config_entry=None)
        self.cover.entity_id = "cover.blind"
        await self.cover.add_to_platform_finish()

    async def report(self, dps):
        async_dispatcher_send(self.hass, "localtuya_blind", dps)
        await self.hass.async_block_till_done()

    async def advance(self, seconds):
        await asyncio.sleep(0)
        self.offset += seconds
        await asyncio.sleep(0.001)

    async def test_availability_with_either_or_neither_configured_dp(self):
        await self.add_cover(current_position_dp=2)
        with self.assertNoLogs("custom_components.localtuya_bildass", level="WARNING"):
            await self.report({"1": "stop"})
            self.assertTrue(self.cover.available)
            await self.report({"2": 64})
            self.assertTrue(self.cover.available)
            self.assertEqual(self.cover.current_cover_position, 64)
            await self.report({"9": 42})
            self.assertFalse(self.cover.available)

    async def test_inverted_target_uses_ha_coordinates_for_direction_and_arrival(self):
        await self.add_cover(
            current_position_dp=2, set_position_dp=3, position_inverted=True
        )
        await self.report({"2": 60})
        self.assertEqual(self.cover.current_cover_position, 40)
        await self.cover.async_set_cover_position(position=80)
        self.device.set_dp.assert_awaited_once_with(20, 3)
        self.assertTrue(self.cover.is_opening)
        await self.report({"2": 20})
        self.assertEqual(self.cover.current_cover_position, 80)
        self.assertFalse(self.cover.is_opening)
        self.assertFalse(self.cover.is_closing)

    async def test_initial_snapshot_is_not_a_physical_command(self):
        await self.add_cover(current_position_dp=2)
        await self.report({"1": "open", "2": 35})
        self.assertEqual(self.hass.states.get("cover.blind").state, "open")

    async def test_physical_open_and_stop_update_direction(self):
        await self.add_cover(current_position_dp=2)
        await self.report({"1": "stop", "2": 30})
        await self.report({"1": "open", "2": 30})
        self.assertTrue(self.cover.is_opening)
        self.assertEqual(self.hass.states.get("cover.blind").state, "opening")
        await self.report({"1": "stop", "2": 45})
        self.assertEqual(self.hass.states.get("cover.blind").state, "open")
        self.assertFalse(self.cover.is_opening)
        self.assertFalse(self.cover.is_closing)
        self.device.set_dp.assert_not_awaited()

    async def test_timed_open_without_position_feedback_outlasts_stall_timeout(self):
        await self.add_cover(mode="timed")
        await self.cover.async_open_cover()
        await self.advance(20)
        self.assertTrue(self.cover.is_opening)
        self.device.set_dp.assert_awaited_once_with("open", 1)
        await self.cover.async_stop_cover()
        self.assertFalse(self.cover.is_opening)

    async def test_timed_position_sends_one_stop_at_fractional_travel_time(self):
        await self.add_cover(mode="timed")
        await self.cover.async_set_cover_position(position=25)
        await self.advance(24)
        self.device.set_dp.assert_awaited_once_with("open", 1)
        await self.advance(2)
        self.assertEqual(
            self.device.set_dp.await_args_list, [call("open", 1), call("stop", 1)]
        )
        await self.advance(100)
        self.assertEqual(self.device.set_dp.await_count, 2)

    async def test_replacement_movement_not_interrupted_by_old_stop(self):
        await self.add_cover(mode="timed")
        await self.cover.async_set_cover_position(position=25)
        await self.advance(10)
        await self.cover.async_close_cover()
        await self.advance(16)
        movement = [call("open", 1), call("close", 1)]
        self.assertEqual(self.device.set_dp.await_args_list, movement)
        await self.advance(100)
        self.assertEqual(
            self.device.set_dp.await_args_list, [*movement, call("stop", 1)]
        )

    async def test_write_latency_does_not_extend_partial_travel(self):
        await self.add_cover(mode="timed")
        release = asyncio.Event()

        async def set_dp(command, dp):
            if command == "open":
                await release.wait()

        self.device.set_dp.side_effect = set_dp
        movement = asyncio.create_task(self.cover.async_set_cover_position(position=10))
        await self.advance(5)
        release.set()
        await movement
        await self.advance(6)
        self.assertEqual(
            self.device.set_dp.await_args_list, [call("open", 1), call("stop", 1)]
        )

    async def test_old_echo_does_not_cancel_replacement_stop(self):
        await self.add_cover(mode="timed")
        await self.report({"1": "stop"})
        release = asyncio.Event()

        async def set_dp(command, dp):
            if command != "stop":
                await release.wait()

        self.device.set_dp.side_effect = set_dp
        opening = asyncio.create_task(self.cover.async_open_cover())
        await self.advance(10)
        closing = asyncio.create_task(self.cover.async_close_cover())
        await asyncio.sleep(0)
        await self.report({"1": "open"})
        self.assertTrue(self.cover.is_closing)
        await self.report({"1": "close"})
        release.set()
        await asyncio.gather(opening, closing)
        await self.advance(110)
        self.assertEqual(
            self.device.set_dp.await_args_list,
            [call("open", 1), call("close", 1), call("stop", 1)],
        )

    async def test_wall_stop_after_command_echo_wins_over_pending_write(self):
        await self.add_cover(mode="timed")
        await self.report({"1": "stop"})
        release = asyncio.Event()

        async def set_dp(command, dp):
            await release.wait()

        self.device.set_dp.side_effect = set_dp
        opening = asyncio.create_task(self.cover.async_open_cover())
        await asyncio.sleep(0)
        await self.report({"1": "open"})
        await self.report({"1": "stop"})
        release.set()
        await opening
        await self.advance(110)
        self.assertFalse(self.cover.is_opening)
        self.device.set_dp.assert_awaited_once_with("open", 1)

    async def test_removal_cancels_pending_stop(self):
        await self.add_cover(mode="timed")
        await self.cover.async_set_cover_position(position=25)
        await self.cover.async_remove()
        await self.advance(120)
        self.device.set_dp.assert_awaited_once_with("open", 1)

    async def test_in_flight_movement_write_cannot_rearm_timer_after_stop(self):
        await self.add_cover(mode="timed")
        started, release = asyncio.Event(), asyncio.Event()

        async def set_dp(command, dp):
            if command == "open":
                started.set()
                await release.wait()

        self.device.set_dp.side_effect = set_dp
        movement = asyncio.create_task(self.cover.async_set_cover_position(position=25))
        await asyncio.wait_for(started.wait(), timeout=1)
        await self.cover.async_stop_cover()
        release.set()
        await movement
        await self.advance(120)
        self.assertEqual(
            self.device.set_dp.await_args_list, [call("open", 1), call("stop", 1)]
        )

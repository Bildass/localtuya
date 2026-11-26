"""Platform to locally control Tuya-based cover devices."""
import asyncio
import logging
import time
from functools import partial

import voluptuous as vol
from homeassistant.components.cover import (
    ATTR_POSITION,
    DOMAIN,
    CoverEntity, CoverEntityFeature,
)

from .common import LocalTuyaEntity, async_setup_entry
from .const import (
    CONF_COMMANDS_SET,
    CONF_CURRENT_POSITION_DP,
    CONF_POSITION_INVERTED,
    CONF_POSITIONING_MODE,
    CONF_SET_POSITION_DP,
    CONF_SPAN_TIME,
)

_LOGGER = logging.getLogger(__name__)

COVER_ONOFF_CMDS = "on_off_stop"
COVER_OPENCLOSE_CMDS = "open_close_stop"
COVER_FZZZ_CMDS = "fz_zz_stop"
COVER_12_CMDS = "1_2_3"
COVER_MODE_NONE = "none"
COVER_MODE_POSITION = "position"
COVER_MODE_TIMED = "timed"
COVER_TIMEOUT_TOLERANCE = 3.0

COVER_MOVEMENT_TIMEOUT = 120.0
COVER_STALL_TIMEOUT = 15.0

DEFAULT_COMMANDS_SET = COVER_ONOFF_CMDS
DEFAULT_POSITIONING_MODE = COVER_MODE_NONE
DEFAULT_SPAN_TIME = 25.0


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Optional(CONF_COMMANDS_SET): vol.In(
            [COVER_ONOFF_CMDS, COVER_OPENCLOSE_CMDS, COVER_FZZZ_CMDS, COVER_12_CMDS]
        ),
        vol.Optional(CONF_POSITIONING_MODE, default=DEFAULT_POSITIONING_MODE): vol.In(
            [COVER_MODE_NONE, COVER_MODE_POSITION, COVER_MODE_TIMED]
        ),
        vol.Optional(CONF_CURRENT_POSITION_DP): vol.In(dps),
        vol.Optional(CONF_SET_POSITION_DP): vol.In(dps),
        vol.Optional(CONF_POSITION_INVERTED, default=False): bool,
        vol.Optional(CONF_SPAN_TIME, default=DEFAULT_SPAN_TIME): vol.All(
            vol.Coerce(float), vol.Range(min=1.0, max=300.0)
        ),
    }


class LocaltuyaCover(LocalTuyaEntity, CoverEntity):
    """Tuya cover device."""

    def __init__(self, device, config_entry, switchid, **kwargs):
        """Initialize a new LocaltuyaCover."""
        super().__init__(device, config_entry, switchid, _LOGGER, **kwargs)
        commands_set = DEFAULT_COMMANDS_SET
        if self.has_config(CONF_COMMANDS_SET):
            commands_set = self._config[CONF_COMMANDS_SET]
        self._open_cmd = commands_set.split("_")[0]
        self._close_cmd = commands_set.split("_")[1]
        self._stop_cmd = commands_set.split("_")[2]
        self._timer_start = time.monotonic()
        self._timed_direction = 0
        self._stop_task = None
        self._pending_timed_write = None
        self._state = None
        self._current_cover_position = 0
        self._movement_target = None
        self._movement_deadline = 0.0
        self._last_position_change = 0.0
        _LOGGER.debug("Initialized cover [%s]", self.name)

    @property
    def available(self):
        """Return if cover is available.

        Covers may use a write-only command DP (e.g. DP 1 "control") which the
        device never reports back, so fall back to the position DP when set.
        """
        return super().available or (
            self.has_config(CONF_CURRENT_POSITION_DP)
            and str(self._config[CONF_CURRENT_POSITION_DP]) in self._status
        )

    @property
    def supported_features(self) -> CoverEntityFeature:
        """Flag supported features."""
        supported_features = CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | CoverEntityFeature.STOP
        if self._config[CONF_POSITIONING_MODE] != COVER_MODE_NONE:
            supported_features = supported_features | CoverEntityFeature.SET_POSITION
        return supported_features

    @property
    def current_cover_position(self):
        """Return current cover position in percent."""
        if self._config[CONF_POSITIONING_MODE] == COVER_MODE_NONE:
            return None
        if self._timed_direction and self._reported_position() is None:
            elapsed = time.monotonic() - self._timer_start
            distance = round(elapsed / self._config[CONF_SPAN_TIME] * 100)
            position = self._current_cover_position + self._timed_direction * distance
            return min(100, max(0, position))
        return self._current_cover_position

    def _reported_position(self):
        if self.has_config(CONF_CURRENT_POSITION_DP):
            return self._status.get(str(self._config[CONF_CURRENT_POSITION_DP]))
        return None

    def _start_movement(self, target):
        self._movement_target = target
        self._last_position_change = time.monotonic()
        self._movement_deadline = self._last_position_change + COVER_MOVEMENT_TIMEOUT

    def _command_direction(self):
        if self._state == self._open_cmd:
            return 1
        if self._state == self._close_cmd:
            return -1
        return 0

    def _movement_direction(self):
        """Return 1 while opening, -1 while closing and 0 when idle.

        With position feedback the command DP (e.g. DP 1 "control") only echoes
        the last command, so it says "open" long after the cover stopped.
        """
        mode = self._config[CONF_POSITIONING_MODE]
        if mode == COVER_MODE_TIMED:
            return self._timed_direction
        if mode == COVER_MODE_NONE or not self.has_config(CONF_CURRENT_POSITION_DP):
            return self._command_direction()

        target = self._movement_target
        position = self._current_cover_position
        if (
            target is None
            or position is None
            or abs(position - target) <= 1
            or time.monotonic() >= self._movement_deadline
            or time.monotonic() - self._last_position_change > COVER_STALL_TIMEOUT
        ):
            return 0

        return 1 if target > position else -1

    @property
    def is_opening(self):
        """Return if cover is opening."""
        return self._movement_direction() > 0

    @property
    def is_closing(self):
        """Return if cover is closing."""
        return self._movement_direction() < 0

    @property
    def is_closed(self):
        """Return if the cover is closed or not."""
        if self._config[CONF_POSITIONING_MODE] == COVER_MODE_NONE:
            return False

        return self.current_cover_position == 0

    async def async_set_cover_position(self, **kwargs):
        """Move the cover to a specific position."""
        self.debug("Setting cover position: %r", kwargs[ATTR_POSITION])
        if self._config[CONF_POSITIONING_MODE] == COVER_MODE_TIMED:
            newpos = float(kwargs[ATTR_POSITION])

            currpos = self.current_cover_position
            posdiff = abs(newpos - currpos)
            mydelay = posdiff / 100.0 * self._config[CONF_SPAN_TIME]
            if newpos == currpos:
                if self._timed_direction:
                    await self.async_stop_cover()
                return
            await self._async_move(newpos > currpos, delay=mydelay)

        elif self._config[CONF_POSITIONING_MODE] == COVER_MODE_POSITION:
            target = int(kwargs[ATTR_POSITION])
            if 0 <= target <= 100 and self.has_config(CONF_SET_POSITION_DP):
                self._start_movement(target)
                converted_position = (
                    100 - target if self._config[CONF_POSITION_INVERTED] else target
                )
                await self._device.set_dp(
                    converted_position, self._config[CONF_SET_POSITION_DP]
                )

    def _cancel_timed_stop(self):
        self._pending_timed_write = None
        if self._stop_task is not None:
            self._stop_task.cancel()
            self._stop_task = None

    def _set_timed_direction(self, direction):
        if self._timed_direction:
            # Without position feedback, elapsed travel is the only baseline for a reversal.
            self._current_cover_position = self.current_cover_position
        self._timed_direction = direction
        # Wall-clock corrections must not count as motor travel.
        self._timer_start = time.monotonic()

    async def _async_stop_at(self, deadline):
        """Stop the cover if timeout (max movement span) occurred."""
        await asyncio.sleep(max(0, deadline - time.monotonic()))
        self._stop_task = None
        await self.async_stop_cover()

    async def async_open_cover(self, **kwargs):
        """Open the cover."""
        await self._async_move(True)

    async def async_close_cover(self, **kwargs):
        """Close cover."""
        await self._async_move(False)

    async def _async_move(self, opening, *, delay=None):
        command = self._open_cmd if opening else self._close_cmd
        self.debug("Launching command %s to cover", command)
        mode = self._config[CONF_POSITIONING_MODE]
        if mode != COVER_MODE_TIMED:
            if mode == COVER_MODE_POSITION:
                self._start_movement(100 if opening else 0)
            await self._device.set_dp(command, self._dp_id)
            return

        self._cancel_timed_stop()
        self._set_timed_direction(1 if opening else -1)
        if delay is None:
            # A Tuya control ACK confirms the write, not arrival at the mechanical limit.
            # The configured span is an estimate, so allow for a slower end-to-end run.
            delay = self._config[CONF_SPAN_TIME] + COVER_TIMEOUT_TOLERANCE
        self._stop_task = self.hass.async_create_background_task(
            self._async_stop_at(self._timer_start + delay), f"Timed stop for {self.entity_id}"
        )
        await self._async_write_timed_command(command)

    async def _async_write_timed_command(self, command):
        write = self._pending_timed_write = object()
        try:
            await self._device.set_dp(command, self._dp_id)
        finally:
            if self._pending_timed_write is write:
                self._pending_timed_write = None
                self.async_write_ha_state()

    async def async_stop_cover(self, **kwargs):
        """Stop the cover."""
        self.debug("Launching command %s to cover ", self._stop_cmd)
        self._movement_target = None
        if self._config[CONF_POSITIONING_MODE] == COVER_MODE_TIMED:
            self._cancel_timed_stop()
            self._set_timed_direction(0)
            await self._async_write_timed_command(self._stop_cmd)
        else:
            await self._device.set_dp(self._stop_cmd, self._dp_id)

    async def async_will_remove_from_hass(self):
        self._cancel_timed_stop()
        await super().async_will_remove_from_hass()

    def status_restored(self, stored_state):
        """Restore the last stored cover status."""
        if self._config[CONF_POSITIONING_MODE] == COVER_MODE_TIMED:
            stored_pos = stored_state.attributes.get("current_position")
            if stored_pos is not None:
                self._current_cover_position = stored_pos
                self.debug("Restored cover position %s", self._current_cover_position)

    def status_updated(self):
        """Device status was updated."""
        previous_state = self._state
        self._state = self._status.get(str(self._dp_id))
        # The command DP may be write-only (never reported), so state can be
        # None and is not necessarily a string (position DPs are integers).
        if isinstance(self._state, str) and self._state.isupper():
            self._open_cmd = self._open_cmd.upper()
            self._close_cmd = self._close_cmd.upper()
            self._stop_cmd = self._stop_cmd.upper()

        mode = self._config[CONF_POSITIONING_MODE]
        commands = (self._open_cmd, self._close_cmd, self._stop_cmd)
        if (
            previous_state is not None
            and self._state != previous_state
            and self._state in commands
        ):
            direction = self._command_direction()
            if mode == COVER_MODE_TIMED:
                if direction == self._timed_direction:
                    self._pending_timed_write = None
                elif self._pending_timed_write is None:
                    self._cancel_timed_stop()
                    self._set_timed_direction(direction)
            elif mode == COVER_MODE_POSITION:
                if not direction:
                    self._movement_target = None
                elif direction != self._movement_direction():
                    self._start_movement(100 if direction > 0 else 0)

        curr_pos = self._reported_position()
        if curr_pos is not None:
            if self._config[CONF_POSITION_INVERTED]:
                curr_pos = 100 - curr_pos
            if curr_pos != self._current_cover_position:
                self._last_position_change = time.monotonic()
            target = self._movement_target
            if target is not None and (
                abs(curr_pos - target) <= 1
                or (self._current_cover_position - target) * (curr_pos - target) < 0
            ):
                self._movement_target = None
            self._current_cover_position = curr_pos

        # Keep record in last_state as long as not during connection/re-connection,
        # as last state will be used to restore the previous state
        if (self._state is not None) and (not self._device.is_connecting):
            self._last_state = self._state


async_setup_entry = partial(async_setup_entry, DOMAIN, LocaltuyaCover, flow_schema)

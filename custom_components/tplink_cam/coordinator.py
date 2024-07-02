"""Component to embed TP-Link camera devices."""
from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .lib.camera import TPLinkIPCam44AW

_LOGGER = logging.getLogger(__name__)

REQUEST_REFRESH_DELAY = 0.35


class TPLinkCamDataUpdateCoordinator(DataUpdateCoordinator):
    """DataUpdateCoordinator to gather data for a specific TPLink device."""

    def __init__(
        self,
        hass: HomeAssistant,
        device: TPLinkIPCam44AW,
    ) -> None:
        """Initialize DataUpdateCoordinator to gather data for camera."""
        self.device = device
        update_interval = timedelta(seconds=1)
        super().__init__(
            hass,
            _LOGGER,
            name=device.info['mac'],
            update_interval=update_interval,
            # We don't want an immediate refresh since the device
            # takes a moment to reflect the state change
            request_refresh_debouncer=Debouncer(
                hass, _LOGGER, cooldown=REQUEST_REFRESH_DELAY, immediate=False
            ),
        )

    async def _async_update_data(self) -> None:
        """Fetch all device and sensor data from api."""
        try:
            await self.hass.async_add_executor_job(self.device.update)
        finally:
            pass

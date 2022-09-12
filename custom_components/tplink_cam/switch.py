"""Switch platform for TPLink Camera integration."""
from __future__ import annotations

from typing import Any, cast

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity


from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.const import CONF_NAME

from .const import DOMAIN
from .coordinator import TPLinkCamDataUpdateCoordinator
from .camera import TPLinkIPCam44AW

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Initialize TPLink Camera config entry."""
    device = hass.data[DOMAIN][config_entry.entry_id]
    coordinator = TPLinkCamDataUpdateCoordinator(hass, device)

    async_add_entities([CameraLensSwitch(device, coordinator, config_entry.data[CONF_NAME])])


class CameraLensSwitch(CoordinatorEntity[TPLinkCamDataUpdateCoordinator], SwitchEntity):
    device: TPLinkIPCam44AW

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self, device: TPLinkIPCam44AW, coordinator: TPLinkCamDataUpdateCoordinator, config_entry_name: str | None = None
    ) -> None:
        """Initialize the cam switch."""
        super().__init__(coordinator)
        self.device: TPLinkIPCam44AW = device
        if config_entry_name is not None:
            config_entry_name = config_entry_name.strip()
            if len(config_entry_name) == 0:
                config_entry_name = None
        self.config_entry_name = config_entry_name

        self._attr_name = f"{self.config_entry_name or self.device.info['device_alias']} Lens"
        self._attr_unique_id = f"{self.device.info['mac']}_lens"

    @property
    def device_info(self) -> DeviceInfo:
        """Return information about the device."""
        return DeviceInfo(
            connections={(dr.CONNECTION_NETWORK_MAC, self.device.info['mac'])},
            identifiers={(DOMAIN, str(self.device.info['barcode']))},
            manufacturer=self.device.info['manufacturer_name'],
            model=self.device.info['device_model'],
            name=self.config_entry_name or self.device.info['device_alias'],
            sw_version=self.device.info['sw_version'],
            hw_version=self.device.info['hw_version'],
        )

    @property
    def is_on(self) -> bool:
        """Return true if switch is on."""
        return bool(not self.device.is_mask_on)

    @property
    def icon(self) -> str:
        """Return the icon for the on-off state."""
        return "mdi:cctv" if self.is_on else "mdi:cctv-off"

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the camera switch on."""
        await self.hass.async_add_executor_job(self.device.set_mask, False)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the camera switch off."""
        await self.hass.async_add_executor_job(self.device.set_mask, True)

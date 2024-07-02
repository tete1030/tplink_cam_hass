"""The TPLink Camera integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry, ConfigEntryNotReady
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant

from .lib.camera import AuthenticationError, TPLinkIPCam44AW, TPLinkIPCamError
from .const import CONF_API_URL, DOMAIN


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up TPLink Camera from a config entry."""
    try:
        device = TPLinkIPCam44AW(
            entry.data[CONF_API_URL],
            entry.data[CONF_USERNAME],
            entry.data[CONF_PASSWORD],
        )

        await hass.async_add_executor_job(device.login)
        await hass.async_add_executor_job(device.update_info)
    except AuthenticationError as e:
        raise ConfigEntryNotReady from e
    except TPLinkIPCamError as e:
        raise ConfigEntryNotReady from e

    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = dict()
    hass.data[DOMAIN][entry.entry_id] = device

    await hass.config_entries.async_forward_entry_setups(entry, (Platform.SWITCH,))

    entry.async_on_unload(entry.add_update_listener(config_entry_update_listener))

    return True


async def config_entry_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update listener, called when the config entry options are changed."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(
        entry, (Platform.SWITCH,)
    ):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok

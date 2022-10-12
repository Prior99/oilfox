"""The Oilfox integration."""
from __future__ import annotations
from datetime import timedelta
import logging
from pickle import FALSE
from homeassistant.components.oilfox.oilfox import OilfoxDevice, OilfoxHub

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DATA_COODINATOR, DOMAIN

_LOGGER = logging.getLogger(__name__)

# TODO List the platforms that you want to support.
# For your initial PR, limit it to 1 platform.
PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, config: ConfigEntry) -> bool:
    """Set up Oilfox from a config entry."""

    coordinator = OilfoxDataUpdateCoordinator(hass, config)

    if not await coordinator.async_login():
        return False

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][config.entry_id] = {
        DATA_COODINATOR: coordinator
    }

    await hass.config_entries.async_forward_entry_setups(config, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class OilfoxDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, config: ConfigEntry) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=timedelta(hours=1))
        self.hub = OilfoxHub(async_get_clientsession(hass))
        self.config = config

    async def async_login(self) -> bool:
        login_success = await self.hub.authenticate(self.config.data["email"], self.config.data["password"])
        return login_success
    
    async def _async_update_data(self) -> list[OilfoxDevice]:
        return await self.hub.list_devices()

    def _unsub_refresh(self):
        return
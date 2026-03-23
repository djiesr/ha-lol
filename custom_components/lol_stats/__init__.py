"""Intégration League of Legends Stats (API Riot, match-v5)."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import aiohttp_client

from .api import RiotApiClient
from .const import CONF_API_KEY, CONF_GAME_NAME, CONF_PLATFORM, CONF_TAG_LINE, DOMAIN, PLATFORM_TO_REGIONAL
from .coordinator import LolStatsCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configure l’entrée : coordinator + plateformes."""
    hass.data.setdefault(DOMAIN, {})
    regional = PLATFORM_TO_REGIONAL[entry.data[CONF_PLATFORM]]
    session = aiohttp_client.async_get_clientsession(hass)
    client = RiotApiClient(session, entry.data[CONF_API_KEY], regional)
    coordinator = LolStatsCoordinator(
        hass,
        client,
        entry.data[CONF_GAME_NAME],
        entry.data[CONF_TAG_LINE],
        entry.data["puuid"],
    )
    await coordinator.async_config_entry_first_refresh()
    hass.data[DOMAIN][entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Décharge l’entrée."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok

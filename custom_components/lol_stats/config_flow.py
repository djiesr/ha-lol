"""Config flow : Riot ID + tag, région (plateforme), clé API."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers import aiohttp_client, translation
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .api import (
    RiotApiClient,
    RiotApiError,
    RiotAuthError,
    RiotNotFoundError,
    RiotRateLimitError,
)
from .const import (
    CONF_API_KEY,
    CONF_GAME_NAME,
    CONF_PLATFORM,
    CONF_TAG_LINE,
    DOMAIN,
    PLATFORM_ORDER,
    PLATFORM_TO_REGIONAL,
)

async def _platform_options(hass: HomeAssistant) -> list[dict[str, str]]:
    """Libellés de plateforme selon la langue HA."""
    trl = await translation.async_get_translations(
        hass, hass.config.language, "integration", [DOMAIN]
    )
    opts: list[dict[str, str]] = []
    for key in PLATFORM_ORDER:
        if key not in PLATFORM_TO_REGIONAL:
            continue
        label = trl.get(f"component.{DOMAIN}.config.platform.{key}", key)
        opts.append({"value": key, "label": label})
    return opts


class LolStatsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Flux de configuration unique (multi-entrées possible)."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Étape unique : identifiants + région + clé."""
        errors: dict[str, str] = {}
        if user_input is not None:
            platform = user_input[CONF_PLATFORM]
            if platform not in PLATFORM_TO_REGIONAL:
                errors["base"] = "unknown"
            else:
                regional = PLATFORM_TO_REGIONAL[platform]
                session = aiohttp_client.async_get_clientsession(self.hass)
                client = RiotApiClient(session, user_input[CONF_API_KEY], regional)
                try:
                    account = await client.get_account_by_riot_id(
                        user_input[CONF_GAME_NAME].strip(),
                        user_input[CONF_TAG_LINE].strip(),
                    )
                except RiotAuthError:
                    errors["base"] = "invalid_auth"
                except RiotNotFoundError:
                    errors["base"] = "not_found"
                except RiotRateLimitError:
                    errors["base"] = "rate_limited"
                except RiotApiError:
                    errors["base"] = "unknown"
                else:
                    puuid = account.get("puuid")
                    if not puuid:
                        errors["base"] = "unknown"
                    else:
                        game_name = user_input[CONF_GAME_NAME].strip()
                        tag_line = user_input[CONF_TAG_LINE].strip()
                        await self.async_set_unique_id(
                            f"{platform}_{game_name.lower()}_{tag_line.lower()}"
                        )
                        self._abort_if_unique_id_configured()
                        title = f"{game_name}#{tag_line}"
                        return self.async_create_entry(
                            title=title,
                            data={
                                CONF_API_KEY: user_input[CONF_API_KEY].strip(),
                                CONF_GAME_NAME: game_name,
                                CONF_TAG_LINE: tag_line,
                                CONF_PLATFORM: platform,
                                "puuid": puuid,
                            },
                        )

        options = await _platform_options(self.hass)
        schema = vol.Schema(
            {
                vol.Required(CONF_API_KEY): str,
                vol.Required(CONF_GAME_NAME): str,
                vol.Required(CONF_TAG_LINE): str,
                vol.Required(CONF_PLATFORM): SelectSelector(
                    SelectSelectorConfig(
                        options=options,
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

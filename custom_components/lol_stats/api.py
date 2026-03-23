"""Client HTTP async pour l'API Riot (compte + match-v5)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from urllib.parse import quote

import aiohttp

from .const import MATCH_HISTORY_COUNT

_LOGGER = logging.getLogger(__name__)

RIOT_TOKEN_HEADER = "X-Riot-Token"


class RiotApiError(Exception):
    """Erreur générique API Riot."""


class RiotAuthError(RiotApiError):
    """Clé API invalide ou expirée."""


class RiotNotFoundError(RiotApiError):
    """Compte ou ressource introuvable."""


class RiotRateLimitError(RiotApiError):
    """Quota ou limite de débit dépassé."""


class RiotApiClient:
    """Client minimal account-v1 + match-v5."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        api_key: str,
        regional_host: str,
    ) -> None:
        self._session = session
        self._api_key = api_key
        self._base = f"https://{regional_host}.api.riotgames.com"

    def _headers(self) -> dict[str, str]:
        return {RIOT_TOKEN_HEADER: self._api_key}

    async def _request(self, method: str, path: str) -> Any:
        url = f"{self._base}{path}"
        try:
            async with self._session.request(
                method,
                url,
                headers=self._headers(),
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                if resp.status == 401:
                    raise RiotAuthError("Invalid or expired API key")
                if resp.status == 403:
                    raise RiotAuthError("Forbidden (check API key / product access)")
                if resp.status == 404:
                    raise RiotNotFoundError("Resource not found")
                if resp.status == 429:
                    raise RiotRateLimitError("Rate limit exceeded")
                text = await resp.text()
                _LOGGER.debug("Riot API error %s: %s", resp.status, text[:500])
                raise RiotApiError(f"HTTP {resp.status}")
        except aiohttp.ClientError as err:
            raise RiotApiError(str(err)) from err

    async def get_account_by_riot_id(self, game_name: str, tag_line: str) -> dict[str, Any]:
        """GET /riot/account/v1/accounts/by-riot-id/{gameName}/{tagLine}"""
        gn = quote(game_name, safe="")
        tag = quote(tag_line, safe="")
        path = f"/riot/account/v1/accounts/by-riot-id/{gn}/{tag}"
        return await self._request("GET", path)

    async def get_match_ids(self, puuid: str, count: int = MATCH_HISTORY_COUNT) -> list[str]:
        """GET /lol/match/v5/matches/by-puuid/{puuid}/ids"""
        p = quote(puuid, safe="")
        path = f"/lol/match/v5/matches/by-puuid/{p}/ids?start=0&count={count}"
        data = await self._request("GET", path)
        if not isinstance(data, list):
            return []
        return [str(x) for x in data]

    async def get_match(self, match_id: str) -> dict[str, Any]:
        """GET /lol/match/v5/matches/{matchId}"""
        mid = quote(match_id, safe="")
        path = f"/lol/match/v5/matches/{mid}"
        return await self._request("GET", path)

    async def get_matches(self, match_ids: list[str], max_concurrent: int = 5) -> list[dict[str, Any]]:
        """Télécharge plusieurs matchs avec limite de concurrence."""
        if not match_ids:
            return []

        sem = asyncio.Semaphore(max_concurrent)

        async def one(mid: str) -> dict[str, Any]:
            async with sem:
                return await self.get_match(mid)

        return await asyncio.gather(*[one(mid) for mid in match_ids])

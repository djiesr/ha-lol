"""Coordinator : détection de changement sur les IDs de match puis agrégation."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    RiotApiClient,
    RiotAuthError,
    RiotNotFoundError,
    RiotRateLimitError,
)
from .const import DEFAULT_SCAN_INTERVAL, MATCH_HISTORY_COUNT

_LOGGER = logging.getLogger(__name__)


@dataclass
class ChampionAgg:
    """Agrégation par champion sur la fenêtre courante."""

    games: int = 0
    wins: int = 0


@dataclass
class MatchSummary:
    """Résumé d'une partie pour le joueur."""

    match_id: str
    win: bool
    champion_name: str
    kills: int
    deaths: int
    assists: int
    queue_id: int | None
    game_duration_sec: int
    game_mode: str | None


@dataclass
class LolStatsData:
    """Données exposées aux entités."""

    game_name: str
    tag_line: str
    puuid: str
    wins: int
    losses: int
    win_rate: float | None
    matches: list[MatchSummary] = field(default_factory=list)
    champion_stats: dict[str, ChampionAgg] = field(default_factory=dict)
    matches_window: int = 0


def _parse_match_for_puuid(match: dict[str, Any], puuid: str) -> MatchSummary | None:
    """Extrait les stats du joueur depuis un DTO match-v5."""
    info = match.get("info") or {}
    participants = info.get("participants")
    if not isinstance(participants, list):
        return None
    for p in participants:
        if p.get("puuid") != puuid:
            continue
        champ = p.get("championName") or str(p.get("championId", "?"))
        return MatchSummary(
            match_id=str(match.get("metadata", {}).get("matchId", "")),
            win=bool(p.get("win")),
            champion_name=str(champ),
            kills=int(p.get("kills") or 0),
            deaths=int(p.get("deaths") or 0),
            assists=int(p.get("assists") or 0),
            queue_id=info.get("queueId") if isinstance(info.get("queueId"), int) else None,
            game_duration_sec=int(info.get("gameDuration") or 0),
            game_mode=info.get("gameMode"),
        )
    return None


def _aggregate(matches: list[dict[str, Any]], puuid: str, game_name: str, tag_line: str) -> LolStatsData:
    summaries: list[MatchSummary] = []
    champ: dict[str, ChampionAgg] = {}
    wins = 0
    losses = 0

    for m in matches:
        s = _parse_match_for_puuid(m, puuid)
        if s is None:
            continue
        summaries.append(s)
        if s.win:
            wins += 1
        else:
            losses += 1
        agg = champ.setdefault(s.champion_name, ChampionAgg())
        agg.games += 1
        if s.win:
            agg.wins += 1

    total = wins + losses
    win_rate = (wins / total) if total else None

    return LolStatsData(
        game_name=game_name,
        tag_line=tag_line,
        puuid=puuid,
        wins=wins,
        losses=losses,
        win_rate=win_rate,
        matches=summaries,
        champion_stats=champ,
        matches_window=len(summaries),
    )


class LolStatsCoordinator(DataUpdateCoordinator[LolStatsData]):
    """1 requête liste/min ; détails seulement si les IDs ont changé."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: RiotApiClient,
        game_name: str,
        tag_line: str,
        puuid: str,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{game_name}#{tag_line}",
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.client = client
        self.game_name = game_name
        self.tag_line = tag_line
        self.puuid = puuid
        self._last_match_ids: tuple[str, ...] | None = None

    async def _async_update_data(self) -> LolStatsData:
        try:
            ids = await self.client.get_match_ids(self.puuid, MATCH_HISTORY_COUNT)
        except RiotAuthError as err:
            raise UpdateFailed(f"Authentication failed: {err}") from err
        except RiotNotFoundError as err:
            raise UpdateFailed(f"Not found: {err}") from err
        except RiotRateLimitError as err:
            raise UpdateFailed(f"Rate limited: {err}") from err
        except Exception as err:
            raise UpdateFailed(str(err)) from err

        key = tuple(ids)
        if self._last_match_ids == key and self.data is not None:
            return self.data

        if not ids:
            empty = LolStatsData(
                game_name=self.game_name,
                tag_line=self.tag_line,
                puuid=self.puuid,
                wins=0,
                losses=0,
                win_rate=None,
                matches=[],
                champion_stats={},
                matches_window=0,
            )
            self._last_match_ids = key
            return empty

        try:
            raw_matches = await self.client.get_matches(ids)
        except RiotAuthError as err:
            raise UpdateFailed(f"Authentication failed: {err}") from err
        except RiotRateLimitError as err:
            raise UpdateFailed(f"Rate limited: {err}") from err
        except Exception as err:
            raise UpdateFailed(str(err)) from err

        data = _aggregate(raw_matches, self.puuid, self.game_name, self.tag_line)
        self._last_match_ids = key
        return data

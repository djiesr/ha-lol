"""Capteurs : profil, W/L, winrate, 5 derniers matchs, top 5 champions."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import translation
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    LAST_MATCHES_COUNT,
    MATCH_HISTORY_COUNT,
    QUEUE_ID_LABEL_KEYS,
    QUEUE_ID_SHORT_FALLBACK,
    TOP_CHAMPIONS_COUNT,
)
from .coordinator import ChampionAgg, LolStatsCoordinator, LolStatsData, MatchSummary


async def _load_queue_labels(hass: HomeAssistant, domain: str) -> dict[int, str]:
    trl = await translation.async_get_translations(
        hass, hass.config.language, "integration", [domain]
    )
    prefix = f"component.{domain}.config.queue."
    out: dict[int, str] = {}
    for qid, key in QUEUE_ID_LABEL_KEYS.items():
        fallback = QUEUE_ID_SHORT_FALLBACK.get(qid, f"Queue {qid}")
        out[qid] = trl.get(f"{prefix}{key}", fallback)
    return out


def _device_info(entry_id: str, coordinator: LolStatsCoordinator) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, entry_id)},
        name=f"{coordinator.game_name}#{coordinator.tag_line}",
        manufacturer="Riot Games API",
        model="League of Legends",
    )


def _top_champions(
    data: LolStatsData | None, n: int
) -> list[tuple[str, ChampionAgg]]:
    if not data or not data.champion_stats:
        return []
    items = sorted(
        data.champion_stats.items(),
        key=lambda kv: (-kv[1].games, -kv[1].wins),
    )
    return items[:n]


def _match_state_line(m: MatchSummary, queue_labels: dict[int, str]) -> str:
    mode = "?"
    if m.queue_id is not None and m.queue_id in queue_labels:
        mode = queue_labels[m.queue_id]
        # Ancien bug : fallback traduction = str(queue_id) → « 450 »
        if mode == str(m.queue_id):
            mode = QUEUE_ID_SHORT_FALLBACK.get(m.queue_id, m.game_mode or mode)
    elif m.queue_id is not None:
        mode = QUEUE_ID_SHORT_FALLBACK.get(
            m.queue_id, m.game_mode or str(m.queue_id)
        )
    else:
        mode = m.game_mode or "?"
    result = "WIN" if m.win else "LOSS"
    champ = m.champion_name.replace(" ", "")
    return f"{mode} - {result} - {champ}"


def _match_attrs(m: MatchSummary, queue_labels: dict[int, str]) -> dict[str, Any]:
    d: dict[str, Any] = {
        "match_id": m.match_id,
        "win": m.win,
        "champion": m.champion_name,
        "kills": m.kills,
        "deaths": m.deaths,
        "assists": m.assists,
        "queue_id": m.queue_id,
        "game_duration_sec": m.game_duration_sec,
        "game_mode": m.game_mode,
    }
    if m.queue_id is not None:
        q = queue_labels.get(m.queue_id)
        if q is None or q == str(m.queue_id):
            q = QUEUE_ID_SHORT_FALLBACK.get(m.queue_id, str(m.queue_id))
        d["queue_label"] = q
    return d


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Enregistre tous les capteurs pour cette entrée."""
    coordinator: LolStatsCoordinator = hass.data[DOMAIN][entry.entry_id]
    queue_labels = await _load_queue_labels(hass, DOMAIN)

    entities: list[SensorEntity] = [
        LolStatsNicknameSensor(coordinator, entry),
        LolStatsWinsSensor(coordinator, entry),
        LolStatsLossesSensor(coordinator, entry),
        LolStatsWinRateSensor(coordinator, entry),
    ]
    entities.extend(
        LolStatsMatchSensor(coordinator, entry, i, queue_labels)
        for i in range(LAST_MATCHES_COUNT)
    )
    entities.extend(
        LolStatsChampionSensor(coordinator, entry, i) for i in range(TOP_CHAMPIONS_COUNT)
    )
    async_add_entities(entities)


class LolStatsNicknameSensor(CoordinatorEntity[LolStatsCoordinator], SensorEntity):
    """Riot ID (nom) + attributs riot_id / puuid / fenêtre."""

    _attr_has_entity_name = True
    _attr_translation_key = "nickname"
    _attr_should_poll = False

    def __init__(self, coordinator: LolStatsCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry_id = entry.entry_id
        self._attr_unique_id = f"{entry.entry_id}_nickname"

    @property
    def native_value(self) -> str | None:
        data = self.coordinator.data
        return data.game_name if data else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data
        if data is None:
            return {}
        return {
            "matches_window": MATCH_HISTORY_COUNT,
            "riot_id": f"{data.game_name}#{data.tag_line}",
            "puuid": data.puuid,
        }

    @property
    def device_info(self) -> DeviceInfo:
        return _device_info(self._entry_id, self.coordinator)


class LolStatsWinsSensor(CoordinatorEntity[LolStatsCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "wins"
    _attr_should_poll = False

    def __init__(self, coordinator: LolStatsCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry_id = entry.entry_id
        self._attr_unique_id = f"{entry.entry_id}_wins"

    @property
    def native_value(self) -> int | None:
        data = self.coordinator.data
        return data.wins if data else None

    @property
    def device_info(self) -> DeviceInfo:
        return _device_info(self._entry_id, self.coordinator)


class LolStatsLossesSensor(CoordinatorEntity[LolStatsCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "losses"
    _attr_should_poll = False

    def __init__(self, coordinator: LolStatsCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry_id = entry.entry_id
        self._attr_unique_id = f"{entry.entry_id}_losses"

    @property
    def native_value(self) -> int | None:
        data = self.coordinator.data
        return data.losses if data else None

    @property
    def device_info(self) -> DeviceInfo:
        return _device_info(self._entry_id, self.coordinator)


class LolStatsWinRateSensor(CoordinatorEntity[LolStatsCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "win_rate"
    _attr_should_poll = False
    _attr_native_unit_of_measurement = "%"
    _attr_suggested_display_precision = 0

    def __init__(self, coordinator: LolStatsCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry_id = entry.entry_id
        self._attr_unique_id = f"{entry.entry_id}_win_rate"

    @property
    def native_value(self) -> int | None:
        data = self.coordinator.data
        if data is None or data.win_rate is None:
            return None
        return int(round(data.win_rate * 100.0))

    @property
    def device_info(self) -> DeviceInfo:
        return _device_info(self._entry_id, self.coordinator)


class LolStatsMatchSensor(CoordinatorEntity[LolStatsCoordinator], SensorEntity):
    """Une des 5 dernières parties (état texte + détail en attributs)."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: LolStatsCoordinator,
        entry: ConfigEntry,
        index: int,
        queue_labels: dict[int, str],
    ) -> None:
        super().__init__(coordinator)
        self._entry_id = entry.entry_id
        self._index = index
        self._queue_labels = queue_labels
        n = index + 1
        self._attr_translation_key = f"match_{n}"
        self._attr_unique_id = f"{entry.entry_id}_match_{n}"

    @property
    def native_value(self) -> str | None:
        data = self.coordinator.data
        if not data or self._index >= len(data.matches):
            return None
        return _match_state_line(data.matches[self._index], self._queue_labels)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data
        if not data or self._index >= len(data.matches):
            return {}
        return _match_attrs(data.matches[self._index], self._queue_labels)

    @property
    def device_info(self) -> DeviceInfo:
        return _device_info(self._entry_id, self.coordinator)


class LolStatsChampionSensor(CoordinatorEntity[LolStatsCoordinator], SensorEntity):
    """Un des 5 champions les plus joués (état = nom, stats en attributs)."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, coordinator: LolStatsCoordinator, entry: ConfigEntry, rank: int) -> None:
        super().__init__(coordinator)
        self._entry_id = entry.entry_id
        self._rank = rank
        n = rank + 1
        self._attr_translation_key = f"champion_{n}"
        self._attr_unique_id = f"{entry.entry_id}_champion_{n}"

    @property
    def native_value(self) -> str | None:
        data = self.coordinator.data
        top = _top_champions(data, TOP_CHAMPIONS_COUNT)
        if self._rank >= len(top):
            return None
        return top[self._rank][0]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data
        top = _top_champions(data, TOP_CHAMPIONS_COUNT)
        if self._rank >= len(top):
            return {}
        name, agg = top[self._rank]
        losses = agg.games - agg.wins
        wr_pct = (
            int(round((agg.wins / agg.games) * 100.0)) if agg.games else None
        )
        return {
            "champion": name,
            "games": agg.games,
            "wins": agg.wins,
            "losses": losses,
            "win_rate": wr_pct,
        }

    @property
    def device_info(self) -> DeviceInfo:
        return _device_info(self._entry_id, self.coordinator)

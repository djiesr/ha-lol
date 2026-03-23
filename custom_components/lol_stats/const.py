"""Constantes pour l'intégration League of Legends Stats."""

from datetime import timedelta

DOMAIN = "lol_stats"

CONF_GAME_NAME = "game_name"
CONF_TAG_LINE = "tag_line"
CONF_PLATFORM = "platform"
CONF_API_KEY = "api_key"

DEFAULT_SCAN_INTERVAL = timedelta(seconds=60)

# Fenêtre agrégée (W/L, top champions) — volontairement modeste pour rester sous les rate limits Riot
MATCH_HISTORY_COUNT = 10
# Derniers matchs exposés en capteurs séparés
LAST_MATCHES_COUNT = 5
# Top champions (capteurs séparés)
TOP_CHAMPIONS_COUNT = 5

# Plateforme de jeu (routing) -> hôte régional Riot (account + match-v5)
# https://developer.riotgames.com/docs/lol#routing-values
PLATFORM_TO_REGIONAL: dict[str, str] = {
    "BR1": "americas",
    "EUN1": "europe",
    "EUW1": "europe",
    "JP1": "asia",
    "KR": "asia",
    "LA1": "americas",
    "LA2": "americas",
    "NA1": "americas",
    "OC1": "sea",
    "TR1": "europe",
    "RU": "europe",
}

# Ordre d’affichage dans le config flow (régions les plus courantes en premier)
PLATFORM_ORDER: list[str] = [
    "EUW1",
    "EUN1",
    "NA1",
    "BR1",
    "JP1",
    "KR",
    "LA1",
    "LA2",
    "OC1",
    "TR1",
    "RU",
]

# queueId -> clé de traduction (config.queue.*)
QUEUE_ID_LABEL_KEYS: dict[int, str] = {
    420: "ranked_solo",
    430: "normal_blind",
    440: "ranked_flex",
    450: "aram",
    400: "normal_draft",
    900: "urf",
    1020: "one_for_all",
    1300: "nexus_blitz",
    1400: "ultimate_spellbook",
    1700: "arena",
    1900: "urf_alt",
}

# Libellé court si la traduction HA n’est pas résolue (évite d’afficher « 450 » au lieu de « ARAM »)
# Réf. queueId Riot : https://developer.riotgames.com/docs/lol#match-v5/GET_getMatch
QUEUE_ID_SHORT_FALLBACK: dict[int, str] = {
    400: "Normal Draft",
    420: "Ranked Solo/Duo",
    430: "Normal (Blind)",
    440: "Ranked Flex",
    450: "ARAM",
    900: "URF",
    1020: "One for All",
    1300: "Nexus Blitz",
    1400: "Ultimate Spellbook",
    1700: "Arena",
    1900: "URF",
}

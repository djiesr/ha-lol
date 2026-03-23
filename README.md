# League of Legends Stats (Home Assistant)

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

Custom integration for [Home Assistant](https://www.home-assistant.io/) that pulls your League of Legends stats from the **Riot Games API** (account + **match-v5**).

**Repository:** [github.com/djiesr/ha-lol](https://github.com/djiesr/ha-lol)

## Features

- **Sensors**: Riot ID (summoner name), **wins / losses / win rate** over the last **50** ranked matches returned by the API, **last 5 matches** (state string + details in attributes), **top 5 champions** (name + stats in attributes).
- **Refresh**: about **once per minute**; one lightweight call for **match IDs**; full match payloads are fetched **only when the ID list changes** (saves API quota).

UI strings: **English** (default) and **French** (via Home Assistant language).

## Requirements

1. A **Riot developer account** and API key (see [Riot API key](#riot-api-key) below).
2. Your **Riot ID** as **game name** + **tag** (the part after `#` in the Riot client, e.g. `Player` + `NA1`).

## Riot API key

1. Open the **[Riot Developer Portal](https://developer.riotgames.com/)** and sign in with your Riot account.
2. Click **Register product** (or **Register Product**).
3. Follow the flow and choose **Personal API Key** when prompted (for personal / small projects).
4. Complete the **registration form** (product name, description, etc.) as required by Riot.
5. After approval / setup, copy your **API key** and use it in Home Assistant.  
   - **Development** keys often expire every **24 hours**; regenerate or move to a **production** key for long-term use.  
   - Respect [Riot’s policies](https://developer.riotgames.com/docs/lol) and **rate limits**.

## Installation

### HACS

1. Open HACS → **Integrations** → menu **⋮** → **Custom repositories**.
2. Add repository URL `https://github.com/djiesr/ha-lol`, category **Integration**.
3. Install **League of Legends Stats**.
4. Restart Home Assistant.
5. **Settings** → **Devices & services** → **Add integration** → **League of Legends Stats**.

### Manual

Copy the `custom_components/lol_stats` folder into your Home Assistant configuration directory (`/config/custom_components/lol_stats`), restart Home Assistant, then add the integration as above.

### Branding

`icon.png` (next to `manifest.json`) is used for the integration card. Restart HA or hard-refresh the browser if the icon does not update.

## Configuration

| Field | Description |
|--------|-------------|
| **API key** | Sent as `X-Riot-Token` |
| **Riot ID** | Game name (before `#`) |
| **Tag** | Tag only, **without** `#` |
| **Region (platform)** | e.g. EUW1, NA1 — must match the server you play on |

You can add **multiple entries** (e.g. EU + NA) by adding the integration again.

## Entities

| Entity ID pattern | Description |
|-------------------|-------------|
| `nickname` | Summoner name; attributes: `matches_window`, `riot_id`, `puuid` |
| `wins` / `losses` | Counts on the 50-match window |
| `win_rate` | Percentage (integer), no decimals |
| `match_1` … `match_5` | Last five matches (state + attributes) |
| `champion_1` … `champion_5` | Top five champions by games played |

## Rate limits

The integration is designed to minimize calls. A full refresh (50 match details) can still spike usage; if you see **rate limit** errors, wait a few minutes, avoid repeated failed config submissions, and ensure no other app uses the same key.

## Developer tools (optional)

The repo includes **`tools/sync_to_ha.py`** / **`sync_to_ha.ps1`** to copy `custom_components/lol_stats` to a host over SSH and restart Core. Copy `ha-sync.example.env` to `tools/ha_local.env` (gitignored) and set `HA_SSH_HOST`, `HA_SSH_PASSWORD`, etc. Requires `pip install paramiko scp`.

See also **`ha-sync.example.env`** at the repository root.

## License

MIT — see [LICENSE](LICENSE).

## Disclaimer

League of Legends is a trademark of Riot Games, Inc. This project is not affiliated with or endorsed by Riot Games.

# RL Tracker

A local session and lifetime stat tracker for Rocket League, built in Python. No memory reading, no DLL injection — it connects to the official Stats API that Psyonix built into the game for exactly this purpose.

---

## How it works

Rocket League has a built-in Stats API that broadcasts live match data over a local TCP socket at `127.0.0.1:49123`. It's an official Psyonix feature enabled via a config file — no mods, no third-party plugins required. This tracker connects to that socket and reads the stream passively, which means it's completely safe alongside anti-cheat.

To enable the API, add the following to `DefaultStatsAPI.ini` in your Rocket League config folder:

```ini
[TAGame.MatchStatsExporter_TA]
Port=49123
PacketSendRate=10
```

`PacketSendRate` controls how many times per second the game sends telemetry. A higher value gives more samples for speed and boost averages, but honestly those metrics aren't particularly meaningful — they're in the tracker because the data was there and stats are fun, not because they drive any real insight. 10 is plenty. Bumping it up won't break anything, it'll just use more of your CPU for marginal gains on a stat you probably won't make decisions from.

Restart the game after saving. The socket will open automatically whenever you're in a match.

The two event types the tracker listens for:

- `UpdateState` — fires continuously during a match. Used for live telemetry sampling (speed, boost, supersonic) and goal timeline detection.
- `MatchDestroyed` — fires when a lobby closes. Used as a fallback commit trigger if the primary trigger (`bHasWinner`) didn't fire.

Match results are committed as soon as `bHasWinner` flips to true in the game state, which means forfeits are caught instantly without waiting for the lobby to close.

---

## Features

**Session tracking** — sessions are ephemeral. Every time you launch the tracker you start from 0:0. Wins, losses, win rate, streak, and goal differential are tracked separately for ranked and unranked. You can toggle between the two with the RANKED / UNRANKED button; each has its own independent counters.

**Manual correction** — +/− buttons under the W and L displays let you nudge the score if the tracker misfires.

**Lifetime stats** — ranked matches accumulate into a persistent lifetime record. Accessible via the 📊 button. Stats are tracked per entity: yourself, each tracked teammate individually, and every duo/trio combination you've queued with.

**Teammate detection** — define your regular squadmates in Settings. Each teammate supports a list of alt account names so the tracker resolves them correctly regardless of which account they're on. When a teammate is detected in your lobby, that match is written to their individual lifetime node and to the relevant duo/trio group node.

**Nerd Stats** (expandable panel) — per-player breakdown of goals, assists, saves, shot accuracy, assist rate, average speed, average boost, and supersonic percentage for the current session. Also shows OT rate, comeback count (came back from 3+ down), and a goal-by-goal timeline for the last match.

**OBS integration** — four text files are written to `%APPDATA%\RLTracker\obs_outputs\` and updated the moment any session stat changes:

| File | Contents |
|---|---|
| `wins.txt` | Current session wins |
| `losses.txt` | Current session losses |
| `winrate.txt` | Win rate as a percentage |
| `streak.txt` | Current streak, e.g. `🔥 3W` or `🧊 2L` |

Files always reflect whichever session is active — if you switch to unranked, the files switch with it.

---

## OBS setup

1. Add a **Text (GDI+)** source in OBS.
2. Check **Read from file**.
3. Point it to the relevant file in `%APPDATA%\RLTracker\obs_outputs\`.
4. Style the font, size, and color directly in OBS.

Each file can be its own text source, giving you full control over layout and positioning on your scene.

---

## Requirements

- Python 3.8+
- Rocket League with the Stats API enabled (see above)
- `customtkinter` (see `requirements.txt`)

---

## Installation

```bash
git clone https://github.com/Artificial-Dumbness420/rl_tracker
cd rl-tracker
pip install -r requirements.txt
python rl_tracker.py
```

Launch the tracker before or after opening Rocket League — it will keep retrying the connection every 3 seconds until the socket is available.

---

## First-time setup

On first launch you'll be prompted to enter your Rocket League name. The tracker uses partial string matching, so you don't need an exact match — just enough to be unambiguous.

To add teammates, open Settings (⚙️), click **+ Add Teammate**, and fill in their name and any alt account names. Save and you're done.

---

## Data storage

The save file lives at `%APPDATA%\RLTracker\tracker_save_data.json`. It stores your config and lifetime stats only — session data is never written to disk.

---

## Known limitations

- The telemetry plugin does not broadcast playlist type (Ranked vs Casual) or MMR. Ranked/Unranked mode must be toggled manually.
- Game mode (1v1, 2v2, etc.) is also not broadcast and must be set manually via the dropdown.
- Telemetry is only sampled for players defined in your config. Opponents and unknown teammates are not tracked.

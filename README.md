# RL Tracker

A local session and lifetime stat tracker for Rocket League, built in Python. No memory reading, no DLL injection — it listens to the telemetry socket that Rocket League already broadcasts natively for third-party tools.

---

## How it works

Rocket League (with BakkesMod or a compatible plugin) broadcasts live match data over a local TCP socket at `127.0.0.1:49123`. This tracker connects to that socket and reads the stream passively. It never touches game memory or modifies any files, which means it's safe to use alongside any anti-cheat.

The two event types it listens for:

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
- BakkesMod or a compatible Rocket League plugin that broadcasts on `127.0.0.1:49123`
- `customtkinter` (see `requirements.txt`)

---

## Installation

```bash
git clone https://github.com/yourname/rl-tracker.git
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

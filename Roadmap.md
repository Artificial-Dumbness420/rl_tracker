# Roadmap

This is a working document. Nothing here is a promise, but it reflects where the project is genuinely headed.

The tracker already does its core job well — session W/L, lifetime stats, teammate synergy, live telemetry, and OBS outputs. The next phases are about presentation and reach.

---

## Near-term

**Discord webhook**
At session reset or close, package the session data into a payload and post it automatically to a Discord channel. End-of-session recap showing squad win rate, goal differential, individual telemetry highlights, and comeback count. No copy-pasting, no screenshots.

**OBS scene trigger**
A `last_result.txt` file written on every match commit (`WIN` / `LOSS`). Lets you set up OBS scene transitions or alerts that fire automatically when a match ends — win animations, loss reactions, whatever you want.

---

## Medium-term

**React frontend**
The Python script becomes a hidden background service. A React app (via Electron or Tauri) reads the session data and renders it properly — momentum graphs built from the match timeline, animated stat cards, a floating transparent overlay. The data architecture is already designed for this; the backend won't need significant changes.

---

## Not planned

A few things that come up naturally but aren't possible given how the telemetry plugin works:

- **Auto-detecting Ranked vs Casual** — the plugin doesn't broadcast playlist type. This has to stay a manual toggle.
- **Auto-detecting game mode** — same limitation. 1v1/2v2/3v3 isn't in the data stream.
- **MMR tracking** — also not broadcast. Would require a separate API integration which is out of scope for a local tool.

---

## Feedback

If you're using this and have ideas, open an issue or drop a comment. Priorities can shift based on what people actually find useful.
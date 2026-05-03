import socket
import json
import threading
import os
import customtkinter as ctk
from datetime import datetime
from itertools import combinations

# --- CONFIGURATION ---
HOST = '127.0.0.1'
PORT = 49123

appdata_path = os.getenv('APPDATA')
SAVE_DIR = os.path.join(appdata_path, 'RLTracker')
os.makedirs(SAVE_DIR, exist_ok=True)
SAVE_FILE = os.path.join(SAVE_DIR, "tracker_save_data.json")

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


# ── HELPERS ──────────────────────────────────────────────────────────────────

def blank_session():
    return {"wins": 0, "losses": 0, "streak": 0, "goal_diff": 0,
            "players": {}, "maps": {}, "match_history":[]}

def blank_entity_stats():
    """Lifetime stats node for a player or group."""
    return {
        "wins": 0, "losses": 0,
        "goals": 0, "assists": 0, "saves": 0, "shots": 0, "demos": 0,
        "speed_sum": 0, "boost_sum": 0, "supersonic_frames": 0, "samples": 0,
        "by_mode": {}
    }

def get_entity_node(lifetime, key):
    if key not in lifetime:
        lifetime[key] = blank_entity_stats()
    return lifetime[key]

def get_mode_subnode(entity_node, mode):
    if mode not in entity_node["by_mode"]:
        entity_node["by_mode"][mode] = {"wins": 0, "losses": 0}
    return entity_node["by_mode"][mode]

def commit_entity(lifetime, key, mode, result, match_stats):
    """Write one match result + telemetry into a lifetime entity node."""
    node      = get_entity_node(lifetime, key)
    mode_node = get_mode_subnode(node, mode)
    if result == "win":
        node["wins"]      += 1
        mode_node["wins"] += 1
    else:
        node["losses"]      += 1
        mode_node["losses"] += 1
    for stat in["goals", "assists", "saves", "shots", "demos",
                 "speed_sum", "boost_sum", "supersonic_frames", "samples"]:
        node[stat] = node.get(stat, 0) + match_stats.get(stat, 0)

def format_stat_block(node, label):
    """Return a formatted text block for a lifetime entity node."""
    w    = node.get("wins", 0)
    l    = node.get("losses", 0)
    tot  = w + l
    wr   = f"{int(w/tot*100)}%" if tot > 0 else "N/A"
    g    = node.get("goals", 0)
    a    = node.get("assists", 0)
    sv   = node.get("saves", 0)
    sh   = node.get("shots", 0)
    samp = node.get("samples", 0)
    acc  = f"{int(g/sh*100)}%"  if sh   > 0 else "N/A"
    ar   = f"{int(a/g*100)}%"   if g    > 0 else "N/A"
    spd  = int(node.get("speed_sum", 0) / samp)          if samp > 0 else 0
    bst  = int(node.get("boost_sum", 0) / samp)          if samp > 0 else 0
    ss   = int(node.get("supersonic_frames", 0)/samp*100) if samp > 0 else 0

    lines =[
        f"=== {label} ===",
        f"  Record   : {w}W – {l}L  (WR: {wr})",
        f"  G:{g}  A:{a}  Sv:{sv}  Shots:{sh}",
        f"  Shot Acc : {acc}  |  Assist Rate: {ar}",
        f"  Avg Speed: {spd}  |  Avg Boost: {bst}",
        f"  Supersonic: {ss}% of match",
    ]
    by_mode = node.get("by_mode", {})
    if by_mode:
        lines.append("  By Mode:")
        for mode, mn in sorted(by_mode.items()):
            lines.append(f"    {mode}: {mn['wins']}W {mn['losses']}L")
    return "\n".join(lines)


# ── SETTINGS WINDOW ───────────────────────────────────────────────────────────

class SettingsWindow(ctk.CTkToplevel):
    """
    Dynamic teammate management. Each teammate has a canonical name + aliases.
    Config structure:
        config["teammates"] = [
            {"name": "Nibbler", "aliases": ["NibblerAlt"]},
            {"name": "jstfrx",  "aliases":[]},
        ]
    """
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Settings")
        self.geometry("380x500")
        self.attributes("-topmost", True)
        self.resizable(False, False)
        self.parent = parent

        ctk.CTkLabel(self, text="Your RL Name (partial match):",
                     font=("Arial", 12, "bold")).pack(pady=(15, 2))
        self.name_entry = ctk.CTkEntry(self, width=280)
        self.name_entry.pack(pady=(0, 10))
        self.name_entry.insert(0, parent.config.get("primary_player", ""))

        ctk.CTkLabel(self, text="Tracked Teammates:",
                     font=("Arial", 12, "bold")).pack(pady=(5, 2))

        self.teammate_frame = ctk.CTkScrollableFrame(self, width=340, height=240)
        self.teammate_frame.pack(padx=10, pady=(0, 8))

        self.teammate_rows =[]
        for tm in parent.config.get("teammates",[]):
            self._add_teammate_row(tm.get("name", ""), ", ".join(tm.get("aliases",[])))

        ctk.CTkButton(self, text="+ Add Teammate", width=160,
                      fg_color="#2980B9", hover_color="#2471A3",
                      command=lambda: self._add_teammate_row()).pack(pady=(0, 6))

        ctk.CTkButton(self, text="Save Settings", width=160,
                      fg_color="#2ECC71", hover_color="#27AE60",
                      command=self.save_settings).pack(pady=(4, 15))

    def _add_teammate_row(self, name="", aliases=""):
        row_frame = ctk.CTkFrame(self.teammate_frame, fg_color="#2b2b2b", corner_radius=6)
        row_frame.pack(fill="x", padx=4, pady=4)

        inner = ctk.CTkFrame(row_frame, fg_color="transparent")
        inner.pack(fill="x", padx=6, pady=4)

        ctk.CTkLabel(inner, text="Name:", width=46, anchor="w").grid(row=0, column=0, sticky="w")
        name_entry = ctk.CTkEntry(inner, width=180)
        name_entry.grid(row=0, column=1, padx=(4, 4))
        name_entry.insert(0, name)

        del_btn = ctk.CTkButton(
            inner, text="✕", width=28, height=24,
            fg_color="#C0392B", hover_color="#A93226",
            command=lambda rf=row_frame: self._remove_row(rf))
        del_btn.grid(row=0, column=2)

        ctk.CTkLabel(inner, text="Alts:", width=46, anchor="w").grid(
            row=1, column=0, sticky="w", pady=(4, 0))
        alias_entry = ctk.CTkEntry(inner, width=180, placeholder_text="comma separated")
        alias_entry.grid(row=1, column=1, padx=(4, 4), pady=(4, 0))
        alias_entry.insert(0, aliases)

        self.teammate_rows.append(
            {"frame": row_frame, "name_entry": name_entry, "alias_entry": alias_entry})

    def _remove_row(self, frame):
        self.teammate_rows =[r for r in self.teammate_rows if r["frame"] is not frame]
        frame.destroy()

    def save_settings(self):
        self.parent.config["primary_player"] = self.name_entry.get().strip()
        teammates =[]
        for row in self.teammate_rows:
            name = row["name_entry"].get().strip()
            if not name:
                continue
            aliases_raw = row["alias_entry"].get().strip()
            aliases =[a.strip() for a in aliases_raw.split(",") if a.strip()]
            teammates.append({"name": name, "aliases": aliases})
        self.parent.config["teammates"] = teammates
        self.parent.save_data()
        self.parent.update_status("⚙️ Settings saved!", "#3498DB")
        self.destroy()


# ── LIFETIME STATS WINDOW ─────────────────────────────────────────────────────

class LifetimeWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Lifetime Stats")
        self.geometry("400x480")
        self.attributes("-topmost", True)
        self.resizable(False, False)
        self.parent = parent

        self.tab_view = ctk.CTkTabview(self, width=380, height=440)
        self.tab_view.pack(padx=10, pady=10, fill="both", expand=True)
        self._build_tabs()

    def _build_tabs(self):
        lifetime   = self.parent.lifetime_stats
        teammates  = self.parent.config.get("teammates",[])

        # Me tab
        self._make_text_tab("Me", lifetime.get("_me", blank_entity_stats()))

        # Per-teammate tabs
        for tm in teammates:
            name = tm["name"]
            key  = f"_player_{name.lower()}"
            self._make_text_tab(name, lifetime.get(key, blank_entity_stats()))

        # Duos & Trios tab
        pair_keys =[k for k in lifetime if k.startswith("_with_")]
        if pair_keys:
            duo_tab = self.tab_view.add("Duos & Trios")
            box = ctk.CTkTextbox(duo_tab, width=355, height=390, font=("Courier", 11))
            box.pack(padx=5, pady=5)
            text = ""
            for k in sorted(pair_keys):
                label = k.replace("_with_", "With ").replace("_", " & ").title()
                text += format_stat_block(lifetime[k], label) + "\n\n"
            box.insert("0.0", text.strip() if text.strip() else "No duo/trio data yet.")
            box.configure(state="disabled")

    def _make_text_tab(self, label, node):
        tab = self.tab_view.add(label)
        box = ctk.CTkTextbox(tab, width=355, height=390, font=("Courier", 11))
        box.pack(padx=5, pady=5)
        box.insert("0.0", format_stat_block(node, label))
        box.configure(state="disabled")


# ── MAIN TRACKER ──────────────────────────────────────────────────────────────

class TrackerGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("RL Tracker")
        self.geometry("300x340")
        self.attributes("-topmost", True)
        self.resizable(False, False)

        self.is_expanded  = False
        self.is_unranked  = False
        self.config       = {"primary_player": "", "teammates":[]}
        self.lifetime_stats = {}

        self.session_ranked   = blank_session()
        self.session_unranked = blank_session()

        self.load_data()

        # In-game state
        self.current_match_guid     = ""
        self.counted_match_guid     = ""
        self.current_arena          = "Unknown"
        self.my_team_num            = None
        self.match_result_committed = False

        self.live_team_scores  = {0: 0, 1: 0}
        self.live_player_goals = {}
        self.live_timeline     =[]
        self.live_match_stats  = {}

        self.build_minimal_ui()
        self.build_expanded_ui()
        self.update_gui_stats()

        if not self.config.get("primary_player"):
            self.after(500, self.prompt_first_login)

        self.listener_thread = threading.Thread(target=self.listen_for_data, daemon=True)
        self.listener_thread.start()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # ── SESSION PROPERTY ─────────────────────────────────────────────────────

    @property
    def session(self):
        return self.session_unranked if self.is_unranked else self.session_ranked

    # ── UI CONSTRUCTION ──────────────────────────────────────────────────────

    def build_minimal_ui(self):
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(pady=(10, 0), fill="x", padx=10)

        self.current_mode = ctk.StringVar(value="2v2")
        self.mode_menu = ctk.CTkOptionMenu(
            top, variable=self.current_mode,
            values=["1v1", "2v2", "3v3", "Rumble", "Hoops", "Dropshot", "Snowday"],
            command=self.on_dropdown_change, width=90)
        self.mode_menu.pack(side="left", padx=(0, 2))

        self.ranked_toggle_btn = ctk.CTkButton(
            top, text="RANKED", width=72, height=28,
            fg_color="#1A6FA8", hover_color="#155d8e",
            command=self.toggle_ranked)
        self.ranked_toggle_btn.pack(side="left", padx=2)

        ctk.CTkButton(top, text="📊", width=32, height=28,
                      fg_color="#6C3483", hover_color="#5B2C6F",
                      command=self.open_lifetime).pack(side="left", padx=2)

        ctk.CTkButton(top, text="⚙️", width=32, height=28,
                      fg_color="gray", command=self.open_settings).pack(side="right")

        # W / L columns
        stats_frame = ctk.CTkFrame(self, fg_color="transparent")
        stats_frame.pack(pady=(10, 0))

        win_col = ctk.CTkFrame(stats_frame, fg_color="transparent")
        win_col.grid(row=0, column=0, padx=18)
        self.win_label = ctk.CTkLabel(
            win_col, text="0", font=("Arial", 50, "bold"), text_color="#2ECC71")
        self.win_label.pack()
        ctk.CTkLabel(win_col, text="SESSION W", font=("Arial", 11, "bold")).pack()
        wbtn = ctk.CTkFrame(win_col, fg_color="transparent")
        wbtn.pack(pady=(2, 0))
        ctk.CTkButton(wbtn, text="+", width=30, height=20, font=("Arial", 12, "bold"),
                      fg_color="#1E8449", hover_color="#196F3D",
                      command=lambda: self.manual_correct("wins", +1)).pack(side="left", padx=2)
        ctk.CTkButton(wbtn, text="−", width=30, height=20, font=("Arial", 12, "bold"),
                      fg_color="#515A5A", hover_color="#3D4244",
                      command=lambda: self.manual_correct("wins", -1)).pack(side="left", padx=2)

        loss_col = ctk.CTkFrame(stats_frame, fg_color="transparent")
        loss_col.grid(row=0, column=1, padx=18)
        self.loss_label = ctk.CTkLabel(
            loss_col, text="0", font=("Arial", 50, "bold"), text_color="#E74C3C")
        self.loss_label.pack()
        ctk.CTkLabel(loss_col, text="SESSION L", font=("Arial", 11, "bold")).pack()
        lbtn = ctk.CTkFrame(loss_col, fg_color="transparent")
        lbtn.pack(pady=(2, 0))
        ctk.CTkButton(lbtn, text="+", width=30, height=20, font=("Arial", 12, "bold"),
                      fg_color="#922B21", hover_color="#7B241C",
                      command=lambda: self.manual_correct("losses", +1)).pack(side="left", padx=2)
        ctk.CTkButton(lbtn, text="−", width=30, height=20, font=("Arial", 12, "bold"),
                      fg_color="#515A5A", hover_color="#3D4244",
                      command=lambda: self.manual_correct("losses", -1)).pack(side="left", padx=2)

        self.mode_context_label = ctk.CTkLabel(
            self, text="RANKED SESSION", font=("Arial", 10, "bold"), text_color="#1A6FA8")
        self.mode_context_label.pack(pady=(4, 0))

        self.session_info_label = ctk.CTkLabel(
            self, text="Win Rate: 0% | Streak: -", font=("Arial", 12))
        self.session_info_label.pack(pady=(4, 4))

        self.reset_btn = ctk.CTkButton(
            self, text="🔄 Reset Session", width=140, height=24,
            fg_color="#D35400", hover_color="#A04000", command=self.reset_session)
        self.reset_btn.pack(pady=(0, 6))

        self.status_label = ctk.CTkLabel(
            self, text="Waiting for Rocket League...",
            font=("Arial", 11, "italic"), text_color="gray")
        self.status_label.pack(pady=(0, 4))

        self.expand_btn = ctk.CTkButton(
            self, text="▼ Show Telemetry", width=200, height=24,
            fg_color="transparent", border_width=1, command=self.toggle_expand)
        self.expand_btn.pack(pady=0)

    def build_expanded_ui(self):
        self.advanced_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.advanced_stats_box = ctk.CTkTextbox(
            self.advanced_frame, width=280, height=280, font=("Courier", 11))
        self.advanced_stats_box.pack(pady=(5, 10))
        self.advanced_stats_box.insert("0.0", "Advanced stats will appear here...")
        self.advanced_stats_box.configure(state="disabled")

    # ── DATA MANAGEMENT ──────────────────────────────────────────────────────

    def load_data(self):
        if os.path.exists(SAVE_FILE):
            with open(SAVE_FILE, "r") as f:
                try:
                    data = json.load(f)
                    self.config         = data.get("config", self.config)
                    self.lifetime_stats = data.get("lifetime_stats", {})
                except json.JSONDecodeError:
                    pass

    def save_data(self):
        with open(SAVE_FILE, "w") as f:
            json.dump({"config": self.config,
                       "lifetime_stats": self.lifetime_stats}, f, indent=4)

    def on_close(self):
        self.destroy()

    # ── TEAMMATE RESOLUTION ──────────────────────────────────────────────────

    def resolve_tracked_player(self, ingame_name):
        """
        Returns (canonical_name, is_primary).
        Checks primary player first, then all teammates + their aliases.
        """
        lower   = ingame_name.lower()
        primary = self.config.get("primary_player", "")
        if primary and primary.lower() in lower:
            return primary, True

        for tm in self.config.get("teammates",[]):
            all_names = [tm["name"]] + tm.get("aliases",[])
            if any(n.lower() in lower for n in all_names):
                return tm["name"], False

        return None, False

    def get_present_teammates(self):
        """Canonical teammate names detected in the current match."""
        present =[]
        for ingame_name in self.live_match_stats:
            canon, is_primary = self.resolve_tracked_player(ingame_name)
            if canon and not is_primary:
                present.append(canon)
        return present

    # ── GUI LOGIC ────────────────────────────────────────────────────────────

    def prompt_first_login(self):
        dialog = ctk.CTkInputDialog(
            text="Welcome! What is your Rocket League name?", title="First Time Setup")
        name = dialog.get_input()
        if name:
            self.config["primary_player"] = name.strip()
            self.save_data()
            self.update_status(f"👋 Logged in as {self.config['primary_player']}", "#2ECC71")

    def open_settings(self):
        SettingsWindow(self)

    def open_lifetime(self):
        LifetimeWindow(self)

    def toggle_ranked(self):
        self.is_unranked = not self.is_unranked
        if self.is_unranked:
            self.ranked_toggle_btn.configure(
                text="UNRANKED", fg_color="#8E44AD", hover_color="#7D3C98")
            self.mode_context_label.configure(text="UNRANKED SESSION", text_color="#8E44AD")
        else:
            self.ranked_toggle_btn.configure(
                text="RANKED", fg_color="#1A6FA8", hover_color="#155d8e")
            self.mode_context_label.configure(text="RANKED SESSION", text_color="#1A6FA8")
        self.update_gui_stats()

    def manual_correct(self, field, delta):
        self.session[field] = max(0, self.session.get(field, 0) + delta)
        self.update_gui_stats()
        self.update_status(f"✏️ {field.capitalize()} manually adjusted.", "#E67E22")

    def reset_session(self):
        if self.is_unranked:
            self.session_unranked = blank_session()
        else:
            self.session_ranked = blank_session()
        self.update_gui_stats()
        label = "Unranked" if self.is_unranked else "Ranked"
        self.update_status(f"🔄 {label} session reset. Good luck!", "#3498DB")

    def toggle_expand(self):
        if self.is_expanded:
            self.geometry("300x340")
            self.advanced_frame.pack_forget()
            self.expand_btn.configure(text="▼ Show Telemetry")
        else:
            self.geometry("300x650")
            self.advanced_frame.pack(fill="both", expand=True, padx=10, pady=5)
            self.expand_btn.configure(text="▲ Hide Telemetry")
        self.is_expanded = not self.is_expanded
        self.update_gui_stats()

    def on_dropdown_change(self, _):
        self.update_gui_stats()

    def update_status(self, text, color="gray"):
        self.status_label.configure(text=text, text_color=color)

    def update_gui_stats(self):
        sw     = self.session.get("wins", 0)
        sl     = self.session.get("losses", 0)
        streak = self.session.get("streak", 0)

        self.win_label.configure(text=str(sw))
        self.loss_label.configure(text=str(sl))

        total    = sw + sl
        win_rate = int(sw / total * 100) if total > 0 else 0
        streak_text = (f"🔥 {streak}W" if streak > 0
                       else f"🧊 {abs(streak)}L" if streak < 0 else "-")
        self.session_info_label.configure(
            text=f"Win Rate: {win_rate}% | Streak: {streak_text}")
            
        # Push to OBS files
        self.update_obs_files()

        if not self.is_expanded:
            return

        diff     = self.session.get("goal_diff", 0)
        diff_str = f"+{diff}" if diff > 0 else str(diff)
        history  = self.session.get("match_history",[])
        ot_count = sum(1 for m in history if m.get("went_to_ot"))
        mc       = len(history)
        cb_count = self._count_comebacks(history)

        mode_label = "UNRANKED" if self.is_unranked else "RANKED"
        text = f"--- {mode_label} SESSION (Diff: {diff_str}) ---\n"
        if mc > 0:
            text += f"OT Rate   : {ot_count}/{mc} matches\n"
        if cb_count > 0:
            text += f"Comebacks : {cb_count} (came back from 3+)\n"

        text += "\n--- PLAYER STATS ---\n"
        players = self.session.get("players", {})
        if not players:
            text += "No telemetry data yet.\n"
        else:
            for name, p in players.items():
                g    = p.get("goals", 0)
                a    = p.get("assists", 0)
                s    = p.get("saves", 0)
                sh   = p.get("shots", 0)
                samp = p.get("samples", 0)
                acc  = f"{int(g/sh*100)}%"  if sh   > 0 else "N/A"
                ar   = f"{int(a/g*100)}%"   if g    > 0 else "N/A"
                spd  = int(p.get("speed_sum", 0) / samp)           if samp > 0 else 0
                bst  = int(p.get("boost_sum", 0) / samp)           if samp > 0 else 0
                ss   = int(p.get("supersonic_frames", 0)/samp*100) if samp > 0 else 0
                text += (f"\n[{name}]\n"
                         f"  G:{g}  A:{a}  Sv:{s}  Shots:{sh}\n"
                         f"  Shot Acc : {acc}  |  Assist Rate: {ar}\n"
                         f"  Avg Speed: {spd}  |  Avg Boost: {bst}\n"
                         f"  Supersonic: {ss}% of match\n")

        if history:
            lm     = history[-1]
            res    = lm["result"].upper()
            ot_tag = " (OT)" if lm.get("went_to_ot") else ""
            text  += f"\n--- LAST MATCH: {res} {lm['score_us']}-{lm['score_them']}{ot_tag} ---\n"
            if not lm["timeline"]:
                text += "  No goals scored.\n"
            else:
                for ev in lm["timeline"]:
                    t   = ev["time_seconds"]
                    ot  = " OT" if ev["is_overtime"] else ""
                    ts  = f"{t // 60}:{t % 60:02d}{ot}"
                    ico = "🔵" if ev["team"] == "us" else "🔴"
                    text += f"  [{ts}] {ico} {ev['scorer']}\n"

        self.advanced_stats_box.configure(state="normal")
        self.advanced_stats_box.delete("0.0", "end")
        self.advanced_stats_box.insert("0.0", text.strip())
        self.advanced_stats_box.configure(state="disabled")

    def update_obs_files(self):
        """Writes current session stats to text files for OBS to read."""
        obs_dir = os.path.join(SAVE_DIR, 'obs_outputs')
        os.makedirs(obs_dir, exist_ok=True)
        
        sw = self.session.get("wins", 0)
        sl = self.session.get("losses", 0)
        streak = self.session.get("streak", 0)
        diff = self.session.get("goal_diff", 0)
        
        streak_text = f"{streak}W" if streak > 0 else f"{abs(streak)}L" if streak < 0 else "-"
        diff_text = f"+{diff}" if diff > 0 else str(diff)
        
        try:
            # Write individual files so streamers can place them anywhere
            with open(os.path.join(obs_dir, "wins.txt"), "w") as f: f.write(str(sw))
            with open(os.path.join(obs_dir, "losses.txt"), "w") as f: f.write(str(sl))
            with open(os.path.join(obs_dir, "streak.txt"), "w") as f: f.write(streak_text)
            with open(os.path.join(obs_dir, "diff.txt"), "w") as f: f.write(diff_text)
            
            # Write a combined file if they just want one line
            with open(os.path.join(obs_dir, "combined.txt"), "w") as f: 
                f.write(f"W: {sw} | L: {sl} | Streak: {streak_text}")
        except Exception:
            pass # Fails silently if OS prevents write access temporarily

    def _count_comebacks(self, history):
        count = 0
        for match in history:
            if match.get("result") != "win":
                continue
            us = them = 0
            for ev in match.get("timeline", []):
                if ev["team"] == "us": us += 1
                else: them += 1
                if (them - us) >= 3:
                    count += 1
                    break
        return count

    # ── MATCH LOGIC ──────────────────────────────────────────────────────────

    def commit_match_stats(self, result):
        mode       = self.current_mode.get()
        score_us   = self.live_team_scores.get(self.my_team_num, 0)
        score_them = self.live_team_scores.get(1 if self.my_team_num == 0 else 0, 0)
        match_diff = abs(score_us - score_them)
        arena      = self.current_arena

        # ── Session update ──
        self.session.setdefault("maps", {}).setdefault(
            arena, {"wins": 0, "losses": 0})
        if result == "win":
            self.session["wins"]      += 1
            self.session["goal_diff"] += match_diff
            self.session["maps"][arena]["wins"] += 1
            if self.session["streak"] < 0: self.session["streak"] = 0
            self.session["streak"] += 1
            tag = " [U]" if self.is_unranked else ""
            self.after(0, lambda: self.update_status(
                f"🎉 {mode}{tag} Win! (+{match_diff})", "#2ECC71"))
        else:
            self.session["losses"]    += 1
            self.session["goal_diff"] -= match_diff
            self.session["maps"][arena]["losses"] += 1
            if self.session["streak"] > 0: self.session["streak"] = 0
            self.session["streak"] -= 1
            tag = " [U]" if self.is_unranked else ""
            self.after(0, lambda: self.update_status(
                f"💀 {mode}{tag} Loss! (-{match_diff})", "#E74C3C"))

        # ── Match history ──
        went_to_ot = any(ev.get("is_overtime") for ev in self.live_timeline)
        self.session.setdefault("match_history",[]).append({
            "guid": self.counted_match_guid, "arena": arena,
            "result": result, "score_us": score_us, "score_them": score_them,
            "went_to_ot": went_to_ot, "timeline": self.live_timeline
        })

        # ── Session telemetry per player ──
        for player_name, ms in self.live_match_stats.items():
            self.session["players"].setdefault(player_name, {
                "goals": 0, "assists": 0, "saves": 0, "shots": 0, "demos": 0,
                "speed_sum": 0, "boost_sum": 0, "supersonic_frames": 0, "samples": 0
            })
            node = self.session["players"][player_name]
            for k in["goals", "assists", "saves", "shots", "demos",
                      "speed_sum", "boost_sum", "supersonic_frames", "samples"]:
                node[k] += ms.get(k, 0)

        # ── Lifetime stats (ranked only) ──
        if not self.is_unranked:
            present_teammates = self.get_present_teammates()

            # Collect my stats from live_match_stats
            my_stats = {}
            for ingame_name, ms in self.live_match_stats.items():
                _, is_primary = self.resolve_tracked_player(ingame_name)
                if is_primary:
                    my_stats = dict(ms)
                    break

            # _me node
            commit_entity(self.lifetime_stats, "_me", mode, result, my_stats)

            # Per-teammate nodes
            for tm_name in present_teammates:
                tm_key   = f"_player_{tm_name.lower()}"
                tm_stats = {}
                for ingame_name, ms in self.live_match_stats.items():
                    canon, _ = self.resolve_tracked_player(ingame_name)
                    if canon == tm_name:
                        tm_stats = dict(ms)
                        break
                commit_entity(self.lifetime_stats, tm_key, mode, result, tm_stats)

            # Duo / trio group nodes (W/L record only)
            for size in range(1, len(present_teammates) + 1):
                for combo in combinations(sorted(present_teammates), size):
                    group_key = "_with_" + "_".join(n.lower() for n in combo)
                    commit_entity(self.lifetime_stats, group_key, mode, result, {})

            self.save_data()

        self.live_match_stats = {}
        self.after(0, self.update_gui_stats)

    def process_match_data(self, payload):
        event = payload.get("Event")

        # ── MatchDestroyed: fallback trigger ──
        if event == "MatchDestroyed":
            raw = payload.get("Data", {})
            if isinstance(raw, str):
                try: raw = json.loads(raw)
                except: return
            match_guid = raw.get("MatchGuid", "")
            if match_guid and match_guid == self.counted_match_guid:
                return  # Already handled by bHasWinner
            if self.my_team_num is not None:
                self.counted_match_guid = match_guid
                su = self.live_team_scores.get(self.my_team_num, 0)
                st = self.live_team_scores.get(1 if self.my_team_num == 0 else 0, 0)
                if   su > st: self.commit_match_stats("win")
                elif st > su: self.commit_match_stats("loss")
                else: self.after(0, self.update_status, "🤝 Match Tied/Aborted!", "gray")
            else:
                self.after(0, self.update_status,
                           "⚠️ Match ended (player not found)", "#E67E22")
            return

        if event != "UpdateState": return

        raw = payload.get("Data", "{}")
        if isinstance(raw, str):
            try: data = json.loads(raw)
            except: return
        else: data = raw

        players    = data.get("Players",[])
        game       = data.get("Game", {})
        match_guid = data.get("MatchGuid", "")

        # ── New match ──
        if match_guid and match_guid != self.current_match_guid:
            self.current_match_guid     = match_guid
            self.current_arena          = game.get("Arena", "Unknown")
            self.my_team_num            = None
            self.live_team_scores       = {0: 0, 1: 0}
            self.live_player_goals      = {}
            self.live_timeline          =[]
            self.live_match_stats       = {}
            self.match_result_committed = False

        # ── Find my team ──
        if self.my_team_num is None:
            primary = self.config.get("primary_player", "").lower()
            if primary:
                for p in players:
                    if primary in p.get("Name", "").lower():
                        self.my_team_num = p.get("TeamNum")
                        self.after(0, self.update_status,
                                   "👀 Tracking match...", "#3498DB")
                        break

        if self.my_team_num is None: return

        # ── Goal scorer detection ──
        scorer_name = "Unknown"
        for p in players:
            pname  = p.get("Name", "Unknown")
            pgoals = p.get("Goals", 0)
            if pgoals > self.live_player_goals.get(pname, 0):
                scorer_name = pname
            self.live_player_goals[pname] = pgoals

        # ── Timeline ──
        for team in game.get("Teams",[]):
            t_num   = team.get("TeamNum")
            t_score = team.get("Score", 0)
            if t_score > self.live_team_scores.get(t_num, 0):
                label = "us" if t_num == self.my_team_num else "them"
                self.live_timeline.append({
                    "time_seconds": game.get("TimeSeconds", 0),
                    "is_overtime":  game.get("bOvertime", False),
                    "team": label, "scorer": scorer_name
                })
            self.live_team_scores[t_num] = t_score

        # ── Telemetry sampling ──
        for p in players:
            canon, _ = self.resolve_tracked_player(p.get("Name", ""))
            if canon:
                self.live_match_stats.setdefault(canon, {
                    "goals": 0, "assists": 0, "saves": 0, "shots": 0, "demos": 0,
                    "speed_sum": 0, "boost_sum": 0, "supersonic_frames": 0, "samples": 0
                })
                ps = self.live_match_stats[canon]
                ps["goals"]   = p.get("Goals",   ps["goals"])
                ps["assists"] = p.get("Assists",  ps["assists"])
                ps["saves"]   = p.get("Saves",    ps["saves"])
                ps["shots"]   = p.get("Shots",    ps["shots"])
                ps["demos"]   = p.get("Demos",    ps["demos"])
                spd = p.get("Speed", 0)
                if spd > 0:
                    ps["speed_sum"]         += spd
                    ps["boost_sum"]         += p.get("Boost", 0)
                    ps["supersonic_frames"] += int(p.get("bSupersonic", False))
                    ps["samples"]           += 1

        # ── bHasWinner: primary commit trigger ──
        if game.get("bHasWinner") and not self.match_result_committed:
            self.match_result_committed = True
            self.counted_match_guid     = self.current_match_guid
            su = self.live_team_scores.get(self.my_team_num, 0)
            st = self.live_team_scores.get(1 if self.my_team_num == 0 else 0, 0)
            if su > st:
                threading.Thread(
                    target=self.commit_match_stats, args=("win",),  daemon=True).start()
            elif st > su:
                threading.Thread(
                    target=self.commit_match_stats, args=("loss",), daemon=True).start()

    # ── SOCKET LISTENER ──────────────────────────────────────────────────────

    def listen_for_data(self):
        import time
        decoder = json.JSONDecoder()
        while True:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect((HOST, PORT))
                    self.after(0, self.update_status,
                               "✅ Connected. Waiting for match...", "#2ECC71")
                    buffer = ""
                    while True:
                        chunk = s.recv(4096).decode('utf-8', errors='ignore')
                        if not chunk: break
                        buffer += chunk.replace('\x00', '')
                        while buffer:
                            buffer = buffer.lstrip()
                            if not buffer: break
                            try:
                                obj, idx = decoder.raw_decode(buffer)
                                self.process_match_data(obj)
                                buffer = buffer[idx:]
                            except json.JSONDecodeError:
                                break
            except ConnectionRefusedError:
                self.after(0, self.update_status,
                           "🔄 Waiting for Rocket League...", "gray")
                time.sleep(3)
            except Exception:
                # Silently catch regular disconnects without throwing scary UI text
                self.after(0, self.update_status, 
                           "🔄 Connection lost. Waiting for Rocket League...", "gray")
                time.sleep(3)


if __name__ == "__main__":
    app = TrackerGUI()
    app.mainloop()

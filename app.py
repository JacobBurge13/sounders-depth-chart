"""
Seattle Sounders Depth Chart Dashboard
Shiny for Python app - embeddable via Shinylive
"""

import json
import io
import base64
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
import matplotlib.patches as mpatches
from matplotlib.path import Path as MplPath
from scipy.stats import gaussian_kde

try:
    from mplsoccer import football_shirt_marker
    HAS_MPLSOCCER = True
except ImportError:
    HAS_MPLSOCCER = False

from shiny import App, reactive, render, ui

# ============================================================
# CONFIGURATION - EDIT THIS SECTION
# ============================================================

# Color scheme - Black with green/white accents
BG_COLOR = "#0a0a0a"           # Main background - black
CARD_BG = "#111111"            # Card background - dark gray
PITCH_COLOR = "#0a0a0a"        # Pitch background - black
LINE_COLOR = "#444444"         # Pitch lines - gray for visibility on black
ACCENT_GREEN = "#96D35F"       # Rave Green (lighter for visibility)
ACCENT_WHITE = "#ffffff"       # White
TEXT_COLOR = "#ffffff"         # Main text
SUBTEXT_COLOR = "#888888"      # Secondary text
JERSEY_GREEN = "#5D9741"       # Jersey color - Rave Green
DEFIANCE_BLUE = "#5BC0EB"      # Defiance light blue

# Pitch dimensions (120 x 80 yards, scaled)
PITCH_LENGTH = 120
PITCH_WIDTH = 80

# Formation to use
FORMATION = "4231"

# Roster designation labels
ROSTER_DESIGNATIONS = {
    "DP": "Designated Player",
    "TAM": "Targeted Allocation",
    "U22": "U22 Initiative",
    "HG": "Homegrown",
    "INT": "International",
    "SEN": "Senior Roster",
    "SUP": "Supplemental",
    "LOAN": "On Loan",
    "DEF": "Defiance",
    "SEI": "Season Ending Injury",
}

# ============================================================
# DEPTH CHART - MANUALLY ASSIGN PLAYERS TO POSITIONS
# ============================================================

DEPTH_CHART = {
    "GK": [
        {"name": "Stefan Frei", "designation": "SEN", "photo": "https://images.mlssoccer.com/image/private/t_thumb_squared/f_png/mls/ohm7sxqzwo5lzzjfwza9.png","international": False, "supplemental": False, "off_roster": False, "unavailable": False, "on_loan": False},
        {"name": "Andrew Thomas", "designation": "SEN", "photo": "https://images.mlssoccer.com/image/private/t_thumb_squared/f_png/mls/v7ywfzz0yxjx5xfnqyhs.png", "international": False, "supplemental": False, "off_roster": False, "unavailable": False, "on_loan": False},
        {"name": "Jacob Castro", "designation": "HG", "photo": "https://images.mlssoccer.com/image/private/t_thumb_squared/f_png/mls/player-placeholder.png", "international": False, "supplemental": True, "off_roster": False, "unavailable": False, "on_loan": False},
    ],
    "RB": [
        {"name": "Alex Roldan", "designation": "TAM", "photo": "https://images.mlssoccer.com/image/private/t_thumb_squared/f_png/mls/nqxcyv4xbn6dmzocubu6.png","international": False, "supplemental": False, "off_roster": False, "unavailable": False, "on_loan": False},
        {"name": "Kalani Kossa-Rienzi", "designation": "SUP", "photo": "https://images.mlssoccer.com/image/private/t_thumb_squared/f_png/mls/player-placeholder.png","international": False, "supplemental": True, "off_roster": False, "unavailable": False, "on_loan": False},
        {"name": "Cody Baker", "designation": "HG", "photo": "https://images.mlssoccer.com/image/private/t_thumb_squared/f_png/mls/player-placeholder.png", "international": False, "supplemental": True, "off_roster": False, "unavailable": True, "on_loan": True},
    ],
    "CB": [
        {"name": "Yeimar Gómez", "designation": "TAM", "photo": "https://images.mlssoccer.com/image/private/t_thumb_squared/f_png/mls/nv1n00o9nqj3b8xp3d7x.png","international": False, "supplemental": False, "off_roster": False, "unavailable": False, "on_loan": False},
        {"name": "Kim Kee-Hee", "designation": "SUP", "photo": "https://images.mlssoccer.com/image/private/t_thumb_squared/f_png/mls/uh4ypwn6ffjzzmkqjgaz.png", "international": True,"supplemental": False, "off_roster": False, "unavailable": False, "on_loan": False},
        {"name": "Leo Burney", "designation": "HG", "photo": "https://images.mlssoccer.com/image/private/t_thumb_squared/f_png/mls/player-placeholder.png", "international": False,"supplemental": True, "off_roster": True, "unavailable": True, "on_loan": True},

    ],
    "CB2": [
        {"name": "Jackson Ragen", "designation": "SEN", "photo": "https://images.mlssoccer.com/image/private/t_thumb_squared/f_png/mls/lzqqe2bqomxhz3khsjdx.png", "international": False, "supplemental": False, "off_roster": False, "unavailable": False, "on_loan": False},
        {"name": "Jon Bell", "designation": "SEN", "photo": "https://images.mlssoccer.com/image/private/t_thumb_squared/f_png/mls/aeqgzncldvjzgtxlm8xz.png", "international": False, "supplemental": False,"off_roster": False, "unavailable": False, "on_loan": False},
        {"name": "Stuart Hawkins", "designation": "HG", "photo": "https://images.mlssoccer.com/image/private/t_thumb_squared/f_png/mls/player-placeholder.png", "international": False, "supplemental": True, "off_roster": False, "unavailable": False, "on_loan": False},
    ],
    "LB": [
        {"name": "Nouhou Tolo", "designation": "SEN", "photo": "https://images.mlssoccer.com/image/private/t_thumb_squared/f_png/mls/jyjpg9vb3kzmixbcryjq.png", "international": False, "supplemental": False, "off_roster": False, "unavailable": False, "on_loan": False},
        {"name": "Reed Baker-Whiting", "designation": "U22", "photo": "https://images.mlssoccer.com/image/private/t_thumb_squared/f_png/mls/qvdqsyv9bv2gu3hjvnjq.png", "international":False, "supplemental": True, "off_roster": False, "unavailable": False, "on_loan": False},
        {"name": "Tomas Sousa", "designation": "SEN", "photo": "https://images.mlssoccer.com/image/private/t_thumb_squared/f_png/mls/player-placeholder.png", "international": False, "supplemental": True, "off_roster": False, "unavailable": True, "on_loan": True},
        {"name": "Paul Arriola", "designation": "SEI", "photo": "https://images.mlssoccer.com/image/private/t_thumb_squared/f_png/mls/player-placeholder.png","international": False, "supplemental": False, "off_roster": False, "unavailable": False, "on_loan": False},
    ],
    "CDM": [
        {"name": "Obed Vargas", "designation": "HG", "photo": "https://images.mlssoccer.com/image/private/t_thumb_squared/f_png/mls/taa9y0fcr9qr0kmjkfob.png","international": False, "supplemental": True, "off_roster": False, "unavailable": False, "on_loan": False},
        {"name": "Snyder Brunell", "designation": "HG", "photo": "https://images.mlssoccer.com/image/private/t_thumb_squared/f_png/mls/player-placeholder.png", "international": False, "supplemental": True, "off_roster": False, "unavailable": False, "on_loan": False},

    ],
    "CDM2": [
        {"name": "Cristian Roldan", "designation": "TAM", "photo": "https://images.mlssoccer.com/image/private/t_thumb_squared/f_png/mls/m5qdkkjckwl4nmkdznmr.png", "international": False, "supplemental": False, "off_roster": False, "unavailable": False, "on_loan": False},
        {"name": "João Paulo", "designation": "SEN", "photo": "https://images.mlssoccer.com/image/private/t_thumb_squared/f_png/mls/jxmb4clwkxqxyxjlwpkk.png", "international": False, "supplemental": False, "off_roster": False, "unavailable": False, "on_loan": False},
    ],
    "RAM": [
        {"name": "Jesús Ferreira", "designation": "TAM", "photo": "https://images.mlssoccer.com/image/private/t_thumb_squared/f_png/mls/obqzpexcfgf35uvzv2nr.png", "international": False, "supplemental": False, "off_roster": False, "unavailable": False, "on_loan": False},
        {"name": "Georgi Minoungou", "designation": "SEN", "photo": "https://images.mlssoccer.com/image/private/t_thumb_squared/f_png/mls/player-placeholder.png", "international": True, "supplemental": True, "off_roster": False, "unavailable": False, "on_loan": False},
    ],
    "CAM": [
        {"name": "Albert Rusnák", "designation": "DP", "photo": "https://images.mlssoccer.com/image/private/t_thumb_squared/f_png/mls/dvkfxhjyurvbh3xbfwqe.png", "international": False, "supplemental": False, "off_roster": False, "unavailable": False, "on_loan": False},
        {"name": "Danny Leyva", "designation": "SEN", "photo": "https://images.mlssoccer.com/image/private/t_thumb_squared/f_png/mls/i8llg4w0fqrshzqz0zhk.png", "international": False, "supplemental": False, "off_roster": False, "unavailable": False, "on_loan": False},
    ],
    "LAM": [
        {"name": "Paul Rothrock", "designation": "SUP", "photo": "https://images.mlssoccer.com/image/private/t_thumb_squared/f_png/mls/ckwworz7vczyepsrl6ow.png", "international": False, "supplemental": True, "off_roster": False, "unavailable": False, "on_loan": False},
        {"name": "Pedro de la Vega", "designation": "DP", "photo": "https://images.mlssoccer.com/image/private/t_thumb_squared/f_png/mls/xwfkzwzxpq8jxdhqhjqq.png", "international": True, "supplemental": False, "off_roster": False, "unavailable": False, "on_loan": False},
        {"name": "Ryan Kent", "designation": "TAM", "photo": "https://images.mlssoccer.com/image/private/t_thumb_squared/f_png/mls/player-placeholder.png", "international": True, "supplemental": False, "off_roster": False, "unavailable": False, "on_loan": False},
    ],
    "ST": [
        {"name": "Jordan Morris", "designation": "DP", "photo": "https://images.mlssoccer.com/image/private/t_thumb_squared/f_png/mls/gdhhtbzmgmxrgq1nqjql.png", "international": False, "supplemental": False, "off_roster": False, "unavailable": False, "on_loan": False},
        {"name": "Danny Musovski", "designation": "SEN", "photo": "https://images.mlssoccer.com/image/private/t_thumb_squared/f_png/mls/qfhqr8jq1ycqz5xyhzqj.png", "international": False, "supplemental": False, "off_roster": False, "unavailable": False, "on_loan": False},
        {"name": "Osaze De Rosario", "designation": "SUP", "photo": "https://images.mlssoccer.com/image/private/t_thumb_squared/f_png/mls/rqjv5p4mzchm8x9qhkqz.png", "international": False, "supplemental": True, "off_roster": False, "unavailable": False, "on_loan": False},
    ],
}

# Position order for 4-2-3-1 (First Team)
POSITION_ORDER = ["GK", "RB", "CB", "CB2", "LB", "CDM", "CDM2", "RAM", "CAM", "LAM", "ST"]

# Position coordinates on 120x80 pitch (x=width 0-80, y=length 0-120)
# Vertical pitch: y=0 is defending goal, y=120 is attacking goal
POSITION_COORDS = {
    "GK": (40, 10),
    "LB": (10, 30),
    "CB": (28, 30),
    "CB2": (52, 30),
    "RB": (70, 30),
    "CDM": (28, 55),
    "CDM2": (52, 55),
    "LAM": (15, 80),
    "CAM": (40, 80),
    "RAM": (65, 80),
    "ST": (40, 105),
}

# ============================================================
# DEFIANCE DEPTH CHART (MLS NEXT PRO) - 3-4-3 Formation
# ============================================================

DEFIANCE_DEPTH_CHART = {
    "GK": [
        {"name": "M.Shour", "designation": "DEF", "academy": True},
    ],
    "LCB": [
        {"name": "A.Lopez", "designation": "DEF", "academy": True},
    ],
    "CB": [
        {"name": "Kaito", "designation": "DEF", "loanee": True},
        {"name": "Alvarez", "designation": "DEF"},
    ],
    "RCB": [
        {"name": "Katsaros", "designation": "DEF", "academy": True},
    ],
    "LM": [

        {"name": "Diaw", "designation": "DEF"},
    ],
    "LCM": [
        {"name": "Dodzi", "designation": "DEF"},
        {"name": "Robles", "designation": "DEF", "academy": True},

    ],
    "RCM": [
        {"name": "Kingston", "designation": "DEF"},
        {"name": "Baer", "designation": "DEF"},

    ],

    "RM": [
        {"name": "Kang", "designation": "DEF"},
        {"name": "Gaffney", "designation": "DEF", "academy": True},

    ],
    "LW": [
        {"name": "Gomez", "designation": "DEF", "academy": True},
        {"name": "Khoury", "designation": "DEF"},
    ],
    "ST": [
        {"name": "Tsukanome", "designation": "DEF"},
    ],
    "RW": [
        {"name": "Pedder", "designation": "DEF"},
        {"name": "Hassan", "designation": "DEF", "academy": True},


    ],
}

# Injured/On Loan: Tsukanome, Khoury, Pedder, Hassan

DEFIANCE_POSITION_ORDER = ["GK", "LCB", "CB", "RCB", "LM", "LCM", "RCM", "RM", "LW", "ST", "RW"]

# 3-4-3 coordinates
DEFIANCE_POSITION_COORDS = {
    "GK": (40, 10),
    "LCB": (20, 30),
    "CB": (40, 30),
    "RCB": (60, 30),
    "LM": (10, 60),
    "LCM": (30, 55),
    "RCM": (50, 55),
    "RM": (70, 60),
    "LW": (15, 95),
    "ST": (40, 100),
    "RW": (65, 95),
}

# ============================================================
# LOAD DATA
# ============================================================

DATA_DIR = Path(__file__).parent / "data"

with open(DATA_DIR / "players.json") as f:
    PLAYERS_DATA = json.load(f)

with open(DATA_DIR / "events.json") as f:
    EVENTS_DATA = json.load(f)

# Load logo as base64 for header
LOGO_BASE64 = ""
logo_path = DATA_DIR / "logo.png"
if logo_path.exists():
    with open(logo_path, "rb") as f:
        LOGO_BASE64 = base64.b64encode(f.read()).decode('utf-8')

# Load matches data (may not exist yet - run export_data.py to create it)
MATCHES_DATA = []
matches_file = DATA_DIR / "matches.json"
if matches_file.exists():
    with open(matches_file) as f:
        MATCHES_DATA = json.load(f)

PLAYER_LOOKUP = {p["name"]: p for p in PLAYERS_DATA}
MATCH_LOOKUP = {m["match_id"]: m for m in MATCHES_DATA}
# Pre-compute minutes lookup for sorting
MINUTES_LOOKUP = {p["name"]: p.get("mins", 0) or 0 for p in PLAYERS_DATA}

def get_player_matches(player_id):
    """Get list of matches a player appeared in."""
    match_ids = set()
    for e in EVENTS_DATA:
        if e.get("player_id") == player_id and e.get("match_id"):
            match_ids.add(e["match_id"])

    # Get match details and sort by date
    matches = []
    for mid in match_ids:
        if mid in MATCH_LOOKUP:
            matches.append(MATCH_LOOKUP[mid])

    # Sort by date descending
    matches.sort(key=lambda m: m.get("start_date", ""), reverse=True)
    return matches

# ============================================================
# JERSEY MARKER
# ============================================================

def create_jersey_marker():
    """Get the best available jersey marker."""
    if HAS_MPLSOCCER:
        # Use mplsoccer's professional jersey marker
        return football_shirt_marker
    else:
        # Fallback: create a simple jersey shape
        verts = [
            (-0.4, -0.5),   # Bottom left
            (-0.4, 0.1),    # Left side up
            (-0.7, 0.2),    # Left sleeve
            (-0.7, 0.45),   # Left sleeve top
            (-0.4, 0.35),   # Left shoulder
            (-0.2, 0.5),    # Left collar
            (0.0, 0.4),     # Center collar
            (0.2, 0.5),     # Right collar
            (0.4, 0.35),    # Right shoulder
            (0.7, 0.45),    # Right sleeve top
            (0.7, 0.2),     # Right sleeve
            (0.4, 0.1),     # Right side
            (0.4, -0.5),    # Bottom right
            (-0.4, -0.5),   # Close
        ]
        codes = [MplPath.MOVETO] + [MplPath.LINETO] * 12 + [MplPath.CLOSEPOLY]
        return MplPath(verts, codes)

JERSEY_MARKER = create_jersey_marker()

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def sanitize_id(name):
    """Convert player name to valid Shiny ID (letters, numbers, underscore only)."""
    import re
    # Replace spaces and hyphens with underscores
    safe = name.replace(' ', '_').replace('-', '_')
    # Remove any character that isn't alphanumeric or underscore
    safe = re.sub(r'[^a-zA-Z0-9_]', '', safe)
    return safe


def get_player_data(name):
    """Get player data by name, with fuzzy matching."""
    if name in PLAYER_LOOKUP:
        return PLAYER_LOOKUP[name]
    name_lower = name.lower()
    for pname, pdata in PLAYER_LOOKUP.items():
        if name_lower in pname.lower() or pname.lower() in name_lower:
            return pdata
    return None


def get_game_stats(player_id, match_id):
    """Calculate stats for a specific game from events data."""
    events = [e for e in EVENTS_DATA if e.get("player_id") == player_id and str(e.get("match_id")) == str(match_id)]

    if not events:
        return None

    # Count events by type - use is_shot and is_goal flags where available
    passes = [e for e in events if e.get("type_display_name") == "Pass"]
    carries = [e for e in events if e.get("type_display_name") == "Carry"]
    # Use is_shot flag to properly identify shots
    shots = [e for e in events if e.get("is_shot", False)]
    # Use is_goal flag to properly identify goals
    goals = [e for e in events if e.get("is_goal", False)]
    tackles = [e for e in events if e.get("type_display_name") == "Tackle"]
    interceptions = [e for e in events if e.get("type_display_name") == "Interception"]
    clearances = [e for e in events if e.get("type_display_name") == "Clearance"]
    recoveries = [e for e in events if e.get("type_display_name") == "BallRecovery"]
    receptions = [e for e in events if e.get("type_display_name") == "Reception"]

    # Calculate pass-related stats
    successful_passes = [p for p in passes if p.get("outcome_type_display_name") == "Successful"]
    key_passes = [p for p in passes if p.get("is_keypass", False)]
    progressive_passes = [p for p in passes if p.get("is_progressive_pass", False)]
    final_third_passes = [p for p in passes if p.get("is_final_third_pass", False)]
    deep_passes = [p for p in passes if p.get("is_deep_pass", False)]

    # Calculate carry-related stats
    final_third_carries = [c for c in carries if c.get("is_final_third_carry", False)]
    deep_carries = [c for c in carries if c.get("is_deep_carry", False)]
    progressive_carries = [c for c in carries if c.get("is_progressive_carry", False)]

    # Calculate reception-related stats
    final_third_receptions = [r for r in receptions if r.get("x", 0) >= 66.67]
    deep_receptions = [r for r in receptions if r.get("x", 0) >= 83.33]

    # Shots on target: SavedShot and Goal where not blocked
    shots_on_target = [s for s in shots if not s.get("is_blocked", False) and s.get("type_display_name") in ["SavedShot", "Goal"]]

    # Calculate PV sums
    pv_passing = sum(e.get("pv_added", 0) or 0 for e in passes)
    pv_carrying = sum(e.get("pv_added", 0) or 0 for e in carries)
    pv_receiving = sum(e.get("pv_added", 0) or 0 for e in receptions)
    pv_defending = sum(e.get("pv_added", 0) or 0 for e in (tackles + interceptions + clearances + recoveries))
    pv_shooting = sum(e.get("pv_added", 0) or 0 for e in shots)

    return {
        "gp": 1,
        "gs": 1,  # Can't determine from events
        "goals": len(goals),
        "assists": sum(1 for p in passes if p.get("is_assist", False)),
        "total_passes": len(passes),
        "passes": len(successful_passes),
        "key_passes": len(key_passes),
        "progressive_passes": len(progressive_passes),
        "final_third_passes": len(final_third_passes),
        "deep_passes": len(deep_passes),
        "xg_assisted": sum(p.get("xg_assisted", 0) or 0 for p in passes),
        "carries": len(carries),
        "final_third_carries": len(final_third_carries),
        "deep_carries": len(deep_carries),
        "progressive_carries": len(progressive_carries),
        "receptions": len(receptions),
        "final_third_receptions": len(final_third_receptions),
        "deep_receptions": len(deep_receptions),
        "shots": len(shots),
        "shots_on_target": len(shots_on_target),
        "tackles": len(tackles),
        "interceptions": len(interceptions),
        "clearances": len(clearances),
        "ball_recoveries": len(recoveries),
        "defensive_actions": len(tackles) + len(interceptions) + len(clearances) + len(recoveries),
        "pv_total": pv_passing + pv_carrying + pv_receiving + pv_defending + pv_shooting,
        "pv_passing": pv_passing,
        "pv_carrying": pv_carrying,
        "pv_receiving": pv_receiving,
        "pv_defending": pv_defending,
        "pv_shooting": pv_shooting,
        "xg": sum(e.get("xg", 0) or 0 for e in shots),
        "mins": 90,  # Assume 90 for single game stats
    }


def calculate_roster_counts(depth_chart):
    """Calculate roster slot counts from depth chart data."""
    all_players = []
    for pos, players in depth_chart.items():
        all_players.extend(players)

    # Count various roster categories
    total_on_roster = sum(1 for p in all_players if not p.get("off_roster", False))
    senior_roster = sum(1 for p in all_players if not p.get("supplemental", False) and not p.get("off_roster", False))
    supplemental_roster = sum(1 for p in all_players if p.get("supplemental", False) and not p.get("off_roster", False))
    dp_spots = sum(1 for p in all_players if p.get("designation") == "DP")
    u22_count = sum(1 for p in all_players if p.get("designation") == "U22")
    tam_count = sum(1 for p in all_players if p.get("designation") == "TAM")
    international_count = sum(1 for p in all_players if p.get("international", False))
    on_loan_count = sum(1 for p in all_players if p.get("on_loan", False))
    off_roster = sum(1 for p in all_players if p.get("off_roster", False))
    unavailable_count = sum(1 for p in all_players if p.get("unavailable", False))
    sei_count = sum(1 for p in all_players if p.get("designation") == "SEI")

    return {
        "total_on_roster": total_on_roster,
        "total_max": 31,
        "senior_roster": senior_roster,
        "senior_max": 20,
        "supplemental_roster": supplemental_roster,
        "supplemental_max": 11,
        "dp_spots": dp_spots,
        "dp_max": 3,
        "u22_count": u22_count,
        "u22_max": 3,
        "tam_count": tam_count,
        "international_count": international_count,
        "international_max": 4,
        "open_international": max(0, 4 - international_count),
        "on_loan_count": on_loan_count,
        "off_roster": off_roster,
        "unavailable_count": unavailable_count,
        "sei_count": sei_count,
    }


def calculate_percentiles(players_data):
    """Calculate percentile rank for each stat across all teammates."""
    from scipy.stats import percentileofscore

    stat_fields = [
        'goals', 'assists', 'shots', 'shots_on_target', 'passes', 'total_passes',
        'key_passes', 'defensive_actions', 'tackles', 'interceptions', 'clearances',
        'ball_recoveries', 'carries', 'pv_total', 'pv_passing', 'pv_receiving',
        'pv_carrying', 'pv_shooting', 'pv_defending', 'matches', 'mins', 'gp', 'gs',
        'progressive_passes', 'final_third_passes', 'deep_passes', 'xg_assisted',
        'final_third_carries', 'deep_carries', 'progressive_carries',
        'receptions', 'final_third_receptions', 'deep_receptions', 'total_actions',
        'total_xg'
    ]

    # Calculate total_actions for each player before percentile calculation
    for player in players_data:
        player['total_actions'] = (player.get('passes', 0) or 0) + (player.get('carries', 0) or 0) + (player.get('defensive_actions', 0) or 0)

    # Stats that need per 90 percentiles (for Per 90 mode and radar chart)
    per90_stats = [
        'pv_total', 'pv_passing', 'pv_carrying', 'pv_receiving', 'pv_defending', 'pv_shooting',
        'passes', 'total_passes', 'key_passes', 'progressive_passes', 'final_third_passes', 'deep_passes',
        'carries', 'final_third_carries', 'deep_carries', 'progressive_carries',
        'receptions', 'final_third_receptions', 'deep_receptions',
        'shots', 'shots_on_target', 'goals',
        'defensive_actions', 'tackles', 'interceptions', 'clearances', 'ball_recoveries',
        'xg_assisted', 'total_actions', 'total_xg'
    ]

    # Calculate percentiles for each stat
    for stat in stat_fields:
        # Get all non-None values for this stat
        values = [p.get(stat, 0) or 0 for p in players_data]
        if not values or max(values) == 0:
            continue

        for player in players_data:
            val = player.get(stat, 0) or 0
            # Calculate percentile rank (0-100)
            pct = percentileofscore(values, val, kind='rank')
            player[f'{stat}_percentile'] = round(pct)

    # Calculate per 90 percentiles for all relevant stats
    for stat in per90_stats:
        # Calculate per 90 values for all players with enough minutes
        per90_values = []
        for p in players_data:
            mins = p.get('mins', 0) or 0
            val = p.get(stat, 0) or 0
            if mins >= 90:  # Only include players with at least 90 minutes
                per90 = val / (mins / 90)
                per90_values.append((p, per90))
            else:
                per90_values.append((p, 0))

        # Get just the values for percentile calculation
        values_only = [v for _, v in per90_values]
        if not values_only or max(values_only) == 0:
            continue

        for player, per90_val in per90_values:
            pct = percentileofscore(values_only, per90_val, kind='rank')
            player[f'{stat}_per90_percentile'] = round(pct)

    return players_data


def format_percentile(percentile):
    """Format percentile with % symbol."""
    if percentile is None:
        return ""
    p = int(percentile)
    return f"({p}%)"


# Calculate percentiles on startup
PLAYERS_DATA = calculate_percentiles(PLAYERS_DATA)


def create_pitch_figure(figsize=(10, 15)):
    """Create a 120x80 vertical pitch figure."""
    fig, ax = plt.subplots(figsize=figsize, facecolor=PITCH_COLOR)
    ax.set_facecolor(PITCH_COLOR)

    lw = 1.5  # Line width

    # Outer boundary
    ax.plot([0, PITCH_WIDTH, PITCH_WIDTH, 0, 0],
            [0, 0, PITCH_LENGTH, PITCH_LENGTH, 0],
            color=LINE_COLOR, lw=lw)

    # Center line
    ax.plot([0, PITCH_WIDTH], [PITCH_LENGTH/2, PITCH_LENGTH/2], color=LINE_COLOR, lw=lw)

    # Center circle (radius ~10 yards)
    circle = plt.Circle((PITCH_WIDTH/2, PITCH_LENGTH/2), 10, fill=False, color=LINE_COLOR, lw=lw)
    ax.add_patch(circle)
    ax.scatter(PITCH_WIDTH/2, PITCH_LENGTH/2, s=30, color=LINE_COLOR, zorder=3)

    # Penalty areas (18-yard box: 44 yards wide, 18 yards deep)
    box_width = 44
    box_depth = 18
    box_left = (PITCH_WIDTH - box_width) / 2

    # Bottom penalty area (defending)
    ax.plot([box_left, box_left, box_left + box_width, box_left + box_width],
            [0, box_depth, box_depth, 0], color=LINE_COLOR, lw=lw)

    # 6-yard box bottom
    six_width = 20
    six_depth = 6
    six_left = (PITCH_WIDTH - six_width) / 2
    ax.plot([six_left, six_left, six_left + six_width, six_left + six_width],
            [0, six_depth, six_depth, 0], color=LINE_COLOR, lw=lw)

    # Penalty spot bottom
    ax.scatter(PITCH_WIDTH/2, 12, s=30, color=LINE_COLOR, zorder=3)

    # Top penalty area (attacking)
    ax.plot([box_left, box_left, box_left + box_width, box_left + box_width],
            [PITCH_LENGTH, PITCH_LENGTH - box_depth, PITCH_LENGTH - box_depth, PITCH_LENGTH],
            color=LINE_COLOR, lw=lw)

    # 6-yard box top
    ax.plot([six_left, six_left, six_left + six_width, six_left + six_width],
            [PITCH_LENGTH, PITCH_LENGTH - six_depth, PITCH_LENGTH - six_depth, PITCH_LENGTH],
            color=LINE_COLOR, lw=lw)

    # Penalty spot top
    ax.scatter(PITCH_WIDTH/2, PITCH_LENGTH - 12, s=30, color=LINE_COLOR, zorder=3)

    # Goal lines (simple rectangles to indicate goals)
    goal_width = 8
    goal_left = (PITCH_WIDTH - goal_width) / 2
    ax.plot([goal_left, goal_left, goal_left + goal_width, goal_left + goal_width],
            [0, -2, -2, 0], color=LINE_COLOR, lw=lw)
    ax.plot([goal_left, goal_left, goal_left + goal_width, goal_left + goal_width],
            [PITCH_LENGTH, PITCH_LENGTH + 2, PITCH_LENGTH + 2, PITCH_LENGTH], color=LINE_COLOR, lw=lw)

    ax.set_xlim(-5, PITCH_WIDTH + 5)
    ax.set_ylim(-5, PITCH_LENGTH + 5)
    ax.set_aspect('equal')
    ax.axis('off')

    return fig, ax


def draw_jersey(ax, x, y, color=JERSEY_GREEN, size=800, number=None):
    """Draw a football jersey at position."""
    ax.scatter(x, y, marker=JERSEY_MARKER, s=size, facecolor=color,
               edgecolor=ACCENT_WHITE, linewidth=1.5, zorder=4)


def fig_to_base64(fig, dpi=120):
    """Convert matplotlib figure to base64 string."""
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=dpi, bbox_inches='tight',
                facecolor=fig.get_facecolor(), edgecolor='none', pad_inches=0.1)
    buf.seek(0)
    plt.close(fig)
    return base64.b64encode(buf.read()).decode('utf-8')


def create_radar_chart(player_data, is_per_90=False, accent_color=None):
    """Create a FotMob-style pentagon radar chart for player stats.

    Shows: Defending, Shooting, Passing, Carrying, Receiving
    Uses percentiles for each category.
    When is_per_90=True, uses per 90 percentiles for shape and shows per 90 PV values in labels.
    accent_color allows overriding the default green (e.g., for Defiance blue).
    """
    if accent_color is None:
        accent_color = ACCENT_GREEN

    # Get percentile values for each category (0-100 scale)
    # Order: PASS at top, then clockwise: CARRY, RCV, DEF, SHOT
    categories = ['PASS', 'CARRY', 'RCV', 'DEF', 'SHOT']
    full_names = ['Passing', 'Carrying', 'Receiving', 'Defending', 'Shooting']
    stat_keys = ['pv_passing', 'pv_carrying', 'pv_receiving', 'pv_defending', 'pv_shooting']

    # Calculate per 90 divisor if needed
    mins = player_data.get("mins", 0) or 1
    per_90_divisor = mins / 90 if mins > 0 else 1

    values = []
    raw_pcts = []
    per_90_values = []
    for key in stat_keys:
        # Use per 90 percentiles for shape when in per 90 mode
        if is_per_90:
            pct = player_data.get(f'{key}_per90_percentile', 50) or 50
        else:
            pct = player_data.get(f'{key}_percentile', 50) or 50
        raw_pcts.append(int(pct))
        values.append(pct / 100)  # Normalize to 0-1
        # Calculate per 90 PV value for label display
        pv_raw = player_data.get(key, 0) or 0
        per_90_values.append(round(pv_raw / per_90_divisor, 2))

    # Number of variables
    N = len(categories)

    # Compute angle for each axis - start from bottom (flipped) with point facing down
    angles = [n / float(N) * 2 * np.pi + np.pi/2 for n in range(N)]
    angles += angles[:1]  # Complete the loop
    values += values[:1]  # Complete the loop

    # Create figure
    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True), facecolor='none')
    ax.set_facecolor('none')

    # Draw the pentagon grid lines
    for i in [0.25, 0.5, 0.75, 1.0]:
        grid_angles = angles.copy()
        ax.plot(grid_angles, [i] * (N + 1), color='#444444', linewidth=1.5, linestyle='-', alpha=0.6)

    # Draw axis lines from center to each point
    for angle in angles[:-1]:
        ax.plot([angle, angle], [0, 1], color='#444444', linewidth=1.5, alpha=0.6)

    # Plot data - filled area
    ax.fill(angles, values, color=accent_color, alpha=0.3)
    ax.plot(angles, values, color=accent_color, linewidth=2.5)

    # Add dots at each point
    ax.scatter(angles[:-1], values[:-1], color=accent_color, s=60, zorder=5, edgecolors='white', linewidth=1.5)

    # Set limits
    ax.set_ylim(0, 1)

    # Remove default labels and ticks
    ax.set_xticks([])
    ax.set_yticks([])
    ax.spines['polar'].set_visible(False)

    # Add category labels with percentile values (both modes show percentiles now)
    for i, (angle, cat, pct) in enumerate(zip(angles[:-1], categories, raw_pcts)):
        # Always show percentile ranking
        ax.text(angle, 1.25, f"{cat}\n{pct}%", ha='center', va='center',
                fontsize=18, color=TEXT_COLOR, fontweight='bold', linespacing=1.2)

    return fig_to_base64(fig, dpi=100)


# ============================================================
# BUILD PLAYER LIST
# ============================================================

all_depth_players = []
for pos in POSITION_ORDER:
    if pos in DEPTH_CHART:
        for player in DEPTH_CHART[pos]:
            if player["name"] not in all_depth_players:
                all_depth_players.append(player["name"])

# ============================================================
# SHINY APP UI
# ============================================================

app_ui = ui.page_fluid(
    ui.tags.head(
        ui.tags.style(f"""
            * {{
                box-sizing: border-box;
            }}
            body {{
                background-color: {BG_COLOR};
                color: {TEXT_COLOR};
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                margin: 0;
                padding: 20px;
            }}
            .main-container {{
                display: flex;
                gap: 20px;
                max-width: 1400px;
                margin: 0 auto;
                min-height: 900px;
            }}
            .pitch-panel {{
                flex: 1.2;
                background-color: {CARD_BG};
                border: 1px solid #222;
                border-radius: 12px;
                padding: 20px;
                display: flex;
                flex-direction: column;
            }}
            .stats-panel {{
                flex: 0.8;
                display: flex;
                flex-direction: column;
                gap: 15px;
            }}
            .card {{
                background-color: {CARD_BG};
                border: 1px solid #222;
                border-radius: 12px;
                padding: 20px;
            }}
            h1 {{
                color: {ACCENT_GREEN};
                text-align: center;
                margin: 0 0 20px 0;
                font-size: 28px;
                font-weight: 700;
                letter-spacing: 2px;
            }}
            h2 {{
                color: {ACCENT_GREEN};
                margin: 0 0 10px 0;
                font-size: 22px;
            }}
            h3 {{
                color: {ACCENT_GREEN};
                margin: 0 0 15px 0;
                font-size: 16px;
                text-transform: uppercase;
                letter-spacing: 1px;
            }}
            .player-btn {{
                background: none;
                border: none;
                color: {TEXT_COLOR};
                cursor: pointer;
                padding: 4px 8px;
                font-size: 12px;
                transition: all 0.2s;
                display: block;
                width: 100%;
                text-align: left;
                border-radius: 4px;
            }}
            .player-btn:hover {{
                background-color: rgba(150, 211, 95, 0.2);
                color: {ACCENT_GREEN};
            }}
            .player-btn.selected {{
                background-color: rgba(150, 211, 95, 0.3);
                color: {ACCENT_GREEN};
                font-weight: bold;
            }}
            .designation-badge {{
                background-color: {ACCENT_GREEN};
                color: {BG_COLOR};
                padding: 4px 12px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: 600;
                display: inline-block;
            }}
            .stat-grid {{
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 15px;
            }}
            .stat-item {{
                text-align: center;
                padding: 10px;
                background-color: rgba(255,255,255,0.03);
                border-radius: 8px;
                position: relative;
                transition: all 0.2s ease;
            }}
            .stat-item.clickable {{
                cursor: pointer;
            }}
            .stat-item.clickable:hover {{
                background-color: rgba(150, 211, 95, 0.15);
            }}
            .stat-item.active {{
                background-color: rgba(150, 211, 95, 0.25);
                border: 1px solid {ACCENT_GREEN};
            }}
            .stat-item.active .stat-label,
            .stat-item.active .stat-value {{
                color: {ACCENT_GREEN};
            }}
            .stat-tooltip {{
                display: none;
                position: absolute;
                bottom: 100%;
                left: 50%;
                transform: translateX(-50%);
                background-color: #222;
                color: {TEXT_COLOR};
                padding: 8px 12px;
                border-radius: 6px;
                font-size: 11px;
                white-space: normal;
                width: 180px;
                text-align: center;
                z-index: 100;
                box-shadow: 0 2px 10px rgba(0,0,0,0.3);
                margin-bottom: 5px;
            }}
            .stat-tooltip::after {{
                content: '';
                position: absolute;
                top: 100%;
                left: 50%;
                transform: translateX(-50%);
                border: 6px solid transparent;
                border-top-color: #222;
            }}
            .stat-item:hover .stat-tooltip {{
                display: block;
            }}
            .stat-label {{
                color: {SUBTEXT_COLOR};
                font-size: 11px;
                text-transform: uppercase;
                letter-spacing: 1px;
                margin-bottom: 5px;
            }}
            .stat-value {{
                color: {TEXT_COLOR};
                font-size: 24px;
                font-weight: 700;
            }}
            .percentile {{
                font-size: 12px;
                opacity: 0.6;
                font-weight: normal;
                color: inherit;
                margin-left: 2px;
            }}
            /* Roster summary styles */
            .roster-legend {{
                display: flex;
                flex-wrap: wrap;
                gap: 15px;
                padding: 10px 15px;
                background-color: rgba(255,255,255,0.03);
                border-radius: 8px;
                margin-bottom: 10px;
                font-size: 11px;
                color: {SUBTEXT_COLOR};
            }}
            .legend-item {{
                display: flex;
                align-items: center;
                gap: 5px;
            }}
            .legend-marker {{
                color: {ACCENT_GREEN};
                font-weight: bold;
            }}
            .legend-marker.red {{
                color: #ff6b6b;
            }}
            .roster-summary {{
                padding: 15px;
                background-color: rgba(255,255,255,0.03);
                border-radius: 8px;
            }}
            .roster-grid {{
                display: flex;
                flex-direction: column;
                gap: 8px;
            }}
            .roster-row {{
                display: flex;
                justify-content: space-between;
                gap: 20px;
            }}
            .roster-item {{
                flex: 1;
                display: flex;
                justify-content: space-between;
                align-items: center;
                position: relative;
                padding: 8px 10px;
                border-radius: 6px;
                transition: all 0.2s ease;
            }}
            .roster-item.clickable {{
                cursor: pointer;
            }}
            .roster-item.clickable:hover {{
                background-color: rgba(150, 211, 95, 0.15);
            }}
            .roster-item.active {{
                background-color: rgba(150, 211, 95, 0.25);
                border: 1px solid {ACCENT_GREEN};
            }}
            .roster-item.active .roster-label,
            .roster-item.active .roster-value {{
                color: {ACCENT_GREEN};
            }}
            .roster-label {{
                color: {SUBTEXT_COLOR};
                font-size: 12px;
            }}
            .roster-value {{
                color: {TEXT_COLOR};
                font-size: 14px;
                font-weight: 600;
            }}
            /* Tooltip styles */
            .roster-tooltip {{
                display: none;
                position: absolute;
                bottom: 100%;
                left: 50%;
                transform: translateX(-50%);
                background-color: #222;
                color: {TEXT_COLOR};
                padding: 8px 12px;
                border-radius: 6px;
                font-size: 11px;
                white-space: normal;
                width: 200px;
                text-align: center;
                z-index: 100;
                box-shadow: 0 2px 10px rgba(0,0,0,0.3);
                margin-bottom: 5px;
            }}
            .roster-tooltip::after {{
                content: '';
                position: absolute;
                top: 100%;
                left: 50%;
                transform: translateX(-50%);
                border: 6px solid transparent;
                border-top-color: #222;
            }}
            .roster-item:hover .roster-tooltip {{
                display: block;
            }}
            /* Category stats header */
            .stats-category-header {{
                color: {ACCENT_GREEN};
                font-size: 12px;
                text-transform: uppercase;
                letter-spacing: 1px;
                margin-bottom: 10px;
                padding-bottom: 5px;
                border-bottom: 1px solid rgba(150, 211, 95, 0.3);
            }}
            .info-row {{
                color: {SUBTEXT_COLOR};
                font-size: 14px;
                margin: 5px 0;
            }}
            .info-row span {{
                color: {TEXT_COLOR};
            }}
            .radio-group {{
                display: flex;
                flex-wrap: wrap;
                gap: 8px;
                margin-bottom: 15px;
            }}
            .radio-group label, .shiny-input-radiogroup label {{
                background-color: rgba(255,255,255,0.05);
                padding: 6px 12px;
                border-radius: 20px;
                cursor: pointer;
                font-size: 11px;
                transition: all 0.2s;
                border: 1px solid transparent;
                color: {ACCENT_WHITE} !important;
            }}
            .radio-group label:hover, .shiny-input-radiogroup label:hover {{
                background-color: rgba(150, 211, 95, 0.2);
            }}
            .shiny-input-radiogroup input[type="radio"]:checked + span {{
                color: {ACCENT_GREEN} !important;
                font-weight: bold;
            }}
            /* Defiance radio button styling */
            .shiny-input-radiogroup input[type="radio"][value="defiance"]:checked + span {{
                color: {DEFIANCE_BLUE} !important;
            }}
            /* Defiance mode - change all green accents to blue */
            body.defiance-mode h1,
            body.defiance-mode h2,
            body.defiance-mode h3,
            body.defiance-mode .designation-badge,
            body.defiance-mode .stats-category-header,
            body.defiance-mode .legend-marker,
            body.defiance-mode .stat-item.active .stat-label,
            body.defiance-mode .stat-item.active .stat-value,
            body.defiance-mode .roster-item.active .roster-label,
            body.defiance-mode .roster-item.active .roster-value {{
                color: {DEFIANCE_BLUE} !important;
            }}
            body.defiance-mode .designation-badge {{
                background-color: {DEFIANCE_BLUE} !important;
            }}
            body.defiance-mode .stat-item.clickable:hover,
            body.defiance-mode .roster-item.clickable:hover {{
                background-color: rgba(91, 192, 235, 0.15) !important;
            }}
            body.defiance-mode .stat-item.active,
            body.defiance-mode .roster-item.active {{
                background-color: rgba(91, 192, 235, 0.25) !important;
                border-color: {DEFIANCE_BLUE} !important;
            }}
            body.defiance-mode .player-btn:hover,
            body.defiance-mode .player-btn.selected {{
                background-color: rgba(91, 192, 235, 0.2) !important;
                color: {DEFIANCE_BLUE} !important;
            }}
            body.defiance-mode .reset-btn:hover {{
                border-color: {DEFIANCE_BLUE} !important;
                color: {DEFIANCE_BLUE} !important;
            }}
            input[type="radio"] {{
                display: none;
            }}
            .shiny-input-radiogroup {{
                display: flex;
                flex-wrap: wrap;
                gap: 8px;
                margin-bottom: 10px;
            }}
            .action-map-buttons .shiny-input-radiogroup {{
                row-gap: 12px;
            }}
            .shiny-input-container {{
                margin-bottom: 0;
            }}
            .form-group {{
                margin-bottom: 0;
            }}
            .pitch-title {{
                text-align: center;
                color: {SUBTEXT_COLOR};
                font-size: 14px;
                margin-bottom: 10px;
                text-transform: uppercase;
                letter-spacing: 2px;
            }}
            .footer {{
                text-align: center;
                color: {SUBTEXT_COLOR};
                font-size: 12px;
                margin-top: 20px;
            }}

            /* Pitch click overlay styles */
            .pitch-container {{
                position: relative;
                width: 100%;
            }}
            .pitch-image {{
                display: block;
                width: 100%;
            }}
            .pitch-overlay {{
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                pointer-events: none;
            }}
            .pitch-click-area {{
                position: absolute;
                width: 70px;
                height: 20px;
                cursor: pointer;
                pointer-events: auto;
                border-radius: 4px;
                transition: all 0.2s;
            }}
            .pitch-click-area:hover {{
                /* No hover effect - just clickable */
            }}
            .pitch-click-area.jersey {{
                width: 40px;
                height: 35px;
                border-radius: 50%;
            }}

            /* Reset button styles */
            .reset-btn {{
                background: none;
                border: 1px solid {SUBTEXT_COLOR};
                color: {SUBTEXT_COLOR};
                padding: 4px 10px;
                border-radius: 4px;
                font-size: 11px;
                cursor: pointer;
                transition: all 0.2s;
                float: right;
                margin-top: -25px;
            }}
            .reset-btn:hover {{
                border-color: {ACCENT_GREEN};
                color: {ACCENT_GREEN};
            }}
            .section-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 10px;
            }}
            .section-header h3 {{
                margin: 0;
            }}

            /* Select dropdown styling */
            select, .form-select {{
                background-color: #1a1a1a !important;
                color: {TEXT_COLOR} !important;
                border: 1px solid #333 !important;
                border-radius: 6px !important;
                padding: 8px 12px !important;
                font-size: 12px !important;
                cursor: pointer;
            }}
            select:focus, .form-select:focus {{
                border-color: {ACCENT_GREEN} !important;
                outline: none !important;
                box-shadow: 0 0 0 2px rgba(150, 211, 95, 0.2) !important;
            }}
            select option {{
                background-color: #1a1a1a;
                color: {TEXT_COLOR};
            }}

            /* Mobile responsive styles */
            @media (max-width: 900px) {{
                .main-container {{
                    flex-direction: column;
                    min-height: auto;
                }}
                .pitch-panel {{
                    flex: none;
                    width: 100%;
                }}
                .stats-panel {{
                    flex: none;
                    width: 100%;
                }}
                .stat-grid {{
                    grid-template-columns: repeat(2, 1fr);
                }}
                h1 {{
                    font-size: 22px;
                }}
            }}

            @media (max-width: 500px) {{
                body {{
                    padding: 10px;
                }}
                .card {{
                    padding: 15px;
                }}
                .stat-grid {{
                    grid-template-columns: repeat(2, 1fr);
                    gap: 10px;
                }}
                .stat-value {{
                    font-size: 20px;
                }}
                h1 {{
                    font-size: 18px;
                    letter-spacing: 1px;
                }}
                h2 {{
                    font-size: 18px;
                }}
                .radio-group label, .shiny-input-radiogroup label {{
                    padding: 6px 12px;
                    font-size: 11px;
                }}
            }}
        """)
    ),

    # Header - logo with title underneath, centered
    ui.div(
        ui.HTML(f'<img src="data:image/png;base64,{LOGO_BASE64}" alt="Sounders Logo" style="height: 50px; display: block; margin: 0 auto;">') if LOGO_BASE64 else "",
        ui.output_ui("team_title"),
        style="max-width: 1400px; margin: 0 auto 20px auto; text-align: center;"
    ),

    ui.div(
        # Left panel - Pitch
        ui.div(
            # Team selector row (logo moved to header)
            ui.div(
                # Team selector
                ui.input_radio_buttons(
                    "team_select",
                    None,
                    choices={"first_team": "First Team", "defiance": "Defiance"},
                    selected="first_team",
                    inline=True
                ),
                style="display: flex; align-items: center; gap: 20px; margin-bottom: 10px;"
            ),
            ui.output_ui("pitch_display"),
            ui.output_ui("roster_summary"),
            class_="pitch-panel"
        ),

        # Right panel - Stats
        ui.div(
            # Player and Game selection row
            ui.div(
                # Player buttons (clickable list)
                ui.div(
                    ui.div(
                        ui.h3("SELECT PLAYER"),
                        ui.input_action_button("reset_player", "Reset", class_="reset-btn"),
                        class_="section-header"
                    ),
                    ui.output_ui("player_buttons"),
                    style="flex: 1;"
                ),
                # Game filter dropdown
                ui.div(
                    ui.div(
                        ui.h3("FILTER BY GAME"),
                        class_="section-header"
                    ),
                    ui.output_ui("game_dropdown"),
                    style="flex: 1;"
                ),
                class_="card",
                style="display: flex; gap: 20px;"
            ),

            # Player info
            ui.div(
                ui.output_ui("player_info"),
                class_="card"
            ),

            # Stats
            ui.div(
                ui.div(
                    ui.h3("SEASON STATS"),
                    ui.output_ui("per_90_toggle"),
                    ui.input_action_button("reset_stats", "Reset", class_="reset-btn"),
                    class_="section-header"
                ),
                ui.div("Percentiles compare to other Sounders players this season",
                       style=f"color: {SUBTEXT_COLOR}; font-size: 11px; margin-bottom: 10px; font-style: italic;"),
                ui.output_ui("stats_table"),
                class_="card"
            ),

            # Action map
            ui.div(
                ui.div(
                    ui.h3("ACTION MAP"),
                    ui.input_action_button("reset_heatmap", "Reset", class_="reset-btn"),
                    class_="section-header"
                ),
                ui.div(
                    ui.input_radio_buttons(
                        "heatmap_type",
                        None,
                        choices={
                            "Overview": "Overview",
                            "Pass": "Pass",
                            "Carry": "Carry",
                            "Reception": "Reception",
                            "Shot": "Shots",
                            "Defensive": "Defensive",
                        },
                        selected="Overview",
                        inline=True
                    ),
                    class_="action-map-buttons",
                    style="margin-bottom: 15px;"
                ),
                ui.output_ui("heatmap_display"),
                # Location toggle, Action/Trajectories/Density, and Export - all under the pitch
                ui.output_ui("location_toggle_ui"),
                ui.div(
                    ui.output_ui("heatmap_mode_toggle"),
                    ui.output_ui("action_map_export_btn"),
                    style="display: flex; justify-content: space-between; align-items: center;"
                ),
                # Events key/legend
                ui.output_ui("events_key_legend"),
                class_="card"
            ),

            class_="stats-panel"
        ),

        class_="main-container"
    ),

    ui.div("Data from Opta | Powered by Sunday League Stats", class_="footer"),
)


# ============================================================
# SERVER
# ============================================================

def server(input, output, session):

    # Reactive value to store selected player (None = no selection on load)
    selected_player = reactive.value(None)

    # Reactive value to store selected roster filter (None = no filter)
    # Options: "senior", "supplemental", "dp", "u22", "international", "on_loan", "off_roster"
    roster_filter = reactive.value(None)

    # Reactive value to store clicked stat for detailed heatmap visualization
    # Options: "key_passes", "carries", "assists", "tackles", "interceptions", etc.
    stat_visualization = reactive.value(None)

    # Reactive value to store selected game filter (None = all games)
    selected_game = reactive.value(None)

    # Reactive value for start/end location toggle (for Pass and Carry)
    location_toggle = reactive.value("start")  # "start" or "end"

    # Reactive value for trajectory lines toggle
    show_trajectories = reactive.value(False)

    # Reactive value for heatmap mode: "action" (dots) or "kde" (density)
    heatmap_mode = reactive.value("action")

    # Reactive value for per 90 mode
    per_90_mode = reactive.value(False)

    def get_current_team_data():
        """Get the depth chart, position order, and coords for selected team."""
        if input.team_select() == "defiance":
            return DEFIANCE_DEPTH_CHART, DEFIANCE_POSITION_ORDER, DEFIANCE_POSITION_COORDS
        return DEPTH_CHART, POSITION_ORDER, POSITION_COORDS

    @output
    @render.ui
    def team_title():
        """Render the team title based on selection."""
        is_defiance = input.team_select() == "defiance"
        if is_defiance:
            title = "TACOMA DEFIANCE DEPTH CHART"
            color = DEFIANCE_BLUE
            # Use img onerror to execute JS since script tags don't run in innerHTML
            js_trigger = '<img src="" onerror="document.body.classList.add(\'defiance-mode\');" style="display:none;">'
        else:
            title = "SEATTLE SOUNDERS DEPTH CHART"
            color = ACCENT_GREEN
            js_trigger = '<img src="" onerror="document.body.classList.remove(\'defiance-mode\');" style="display:none;">'
        return ui.HTML(f'{js_trigger}<h1 style="margin: 8px 0 0 0; text-align: center; font-size: 24px; color: {color};">{title}</h1>')

    @output
    @render.ui
    def player_buttons():
        """Create clickable buttons for each player, sorted by minutes."""
        buttons = []
        current = selected_player.get()
        depth_chart, pos_order, _ = get_current_team_data()
        is_defiance = input.team_select() == "defiance"
        accent_color = DEFIANCE_BLUE if is_defiance else ACCENT_GREEN

        for pos in pos_order:
            if pos not in depth_chart:
                continue
            display_pos = pos.replace("2", "")
            buttons.append(ui.strong(display_pos, style=f"color: {accent_color}; font-size: 11px; display: block; margin-top: 10px;"))

            # Sort players within each position by minutes (descending)
            players_in_pos = depth_chart[pos]
            sorted_players = sorted(players_in_pos, key=lambda p: MINUTES_LOOKUP.get(p["name"], 0), reverse=True)

            for player in sorted_players:
                name = player["name"]
                is_selected = name == current
                btn_class = "player-btn selected" if is_selected else "player-btn"
                btn_id = f"btn_{sanitize_id(name)}"
                buttons.append(
                    ui.input_action_button(btn_id, name, class_=btn_class)
                )

        return ui.div(*buttons, style="max-height: 200px; overflow-y: auto;")

    @output
    @render.ui
    def game_dropdown():
        """Create dropdown of games the selected player appeared in."""
        name = selected_player.get()
        current_game = selected_game.get()

        if not name:
            return ui.p("Select a player first", style=f"color: {SUBTEXT_COLOR}; font-size: 12px;")

        player = get_player_data(name)
        if not player:
            return ui.p("No game data", style=f"color: {SUBTEXT_COLOR}; font-size: 12px;")

        player_id = player.get("player_id")
        matches = get_player_matches(player_id)

        if not matches:
            return ui.p("No game data available. Run export_data.py to update.",
                       style=f"color: {SUBTEXT_COLOR}; font-size: 12px;")

        # Sort matches by date in ascending order (oldest first)
        def parse_date(m):
            date_str = m.get("start_date", "")
            try:
                # Format: MM/DD/YYYY
                parts = date_str.split("/")
                if len(parts) == 3:
                    month, day, year = int(parts[0]), int(parts[1]), int(parts[2])
                    return (year, month, day)
            except (ValueError, IndexError):
                pass
            return (9999, 12, 31)  # Put invalid dates at the end

        sorted_matches = sorted(matches, key=parse_date)

        # Build choices: "All Games" + individual games
        choices = {"all": "All Games"}
        for m in sorted_matches:
            date = m.get("start_date", "")
            opponent = m.get("opponent", "Unknown")
            venue = m.get("venue", "vs")
            # Format: "vs Team Name (2025-01-15)" or "@ Team Name (2025-01-15)"
            label = f"{venue} {opponent} ({date})"
            choices[str(m["match_id"])] = label

        return ui.div(
            ui.input_select(
                "game_select",
                None,
                choices=choices,
                selected=current_game if current_game else "all",
                width="100%"
            ),
            style="max-height: 200px; overflow-y: auto;"
        )

    # Handle game selection changes
    @reactive.effect
    @reactive.event(input.game_select)
    def _():
        val = input.game_select()
        if val == "all":
            selected_game.set(None)
        else:
            selected_game.set(val)

    # Create click handlers for all player buttons (both teams)
    all_players = list(all_depth_players)
    for pos in DEFIANCE_POSITION_ORDER:
        if pos in DEFIANCE_DEPTH_CHART:
            for p in DEFIANCE_DEPTH_CHART[pos]:
                if p["name"] not in all_players:
                    all_players.append(p["name"])

    for player_name in all_players:
        def make_handler(name):
            btn_id = f"btn_{sanitize_id(name)}"
            @reactive.effect
            @reactive.event(input[btn_id])
            def _():
                selected_player.set(name)
                selected_game.set(None)  # Clear game filter on player change
        make_handler(player_name)

    # Handle pitch player clicks
    @reactive.effect
    @reactive.event(input.pitch_player_click)
    def _():
        player_name = input.pitch_player_click()
        if player_name:
            selected_player.set(player_name)
            selected_game.set(None)  # Clear game filter on player change

    # Reset button handlers
    @reactive.effect
    @reactive.event(input.reset_player)
    def _():
        selected_player.set(None)
        roster_filter.set(None)
        selected_game.set(None)

    @reactive.effect
    @reactive.event(input.reset_stats)
    def _():
        stat_visualization.set(None)

    @output
    @render.ui
    def per_90_toggle():
        """Render Per 90 toggle button - hidden for Overview stats."""
        # Hide Per 90 toggle for Overview (overall stats)
        heatmap_type = input.heatmap_type()
        if heatmap_type == "Overview":
            return ui.div()  # Return empty div to hide

        is_per_90 = per_90_mode.get()

        # Determine accent color based on team selection
        is_defiance = input.team_select() == "defiance"
        accent_color = DEFIANCE_BLUE if is_defiance else ACCENT_GREEN

        style = f"background: {accent_color}; color: #000; font-weight: bold;" if is_per_90 else f"background: transparent; color: {TEXT_COLOR}; border: 1px solid #444;"
        return ui.input_action_button(
            "toggle_per_90",
            "Per 90",
            style=f"{style} padding: 4px 12px; border-radius: 4px; margin-left: 8px; margin-right: auto; font-size: 12px; cursor: pointer;"
        )

    @reactive.effect
    @reactive.event(input.toggle_per_90)
    def _toggle_per_90():
        per_90_mode.set(not per_90_mode.get())

    @reactive.effect
    @reactive.event(input.reset_heatmap)
    async def _():
        stat_visualization.set(None)
        location_toggle.set("start")
        show_trajectories.set(False)
        # Reset heatmap to default selection
        await session.send_input_message("heatmap_type", {"value": "Pass"})

    # Handle legend filter clicks
    @reactive.effect
    @reactive.event(input.legend_filter_click)
    def _handle_legend_filter():
        clicked_filter = input.legend_filter_click()
        current = roster_filter.get()
        # Toggle: if clicking the same filter, clear it; otherwise set new filter
        if clicked_filter == current or clicked_filter is None:
            roster_filter.set(None)
        else:
            roster_filter.set(clicked_filter)

    def player_matches_filter(player_entry, filter_type):
        """Check if a player matches the current roster filter."""
        if filter_type is None:
            return True
        if filter_type == "senior":
            return not player_entry.get("supplemental", False) and not player_entry.get("off_roster", False)
        if filter_type == "supplemental":
            return player_entry.get("supplemental", False)
        if filter_type == "tam":
            return player_entry.get("designation") == "TAM"
        if filter_type == "unavailable":
            return player_entry.get("unavailable", False)
        if filter_type == "sei":
            return player_entry.get("designation") == "SEI"
        if filter_type == "on_loan":
            return player_entry.get("on_loan", False)
        if filter_type == "dp":
            return player_entry.get("designation") == "DP"
        if filter_type == "u22":
            return player_entry.get("designation") == "U22"
        if filter_type == "international":
            return player_entry.get("international", False)
        if filter_type == "off_roster":
            return player_entry.get("off_roster", False)
        # Defiance filters
        if filter_type == "academy":
            return player_entry.get("academy", False)
        if filter_type == "loanee":
            return player_entry.get("loanee", False)
        return True

    @output
    @render.ui
    def pitch_display():
        """Render the pitch with jerseys and player names."""
        fig, ax = create_pitch_figure(figsize=(8, 12))

        path_eff = [pe.Stroke(linewidth=2.5, foreground="black"), pe.Normal()]
        current = selected_player.get()
        current_filter = roster_filter.get()
        depth_chart, pos_order, pos_coords = get_current_team_data()

        has_selection = current is not None
        has_filter = current_filter is not None

        for pos in pos_order:
            if pos not in depth_chart or pos not in pos_coords:
                continue

            x, y = pos_coords[pos]
            players_raw = depth_chart[pos]

            # Sort players by minutes played (descending)
            def get_player_minutes(p):
                player_data = get_player_data(p["name"])
                mins = player_data.get("mins") if player_data else 0
                return mins if mins is not None else 0
            players = sorted(players_raw, key=get_player_minutes, reverse=True)

            # Check if any player at this position is the selected player
            position_has_selected = any(p["name"] == current for p in players)

            # Check if any player at this position matches the filter
            position_has_filter_match = any(player_matches_filter(p, current_filter) for p in players)

            # Determine jersey alpha based on selection or filter
            if has_selection and not position_has_selected:
                jersey_alpha = 0.3
            elif has_filter and not position_has_filter_match:
                jersey_alpha = 0.3
            else:
                jersey_alpha = 1.0

            # Choose jersey color based on team
            team = input.team_select()
            is_defiance_team = team == "defiance"
            jersey_color = DEFIANCE_BLUE if is_defiance_team else JERSEY_GREEN
            accent_color = DEFIANCE_BLUE if is_defiance_team else ACCENT_GREEN

            # Draw jersey with alpha
            ax.scatter(x, y, marker=JERSEY_MARKER, s=1200, facecolor=jersey_color,
                       edgecolor=ACCENT_WHITE, linewidth=1.5, zorder=4, alpha=jersey_alpha)

            # Position label above jersey
            display_pos = pos.replace("2", "")
            if has_selection:
                pos_alpha = 0.3 if not position_has_selected else 1.0
            elif has_filter:
                pos_alpha = 0.3 if not position_has_filter_match else 1.0
            else:
                pos_alpha = 1.0
            ax.text(x, y + 4, display_pos, ha='center', va='bottom',
                    fontsize=10, color=accent_color, fontweight='bold', zorder=6, alpha=pos_alpha)

            # Stack player names below jersey
            for i, player_entry in enumerate(players[:3]):
                name = player_entry["name"]
                parts = name.split()
                display_name = parts[-1].upper() if parts else name.upper()

                # Add captain "C" to the left of Cristian Roldan's name
                if name == "Cristian Roldan" and i == 0:
                    display_name = f"(C) {display_name}"

                # Roster designation no longer shown in parentheses on pitch
                # (shown in legend below instead)

                y_offset = y - 6 - (i * 4)

                # Determine color based on selection/filter state
                matches_filter = player_matches_filter(player_entry, current_filter)

                # Highlight selected player, fade others when there's a selection or filter
                if name == current:
                    color = accent_color
                    fontweight = 'bold'
                    fontsize = 10
                    text_alpha = 1.0
                elif has_filter and matches_filter:
                    # Highlight players matching the filter
                    color = accent_color
                    fontweight = 'bold'
                    fontsize = 9 if i == 0 else 8
                    text_alpha = 1.0
                elif has_selection:
                    color = ACCENT_WHITE if i == 0 else SUBTEXT_COLOR
                    fontweight = 'bold' if i == 0 else 'normal'
                    fontsize = 9 if i == 0 else 8
                    text_alpha = 0.3
                elif has_filter:
                    color = ACCENT_WHITE if i == 0 else SUBTEXT_COLOR
                    fontweight = 'bold' if i == 0 else 'normal'
                    fontsize = 9 if i == 0 else 8
                    text_alpha = 0.3
                else:
                    color = ACCENT_WHITE if i == 0 else SUBTEXT_COLOR
                    fontweight = 'bold' if i == 0 else 'normal'
                    fontsize = 9 if i == 0 else 8
                    text_alpha = 1.0

                ax.text(x, y_offset, display_name, ha='center', va='top',
                        fontsize=fontsize, color=color, fontweight=fontweight,
                        zorder=5, path_effects=path_eff, alpha=text_alpha)

        img_data = fig_to_base64(fig, dpi=100)

        # Build clickable overlay areas for each position
        # The pitch is 80 wide x 120 tall in data coords, with padding of 5 on each side
        # Image aspect ratio: figsize (8, 12), so height = 1.5 * width
        # In percentage terms for the overlay:
        # x_pct = (x + 5) / 90 * 100  (since xlim is -5 to 85)
        # y_pct = 100 - (y + 5) / 130 * 100  (since ylim is -5 to 125, and CSS y is inverted)

        click_areas = []
        for pos in pos_order:
            if pos not in depth_chart or pos not in pos_coords:
                continue

            x, y = pos_coords[pos]
            players_raw = depth_chart[pos]

            # Sort players by minutes played (descending) - same as above
            def get_player_mins(p):
                player_data = get_player_data(p["name"])
                mins = player_data.get("mins") if player_data else 0
                return mins if mins is not None else 0
            players = sorted(players_raw, key=get_player_mins, reverse=True)

            # Convert pitch coordinates to percentage for CSS positioning
            # Image shows xlim=(-5, 85) and ylim=(-5, 125)
            x_pct = (x + 5) / 90 * 100
            # Invert y for CSS (top is 0%)
            y_pct = 100 - (y + 5) / 130 * 100

            # Create click area for jersey (starter only)
            if players:
                starter_name = players[0]["name"]
                safe_name = starter_name.replace("'", "\\'").replace('"', '\\"')
                click_areas.append(f'''
                    <div class="pitch-click-area jersey"
                         data-player="{safe_name}"
                         style="left: {x_pct}%; top: {y_pct}%; transform: translate(-50%, -50%);"
                         title="Click to select {starter_name}">
                    </div>
                ''')

            # Create individual click areas for each player name
            for i, player_entry in enumerate(players):
                name = player_entry["name"]
                safe_name = name.replace("'", "\\'").replace('"', '\\"')
                # Names are drawn at y_offset = y - 6 - (i * 4) in pitch coords
                name_y = y - 6 - (i * 4)
                name_y_pct = 100 - (name_y + 5) / 130 * 100
                click_areas.append(f'''
                    <div class="pitch-click-area"
                         data-player="{safe_name}"
                         style="left: {x_pct}%; top: {name_y_pct}%; transform: translate(-50%, -50%);"
                         title="Click to select {name}">
                    </div>
                ''')

        click_areas_html = ''.join(click_areas)

        return ui.div(
            ui.HTML(f'''
                <div class="pitch-container">
                    <img src="data:image/png;base64,{img_data}" class="pitch-image" style="width: 100%; display: block;">
                    <div class="pitch-overlay">
                        {click_areas_html}
                    </div>
                </div>
            '''),
            ui.tags.script("""
                document.querySelectorAll('.pitch-click-area').forEach(function(area) {
                    area.addEventListener('click', function() {
                        var playerName = this.getAttribute('data-player');
                        if (playerName) {
                            Shiny.setInputValue('pitch_player_click', playerName, {priority: 'event'});
                        }
                    });
                });
            """)
        )


    @output
    @render.ui
    def roster_summary():
        """Display clickable roster legend below the pitch."""
        team = input.team_select()

        if team == "defiance":
            # Show Defiance legend with academy/loanee categories
            all_players = []
            for pos, players in DEFIANCE_DEPTH_CHART.items():
                all_players.extend(players)

            academy_players = [p for p in all_players if p.get("academy", False)]
            loanee_players = [p for p in all_players if p.get("loanee", False)]

            academy_names = ", ".join([p["name"] for p in academy_players])
            loanee_names = ", ".join([p["name"] for p in loanee_players])

            current_filter = roster_filter.get()
            academy_active = current_filter == "academy"
            loanee_active = current_filter == "loanee"

            academy_style = f"background: {DEFIANCE_BLUE}; color: #000; font-weight: bold;" if academy_active else ""
            loanee_style = f"background: {DEFIANCE_BLUE}; color: #000; font-weight: bold;" if loanee_active else ""

            summary_html = f'''
            <div class="roster-legend" style="padding: 10px 15px;">
                <div style="display: flex; flex-wrap: wrap; gap: 8px; align-items: center;">
                    <button class="legend-item" data-filter="academy"
                            style="{academy_style} padding: 4px 10px; border-radius: 4px; border: 1px solid #444;
                                   cursor: pointer; font-size: 11px; background: {DEFIANCE_BLUE if academy_active else 'transparent'};
                                   color: {('#000' if academy_active else TEXT_COLOR)};">
                        Academy Products: <strong>{len(academy_players)}</strong>
                        <span style="color: {'#000' if academy_active else '#888'}; font-size: 10px; margin-left: 4px;">({academy_names})</span>
                    </button>
                    <button class="legend-item" data-filter="loanee"
                            style="{loanee_style} padding: 4px 10px; border-radius: 4px; border: 1px solid #444;
                                   cursor: pointer; font-size: 11px; background: {DEFIANCE_BLUE if loanee_active else 'transparent'};
                                   color: {('#000' if loanee_active else TEXT_COLOR)};">
                        Loanee: <strong>{len(loanee_players)}</strong>
                        <span style="color: {'#000' if loanee_active else '#888'}; font-size: 10px; margin-left: 4px;">({loanee_names})</span>
                    </button>
                </div>
            </div>
            <script>
                document.querySelectorAll('.legend-item').forEach(function(btn) {{
                    btn.addEventListener('click', function() {{
                        var filter = this.getAttribute('data-filter');
                        Shiny.setInputValue('legend_filter_click', filter, {{priority: 'event'}});
                    }});
                }});
            </script>
            '''
            return ui.HTML(summary_html)

        # First Team legend
        counts = calculate_roster_counts(DEPTH_CHART)
        current_filter = roster_filter.get()

        # Calculate total on roster excluding on-loan players
        total_active = counts['total_on_roster'] - counts.get('on_loan_count', 0)

        # Build clickable legend items - add Total on Roster first
        legend_items = [
            ("total", "Total on Roster", total_active, counts['total_max']),
            ("senior", "Senior Roster", counts['senior_roster'], counts['senior_max']),
            ("supplemental", "Supplemental", counts['supplemental_roster'], counts['supplemental_max']),
            ("international", "International", counts['international_count'], counts['international_max']),
            ("dp", "DP", counts['dp_spots'], counts['dp_max']),
            ("u22", "U22", counts.get('u22_count', 0), 3),
            ("tam", "TAM", counts.get('tam_count', 0), None),
            ("unavailable", "Unavailable", counts.get('unavailable_count', 0), None),
            ("sei", "SEI", counts.get('sei_count', 0), None),
            ("on_loan", "On Loan", counts.get('on_loan_count', 0), None),
        ]

        accent_color = ACCENT_GREEN

        items_html = ""
        for filter_type, label, count, max_count in legend_items:
            is_active = current_filter == filter_type
            active_style = f"background: {accent_color}; color: #000; font-weight: bold;" if is_active else ""
            max_text = f" of {max_count}" if max_count else ""
            items_html += f'''
                <button class="legend-item" data-filter="{filter_type}"
                        style="{active_style} padding: 4px 10px; border-radius: 4px; border: 1px solid #444;
                               margin: 2px; cursor: pointer; font-size: 11px; background: {accent_color if is_active else 'transparent'};
                               color: {('#000' if is_active else TEXT_COLOR)};">
                    {label}: <strong>{count}{max_text}</strong>
                </button>
            '''

        summary_html = f'''
        <div class="roster-legend" style="padding: 10px 15px;">
            <div style="display: flex; flex-wrap: wrap; gap: 5px; align-items: center;">
                {items_html}
            </div>
        </div>
        <script>
            document.querySelectorAll('.legend-item').forEach(function(btn) {{
                btn.addEventListener('click', function() {{
                    var filter = this.getAttribute('data-filter');
                    Shiny.setInputValue('legend_filter_click', filter, {{priority: 'event'}});
                }});
            }});
        </script>
        '''

        return ui.HTML(summary_html)


    def format_salary(salary):
        """Format salary as currency (e.g., $2,500,000)."""
        if salary is None:
            return None
        try:
            return f"${int(salary):,}"
        except (ValueError, TypeError):
            return None

    @output
    @render.ui
    def player_info():
        """Display selected player's basic info."""
        name = selected_player.get()
        if not name:
            return ui.p("Select a player")

        player = get_player_data(name)

        # Get all roster designations for this player from depth chart
        roster_badges = []
        player_entry = None
        for pos, players in DEPTH_CHART.items():
            for p in players:
                if p["name"] == name:
                    player_entry = p
                    break
            if player_entry:
                break
        # Also check Defiance depth chart
        if not player_entry:
            for pos, players in DEFIANCE_DEPTH_CHART.items():
                for p in players:
                    if p["name"] == name:
                        player_entry = p
                        break
                if player_entry:
                    break

        if player_entry:
            # Build list of applicable roster badges
            designation = player_entry.get("designation", "SEN")
            if designation == "DP":
                roster_badges.append("Designated Player")
            elif designation == "TAM":
                roster_badges.append("TAM")
            elif designation == "U22":
                roster_badges.append("U22 Initiative")
            elif designation == "HG":
                roster_badges.append("Homegrown")
            elif designation == "SEI":
                roster_badges.append("Season Ending Injury")

            if not player_entry.get("supplemental", False) and not player_entry.get("off_roster", False):
                roster_badges.append("Senior Roster")
            elif player_entry.get("supplemental", False):
                roster_badges.append("Supplemental")

            if player_entry.get("international", False):
                roster_badges.append("International")
            if player_entry.get("on_loan", False):
                roster_badges.append("On Loan")
            if player_entry.get("unavailable", False) and not player_entry.get("on_loan", False):
                roster_badges.append("Unavailable")

        if player:
            # Determine accent color based on team selection
            is_defiance = input.team_select() == "defiance"
            accent_color = DEFIANCE_BLUE if is_defiance else ACCENT_GREEN

            # Generate radar chart (with per 90 mode if enabled)
            is_per_90 = per_90_mode.get()
            radar_img = create_radar_chart(player, is_per_90, accent_color=accent_color)

            # Use image_url from database if available, fallback to depth chart photo
            photo_url = player.get('image_url')
            if not photo_url and player_entry:
                photo_url = player_entry.get("photo")

            # Get position from primary_general_position
            position = player.get('primary_general_position', player.get('position', 'N/A'))

            # Get salary and nationality
            salary = format_salary(player.get('base_salary'))
            nation = player.get('country', player.get('nationality', ''))

            # Build roster badges HTML
            badges_html = ""
            for badge in roster_badges:
                badges_html += f'<span class="designation-badge" style="margin-right: 5px; margin-bottom: 5px;">{badge}</span>'

            return ui.div(
                ui.div(
                    # Player photo
                    ui.HTML(f'<img src="{photo_url}" alt="{player["name"]}" style="width: 80px; height: 80px; border-radius: 50%; object-fit: cover; border: 3px solid {accent_color};">') if photo_url else "",
                    # Player name and info
                    ui.div(
                        ui.h2(player["name"], style="margin: 0;"),
                        ui.p(
                            f"#{player.get('shirt_no', '-')} | {position} | Age {player.get('age', 'N/A')}",
                            class_="info-row",
                            style="margin: 5px 0;"
                        ),
                        ui.p(f"Nation: {nation}", class_="info-row", style="margin: 3px 0;") if nation else "",
                        ui.p(f"Salary: {salary}", class_="info-row", style="margin: 3px 0;") if salary else "",
                        ui.HTML(f'<div style="margin-top: 8px; display: flex; flex-wrap: wrap;">{badges_html}</div>') if badges_html else "",
                        style="flex: 1;"
                    ),
                    # Radar chart on the right
                    ui.HTML(f'<img src="data:image/png;base64,{radar_img}" alt="Player radar" style="width: 200px; height: 200px;">'),
                    style="display: flex; align-items: center; gap: 15px;"
                ),
            )
        else:
            photo_url = player_entry.get("photo") if player_entry else None
            badges_html = ""
            for badge in roster_badges:
                badges_html += f'<span class="designation-badge" style="margin-right: 5px; margin-bottom: 5px;">{badge}</span>'

            # Determine accent color for else case too
            is_defiance_else = input.team_select() == "defiance"
            accent_color_else = DEFIANCE_BLUE if is_defiance_else else ACCENT_GREEN

            return ui.div(
                ui.div(
                    ui.HTML(f'<img src="{photo_url}" alt="{name}" style="width: 80px; height: 80px; border-radius: 50%; object-fit: cover; border: 3px solid {accent_color_else};">') if photo_url else "",
                    ui.div(
                        ui.h2(name, style="margin: 0;"),
                        ui.p("Player data not found", class_="info-row"),
                        ui.HTML(f'<div style="margin-top: 8px; display: flex; flex-wrap: wrap;">{badges_html}</div>') if badges_html else "",
                        style="flex: 1;"
                    ),
                    style="display: flex; align-items: center; gap: 15px;"
                ),
            )


    # Define stat tooltips and which stats are clickable for heatmap visualization
    STAT_INFO = {
        "matches": {"tooltip": "Total games played this season", "clickable": False},
        "goals": {"tooltip": "Goals scored. Click to see shot locations that resulted in goals", "clickable": True, "viz_type": "goals"},
        "assists": {"tooltip": "Intentional passes leading directly to goals. Click to see assist passes", "clickable": True, "viz_type": "assists"},
        "shots": {"tooltip": "Total shot attempts. Click to see all shot locations", "clickable": True, "viz_type": "all_shots"},
        "shots_on_target": {"tooltip": "Shots on target. Click to see SOT locations", "clickable": True, "viz_type": "shots_on_target"},
        "passes": {"tooltip": "Successful passes completed", "clickable": False},
        "total_passes": {"tooltip": "All pass attempts. Click to see all pass locations", "clickable": True, "viz_type": "all_passes"},
        "pass_pct": {"tooltip": "Pass completion percentage - successful passes divided by total pass attempts", "clickable": False},
        "key_passes": {"tooltip": "Passes leading to a shot attempt. Click to see key pass trajectories", "clickable": True, "viz_type": "key_passes"},
        "progressive_passes": {"tooltip": "Passes that move the ball significantly closer to goal. Click to see locations", "clickable": True, "viz_type": "progressive_passes"},
        "final_third_passes": {"tooltip": "Passes into or within the final third. Click to see locations", "clickable": True, "viz_type": "final_third_passes"},
        "deep_passes": {"tooltip": "Passes into the deep area near the box. Click to see locations", "clickable": True, "viz_type": "deep_passes"},
        "xg_assisted": {"tooltip": "Expected goals from chances created by this player's passes", "clickable": False},
        "defensive_actions": {"tooltip": "Combined tackles, interceptions, clearances, and recoveries. Click to see all defensive action locations", "clickable": True, "viz_type": "all_defensive"},
        "tackles": {"tooltip": "Successful tackle attempts. Click to see tackle locations", "clickable": True, "viz_type": "tackles"},
        "interceptions": {"tooltip": "Passes intercepted. Click to see interception locations", "clickable": True, "viz_type": "interceptions"},
        "clearances": {"tooltip": "Defensive clearances. Click to see clearance locations", "clickable": True, "viz_type": "clearances"},
        "ball_recoveries": {"tooltip": "Loose balls recovered. Click to see recovery locations", "clickable": True, "viz_type": "recoveries"},
        "carries": {"tooltip": "Ball carries (dribbles). Click to see carry paths", "clickable": True, "viz_type": "all_carries"},
        "final_third_carries": {"tooltip": "Carries into or within the final third. Click to see locations", "clickable": True, "viz_type": "final_third_carries"},
        "deep_carries": {"tooltip": "Carries into the deep area near the box. Click to see locations", "clickable": True, "viz_type": "deep_carries"},
        "progressive_carries": {"tooltip": "Carries that move the ball significantly closer to goal. Click to see locations", "clickable": True, "viz_type": "progressive_carries"},
        "receptions": {"tooltip": "All ball receptions. Click to see reception locations", "clickable": True, "viz_type": "all_receptions"},
        "final_third_receptions": {"tooltip": "Receptions in the final third. Click to see locations", "clickable": True, "viz_type": "final_third_receptions"},
        "deep_receptions": {"tooltip": "Deep receptions near the box. Click to see locations", "clickable": True, "viz_type": "deep_receptions"},
        "pv_total": {"tooltip": "Total Possession Value Added - overall contribution to scoring chances", "clickable": False},
        "pv_passing": {"tooltip": "Possession Value from passing - how much passes increased scoring probability", "clickable": False},
        "pv_receiving": {"tooltip": "Possession Value from receiving - value added by receiving passes in good positions", "clickable": False},
        "pv_carrying": {"tooltip": "Possession Value from carrying - value added by dribbling/carrying the ball", "clickable": False},
        "pv_shooting": {"tooltip": "Possession Value from shooting - expected goals from shot quality", "clickable": False},
        "pv_defending": {"tooltip": "Possession Value from defending - value added/lost from defensive actions", "clickable": False},
        "xg": {"tooltip": "Expected Goals - the probability of shots becoming goals based on shot quality", "clickable": False},
    }

    @output
    @render.ui
    def stats_table():
        """Display player stats in a grid - general or category-specific based on heatmap selection."""
        name = selected_player.get()
        if not name:
            return ui.p("Select a player")

        player = get_player_data(name)
        if not player:
            return ui.p("No stats available")

        # Check for game filter - use game-specific stats if active
        game_filter = selected_game.get()
        if game_filter and player.get("player_id"):
            game_stats = get_game_stats(player.get("player_id"), game_filter)
            if game_stats:
                # Merge game stats with player data (keep player info like name, position)
                player = {**player, **game_stats}

        heatmap_type = input.heatmap_type()
        current_viz = stat_visualization.get()
        is_per_90 = per_90_mode.get()

        # Calculate per 90 divisor (minutes / 90)
        mins = player.get("mins", 0) or 1
        per_90_divisor = mins / 90 if mins > 0 else 1

        def get_per_90_value(raw_value):
            """Convert raw value to per 90."""
            if not is_per_90 or raw_value is None:
                return raw_value
            try:
                return round(float(raw_value) / per_90_divisor, 2)
            except (ValueError, TypeError):
                return raw_value

        def format_stat_value(raw_value, stat_key):
            """Format stat value, applying per 90 if enabled."""
            if stat_key and stat_key.startswith("pv_"):
                # PV stats - format as decimal
                val = get_per_90_value(raw_value) if is_per_90 else raw_value
                return f"{val:.2f}" if isinstance(val, (int, float)) else str(val)
            elif is_per_90 and isinstance(raw_value, (int, float)):
                val = get_per_90_value(raw_value)
                return f"{val:.2f}" if isinstance(val, float) else str(val)
            return str(raw_value) if raw_value is not None else "0"

        # Determine which stats to show based on heatmap selection
        if heatmap_type == "Pass":
            # Passing stats - all clickable to filter heat map
            category_name = "Passing Stats"
            total_passes = player.get("total_passes", 0) or 0
            passes = player.get("passes", 0) or 0
            pass_pct = round((passes / total_passes * 100) if total_passes > 0 else 0, 1)

            stats = [
                ("Total Passes", total_passes, "total_passes"),
                ("Pass %", f"{pass_pct}%", None),
                ("Prog Passes", player.get("progressive_passes", 0), "progressive_passes"),
                ("Key Passes", player.get("key_passes", 0), "key_passes"),
                ("xG Assisted", player.get('xg_assisted', 0) or 0, "xg_assisted"),
                ("Final 3rd", player.get("final_third_passes", 0), "final_third_passes"),
                ("Deep Passes", player.get("deep_passes", 0), "deep_passes"),
                ("PV+ Passing", player.get('pv_passing', 0) or 0, "pv_passing"),
            ]
        elif heatmap_type == "Carry":
            # Carrying stats - all clickable to filter heat map
            category_name = "Carrying Stats"
            stats = [
                ("Carries", player.get("carries", 0), "carries"),
                ("Final 3rd", player.get("final_third_carries", 0), "final_third_carries"),
                ("Deep Carries", player.get("deep_carries", 0), "deep_carries"),
                ("Prog Carries", player.get("progressive_carries", 0), "progressive_carries"),
                ("PV+ Carrying", player.get('pv_carrying', 0) or 0, "pv_carrying"),
            ]
        elif heatmap_type == "Reception":
            # Reception stats - all clickable to filter heat map
            category_name = "Reception Stats"
            stats = [
                ("Receptions", player.get("receptions", 0), "receptions"),
                ("Final 3rd Recv", player.get("final_third_receptions", 0), "final_third_receptions"),
                ("Deep Recv", player.get("deep_receptions", 0), "deep_receptions"),
                ("PV Receiving", player.get('pv_receiving', 0) or 0, "pv_receiving"),
            ]
        elif heatmap_type == "Shot":
            # Shooting stats - all clickable to filter heat map
            category_name = "Shooting Stats"
            shots = player.get("shots", 0) or 0
            sot = player.get("shots_on_target", 0) or 0
            goals = player.get("goals", 0) or 0
            xg = player.get("total_xg", 0) or 0
            sot_pct = round((sot / shots * 100) if shots > 0 else 0, 1)
            conversion = round((goals / shots * 100) if shots > 0 else 0, 1)

            stats = [
                ("Total Shots", shots, "shots"),
                ("SOT", sot, "shots_on_target"),
                ("SOT %", f"{sot_pct}%", None),
                ("Goals", goals, "goals"),
                ("xG", xg, "total_xg"),
                ("Conversion", f"{conversion}%", None),
                ("PV Shooting", player.get('pv_shooting', 0) or 0, "pv_shooting"),
            ]
        elif heatmap_type == "Defensive":
            # Defensive stats - all clickable to filter heat map
            category_name = "Defensive Stats"
            stats = [
                ("Def Actions", player.get("defensive_actions", 0), "defensive_actions"),
                ("Tackles", player.get("tackles", 0), "tackles"),
                ("Interceptions", player.get("interceptions", 0), "interceptions"),
                ("Clearances", player.get("clearances", 0), "clearances"),
                ("Recoveries", player.get("ball_recoveries", 0), "ball_recoveries"),
                ("PV Defending", player.get('pv_defending', 0) or 0, "pv_defending"),
            ]
        else:
            # Overall Stats (default) - Mins, Games Played, Games Started, Goals, Assists, Total Actions
            category_name = "Overall Stats"
            games_played = player.get("gp", 0) or 0
            games_started = player.get("gs", 0) or 0
            mins = player.get("mins", 0) or 0
            total_actions = (player.get("passes", 0) or 0) + (player.get("carries", 0) or 0) + (player.get("defensive_actions", 0) or 0)
            stats = [
                ("Mins", mins, "mins"),
                ("Games Played", games_played, "gp"),
                ("Games Started", games_started, "gs"),
                ("Goals", player.get("goals", 0), "goals"),
                ("Int. Assists", player.get("assists", 0), "assists"),
                ("Total Actions", total_actions, "total_actions"),
            ]
            # Disable per 90 for overall stats
            is_per_90 = False

        items = []

        # Add category header if showing category-specific stats
        if category_name:
            items.append(ui.div(category_name, class_="stats-category-header"))

        stat_items_html = ""
        # Stats that should always show 2 decimal places
        decimal_stats = ['pv_passing', 'pv_carrying', 'pv_receiving', 'pv_defending', 'pv_shooting', 'pv_total', 'xg_assisted', 'total_xg']

        for stat_tuple in stats:
            label, raw_value, stat_key = stat_tuple

            # Apply per 90 formatting if enabled and value is numeric
            if is_per_90 and stat_key and isinstance(raw_value, (int, float)):
                value = f"{get_per_90_value(raw_value):.2f}"
            elif stat_key in decimal_stats and isinstance(raw_value, (int, float)):
                # Always format decimal stats with 2 decimal places
                value = f"{raw_value:.2f}"
            elif isinstance(raw_value, (int, float)) and not isinstance(raw_value, bool):
                value = str(int(raw_value)) if raw_value == int(raw_value) else f"{raw_value:.2f}"
            else:
                value = str(raw_value) if raw_value is not None else "0"

            # Get percentile if available (use per90 percentiles when in per 90 mode)
            percentile_html = ""
            if stat_key:
                if is_per_90:
                    pct = player.get(f"{stat_key}_per90_percentile")
                else:
                    pct = player.get(f"{stat_key}_percentile")
                if pct is not None:
                    percentile_html = f'<span class="percentile">{format_percentile(pct)}</span>'

            # Get stat info for tooltip and clickability
            stat_info = STAT_INFO.get(stat_key, {"tooltip": "", "clickable": False})
            tooltip = stat_info.get("tooltip", "")
            is_clickable = stat_info.get("clickable", False)
            viz_type = stat_info.get("viz_type", "")

            # Determine if this stat is currently active
            is_active = current_viz == viz_type if viz_type else False

            clickable_class = " clickable" if is_clickable else ""
            active_class = " active" if is_active else ""
            data_attr = f'data-viz="{viz_type}"' if is_clickable else ""

            stat_items_html += f'''
                <div class="stat-item{clickable_class}{active_class}" {data_attr}>
                    <div class="stat-label">{label}</div>
                    <div class="stat-value">{value}{percentile_html}</div>
                    <span class="stat-tooltip">{tooltip}</span>
                </div>
            '''

        items.append(ui.HTML(f'<div class="stat-grid">{stat_items_html}</div>'))

        # Add JavaScript for click handling
        items.append(ui.tags.script("""
            document.querySelectorAll('.stat-item.clickable').forEach(function(item) {
                item.addEventListener('click', function() {
                    var viz = this.getAttribute('data-viz');
                    var isActive = this.classList.contains('active');

                    // Remove active from all stat items
                    document.querySelectorAll('.stat-item').forEach(function(el) {
                        el.classList.remove('active');
                    });

                    // Toggle or set new visualization
                    if (!isActive && viz) {
                        this.classList.add('active');
                        Shiny.setInputValue('stat_viz_click', viz, {priority: 'event'});
                    } else {
                        Shiny.setInputValue('stat_viz_click', null, {priority: 'event'});
                    }
                });
            });
        """))

        return ui.div(*items)

    # Handle stat visualization clicks
    @reactive.effect
    @reactive.event(input.stat_viz_click)
    def _():
        stat_visualization.set(input.stat_viz_click())


    def render_trajectory_viz(player_id, viz_type, game_filter=None, accent_color=None):
        """Render trajectory visualization with comet effect (line from start to end)."""
        from matplotlib.collections import LineCollection

        if accent_color is None:
            accent_color = ACCENT_GREEN

        # Define which event types and filters to use for each viz_type
        VIZ_CONFIG = {
            "key_passes": {"event_type": "Pass", "filter": lambda e: e.get("is_keypass", False), "title": "Key Passes", "needs_end": True},
            "assists": {"event_type": "Pass", "filter": lambda e: e.get("is_keypass", False), "title": "Assists", "needs_end": True},  # Approximation
            "all_carries": {"event_type": "Carry", "filter": lambda e: True, "title": "Carries", "needs_end": True},
            "carries": {"event_type": "Carry", "filter": lambda e: True, "title": "Carries", "needs_end": True},
            "clearances": {"event_type": "Clearance", "filter": lambda e: True, "title": "Clearances", "needs_end": False},
            "tackles": {"event_type": "Tackle", "filter": lambda e: True, "title": "Tackles", "needs_end": False},
            "interceptions": {"event_type": "Interception", "filter": lambda e: True, "title": "Interceptions", "needs_end": False},
            "recoveries": {"event_type": "BallRecovery", "filter": lambda e: True, "title": "Ball Recoveries", "needs_end": False},
            "goals": {"event_type": "Goal", "filter": lambda e: True, "title": "Goals", "needs_end": False},
            # Shot-related visualizations
            "all_shots": {"event_type": ["Shot", "MissedShots", "SavedShot", "ShotOnPost", "Goal"], "filter": lambda e: True, "title": "All Shots", "needs_end": False},
            "shots_on_target": {"event_type": ["SavedShot", "Goal"], "filter": lambda e: True, "title": "Shots on Target", "needs_end": False},
            # Defensive visualizations
            "all_defensive": {"event_type": ["Tackle", "Interception", "Clearance", "BallRecovery"], "filter": lambda e: True, "title": "Defensive Actions", "needs_end": False},
            # Pass-related visualizations
            "all_passes": {"event_type": "Pass", "filter": lambda e: True, "title": "All Passes", "needs_end": True},
            "progressive_passes": {"event_type": "Pass", "filter": lambda e: e.get("is_progressive_pass", False), "title": "Progressive Passes", "needs_end": True},
            "final_third_passes": {"event_type": "Pass", "filter": lambda e: e.get("is_final_third_pass", False), "title": "Final Third Passes", "needs_end": True},
            "deep_passes": {"event_type": "Pass", "filter": lambda e: e.get("is_deep_pass", False), "title": "Deep Passes", "needs_end": True},
            # Carry-related visualizations
            "final_third_carries": {"event_type": "Carry", "filter": lambda e: e.get("is_final_third_carry", False), "title": "Final Third Carries", "needs_end": True},
            "deep_carries": {"event_type": "Carry", "filter": lambda e: e.get("is_deep_carry", False), "title": "Deep Carries", "needs_end": True},
            "progressive_carries": {"event_type": "Carry", "filter": lambda e: e.get("is_progressive_carry", False), "title": "Progressive Carries", "needs_end": True},
            # Reception visualizations
            "all_receptions": {"event_type": "Reception", "filter": lambda e: True, "title": "Receptions", "needs_end": False},
            "final_third_receptions": {"event_type": "Reception", "filter": lambda e: e.get("x", 0) >= 66.67, "title": "Final Third Receptions", "needs_end": False},
            "deep_receptions": {"event_type": "Reception", "filter": lambda e: e.get("x", 0) >= 83.33, "title": "Deep Receptions", "needs_end": False},
        }

        config = VIZ_CONFIG.get(viz_type)
        if not config:
            return ui.p(f"Unknown visualization type", style=f"color: {SUBTEXT_COLOR};")

        # Filter events - handle both single event type and list of event types
        event_types = config["event_type"]
        if isinstance(event_types, str):
            event_types = [event_types]

        events = [e for e in EVENTS_DATA
                  if e["player_id"] == player_id
                  and e["type_display_name"] in event_types
                  and config["filter"](e)
                  and e["x"] is not None and e["y"] is not None]

        # Apply game filter if specified
        if game_filter:
            events = [e for e in events if str(e.get("match_id")) == str(game_filter)]

        if config["needs_end"]:
            events = [e for e in events if e.get("end_x") is not None and e.get("end_y") is not None]

        if len(events) < 1:
            return ui.p(f"No {config['title'].lower()} data available", style=f"color: {SUBTEXT_COLOR};")

        # Create pitch
        HEATMAP_BG = "#000000"
        fig, ax = plt.subplots(figsize=(10, 7), facecolor=HEATMAP_BG)
        ax.set_facecolor(HEATMAP_BG)

        P_WIDTH = 120
        P_HEIGHT = 80

        if config["needs_end"]:
            # Draw trajectory lines with comet effect
            for e in events:
                start_x = e["x"] * P_WIDTH / 100
                start_y = e["y"] * P_HEIGHT / 100
                end_x = e["end_x"] * P_WIDTH / 100
                end_y = e["end_y"] * P_HEIGHT / 100

                # Clip to pitch bounds
                start_x = np.clip(start_x, 0.1, P_WIDTH - 0.1)
                start_y = np.clip(start_y, 0.1, P_HEIGHT - 0.1)
                end_x = np.clip(end_x, 0.1, P_WIDTH - 0.1)
                end_y = np.clip(end_y, 0.1, P_HEIGHT - 0.1)

                # Check if this is an unsuccessful outcome
                is_unsuccessful = e.get("outcome_type_display_name") == "Unsuccessful"
                # Use grey for unsuccessful, accent color for successful
                comet_color = '#666666' if is_unsuccessful else accent_color

                # Create comet effect - line that fades from start to end
                # Draw multiple segments with increasing alpha
                n_segments = 10
                alphas = np.linspace(0.1, 0.8, n_segments)
                widths = np.linspace(1, 3, n_segments)

                for i in range(n_segments):
                    t1 = i / n_segments
                    t2 = (i + 1) / n_segments
                    x1 = start_x + (end_x - start_x) * t1
                    y1 = start_y + (end_y - start_y) * t1
                    x2 = start_x + (end_x - start_x) * t2
                    y2 = start_y + (end_y - start_y) * t2
                    ax.plot([x1, x2], [y1, y2], color=comet_color, alpha=alphas[i],
                            linewidth=widths[i], solid_capstyle='round', zorder=2)

                # Draw start point (small circle)
                if is_unsuccessful:
                    ax.scatter(start_x, start_y, s=30, c='#666666', alpha=0.5,
                              edgecolors='none', zorder=3)
                else:
                    ax.scatter(start_x, start_y, s=30, c=accent_color, alpha=0.5,
                              edgecolors='none', zorder=3)

                # Draw end point (larger circle)
                if is_unsuccessful:
                    ax.scatter(end_x, end_y, s=80, c='#666666', alpha=0.7,
                              edgecolors='none', zorder=4)
                else:
                    ax.scatter(end_x, end_y, s=80, c=accent_color, alpha=0.9,
                              edgecolors='white', linewidth=1, zorder=4)
        else:
            # Just show points for events without end coordinates
            for e in events:
                ex = e["x"] * P_WIDTH / 100
                ey = e["y"] * P_HEIGHT / 100
                ex = np.clip(ex, 0.1, P_WIDTH - 0.1)
                ey = np.clip(ey, 0.1, P_HEIGHT - 0.1)

                # Check if this is an unsuccessful outcome
                is_unsuccessful = e.get("outcome_type_display_name") == "Unsuccessful"

                if viz_type == "goals":
                    # Show goals as stars
                    ax.scatter(ex, ey, s=200, c=accent_color, marker='*',
                              edgecolors='white', linewidth=1.5, zorder=3)
                elif is_unsuccessful:
                    # Unsuccessful outcomes: grey
                    ax.scatter(ex, ey, s=100, c='#666666', alpha=0.7,
                              edgecolors='none', zorder=3)
                else:
                    ax.scatter(ex, ey, s=100, c=accent_color, alpha=0.8,
                              edgecolors='white', linewidth=1, zorder=3)

        # Draw pitch lines
        lw = 2
        line_col = "#ffffff"

        rect = plt.Rectangle((0, 0), P_WIDTH, P_HEIGHT, fill=False,
                              edgecolor=line_col, linewidth=lw, zorder=10)
        ax.add_patch(rect)

        ax.plot([P_WIDTH/2, P_WIDTH/2], [0, P_HEIGHT], color=line_col, lw=lw, zorder=10)

        circle = plt.Circle((P_WIDTH/2, P_HEIGHT/2), 10, fill=False, color=line_col, lw=lw, zorder=10)
        ax.add_patch(circle)
        ax.scatter(P_WIDTH/2, P_HEIGHT/2, s=25, color=line_col, zorder=10)

        box_depth = 18
        box_height = 44
        box_top = (P_HEIGHT - box_height) / 2

        ax.plot([0, box_depth, box_depth, 0],
                [box_top, box_top, box_top + box_height, box_top + box_height],
                color=line_col, lw=lw, zorder=10)
        ax.plot([P_WIDTH, P_WIDTH - box_depth, P_WIDTH - box_depth, P_WIDTH],
                [box_top, box_top, box_top + box_height, box_top + box_height],
                color=line_col, lw=lw, zorder=10)

        six_depth = 6
        six_height = 20
        six_top = (P_HEIGHT - six_height) / 2

        ax.plot([0, six_depth, six_depth, 0],
                [six_top, six_top, six_top + six_height, six_top + six_height],
                color=line_col, lw=lw, zorder=10)
        ax.plot([P_WIDTH, P_WIDTH - six_depth, P_WIDTH - six_depth, P_WIDTH],
                [six_top, six_top, six_top + six_height, six_top + six_height],
                color=line_col, lw=lw, zorder=10)

        ax.scatter(12, P_HEIGHT/2, s=25, color=line_col, zorder=10)
        ax.scatter(P_WIDTH - 12, P_HEIGHT/2, s=25, color=line_col, zorder=10)

        ax.set_xlim(-1, P_WIDTH + 1)
        ax.set_ylim(-1, P_HEIGHT + 1)
        ax.set_aspect('equal')
        ax.axis('off')

        ax.set_title(f"{config['title']}: {len(events)} events", color=SUBTEXT_COLOR, fontsize=10, pad=5)

        img_data = fig_to_base64(fig, dpi=100)

        return ui.HTML(f'<img src="data:image/png;base64,{img_data}" style="width: 100%; display: block; margin: 0 auto;">')


    @output
    @render.ui
    def location_toggle_ui():
        """Render the Start/End Location toggle for Pass/Carry."""
        heatmap_type = input.heatmap_type()

        # Only show for Pass and Carry
        if heatmap_type not in ["Pass", "Carry"]:
            return None

        current_location = location_toggle.get()

        # Determine accent color based on team selection
        is_defiance = input.team_select() == "defiance"
        accent_color = DEFIANCE_BLUE if is_defiance else ACCENT_GREEN

        # Create toggle buttons
        start_style = f"background: {accent_color}; color: #000; font-weight: bold;" if current_location == "start" else f"background: transparent; color: {TEXT_COLOR}; border: 1px solid #444;"
        end_style = f"background: {accent_color}; color: #000; font-weight: bold;" if current_location == "end" else f"background: transparent; color: {TEXT_COLOR}; border: 1px solid #444;"

        return ui.div(
            ui.div(
                ui.input_action_button("loc_start", "Start Location", style=f"{start_style} padding: 4px 12px; border-radius: 4px; margin-right: 8px; font-size: 12px; cursor: pointer;"),
                ui.input_action_button("loc_end", "End Location", style=f"{end_style} padding: 4px 12px; border-radius: 4px; font-size: 12px; cursor: pointer;"),
                style="display: flex; align-items: center; margin-top: 15px; margin-bottom: 10px;"
            )
        )


    @reactive.effect
    @reactive.event(input.loc_start)
    def _set_location_start():
        location_toggle.set("start")


    @reactive.effect
    @reactive.event(input.loc_end)
    def _set_location_end():
        location_toggle.set("end")


    @reactive.effect
    @reactive.event(input.toggle_trajectories)
    def _toggle_trajectories():
        show_trajectories.set(not show_trajectories.get())


    @output
    @render.ui
    def heatmap_mode_toggle():
        """Render the Action vs Trajectories vs Density toggle below the action map."""
        current_mode = heatmap_mode.get()

        # Determine accent color based on team selection
        is_defiance = input.team_select() == "defiance"
        accent_color = DEFIANCE_BLUE if is_defiance else ACCENT_GREEN

        action_style = f"background: {accent_color}; color: #000; font-weight: bold;" if current_mode == "action" else f"background: transparent; color: {TEXT_COLOR}; border: 1px solid #444;"
        traj_style = f"background: {accent_color}; color: #000; font-weight: bold;" if current_mode == "trajectory" else f"background: transparent; color: {TEXT_COLOR}; border: 1px solid #444;"
        kde_style = f"background: {accent_color}; color: #000; font-weight: bold;" if current_mode == "kde" else f"background: transparent; color: {TEXT_COLOR}; border: 1px solid #444;"

        return ui.div(
            ui.div(
                ui.input_action_button("mode_action", "Action", style=f"{action_style} padding: 4px 12px; border-radius: 4px; margin-right: 8px; font-size: 12px; cursor: pointer;"),
                ui.input_action_button("mode_trajectory", "Trajectories", style=f"{traj_style} padding: 4px 12px; border-radius: 4px; margin-right: 8px; font-size: 12px; cursor: pointer;"),
                ui.input_action_button("mode_kde", "Density", style=f"{kde_style} padding: 4px 12px; border-radius: 4px; font-size: 12px; cursor: pointer;"),
                style="display: flex; align-items: center; margin-top: 10px;"
            )
        )


    @reactive.effect
    @reactive.event(input.mode_action)
    def _set_mode_action():
        heatmap_mode.set("action")

    @reactive.effect
    @reactive.event(input.mode_trajectory)
    def _set_mode_trajectory():
        heatmap_mode.set("trajectory")

    @reactive.effect
    @reactive.event(input.mode_kde)
    def _set_mode_kde():
        heatmap_mode.set("kde")


    @output
    @render.ui
    def action_map_export_btn():
        """Render export button for action map."""
        name = selected_player.get()
        if not name:
            return None

        # Determine accent color based on team selection
        is_defiance = input.team_select() == "defiance"
        accent_color = DEFIANCE_BLUE if is_defiance else ACCENT_GREEN

        return ui.download_button(
            "export_action_map",
            "Export",
            style=f"background: {accent_color}; color: #000; border: none; padding: 6px 14px; border-radius: 4px; font-weight: bold; cursor: pointer; font-size: 12px;"
        )


    @output
    @render.ui
    def events_key_legend():
        """Render the events key/legend under the action map."""
        name = selected_player.get()
        if not name:
            return None

        # Determine accent color based on team selection
        is_defiance = input.team_select() == "defiance"
        accent_color = DEFIANCE_BLUE if is_defiance else ACCENT_GREEN

        # Build legend HTML with colored circles
        legend_html = f'''
        <div style="display: flex; gap: 20px; align-items: center; margin-top: 10px; padding: 8px 12px; background: rgba(255,255,255,0.03); border-radius: 6px;">
            <div style="display: flex; align-items: center; gap: 6px;">
                <div style="width: 12px; height: 12px; border-radius: 50%; background: {accent_color}; opacity: 0.8;"></div>
                <span style="color: {SUBTEXT_COLOR}; font-size: 11px;">Successful</span>
            </div>
            <div style="display: flex; align-items: center; gap: 6px;">
                <div style="width: 12px; height: 12px; border-radius: 50%; background: #666666;"></div>
                <span style="color: {SUBTEXT_COLOR}; font-size: 11px;">Unsuccessful</span>
            </div>
            <div style="display: flex; align-items: center; gap: 6px;">
                <div style="width: 14px; height: 14px; color: {accent_color}; font-size: 14px; line-height: 1; -webkit-text-stroke: 1px white; text-shadow: 0 0 2px white;">&#9733;</div>
                <span style="color: {SUBTEXT_COLOR}; font-size: 11px;">Goal</span>
            </div>
        </div>
        '''
        return ui.HTML(legend_html)


    @render.download(filename=lambda: f"{selected_player.get() or 'player'}_{input.heatmap_type().lower()}_action_map.png")
    async def export_action_map():
        """Export current action map as PNG with player info and stats."""
        from io import BytesIO
        from matplotlib.patches import FancyBboxPatch, Circle
        import matplotlib.gridspec as gridspec
        from matplotlib.offsetbox import OffsetImage, AnnotationBbox
        from PIL import Image
        import urllib.request

        name = selected_player.get()
        if not name:
            yield b""
            return

        player = get_player_data(name)
        if not player:
            yield b""
            return

        # Get player entry from depth chart for photo URL
        player_entry = None
        for pos, players in DEPTH_CHART.items():
            for p in players:
                if p["name"] == name:
                    player_entry = p
                    break
            if player_entry:
                break
        if not player_entry:
            for pos, players in DEFIANCE_DEPTH_CHART.items():
                for p in players:
                    if p["name"] == name:
                        player_entry = p
                        break
                if player_entry:
                    break

        player_id = player.get("player_id")
        heatmap_type = input.heatmap_type()
        viz_type = stat_visualization.get()
        game_filter = selected_game.get()
        loc_toggle = location_toggle.get()
        current_heatmap_mode = heatmap_mode.get()
        draw_trajectories = current_heatmap_mode == "trajectory"

        # Determine title based on what's being shown
        if viz_type:
            # Get title from VIZ_CONFIG
            VIZ_TITLES = {
                "key_passes": "Key Passes", "assists": "Assists", "all_carries": "Carries",
                "carries": "Carries", "clearances": "Clearances", "tackles": "Tackles",
                "interceptions": "Interceptions", "recoveries": "Ball Recoveries", "goals": "Goals",
                "all_shots": "All Shots", "shots_on_target": "Shots on Target",
                "all_defensive": "Defensive Actions", "all_passes": "All Passes",
                "progressive_passes": "Progressive Passes", "final_third_passes": "Final Third Passes",
                "deep_passes": "Deep Passes", "final_third_carries": "Final Third Carries",
                "deep_carries": "Deep Carries", "progressive_carries": "Progressive Carries",
                "all_receptions": "Receptions", "final_third_receptions": "Final Third Receptions",
                "deep_receptions": "Deep Receptions"
            }
            map_title = VIZ_TITLES.get(viz_type, viz_type.replace("_", " ").title())
        else:
            loc_label = "End Location" if loc_toggle == "end" else "Start Location"
            map_title = f"{heatmap_type} - {loc_label}"

        # Get game context for title
        if game_filter:
            match_info = MATCH_LOOKUP.get(str(game_filter), {})
            opponent = match_info.get('opponent', 'Unknown')
            match_date = match_info.get('start_date', '')
            game_context = f"vs {opponent} ({match_date})"
        else:
            game_context = "2025 Season"

        # Determine accent color based on team selection
        is_defiance = input.team_select() == "defiance"
        accent_color = DEFIANCE_BLUE if is_defiance else ACCENT_GREEN

        # Create figure with header, pitch, and stats below
        # No headshot image - just the pitch with stats underneath
        fig = plt.figure(figsize=(12, 9), facecolor='#0a0a0a')

        # Header area - left aligned (no player image)
        header_left = 0.05

        # Player name and title - left aligned
        fig.text(header_left, 0.96, f"{player['name']} - {map_title}", fontsize=18, fontweight='bold',
                ha='left', color=accent_color)
        fig.text(header_left, 0.93, game_context, fontsize=12, ha='left', color=TEXT_COLOR)

        # Position and basic info
        position = player.get('primary_general_position', player.get('position', 'N/A'))
        age = player.get('age', 'N/A')
        fig.text(header_left, 0.90, f"#{player.get('shirt_no', '-')} | {position} | Age {age}",
                fontsize=10, ha='left', color=SUBTEXT_COLOR)

        # Create pitch subplot - more space now without headshot, stats go below
        ax = fig.add_axes([0.05, 0.18, 0.9, 0.70])
        ax.set_facecolor('#000000')

        P_WIDTH, P_HEIGHT = 120, 80

        # Get events for visualization
        use_destination = heatmap_type in ["Pass", "Carry"] and loc_toggle == "end"

        if viz_type:
            # Use viz_type to filter events
            VIZ_CONFIG_EXPORT = {
                "key_passes": ("Pass", lambda e: e.get("is_keypass", False)),
                "assists": ("Pass", lambda e: e.get("is_keypass", False)),
                "all_carries": ("Carry", lambda e: True),
                "carries": ("Carry", lambda e: True),
                "all_passes": ("Pass", lambda e: True),
                "progressive_passes": ("Pass", lambda e: e.get("is_progressive_pass", False)),
                "final_third_passes": ("Pass", lambda e: e.get("is_final_third_pass", False)),
                "deep_passes": ("Pass", lambda e: e.get("is_deep_pass", False)),
                "final_third_carries": ("Carry", lambda e: e.get("is_final_third_carry", False)),
                "deep_carries": ("Carry", lambda e: e.get("is_deep_carry", False)),
                "progressive_carries": ("Carry", lambda e: e.get("is_progressive_carry", False)),
            }
            if viz_type in VIZ_CONFIG_EXPORT:
                evt_type, evt_filter = VIZ_CONFIG_EXPORT[viz_type]
                events = [e for e in EVENTS_DATA if e["player_id"] == player_id
                         and e["type_display_name"] == evt_type and evt_filter(e)
                         and e["x"] is not None and e["y"] is not None]
            else:
                # Handle other viz types (shots, defensive, receptions)
                evt_map = {
                    "goals": ["Goal"], "all_shots": ["Shot", "MissedShots", "SavedShot", "ShotOnPost", "Goal"],
                    "shots_on_target": ["SavedShot", "Goal"],
                    "all_defensive": ["Tackle", "Interception", "Clearance", "BallRecovery"],
                    "tackles": ["Tackle"], "interceptions": ["Interception"],
                    "clearances": ["Clearance"], "recoveries": ["BallRecovery"],
                    "all_receptions": ["Reception"],
                    "final_third_receptions": ["Reception"], "deep_receptions": ["Reception"]
                }
                evt_types = evt_map.get(viz_type, [viz_type])
                events = [e for e in EVENTS_DATA if e["player_id"] == player_id
                         and e["type_display_name"] in evt_types
                         and e["x"] is not None and e["y"] is not None]
                # Filter for zone-based receptions
                if viz_type == "final_third_receptions":
                    events = [e for e in events if e.get("x", 0) >= 66.67]
                elif viz_type == "deep_receptions":
                    events = [e for e in events if e.get("x", 0) >= 83.33]
        else:
            # Use heatmap_type
            evt_map = {"Pass": ["Pass"], "Carry": ["Carry"], "Reception": ["Reception"],
                      "Shot": ["Shot", "MissedShots", "SavedShot", "ShotOnPost", "Goal"],
                      "Defensive": ["Tackle", "Interception", "Clearance", "BallRecovery"],
                      "Overview": ["Pass", "Carry", "Reception", "Shot", "MissedShots", "SavedShot", "ShotOnPost", "Goal", "Tackle", "Interception", "Clearance", "BallRecovery"]}
            evt_types = evt_map.get(heatmap_type, [heatmap_type])
            events = [e for e in EVENTS_DATA if e["player_id"] == player_id
                     and e["type_display_name"] in evt_types
                     and e["x"] is not None and e["y"] is not None]

        # Apply game filter
        if game_filter:
            events = [e for e in events if str(e.get("match_id")) == str(game_filter)]

        # Plot events - match the heatmap display logic
        if events:
            if use_destination:
                xs = np.array([e["end_x"] * P_WIDTH / 100 for e in events if e.get("end_x") is not None])
                ys = np.array([e["end_y"] * P_HEIGHT / 100 for e in events if e.get("end_y") is not None])
            else:
                xs = np.array([e["x"] * P_WIDTH / 100 for e in events])
                ys = np.array([e["y"] * P_HEIGHT / 100 for e in events])

            xs = np.clip(xs, 0.1, P_WIDTH - 0.1)
            ys = np.clip(ys, 0.1, P_HEIGHT - 0.1)

            if current_heatmap_mode == "kde" and len(xs) >= 3:
                # KDE Heat Map mode - show density as color gradient
                try:
                    from scipy.stats import gaussian_kde
                    from matplotlib.colors import LinearSegmentedColormap
                    xy = np.vstack([xs, ys])
                    kde = gaussian_kde(xy, bw_method=0.15)
                    x_grid = np.linspace(0, P_WIDTH, 100)
                    y_grid = np.linspace(0, P_HEIGHT, 70)
                    X, Y = np.meshgrid(x_grid, y_grid)
                    positions = np.vstack([X.ravel(), Y.ravel()])
                    Z = kde(positions).reshape(X.shape)
                    if is_defiance:
                        # Blue colormap for Defiance
                        colors = ['#000000', '#1a3d4d', '#2d5a6d', '#3d7a8d', '#4d9aad', '#5BC0EB']
                    else:
                        # Green colormap for Sounders
                        colors = ['#000000', '#1a3d1a', '#2d5a2d', '#3d7a3d', '#5D9741', '#96D35F']
                    cmap = LinearSegmentedColormap.from_list('team_heat', colors)
                    ax.contourf(X, Y, Z, levels=20, cmap=cmap, alpha=0.8, zorder=1)
                except Exception:
                    ax.scatter(xs, ys, s=100, c=accent_color, alpha=0.7, edgecolors='white', linewidth=0.5, zorder=2)
            else:
                # Action mode - show individual dots with density-based alpha
                n_bins_x, n_bins_y = 24, 16
                H, _, _ = np.histogram2d(xs, ys, bins=[n_bins_x, n_bins_y], range=[[0, P_WIDTH], [0, P_HEIGHT]])
                max_count = H.max() if H.max() > 0 else 1

                is_shots_heatmap = heatmap_type == "Shot"
                can_draw_trajectories = draw_trajectories

                for e in events:
                    if use_destination:
                        ex = e["end_x"] * P_WIDTH / 100 if e.get("end_x") else 0
                        ey = e["end_y"] * P_HEIGHT / 100 if e.get("end_y") else 0
                    else:
                        ex = e["x"] * P_WIDTH / 100
                        ey = e["y"] * P_HEIGHT / 100
                    ex = np.clip(ex, 0.1, P_WIDTH - 0.1)
                    ey = np.clip(ey, 0.1, P_HEIGHT - 0.1)

                    bin_x = min(int(ex / P_WIDTH * n_bins_x), n_bins_x - 1)
                    bin_y = min(int(ey / P_HEIGHT * n_bins_y), n_bins_y - 1)
                    density = H[bin_x, bin_y]
                    alpha = 0.15 + 0.75 * (density / max_count) ** 0.5

                    # Check if this is an unsuccessful outcome
                    is_unsuccessful = e.get("outcome_type_display_name") == "Unsuccessful"
                    # Use grey for unsuccessful, accent color for successful
                    comet_color = '#666666' if is_unsuccessful else accent_color

                    # Draw trajectory comets if enabled
                    if can_draw_trajectories and e.get("x") is not None and e.get("end_x") is not None:
                        start_x = e["x"] * P_WIDTH / 100
                        start_y = e["y"] * P_HEIGHT / 100
                        end_x = e["end_x"] * P_WIDTH / 100
                        end_y = e["end_y"] * P_HEIGHT / 100
                        n_segments = 10
                        for seg in range(n_segments):
                            t0, t1 = seg / n_segments, (seg + 1) / n_segments
                            x0 = start_x + t0 * (end_x - start_x)
                            y0 = start_y + t0 * (end_y - start_y)
                            x1 = start_x + t1 * (end_x - start_x)
                            y1 = start_y + t1 * (end_y - start_y)
                            lw_seg = 0.5 + 3.5 * t1
                            alpha_seg = 0.1 + 0.3 * t1
                            ax.plot([x0, x1], [y0, y1], color=comet_color, lw=lw_seg, alpha=alpha_seg, zorder=1)

                    # Goals shown as stars
                    if is_shots_heatmap and e.get("type_display_name") == "Goal":
                        ax.scatter(ex, ey, s=220, c=accent_color, marker='*', edgecolors='white', linewidth=1.5, zorder=3)
                    elif is_unsuccessful:
                        # Unsuccessful outcomes: grey
                        ax.scatter(ex, ey, s=100, c='#666666', alpha=0.7, edgecolors='none', zorder=2)
                    else:
                        ax.scatter(ex, ey, s=100, c=accent_color, alpha=alpha, edgecolors='none', zorder=2)

        # Draw pitch lines
        lw = 2
        line_col = "#ffffff"
        rect = plt.Rectangle((0, 0), P_WIDTH, P_HEIGHT, fill=False, edgecolor=line_col, linewidth=lw, zorder=10)
        ax.add_patch(rect)
        ax.plot([P_WIDTH/2, P_WIDTH/2], [0, P_HEIGHT], color=line_col, lw=lw, zorder=10)
        circle = plt.Circle((P_WIDTH/2, P_HEIGHT/2), 10, fill=False, color=line_col, lw=lw, zorder=10)
        ax.add_patch(circle)
        ax.scatter(P_WIDTH/2, P_HEIGHT/2, s=25, color=line_col, zorder=10)

        # Penalty areas
        box_depth, box_height = 18, 44
        box_top = (P_HEIGHT - box_height) / 2
        ax.plot([0, box_depth, box_depth, 0], [box_top, box_top, box_top + box_height, box_top + box_height],
               color=line_col, lw=lw, zorder=10)
        ax.plot([P_WIDTH, P_WIDTH - box_depth, P_WIDTH - box_depth, P_WIDTH],
               [box_top, box_top, box_top + box_height, box_top + box_height], color=line_col, lw=lw, zorder=10)

        # 6-yard boxes
        six_depth, six_height = 6, 20
        six_top = (P_HEIGHT - six_height) / 2
        ax.plot([0, six_depth, six_depth, 0], [six_top, six_top, six_top + six_height, six_top + six_height],
               color=line_col, lw=lw, zorder=10)
        ax.plot([P_WIDTH, P_WIDTH - six_depth, P_WIDTH - six_depth, P_WIDTH],
               [six_top, six_top, six_top + six_height, six_top + six_height], color=line_col, lw=lw, zorder=10)

        ax.scatter(12, P_HEIGHT/2, s=25, color=line_col, zorder=10)
        ax.scatter(P_WIDTH - 12, P_HEIGHT/2, s=25, color=line_col, zorder=10)

        ax.set_xlim(-1, P_WIDTH + 1)
        ax.set_ylim(-1, P_HEIGHT + 1)
        ax.set_aspect('equal')
        ax.axis('off')

        # Get stats for this player (game-specific or season)
        stats_player = player.copy()
        if game_filter:
            game_stats = get_game_stats(player_id, game_filter)
            if game_stats:
                stats_player = {**player, **game_stats}

        # Build stats line based on heatmap type
        if heatmap_type == "Pass" or (viz_type and "pass" in viz_type.lower()):
            total_p = stats_player.get("total_passes", 0) or 0
            succ_p = stats_player.get("passes", 0) or 0
            pass_pct = round((succ_p / total_p * 100) if total_p > 0 else 0, 1)
            stats_text = f"Passes: {total_p} ({pass_pct}%) | Key Passes: {stats_player.get('key_passes', 0)} | Prog: {stats_player.get('progressive_passes', 0)}"
        elif heatmap_type == "Carry" or (viz_type and "carr" in viz_type.lower()):
            stats_text = f"Carries: {stats_player.get('carries', 0)} | Final 3rd: {stats_player.get('final_third_carries', 0)} | Progressive: {stats_player.get('progressive_carries', 0)}"
        elif heatmap_type == "Shot" or (viz_type and "shot" in viz_type.lower()) or (viz_type and "goal" in viz_type.lower()):
            shots = stats_player.get("shots", 0) or 0
            goals = stats_player.get("goals", 0) or 0
            stats_text = f"Shots: {shots} | Goals: {goals} | SOT: {stats_player.get('shots_on_target', 0)}"
        elif heatmap_type == "Defensive" or (viz_type and "defen" in viz_type.lower()) or (viz_type and "tackle" in viz_type.lower()) or (viz_type and "intercept" in viz_type.lower()):
            stats_text = f"Tackles: {stats_player.get('tackles', 0)} | Interceptions: {stats_player.get('interceptions', 0)} | Recoveries: {stats_player.get('ball_recoveries', 0)}"
        elif heatmap_type == "Reception" or (viz_type and "recep" in viz_type.lower()):
            stats_text = f"Receptions: {stats_player.get('receptions', 0)} | Final 3rd: {stats_player.get('final_third_receptions', 0)} | Deep: {stats_player.get('deep_receptions', 0)}"
        else:
            stats_text = f"Mins: {stats_player.get('mins', 0)} | Goals: {stats_player.get('goals', 0)} | Assists: {stats_player.get('assists', 0)}"

        # Event count and detailed stats - below the pitch
        fig.text(header_left, 0.12, f"{len(events)} events", fontsize=11, ha='left', color=TEXT_COLOR, fontweight='bold')
        fig.text(header_left, 0.08, stats_text, fontsize=10, ha='left', color=SUBTEXT_COLOR)

        # Footer - left aligned
        fig.text(header_left, 0.02, "Data from Opta | Powered by Sunday League Stats", fontsize=8, ha='left', color='#666')

        # Save to buffer
        buf = BytesIO()
        fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor(), edgecolor='none')
        buf.seek(0)
        plt.close(fig)
        yield buf.getvalue()


    @output
    @render.ui
    def heatmap_display():
        """Display heat map for selected player, or trajectory viz if stat is clicked."""
        name = selected_player.get()
        heatmap_type = input.heatmap_type()
        viz_type = stat_visualization.get()
        game_filter = selected_game.get()

        if not name:
            return ui.p("Select a player")

        player = get_player_data(name)
        if not player:
            return ui.p("No event data available")

        player_id = player.get("player_id")
        if not player_id:
            return ui.p("Player ID not found")

        # Get location toggle and current mode
        loc_toggle = location_toggle.get()
        current_heatmap_mode = heatmap_mode.get()
        draw_trajectories = current_heatmap_mode == "trajectory"

        # Determine accent color based on team selection
        is_defiance = input.team_select() == "defiance"
        accent_color = DEFIANCE_BLUE if is_defiance else ACCENT_GREEN

        # If viz_type is set (stat clicked), use trajectory mode only if mode is "trajectory"
        if viz_type and current_heatmap_mode == "trajectory":
            return render_trajectory_viz(player_id, viz_type, game_filter, accent_color=accent_color)

        # Determine event type and whether to use origin or destination coordinates
        use_destination = False
        needs_end_coords = False  # For trajectory drawing

        # If viz_type is set, filter based on that instead of heatmap_type
        if viz_type:
            # Use the VIZ_CONFIG to determine filtering
            VIZ_CONFIG_FILTER = {
                "key_passes": {"event_type": ["Pass"], "filter": lambda e: e.get("is_keypass", False), "needs_end": True},
                "assists": {"event_type": ["Pass"], "filter": lambda e: e.get("is_keypass", False), "needs_end": True},
                "all_carries": {"event_type": ["Carry"], "filter": lambda e: True, "needs_end": True},
                "carries": {"event_type": ["Carry"], "filter": lambda e: True, "needs_end": True},
                "all_passes": {"event_type": ["Pass"], "filter": lambda e: True, "needs_end": True},
                "progressive_passes": {"event_type": ["Pass"], "filter": lambda e: e.get("is_progressive_pass", False), "needs_end": True},
                "final_third_passes": {"event_type": ["Pass"], "filter": lambda e: e.get("is_final_third_pass", False), "needs_end": True},
                "deep_passes": {"event_type": ["Pass"], "filter": lambda e: e.get("is_deep_pass", False), "needs_end": True},
                "final_third_carries": {"event_type": ["Carry"], "filter": lambda e: e.get("is_final_third_carry", False), "needs_end": True},
                "deep_carries": {"event_type": ["Carry"], "filter": lambda e: e.get("is_deep_carry", False), "needs_end": True},
                "progressive_carries": {"event_type": ["Carry"], "filter": lambda e: e.get("is_progressive_carry", False), "needs_end": True},
                "goals": {"event_type": ["Goal"], "filter": lambda e: True, "needs_end": False},
                "all_shots": {"event_type": ["Shot", "MissedShots", "SavedShot", "ShotOnPost", "Goal"], "filter": lambda e: True, "needs_end": False},
                "shots_on_target": {"event_type": ["SavedShot", "Goal"], "filter": lambda e: True, "needs_end": False},
                "all_defensive": {"event_type": ["Tackle", "Interception", "Clearance", "BallRecovery"], "filter": lambda e: True, "needs_end": False},
                "tackles": {"event_type": ["Tackle"], "filter": lambda e: True, "needs_end": False},
                "interceptions": {"event_type": ["Interception"], "filter": lambda e: True, "needs_end": False},
                "clearances": {"event_type": ["Clearance"], "filter": lambda e: True, "needs_end": False},
                "recoveries": {"event_type": ["BallRecovery"], "filter": lambda e: True, "needs_end": False},
                "all_receptions": {"event_type": ["Reception"], "filter": lambda e: True, "needs_end": False},
                "final_third_receptions": {"event_type": ["Reception"], "filter": lambda e: e.get("x", 0) >= 66.67, "needs_end": False},
                "deep_receptions": {"event_type": ["Reception"], "filter": lambda e: e.get("x", 0) >= 83.33, "needs_end": False},
            }
            config = VIZ_CONFIG_FILTER.get(viz_type, {"event_type": [], "filter": lambda e: True, "needs_end": False})
            event_types = config["event_type"]
            event_filter = config["filter"]
            needs_end_coords = config["needs_end"]
        elif heatmap_type == "Overview":
            # Show all touch events for overview
            event_types = ["Pass", "Carry", "Reception", "Shot", "MissedShots", "SavedShot", "ShotOnPost", "Goal", "Tackle", "Interception", "Clearance", "BallRecovery"]
            event_filter = lambda e: True
        elif heatmap_type == "Defensive":
            event_types = ["Tackle", "Interception", "Clearance", "BallRecovery"]
            event_filter = lambda e: True
        elif heatmap_type == "Shot":
            event_types = ["Shot", "MissedShots", "SavedShot", "ShotOnPost", "Goal"]
            event_filter = lambda e: True
        elif heatmap_type == "Pass":
            event_types = ["Pass"]
            use_destination = (loc_toggle == "end")
            needs_end_coords = True
            event_filter = lambda e: True
        elif heatmap_type == "Carry":
            event_types = ["Carry"]
            use_destination = (loc_toggle == "end")
            needs_end_coords = True
            event_filter = lambda e: True
        elif heatmap_type == "Reception":
            event_types = ["Reception"]
            event_filter = lambda e: True
        else:
            event_types = [heatmap_type]
            event_filter = lambda e: True

        # Filter events - for destination, also require end_x/end_y
        if use_destination:
            events = [e for e in EVENTS_DATA
                      if e["player_id"] == player_id
                      and e["type_display_name"] in event_types
                      and event_filter(e)
                      and e["end_x"] is not None and e["end_y"] is not None]
        else:
            events = [e for e in EVENTS_DATA
                      if e["player_id"] == player_id
                      and e["type_display_name"] in event_types
                      and event_filter(e)
                      and e["x"] is not None and e["y"] is not None]

        # For needs_end_coords, also filter to ensure we have end coordinates
        if needs_end_coords and not use_destination:
            events = [e for e in events if e.get("end_x") is not None and e.get("end_y") is not None]

        # Apply game filter if specified
        if game_filter:
            events = [e for e in events if str(e.get("match_id")) == str(game_filter)]

        # Determine the label for error message
        display_label = viz_type.replace("_", " ").title() if viz_type else heatmap_type.lower()

        if len(events) < 1:
            filter_msg = " for this game" if game_filter else ""
            return ui.p(f"No {display_label} data available{filter_msg}", style=f"color: {SUBTEXT_COLOR};")

        # Create HORIZONTAL heatmap: 120 width x 80 height
        # Black background with white lines
        HEATMAP_BG = "#000000"
        fig, ax = plt.subplots(figsize=(10, 7), facecolor=HEATMAP_BG)
        ax.set_facecolor(HEATMAP_BG)

        # Pitch dimensions for horizontal view
        P_WIDTH = 120   # x-axis (length of pitch, attacking right)
        P_HEIGHT = 80   # y-axis (width of pitch)

        # Scale coordinates from 0-100 to horizontal pitch
        # Use end_x/end_y for destination, x/y for origin
        if use_destination:
            xs = np.array([e["end_x"] * P_WIDTH / 100 for e in events])
            ys = np.array([e["end_y"] * P_HEIGHT / 100 for e in events])
        else:
            xs = np.array([e["x"] * P_WIDTH / 100 for e in events])
            ys = np.array([e["y"] * P_HEIGHT / 100 for e in events])

        # Clip to pitch bounds
        xs = np.clip(xs, 0.1, P_WIDTH - 0.1)
        ys = np.clip(ys, 0.1, P_HEIGHT - 0.1)

        if current_heatmap_mode == "kde" and len(xs) >= 3:
            # KDE Heat Map mode - show density as color gradient
            try:
                # Create KDE
                xy = np.vstack([xs, ys])
                kde = gaussian_kde(xy, bw_method=0.15)

                # Create grid for KDE evaluation
                x_grid = np.linspace(0, P_WIDTH, 100)
                y_grid = np.linspace(0, P_HEIGHT, 70)
                X, Y = np.meshgrid(x_grid, y_grid)
                positions = np.vstack([X.ravel(), Y.ravel()])
                Z = kde(positions).reshape(X.shape)

                # Plot KDE as filled contours with team-specific color map
                from matplotlib.colors import LinearSegmentedColormap
                if is_defiance:
                    # Blue colormap for Defiance
                    colors = ['#000000', '#1a3d4d', '#2d5a6d', '#3d7a8d', '#4d9aad', '#5BC0EB']
                else:
                    # Green colormap for Sounders
                    colors = ['#000000', '#1a3d1a', '#2d5a2d', '#3d7a3d', '#5D9741', '#96D35F']
                cmap = LinearSegmentedColormap.from_list('team_heat', colors)
                ax.contourf(X, Y, Z, levels=20, cmap=cmap, alpha=0.8, zorder=1)
            except Exception:
                # Fall back to action mode if KDE fails
                pass
        else:
            # Action mode - show individual dots
            # Create grid-based density for alpha values
            n_bins_x = 24
            n_bins_y = 16
            H, xedges, yedges = np.histogram2d(xs, ys, bins=[n_bins_x, n_bins_y],
                                                range=[[0, P_WIDTH], [0, P_HEIGHT]])

            # For each event, find its bin and calculate alpha based on density
            max_count = H.max() if H.max() > 0 else 1

            # Draw circles for each event with alpha based on local density
            # For shots heatmap, show goals as soccer balls
            is_shots_heatmap = heatmap_type == "Shot"
            can_draw_trajectories = draw_trajectories

            for e in events:
                if use_destination:
                    ex = e["end_x"] * P_WIDTH / 100
                    ey = e["end_y"] * P_HEIGHT / 100
                else:
                    ex = e["x"] * P_WIDTH / 100
                    ey = e["y"] * P_HEIGHT / 100
                ex = np.clip(ex, 0.1, P_WIDTH - 0.1)
                ey = np.clip(ey, 0.1, P_HEIGHT - 0.1)

                # Find which bin this point falls into
                bin_x = min(int(ex / P_WIDTH * n_bins_x), n_bins_x - 1)
                bin_y = min(int(ey / P_HEIGHT * n_bins_y), n_bins_y - 1)

                # Alpha based on density in this bin (0.15 to 0.9)
                density = H[bin_x, bin_y]
                alpha = 0.15 + 0.75 * (density / max_count) ** 0.5

                # Check if this is an unsuccessful outcome
                is_unsuccessful = e.get("outcome_type_display_name") == "Unsuccessful"
                # Use grey for unsuccessful, accent color for successful
                comet_color = '#666666' if is_unsuccessful else accent_color

                # Draw trajectory comets if enabled (for Pass/Carry)
                # Comet effect: line gets thicker from origin to endpoint
                if can_draw_trajectories and e.get("x") is not None and e.get("end_x") is not None:
                    start_x = e["x"] * P_WIDTH / 100
                    start_y = e["y"] * P_HEIGHT / 100
                    end_x = e["end_x"] * P_WIDTH / 100
                    end_y = e["end_y"] * P_HEIGHT / 100
                    # Draw comet with 10 segments, increasing linewidth
                    n_segments = 10
                    for seg in range(n_segments):
                        t0 = seg / n_segments
                        t1 = (seg + 1) / n_segments
                        x0 = start_x + t0 * (end_x - start_x)
                        y0 = start_y + t0 * (end_y - start_y)
                        x1 = start_x + t1 * (end_x - start_x)
                        y1 = start_y + t1 * (end_y - start_y)
                        # Linewidth grows from 0.5 to 4, alpha grows from 0.1 to 0.4
                        lw_seg = 0.5 + 3.5 * t1
                        alpha_seg = 0.1 + 0.3 * t1
                        ax.plot([x0, x1], [y0, y1], color=comet_color, lw=lw_seg, alpha=alpha_seg, zorder=1)

                # Check if this is a goal - show star with white outline
                if is_shots_heatmap and e.get("type_display_name") == "Goal":
                    ax.scatter(ex, ey, s=220, c=accent_color, marker='*', edgecolors='white', linewidth=1.5, zorder=3)
                elif is_unsuccessful:
                    # Unsuccessful outcomes: grey
                    ax.scatter(ex, ey, s=100, c='#666666', alpha=0.7, edgecolors='none', zorder=2)
                else:
                    ax.scatter(ex, ey, s=100, c=accent_color, alpha=alpha, edgecolors='none', zorder=2)

        # Draw pitch lines ON TOP of heatmap
        lw = 2
        line_col = "#ffffff"  # White lines

        # Outer boundary - draw as rectangle to ensure all sides visible
        rect = plt.Rectangle((0, 0), P_WIDTH, P_HEIGHT, fill=False,
                              edgecolor=line_col, linewidth=lw, zorder=10)
        ax.add_patch(rect)

        # Center line (vertical)
        ax.plot([P_WIDTH/2, P_WIDTH/2], [0, P_HEIGHT], color=line_col, lw=lw, zorder=10)

        # Center circle
        circle = plt.Circle((P_WIDTH/2, P_HEIGHT/2), 10, fill=False, color=line_col, lw=lw, zorder=10)
        ax.add_patch(circle)
        ax.scatter(P_WIDTH/2, P_HEIGHT/2, s=25, color=line_col, zorder=10)

        # Penalty areas (18 yards deep, 44 yards wide)
        box_depth = 18
        box_height = 44
        box_top = (P_HEIGHT - box_height) / 2

        # Left penalty area
        ax.plot([0, box_depth, box_depth, 0],
                [box_top, box_top, box_top + box_height, box_top + box_height],
                color=line_col, lw=lw, zorder=10)

        # Right penalty area
        ax.plot([P_WIDTH, P_WIDTH - box_depth, P_WIDTH - box_depth, P_WIDTH],
                [box_top, box_top, box_top + box_height, box_top + box_height],
                color=line_col, lw=lw, zorder=10)

        # 6-yard boxes
        six_depth = 6
        six_height = 20
        six_top = (P_HEIGHT - six_height) / 2

        ax.plot([0, six_depth, six_depth, 0],
                [six_top, six_top, six_top + six_height, six_top + six_height],
                color=line_col, lw=lw, zorder=10)
        ax.plot([P_WIDTH, P_WIDTH - six_depth, P_WIDTH - six_depth, P_WIDTH],
                [six_top, six_top, six_top + six_height, six_top + six_height],
                color=line_col, lw=lw, zorder=10)

        # Penalty spots
        ax.scatter(12, P_HEIGHT/2, s=25, color=line_col, zorder=10)
        ax.scatter(P_WIDTH - 12, P_HEIGHT/2, s=25, color=line_col, zorder=10)

        # Set limits with small padding to show full boundary
        ax.set_xlim(-1, P_WIDTH + 1)
        ax.set_ylim(-1, P_HEIGHT + 1)
        ax.set_aspect('equal')
        ax.axis('off')

        ax.set_title(f"{len(events)} events", color=SUBTEXT_COLOR, fontsize=10, pad=5)

        img_data = fig_to_base64(fig, dpi=100)

        return ui.HTML(f'<img src="data:image/png;base64,{img_data}" style="width: 100%; display: block; margin: 0 auto;">')


app = App(app_ui, server)

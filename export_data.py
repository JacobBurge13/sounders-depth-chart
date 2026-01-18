"""
Export Seattle Sounders data from Supabase to JSON files for Shinylive dashboard.
Run this script to refresh the data: python export_data.py
"""

import json
import os
import psycopg2
import pandas as pd

# Database configuration (same as your notebooks)
DB_CONFIG = {
    "dbname": "postgres",
    "user": "postgres.vvwfcbbyddyodkjuwdbq",
    "password": "BKBKrhdP42zt0Jo2",
    "host": "aws-1-us-east-2.pooler.supabase.com",
    "port": 5432,
}

# Output directory
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)


def get_sounders_team_id(conn):
    """Find Seattle Sounders team_id."""
    query = """
    SELECT DISTINCT team_id, name
    FROM teams
    WHERE LOWER(name) LIKE '%seattle%' OR LOWER(name) LIKE '%sounders%'
    """
    df = pd.read_sql(query, conn)
    if df.empty:
        raise ValueError("Seattle Sounders not found in database")
    print(f"Found team: {df.iloc[0]['name']} (ID: {df.iloc[0]['team_id']})")
    return str(df.iloc[0]["team_id"])


def export_players(conn, team_id):
    """Export Sounders players with aggregated stats."""

    # Get player info and stats
    query = f"""
    SELECT
        p.player_id,
        p.name,
        p.age,
        p.position,
        p.shirt_no,
        p.nationality,
        p.base_salary,
        p.primary_broad_position,
        p.primary_general_position,
        p.image_url,
        p.mins,
        p.gp,
        p.gs,
        COUNT(DISTINCT e.match_id) as matches,
        SUM(CASE WHEN e.is_goal = true THEN 1 ELSE 0 END) as goals,
        0 as assists,  -- Calculated from events after export
        SUM(CASE WHEN e.is_shot = true THEN 1 ELSE 0 END) as shots,
        SUM(CASE WHEN e.is_shot = true AND COALESCE(e.is_blocked, false) = false AND e.type_display_name IN ('SavedShot', 'Goal') THEN 1 ELSE 0 END) as shots_on_target,
        SUM(CASE WHEN e.is_shot = true AND (COALESCE(e.is_blocked, false) = true OR e.type_display_name IN ('MissedShots', 'ShotOnPost')) THEN 1 ELSE 0 END) as shots_off_target,
        SUM(CASE WHEN e.type_display_name = 'Pass' AND e.outcome_type_display_name = 'Successful' THEN 1 ELSE 0 END) as passes,
        SUM(CASE WHEN e.type_display_name = 'Pass' THEN 1 ELSE 0 END) as total_passes,
        SUM(CASE WHEN e.is_keypass = true THEN 1 ELSE 0 END) as key_passes,
        SUM(CASE WHEN e.is_shotassist = true THEN 1 ELSE 0 END) as shot_assists,
        SUM(CASE WHEN e.type_display_name IN ('Tackle', 'Interception', 'Clearance', 'BallRecovery') THEN 1 ELSE 0 END) as defensive_actions,
        SUM(CASE WHEN e.type_display_name = 'Tackle' THEN 1 ELSE 0 END) as tackles,
        SUM(CASE WHEN e.type_display_name = 'Interception' THEN 1 ELSE 0 END) as interceptions,
        SUM(CASE WHEN e.type_display_name = 'Clearance' THEN 1 ELSE 0 END) as clearances,
        SUM(CASE WHEN e.type_display_name = 'BallRecovery' THEN 1 ELSE 0 END) as ball_recoveries,
        SUM(CASE WHEN e.type_display_name = 'Carry' THEN 1 ELSE 0 END) as carries,
        -- Receptions
        SUM(CASE WHEN e.type_display_name = 'Reception' THEN 1 ELSE 0 END) as receptions,
        SUM(CASE WHEN e.type_display_name = 'Reception' AND e.x >= 66.67 THEN 1 ELSE 0 END) as final_third_receptions,
        SUM(CASE WHEN e.type_display_name = 'Reception' AND e.x >= 83.33 THEN 1 ELSE 0 END) as deep_receptions,
        -- Progressive passes: move ball 25%+ closer to goal
        SUM(CASE WHEN e.type_display_name = 'Pass' AND e.end_x IS NOT NULL AND e.x IS NOT NULL
                 AND (100 - e.end_x) < (100 - e.x) * 0.75 THEN 1 ELSE 0 END) as progressive_passes,
        -- Final third passes: end in attacking third
        SUM(CASE WHEN e.type_display_name = 'Pass' AND e.end_x > 66.67 THEN 1 ELSE 0 END) as final_third_passes,
        -- Deep passes: end in penalty area zone
        SUM(CASE WHEN e.type_display_name = 'Pass' AND e.end_x > 83.33 THEN 1 ELSE 0 END) as deep_passes,
        -- Progressive carries
        SUM(CASE WHEN e.type_display_name = 'Carry' AND e.end_x IS NOT NULL AND e.x IS NOT NULL
                 AND (100 - e.end_x) < (100 - e.x) * 0.75 THEN 1 ELSE 0 END) as progressive_carries,
        -- Final third carries
        SUM(CASE WHEN e.type_display_name = 'Carry' AND e.end_x > 66.67 THEN 1 ELSE 0 END) as final_third_carries,
        -- Deep carries
        SUM(CASE WHEN e.type_display_name = 'Carry' AND e.end_x > 83.33 THEN 1 ELSE 0 END) as deep_carries,
        -- Total xG from shots
        SUM(CASE WHEN e.is_shot = true THEN COALESCE(e."xG", 0) ELSE 0 END) as total_xg,
        SUM(COALESCE(e.gplus, 0)) as pv_total,
        SUM(COALESCE(e.gplus_passing, 0)) as pv_passing,
        SUM(COALESCE(e.gplus_receiving, 0)) as pv_receiving,
        SUM(COALESCE(e.gplus_carrying, 0)) as pv_carrying,
        SUM(COALESCE(e.gplus_shooting, 0)) as pv_shooting,
        SUM(COALESCE(e.gplus_defending, 0)) as pv_defending
    FROM players p
    LEFT JOIN match_event e ON p.player_id = e.player_id
    WHERE p.team_id = '{team_id}'
    GROUP BY p.player_id, p.name, p.age, p.position, p.shirt_no,
             p.nationality, p.base_salary, p.primary_broad_position,
             p.primary_general_position, p.image_url, p.mins, p.gp, p.gs
    ORDER BY p.name
    """

    df = pd.read_sql(query, conn)

    # Convert to list of dicts
    players = df.to_dict(orient="records")

    # Clean up numeric types for JSON
    for p in players:
        for key, val in p.items():
            if pd.isna(val):
                p[key] = None
            elif hasattr(val, "item"):  # numpy types
                p[key] = val.item()
        # Calculate xg_assisted (approximate using avg xG of ~0.15 per shot assist)
        shot_assists = p.get("shot_assists", 0) or 0
        p["xg_assisted"] = round(shot_assists * 0.15, 2)

    # Save to JSON
    output_path = os.path.join(DATA_DIR, "players.json")
    with open(output_path, "w") as f:
        json.dump(players, f, indent=2)

    print(f"Exported {len(players)} players to {output_path}")
    return players


def export_events(conn, team_id):
    """Export event coordinates for heat maps."""

    query = f"""
    SELECT
        player_id,
        match_id,
        minute,
        second,
        x,
        y,
        end_x,
        end_y,
        type_display_name,
        outcome_type_display_name,
        COALESCE(is_keypass, false) as is_keypass,
        COALESCE(is_goal, false) as is_goal,
        COALESCE(is_intentionalgoalassist, false) as is_intentionalgoalassist,
        COALESCE(is_intentionalassist, false) as is_intentionalassist,
        COALESCE(gplus, 0) as gplus,
        COALESCE("xG", 0) as xg,
        COALESCE(is_shotassist, false) as is_shotassist,
        COALESCE(is_assisted, false) as is_assisted,
        -- Progressive pass: moves ball 25%+ closer to goal
        CASE WHEN type_display_name = 'Pass' AND end_x IS NOT NULL AND x IS NOT NULL
             AND (100 - end_x) < (100 - x) * 0.75 THEN true ELSE false END as is_progressive_pass,
        -- Final third pass: ends in attacking third (x > 66.67)
        CASE WHEN type_display_name = 'Pass' AND end_x > 66.67 THEN true ELSE false END as is_final_third_pass,
        -- Deep pass: ends in penalty area zone (x > 83.33)
        CASE WHEN type_display_name = 'Pass' AND end_x > 83.33 THEN true ELSE false END as is_deep_pass,
        -- Progressive carry
        CASE WHEN type_display_name = 'Carry' AND end_x IS NOT NULL AND x IS NOT NULL
             AND (100 - end_x) < (100 - x) * 0.75 THEN true ELSE false END as is_progressive_carry,
        -- Final third carry
        CASE WHEN type_display_name = 'Carry' AND end_x > 66.67 THEN true ELSE false END as is_final_third_carry,
        -- Deep carry
        CASE WHEN type_display_name = 'Carry' AND end_x > 83.33 THEN true ELSE false END as is_deep_carry,
        COALESCE(is_shot, false) as is_shot,
        COALESCE(is_blocked, false) as is_blocked
    FROM match_event
    WHERE team_id = '{team_id}'
      AND type_display_name IN ('Pass', 'Reception', 'Carry', 'Shot', 'MissedShots', 'SavedShot', 'ShotOnPost', 'Goal', 'Tackle', 'Interception', 'Clearance', 'BallRecovery')
      AND x IS NOT NULL
      AND y IS NOT NULL
    """

    df = pd.read_sql(query, conn)

    # Convert to list of dicts
    events = df.to_dict(orient="records")

    # Clean up numeric types
    for e in events:
        for key, val in e.items():
            if pd.isna(val):
                e[key] = None
            elif hasattr(val, "item"):
                e[key] = val.item()

    # Save to JSON
    output_path = os.path.join(DATA_DIR, "events.json")
    with open(output_path, "w") as f:
        json.dump(events, f, indent=2)

    print(f"Exported {len(events)} events to {output_path}")
    return events


def export_matches(conn, team_id):
    """Export match information (opponent and date) for Sounders games."""

    # Get match data from matches table
    # Schema: match_id, home_team_name, away_team_name, match_date
    query = """
    SELECT
        m.match_id,
        m.home_team_name,
        m.away_team_name,
        m.match_date
    FROM matches m
    WHERE LOWER(m.home_team_name) LIKE '%seattle%'
       OR LOWER(m.away_team_name) LIKE '%seattle%'
    ORDER BY m.match_date DESC
    """

    try:
        df = pd.read_sql(query, conn)

        # Process rows to determine opponent and venue
        matches = []
        for _, row in df.iterrows():
            match_id = row['match_id']
            home = row['home_team_name']
            away = row['away_team_name']
            match_date = row['match_date']

            # Determine if Seattle is home or away
            is_home = 'seattle' in str(home).lower()
            opponent = away if is_home else home
            venue = 'vs' if is_home else '@'

            # Format date
            if pd.notna(match_date):
                if hasattr(match_date, 'strftime'):
                    date_str = match_date.strftime('%m/%d/%Y')
                else:
                    date_str = str(match_date)
            else:
                date_str = None

            matches.append({
                'match_id': str(match_id) if hasattr(match_id, 'item') else match_id,
                'opponent': opponent,
                'venue': venue,
                'start_date': date_str
            })

    except Exception as ex:
        print(f"Matches table query failed: {ex}")
        # Fallback - get match IDs from events
        query = f"""
        SELECT DISTINCT match_id
        FROM match_event
        WHERE team_id = '{team_id}'
        ORDER BY match_id DESC
        """
        df = pd.read_sql(query, conn)
        matches = []
        for i, row in df.iterrows():
            matches.append({
                'match_id': str(row['match_id']) if hasattr(row['match_id'], 'item') else row['match_id'],
                'opponent': 'Opponent',
                'venue': 'vs',
                'start_date': f"Game {len(df) - i}"
            })

    # Save to JSON
    output_path = os.path.join(DATA_DIR, "matches.json")
    with open(output_path, "w") as f:
        json.dump(matches, f, indent=2)

    print(f"Exported {len(matches)} matches to {output_path}")
    return matches


def calculate_assists_from_events(events, players):
    """
    Calculate assists: is_shotassist where the next shot is a goal with is_assisted=True.
    Updates the players list in-place and returns it.
    """
    from collections import defaultdict

    # Group events by match and sort by minute/second
    events_by_match = defaultdict(list)
    for e in events:
        events_by_match[e.get("match_id")].append(e)

    # Sort each match's events by minute, then second
    for match_id in events_by_match:
        events_by_match[match_id].sort(key=lambda x: (x.get("minute") or 0, x.get("second") or 0))

    # Count assists per player
    assists_by_player = defaultdict(int)
    shot_types = ["Goal", "Shot", "MissedShots", "SavedShot", "ShotOnPost"]

    for match_id, match_events in events_by_match.items():
        for i, e in enumerate(match_events):
            # Check if this is a shot assist
            if e.get("is_shotassist"):
                player_id = e.get("player_id")
                # Look for the next shot event
                for j in range(i + 1, len(match_events)):
                    next_e = match_events[j]
                    if next_e.get("type_display_name") in shot_types:
                        # Check if it's a goal with is_assisted=True
                        if (next_e.get("type_display_name") == "Goal" or next_e.get("is_goal")) and next_e.get("is_assisted"):
                            assists_by_player[player_id] += 1
                        break  # Stop after finding the next shot

    # Update players with calculated assists
    for p in players:
        player_id = p.get("player_id")
        p["assists"] = assists_by_player.get(player_id, 0)

    print(f"Calculated assists for {len(assists_by_player)} players")
    return players


def main():
    print("Connecting to database...")
    conn = psycopg2.connect(**DB_CONFIG)

    try:
        # Get Sounders team ID
        team_id = get_sounders_team_id(conn)

        # Export data
        print("\nExporting player data...")
        players = export_players(conn, team_id)

        print("\nExporting event data for heat maps...")
        events = export_events(conn, team_id)

        print("\nExporting match data...")
        matches = export_matches(conn, team_id)

        # Calculate assists from events (is_shotassist where next shot is assisted goal)
        print("\nCalculating assists from events...")
        players = calculate_assists_from_events(events, players)

        # Re-save players with corrected assists
        output_path = os.path.join(DATA_DIR, "players.json")
        with open(output_path, "w") as f:
            json.dump(players, f, indent=2)
        print(f"Updated players with calculated assists")

        print("\n" + "="*50)
        print("Export complete!")
        print(f"Players: {len(players)}")
        print(f"Events: {len(events)}")
        print(f"Matches: {len(matches)}")
        print("="*50)

    finally:
        conn.close()


if __name__ == "__main__":
    main()

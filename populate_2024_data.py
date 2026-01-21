"""
Populate 2024 Sounders player data (salary, mins, gp, gs, image_url) from:
1. ASA (American Soccer Analysis) - salary and position data
2. MLS Website - GP, GS, Mins, Sub, and player images

Run: python populate_2024_data.py
"""

import pandas as pd
import time
import unicodedata
from thefuzz import fuzz
from supabase import create_client

# ========== CONFIGURATION ==========
SEASON = 2024
CLUB = "seattle-sounders-fc"
MATCH_THRESHOLD = 80

# Supabase credentials
PROJECT_URL = "https://vvwfcbbyddyodkjuwdbq.supabase.co"
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ2d2ZjYmJ5ZGR5b2RranV3ZGJxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTk2NzE2NjQsImV4cCI6MjA3NTI0NzY2NH0.lpAOWtF-sYFUyhvgjVVVb_EkxUbWnoclf7RL0Qrz-BE"

# Manual mappings for players that don't fuzzy match well
MANUAL_MAPPINGS_2024 = {
    'J. Morris': '313037_(2024)',        # Jordan Morris
    'A. Rusnák': '141927_(2024)',         # Albert Rusnák
    'P. Rothrock': '437944_(2024)',       # Paul Rothrock
    'J. Bell': '413742_(2024)',           # Jon Bell
    'D. Musovski': '396235_(2024)',       # Danny Musovski
    'Y. Gómez Andrade': '247429_(2024)',  # Yeimar Gómez
    'O. Vargas': '419580_(2024)',         # Obed Vargas
    'P. de la Vega': '363582_(2024)',     # Pedro de la Vega
    'G. Minoungou': '481296_(2024)',      # Georgi Minoungou
    'R. Baker-Whiting': '415661_(2024)',  # Reed Baker-Whiting
    'A. Thomas': '419582_(2024)',         # Andrew Thomas
    'D. Leyva': '373518_(2024)',          # Danny Leyva
    'J. Atencio': '396104_(2024)',        # Josh Atencio
    'J. Mior': '104866_(2024)',           # João Paulo
    'K. Kossa-Rienzi': '516205_(2024)',   # Kalani Kossa-Rienzi
    'A. Lopez': '527018_(2024)',          # Antino Lopez
    'C. Roldán': '271592_(2024)',         # Cristian Roldan
}
# ===================================


def normalize_name(name: str) -> str:
    """Normalize player name for matching."""
    if not name:
        return ""
    name = unicodedata.normalize('NFD', name)
    name = ''.join(c for c in name if unicodedata.category(c) != 'Mn')
    return name.lower().strip()


def expand_abbreviated_name(abbrev_name: str) -> list:
    """Expand 'D. Musovski' to possible patterns."""
    parts = abbrev_name.split()
    if len(parts) >= 2 and len(parts[0]) <= 2 and parts[0].endswith('.'):
        initial = parts[0].replace('.', '').lower()
        last_name = ' '.join(parts[1:]).lower()
        return [initial, last_name]
    return [abbrev_name.lower()]


def match_player_to_db(scraped_name: str, db_players: list, threshold: int = 80) -> dict | None:
    """Match a scraped player name to database players using fuzzy matching."""
    if not db_players:
        return None

    scraped_normalized = normalize_name(scraped_name)
    name_parts = expand_abbreviated_name(scraped_name)

    best_match = None
    best_score = 0

    for player in db_players:
        db_name = player.get('name', '')
        db_normalized = normalize_name(db_name)

        score1 = fuzz.ratio(scraped_normalized, db_normalized)
        score2 = fuzz.partial_ratio(scraped_normalized, db_normalized)
        score3 = fuzz.token_sort_ratio(scraped_normalized, db_normalized)

        score4 = 0
        if len(name_parts) == 2:
            initial, last_name = name_parts
            db_lower = db_normalized
            if last_name in db_lower and db_lower.startswith(initial):
                score4 = 95

        max_score = max(score1, score2, score3, score4)

        if max_score > best_score:
            best_score = max_score
            best_match = player

    if best_score >= threshold:
        return best_match

    return None


def get_mls_stats_with_images(club_slug: str, season: int, timeout: int = 25) -> pd.DataFrame:
    """Scrape player stats AND images from MLS website."""
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from io import StringIO

    url = f"https://www.mlssoccer.com/clubs/{club_slug}/stats/#season={season}&statType=general&position=all"

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")

    driver = webdriver.Chrome(options=options)

    try:
        print(f"Loading {url}")
        driver.get(url)

        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table tbody tr"))
        )
        time.sleep(3)

        rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
        player_images = {}

        for row in rows:
            try:
                name_cell = row.find_element(By.CSS_SELECTOR, "td:first-child")
                player_name = name_cell.text.strip()

                try:
                    img = row.find_element(By.CSS_SELECTOR, "img")
                    img_url = img.get_attribute("src")
                    if img_url and "placeholder" not in img_url.lower():
                        player_images[player_name] = img_url
                except:
                    pass
            except:
                continue

        html = driver.page_source
        tables = pd.read_html(StringIO(html))

        if not tables:
            raise ValueError("No tables found")

        df = tables[0]

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[1] if isinstance(col, tuple) else col for col in df.columns]

        result = pd.DataFrame()
        result["player_name"] = df["Player"]
        result["gp"] = pd.to_numeric(df["GP"], errors="coerce").fillna(0).astype(int)
        result["gs"] = pd.to_numeric(df["GS"], errors="coerce").fillna(0).astype(int)
        result["mins"] = pd.to_numeric(df["Mins"], errors="coerce").fillna(0).astype(int)
        result["sub"] = pd.to_numeric(df["Sub"], errors="coerce").fillna(0).astype(int)
        result["season"] = season
        result["image_url"] = result["player_name"].map(player_images)

        return result

    finally:
        driver.quit()


def get_asa_salary_data(season: int) -> pd.DataFrame:
    """Get salary data from American Soccer Analysis."""
    from itscalledsoccer.client import AmericanSoccerAnalysis

    print(f"Fetching ASA salary data for {season}...")
    asa = AmericanSoccerAnalysis()

    # Get salary data
    salary_raw = asa.get_player_salaries(leagues=["mls"], season_name=str(season))
    salary_df = pd.DataFrame(salary_raw)

    # Get player info for position data
    players_df = asa.get_players(leagues=["mls"])

    # Filter to players with this season
    def has_season(season_list, target_season):
        if isinstance(season_list, (list, tuple, set)):
            return any(int(x) == target_season for x in season_list)
        if isinstance(season_list, (int, str)):
            return int(season_list) == target_season
        return False

    season_players = players_df[players_df["season_name"].apply(lambda x: has_season(x, season))].copy()

    # Clean up salary (take max per player)
    salary_clean = salary_df.groupby("player_id", as_index=False).agg({
        "base_salary": "max",
        "guaranteed_compensation": "max"
    })

    # Merge salary with player info
    merged = season_players.merge(salary_clean, on="player_id", how="left")

    print(f"Found {len(merged)} players with salary data")
    return merged


def main():
    print("="*60)
    print(f"Populating 2024 Sounders player data")
    print("="*60)

    # Connect to Supabase
    supabase = create_client(PROJECT_URL, API_KEY)
    print("Connected to Supabase")

    # Get existing 2024 players from database
    response = supabase.table("players").select("player_id, name").execute()
    all_db_players = response.data
    season_players = [p for p in all_db_players if f"_({SEASON})" in str(p.get('player_id', ''))]
    print(f"Found {len(season_players)} players for {SEASON} in database")

    # 1. Get salary data from ASA
    print("\n" + "-"*40)
    print("Step 1: Fetching salary data from ASA...")
    print("-"*40)
    asa_data = get_asa_salary_data(SEASON)

    # 2. Get MLS stats (GP, GS, Mins, images)
    print("\n" + "-"*40)
    print("Step 2: Scraping MLS website for stats and images...")
    print("-"*40)
    mls_data = get_mls_stats_with_images(CLUB, SEASON)
    print(f"Scraped {len(mls_data)} players from MLS website")

    # 3. Match MLS data to database players
    print("\n" + "-"*40)
    print("Step 3: Matching players...")
    print("-"*40)

    matches = []
    unmatched_mls = []

    for _, row in mls_data.iterrows():
        scraped_name = row['player_name']

        # Check manual mappings first
        if scraped_name in MANUAL_MAPPINGS_2024:
            player_id = MANUAL_MAPPINGS_2024[scraped_name]
            matches.append({
                'scraped_name': scraped_name,
                'db_player_id': player_id,
                'db_name': scraped_name,
                'gp': row['gp'],
                'gs': row['gs'],
                'mins': row['mins'],
                'sub': row['sub'],
                'image_url': row['image_url'],
            })
            continue

        match = match_player_to_db(scraped_name, season_players, MATCH_THRESHOLD)

        if match:
            matches.append({
                'scraped_name': scraped_name,
                'db_player_id': match['player_id'],
                'db_name': match['name'],
                'gp': row['gp'],
                'gs': row['gs'],
                'mins': row['mins'],
                'sub': row['sub'],
                'image_url': row['image_url'],
            })
        else:
            unmatched_mls.append(scraped_name)

    print(f"MLS data matched: {len(matches)} players")
    if unmatched_mls:
        print(f"MLS unmatched: {unmatched_mls}")

    # 4. Match ASA salary data to database players
    salary_matches = {}
    for _, row in asa_data.iterrows():
        asa_name = row.get('player_name', '')
        match = match_player_to_db(asa_name, season_players, MATCH_THRESHOLD)
        if match and pd.notna(row.get('base_salary')):
            salary_matches[match['player_id']] = {
                'base_salary': row['base_salary'],
                'primary_broad_position': row.get('primary_broad_position'),
                'primary_general_position': row.get('primary_general_position'),
            }

    print(f"Salary data matched: {len(salary_matches)} players")

    # 5. Combine and upload
    print("\n" + "-"*40)
    print("Step 4: Uploading to Supabase...")
    print("-"*40)

    updated = 0
    errors = []

    for m in matches:
        update_data = {
            'gp': m['gp'],
            'gs': m['gs'],
            'mins': m['mins'],
        }

        if m.get('image_url') and pd.notna(m['image_url']):
            update_data['image_url'] = m['image_url']

        # Add salary data if available
        player_id = m['db_player_id']
        if player_id in salary_matches:
            sal_data = salary_matches[player_id]
            update_data['base_salary'] = sal_data['base_salary']
            if sal_data.get('primary_broad_position'):
                update_data['primary_broad_position'] = sal_data['primary_broad_position']
            if sal_data.get('primary_general_position'):
                update_data['primary_general_position'] = sal_data['primary_general_position']

        try:
            supabase.table("players").update(update_data).eq("player_id", player_id).execute()
            updated += 1
            print(f"  Updated {player_id} ({m['db_name']}): GP={m['gp']}, GS={m['gs']}, Mins={m['mins']}, Salary={update_data.get('base_salary', 'N/A')}")
        except Exception as e:
            errors.append(f"{player_id}: {e}")

    # Also update players that only have salary data (no MLS stats match)
    matched_ids = {m['db_player_id'] for m in matches}
    for player_id, sal_data in salary_matches.items():
        if player_id not in matched_ids:
            try:
                update_data = {'base_salary': sal_data['base_salary']}
                if sal_data.get('primary_broad_position'):
                    update_data['primary_broad_position'] = sal_data['primary_broad_position']
                if sal_data.get('primary_general_position'):
                    update_data['primary_general_position'] = sal_data['primary_general_position']

                supabase.table("players").update(update_data).eq("player_id", player_id).execute()
                updated += 1
                print(f"  Updated salary only for {player_id}: Salary={sal_data['base_salary']}")
            except Exception as e:
                errors.append(f"{player_id}: {e}")

    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Total updated: {updated}")
    if errors:
        print(f"Errors: {len(errors)}")
        for e in errors[:5]:
            print(f"  - {e}")
    print("="*60)


if __name__ == "__main__":
    main()

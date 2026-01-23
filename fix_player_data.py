"""
Fix player data for 2024 and 2025 seasons.
Ensures all players have correct image_url, nationality, salary from ASA,
and MLS stats (GP, GS, Mins) from the correct season.

Run: python fix_player_data.py
"""

import json
import os
import time
import pandas as pd
from thefuzz import fuzz
import unicodedata

# ========== CONFIGURATION ==========
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CLUB_SLUG = "seattle-sounders-fc"

# ASA team ID for Seattle Sounders
SEATTLE_ASA_TEAM_ID = 'jYQJ19EqGR'

# Manual name mappings for MLS website -> player_id
MANUAL_MAPPINGS_2024 = {
    'J. Morris': '313037_(2024)',
    'A. Rusnák': '141927_(2024)',
    'P. Rothrock': '437944_(2024)',
    'J. Bell': '413742_(2024)',
    'D. Musovski': '396235_(2024)',
    'Y. Gómez Andrade': '247429_(2024)',
    'O. Vargas': '419580_(2024)',
    'P. de la Vega': '363582_(2024)',
    'G. Minoungou': '481296_(2024)',
    'R. Baker-Whiting': '415661_(2024)',
    'A. Thomas': '419582_(2024)',
    'D. Leyva': '373518_(2024)',
    'J. Atencio': '396104_(2024)',
    'J. Mior': '104866_(2024)',
    'K. Kossa-Rienzi': '516205_(2024)',
    'A. Lopez': '527018_(2024)',
    'C. Roldán': '271592_(2024)',
    'N. Tolo': '335583_(2024)',
    'S. Frei': '72630_(2024)',
    'A. Roldan': '354086_(2024)',
    'J. Ragen': '433622_(2024)',
    'C. Baker': '480644_(2024)',
    'D. Teves': '433623_(2024)',
    'S. Kitahara': '462097_(2024)',
    'L. Chú': '389174_(2024)',
    'R. Ruidíaz': '85915_(2024)',
}

MANUAL_MAPPINGS_2025 = {
    'J. Morris': '313037_(2025)',
    'A. Rusnák': '141927_(2025)',
    'P. Rothrock': '437944_(2025)',
    'J. Bell': '413742_(2025)',
    'D. Musovski': '396235_(2025)',
    'Y. Gómez Andrade': '247429_(2025)',
    'O. Vargas': '419580_(2025)',
    'P. de la Vega': '363582_(2025)',
    'G. Minoungou': '481296_(2025)',
    'R. Baker-Whiting': '415661_(2025)',
    'A. Thomas': '419582_(2025)',
    'D. Leyva': '373518_(2025)',
    'K. Kossa-Rienzi': '516205_(2025)',
    'C. Roldán': '271592_(2025)',
    'N. Tolo': '335583_(2025)',
    'S. Frei': '72630_(2025)',
    'A. Roldan': '354086_(2025)',
    'J. Ragen': '433622_(2025)',
    'C. Baker': '480644_(2025)',
    'J. Paulo': '104866_(2025)',
    'J. Ferreira': '339092_(2025)',
    'K. Kee-Hee': '142047_(2025)',
    'P. Arriola': '132631_(2025)',
    'R. Kent': '295922_(2025)',
    'S. Brunell': '527019_(2025)',
    'S. Hawkins': '502132_(2025)',
    'O. De Rosario': '527020_(2025)',
}

# ASA player names -> database player_id
ASA_NAME_TO_DB_2024 = {
    'Albert Rusnák': '141927_(2024)',
    'Jordan Morris': '313037_(2024)',
    'Cristian Roldan': '271592_(2024)',
    'João Paulo': '104866_(2024)',
    'Raúl Ruidíaz': '85915_(2024)',
    'Obed Vargas': '419580_(2024)',
    'Alex Roldan': '354086_(2024)',
    'Jackson Ragen': '433622_(2024)',
    'Nouhou': '335583_(2024)',
    'Stefan Frei': '72630_(2024)',
    'Yeimar Gómez Andrade': '247429_(2024)',
    'Pedro de la Vega': '363582_(2024)',
    'Josh Atencio': '396104_(2024)',
    'Reed Baker-Whiting': '415661_(2024)',
    'Paul Rothrock': '437944_(2024)',
    'Léo Chú': '389174_(2024)',
    'Danny Leyva': '373518_(2024)',
    'Danny Musovski': '396235_(2024)',
    'Jon Bell': '413742_(2024)',
    'Cody Baker': '480644_(2024)',
    'Dylan Teves': '433623_(2024)',
    'Georgi Minoungou': '481296_(2024)',
    'Andrew Thomas': '419582_(2024)',
    'Sota Kitahara': '462097_(2024)',
    'Nathan': '240917_(2024)',
    'Stuart Hawkins': '502132_(2024)',
    'Jacob Castro': '468751_(2024)',
    'Kalani Kossa-Rienzi': '516205_(2024)',
    'Antino Lopez': '527018_(2024)',
}

ASA_NAME_TO_DB_2025 = {
    'Albert Rusnák': '141927_(2025)',
    'Jordan Morris': '313037_(2025)',
    'Cristian Roldan': '271592_(2025)',
    'João Paulo': '104866_(2025)',
    'Obed Vargas': '419580_(2025)',
    'Alex Roldan': '354086_(2025)',
    'Jackson Ragen': '433622_(2025)',
    'Nouhou': '335583_(2025)',
    'Stefan Frei': '72630_(2025)',
    'Yeimar Gómez Andrade': '247429_(2025)',
    'Pedro de la Vega': '363582_(2025)',
    'Reed Baker-Whiting': '415661_(2025)',
    'Paul Rothrock': '437944_(2025)',
    'Danny Leyva': '373518_(2025)',
    'Danny Musovski': '396235_(2025)',
    'Jon Bell': '413742_(2025)',
    'Cody Baker': '480644_(2025)',
    'Georgi Minoungou': '481296_(2025)',
    'Andrew Thomas': '419582_(2025)',
    'Stuart Hawkins': '502132_(2025)',
    'Jacob Castro': '468751_(2025)',
    'Kalani Kossa-Rienzi': '516205_(2025)',
    'Antino Lopez': '527018_(2025)',
    'Jesús Ferreira': '339092_(2025)',
    'Kim Kee-hee': '142047_(2025)',
    'Kim Kee-Hee': '142047_(2025)',
    'Paul Arriola': '132631_(2025)',
    'Ryan Kent': '295922_(2025)',
    'Snyder Brunell': '527019_(2025)',
    'Osaze De Rosario': '527020_(2025)',
    'Peter Kingston': '587705_(2025)',
    'Sebastian Gomez': '587706_(2025)',
    'Travian Sousa': '480643_(2025)',
}

# Known nationalities for players
NATIONALITIES = {
    'Albert Rusnák': 'Slovakia',
    'Jordan Morris': 'USA',
    'Cristian Roldan': 'USA',
    'João Paulo': 'Brazil',
    'Raúl Ruidíaz': 'Peru',
    'Obed Vargas': 'USA',
    'Alex Roldan': 'USA',
    'Jackson Ragen': 'USA',
    'Nouhou': 'Cameroon',
    'Nouhou Tolo': 'Cameroon',
    'Stefan Frei': 'USA',
    'Yeimar Gómez Andrade': 'Colombia',
    'Yeimar Gómez': 'Colombia',
    'Pedro de la Vega': 'Argentina',
    'Josh Atencio': 'USA',
    'Reed Baker-Whiting': 'USA',
    'Paul Rothrock': 'USA',
    'Léo Chú': 'Brazil',
    'Danny Leyva': 'USA',
    'Danny Musovski': 'USA',
    'Jon Bell': 'USA',
    'Cody Baker': 'USA',
    'Dylan Teves': 'USA',
    'Georgi Minoungou': 'Ivory Coast',
    'Andrew Thomas': 'USA',
    'Sota Kitahara': 'Japan',
    'Nathan': 'Brazil',
    'Stuart Hawkins': 'USA',
    'Jacob Castro': 'USA',
    'Kalani Kossa-Rienzi': 'USA',
    'Antino Lopez': 'USA',
    'Jesús Ferreira': 'USA',
    'Kim Kee-hee': 'South Korea',
    'Kim Kee-Hee': 'South Korea',
    'Paul Arriola': 'USA',
    'Ryan Kent': 'England',
    'Snyder Brunell': 'USA',
    'Osaze De Rosario': 'Canada',
    'Peter Kingston': 'USA',
    'Sebastian Gomez': 'USA',
    'Travian Sousa': 'USA',
}


def normalize_name(name: str) -> str:
    """Normalize player name for matching."""
    if not name:
        return ""
    name = unicodedata.normalize('NFD', name)
    name = ''.join(c for c in name if unicodedata.category(c) != 'Mn')
    return name.lower().strip()


def match_player_name(scraped_name: str, players: list, threshold: int = 75) -> dict | None:
    """Match a scraped player name to players using fuzzy matching."""
    scraped_normalized = normalize_name(scraped_name)

    best_match = None
    best_score = 0

    for player in players:
        db_name = player.get('name', '')
        db_normalized = normalize_name(db_name)

        score = max(
            fuzz.ratio(scraped_normalized, db_normalized),
            fuzz.partial_ratio(scraped_normalized, db_normalized),
            fuzz.token_sort_ratio(scraped_normalized, db_normalized)
        )

        if score > best_score:
            best_score = score
            best_match = player

    return best_match if best_score >= threshold else None


def get_mls_stats_with_images(club_slug: str, season: int) -> pd.DataFrame:
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
        print(f"  Loading {url}")
        driver.get(url)

        WebDriverWait(driver, 25).until(
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
        result["image_url"] = result["player_name"].map(player_images)

        print(f"  Scraped {len(result)} players with {len(player_images)} images")
        return result

    finally:
        driver.quit()


def get_asa_salary_data(season: int, asa_name_map: dict) -> dict:
    """Get salary data from American Soccer Analysis for Seattle Sounders."""
    from itscalledsoccer.client import AmericanSoccerAnalysis

    print(f"  Fetching ASA salary data for {season}...")
    asa = AmericanSoccerAnalysis()

    salary_raw = asa.get_player_salaries(leagues=["mls"], season_name=str(season))
    salary_df = pd.DataFrame(salary_raw)

    seattle_salaries = salary_df[salary_df['team_id'] == SEATTLE_ASA_TEAM_ID].copy()
    print(f"  Found {len(seattle_salaries)} Seattle salary records")

    players_df = asa.get_players(leagues=["mls"])
    merged = seattle_salaries.merge(players_df, on="player_id", how="left")

    merged = merged.groupby("player_name", as_index=False).agg({
        "base_salary": "max",
        "guaranteed_compensation": "max",
        "primary_broad_position": "first",
        "primary_general_position": "first",
    })

    results = {}
    for _, row in merged.iterrows():
        asa_name = row.get('player_name', '')
        db_player_id = asa_name_map.get(asa_name)

        if db_player_id:
            results[db_player_id] = {
                'base_salary': row.get('base_salary'),
                'primary_broad_position': row.get('primary_broad_position'),
                'primary_general_position': row.get('primary_general_position'),
            }

    print(f"  Matched {len(results)} players to database IDs")
    return results


def fix_season_data(season: int):
    """Fix player data for a specific season."""
    print(f"\n{'='*60}")
    print(f"Fixing {season} data")
    print('='*60)

    # Determine file names and mappings based on season
    if season == 2024:
        players_file = os.path.join(DATA_DIR, "players_2024.json")
        manual_mappings = MANUAL_MAPPINGS_2024
        asa_name_map = ASA_NAME_TO_DB_2024
    else:
        players_file = os.path.join(DATA_DIR, "players.json")
        manual_mappings = MANUAL_MAPPINGS_2025
        asa_name_map = ASA_NAME_TO_DB_2025

    # Load existing players
    with open(players_file, 'r') as f:
        players = json.load(f)

    print(f"Loaded {len(players)} players from {players_file}")

    # Create lookup by player_id
    players_by_id = {p['player_id']: p for p in players}

    # Step 1: Get ASA salary data
    print("\nStep 1: Fetching ASA salary data...")
    try:
        asa_data = get_asa_salary_data(season, asa_name_map)
    except Exception as e:
        print(f"  Warning: ASA fetch failed: {e}")
        asa_data = {}

    # Step 2: Scrape MLS website
    print("\nStep 2: Scraping MLS website...")
    try:
        mls_data = get_mls_stats_with_images(CLUB_SLUG, season)
    except Exception as e:
        print(f"  Warning: MLS scraping failed: {e}")
        mls_data = None

    # Step 3: Update player data
    print("\nStep 3: Updating player data...")
    updates_count = 0

    # Update from ASA data
    for player_id, asa_info in asa_data.items():
        if player_id in players_by_id:
            player = players_by_id[player_id]
            updated = False

            if asa_info.get('base_salary') and pd.notna(asa_info['base_salary']):
                if player.get('base_salary') != asa_info['base_salary']:
                    player['base_salary'] = float(asa_info['base_salary'])
                    updated = True

            if asa_info.get('primary_broad_position') and pd.notna(asa_info['primary_broad_position']):
                if player.get('primary_broad_position') != asa_info['primary_broad_position']:
                    player['primary_broad_position'] = asa_info['primary_broad_position']
                    updated = True

            if asa_info.get('primary_general_position') and pd.notna(asa_info['primary_general_position']):
                if player.get('primary_general_position') != asa_info['primary_general_position']:
                    player['primary_general_position'] = asa_info['primary_general_position']
                    updated = True

            if updated:
                updates_count += 1

    # Update from MLS data
    if mls_data is not None:
        for _, row in mls_data.iterrows():
            scraped_name = row['player_name']

            # Try manual mapping first
            player_id = manual_mappings.get(scraped_name)

            if not player_id:
                # Try fuzzy matching
                match = match_player_name(scraped_name, players)
                if match:
                    player_id = match['player_id']

            if player_id and player_id in players_by_id:
                player = players_by_id[player_id]
                updated = False

                # Update GP, GS, Mins
                if row['gp'] > 0:
                    player['gp'] = float(row['gp'])
                    player['gs'] = float(row['gs'])
                    player['mins'] = float(row['mins'])
                    updated = True

                # Update image if available and not placeholder
                if pd.notna(row.get('image_url')) and row['image_url']:
                    img_url = row['image_url']
                    # Standardize image URL format
                    if 'mlssoccer.com' in img_url:
                        player['image_url'] = img_url
                        updated = True

                if updated:
                    updates_count += 1

    # Step 4: Fix missing nationalities
    print("\nStep 4: Fixing missing nationalities...")
    for player in players:
        if not player.get('nationality'):
            player_name = player.get('name', '')
            for known_name, nationality in NATIONALITIES.items():
                if normalize_name(known_name) == normalize_name(player_name):
                    player['nationality'] = nationality
                    updates_count += 1
                    print(f"  Set nationality for {player_name}: {nationality}")
                    break

    # Step 5: Save updated data
    print(f"\nStep 5: Saving {len(players)} players to {players_file}...")
    with open(players_file, 'w') as f:
        json.dump(players, f, indent=2)

    print(f"Total updates: {updates_count}")

    # Print players with missing data
    print("\nPlayers still missing data:")
    for p in players:
        missing = []
        if not p.get('nationality'):
            missing.append('nationality')
        if not p.get('image_url'):
            missing.append('image_url')
        if p.get('gp') is None:
            missing.append('gp')
        if p.get('base_salary') is None:
            missing.append('salary')

        if missing:
            print(f"  {p['name']}: missing {', '.join(missing)}")


def main():
    print("="*60)
    print("Fixing Seattle Sounders player data for 2024 and 2025")
    print("="*60)

    # Fix both seasons
    fix_season_data(2024)
    fix_season_data(2025)

    print("\n" + "="*60)
    print("Done!")
    print("="*60)


if __name__ == "__main__":
    main()

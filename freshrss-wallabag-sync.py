#!/usr/bin/env python3
"""
Sync starred articles from FreshRSS to Wallabag
Designed for FreshRSS → Wallabag workflow
"""

import logging
import requests
import json
import time
import hashlib
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import List

SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "config.json"

def load_config():
    """Load configuration from config.json file"""
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(
            f"Config file not found at {CONFIG_FILE}\n"
            "Please create config.json with your credentials. See config.example.json"
        )

    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

config = load_config()

# Config values from the config feel - you should probably keep as is
FRESHRSS_URL = config["freshrss"]["url"]
FRESHRSS_USERNAME = config["freshrss"]["username"]
FRESHRSS_API_PASSWORD = config["freshrss"]["api_password"]
WALLABAG_URL = config["wallabag"]["url"]
WALLABAG_CLIENT_ID = config["wallabag"]["client_id"]
WALLABAG_CLIENT_SECRET = config["wallabag"]["client_secret"]
WALLABAG_USERNAME = config["wallabag"]["username"]
WALLABAG_PASSWORD = config["wallabag"]["password"]
FEVER_API_KEY = hashlib.md5(f"{FRESHRSS_USERNAME}:{FRESHRSS_API_PASSWORD}".encode()).hexdigest()

TRACKING_FILE = SCRIPT_DIR / "synced_articles.json"
LOG_FILE = SCRIPT_DIR / "sync.log"

# Logging options - by default allows maximum of 5 log files, 1MB of maximum size each
MAX_LOG_FILE_SIZE = 1024 * 1024 # Maximum log file size in bytes
BACKUP_COUNT = 5 # Number of backup files (log.txt.1, log.txt.2) to keep

# Wallabar API options - feel free to customize
WALLABAR_API_REQUEST_COOLDOWN = 1 # Number of seconds to wait between each request
DEFAULT_TAGS = "freshrss-sync" # Comma-separated list of tags

# Logging handlers setup
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
         RotatingFileHandler(
            LOG_FILE,
            maxBytes=MAX_LOG_FILE_SIZE,
            backupCount=BACKUP_COUNT
        ),
        logging.StreamHandler()
    ]
)

def load_synced_articles() -> List[int]:
    """Load list of already synced article IDs"""
    if TRACKING_FILE.exists():
        with open(TRACKING_FILE, "r") as f:
            data = json.load(f)
            return [int(item_id) for item_id in data]
    return []

def save_synced_articles(article_ids: List[int]) -> None:
    """Save list of synced article IDs"""
    with open(TRACKING_FILE, "w") as f:
        json.dump([int(item_id) for item_id in article_ids], f, indent=2)

def get_freshrss_starred_items() -> List[int]:
    """Fetch starred item IDs from FreshRSS Fever API"""
    try:
        response = requests.post(
            FRESHRSS_URL,
            data={
                "api_key": FEVER_API_KEY,
                "api": "",
                "saved_item_ids": ""
            },
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

        if data.get("auth") != 1:
            logging.error("FreshRSS authentication failed (auth=0)")
            return []

        if "saved_item_ids" in data and data["saved_item_ids"]:
            # Fever API returns comma-separated string of IDs
            item_ids = [int(id_str) for id_str in data["saved_item_ids"].split(",")]
            logging.info(f"Found {len(item_ids)} starred articles in FreshRSS")
            return item_ids
        else:
            logging.info("No starred articles found in FreshRSS")
            return []

    except Exception as e:
        logging.error(f"Error fetching starred items from FreshRSS: {e}")
        return []

def get_freshrss_item_details(item_ids: List[int]) -> List[dict]:
    """Fetch full details for specific items from FreshRSS"""
    if not item_ids:
        return []

    try:
        # Fever API accepts comma-separated IDs
        ids_string = ",".join(str(id) for id in item_ids)
 
        response = requests.post(
            FRESHRSS_URL,
            data={
                "api_key": FEVER_API_KEY,
                "api": "",
                "items": "",
                "with_ids": ids_string
            },
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

        return data.get("items", [])

    except Exception as e:
        logging.error(f"Error fetching item details from FreshRSS: {e}")
        return []

def get_wallabag_token() -> str:
    """Obtain OAuth2 access token from Wallabag"""
    try:
        response = requests.post(
            f"{WALLABAG_URL}/oauth/v2/token",
            data={
                "grant_type": "password",
                "client_id": WALLABAG_CLIENT_ID,
                "client_secret": WALLABAG_CLIENT_SECRET,
                "username": WALLABAG_USERNAME,
                "password": WALLABAG_PASSWORD
            },
            timeout=30
        )
        response.raise_for_status()
        token_data = response.json()
        return token_data["access_token"]

    except Exception as e:
        logging.error(f"Error obtaining Wallabag token: {e}")
        raise

def add_to_wallabag(article: dict, access_token:str) -> bool:
    """Add article to Wallabag"""
    try:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        payload = {
            "url": article["url"],
            "title": article.get("title", "Untitled"),
            "starred": 1,
            "tags": DEFAULT_TAGS 
        }

        response = requests.post(
            f"{WALLABAG_URL}/api/entries.json",
            headers=headers,
            json=payload,
            timeout=30
        )

        if response.status_code in [200, 201]:
            logging.info(f"✓ Added to Wallabag: {article.get('title', 'Untitled')[:60]}")
            return True
        else:
            logging.error(f"✗ Failed to add article (HTTP {response.status_code}): {article.get('title', 'Untitled')[:60]}")
            return False

    except Exception as e:
        logging.error(f"✗ Error adding to Wallabag: {e}")
        return False

def main():
    logging.info("=" * 60)
    logging.info("Starting FreshRSS → Wallabag sync")
    synced_ids = load_synced_articles()
    logging.info(f"Previously synced: {len(synced_ids)} articles")
    starred_ids = get_freshrss_starred_items()

    if not starred_ids:
        logging.info("No starred items to sync. Exiting.")
        return

    synced_ids_set = set(synced_ids)

    new_ids = [item_id for item_id in starred_ids if item_id not in synced_ids_set]
    if not new_ids:
        logging.info("No new starred articles to sync. All up to date!")
        return
    logging.info(f"Found {len(new_ids)} new starred articles to sync")

    articles = get_freshrss_item_details(new_ids)
    if not articles:
        logging.error("Could not fetch article details. Exiting.")
        return

    access_token = get_wallabag_token()
    if not access_token:
        logging.error("Failed to authenticate with Wallabag. Exiting.")
        return

    success_count = 0
    newly_synced_ids = []
    for article in articles:
        article_id = article["id"]
        if add_to_wallabag(article, access_token):
            success_count += 1
            newly_synced_ids.append(article_id)
            time.sleep(WALLABAR_API_REQUEST_COOLDOWN)

    synced_ids.extend(newly_synced_ids)
    save_synced_articles(synced_ids)

    logging.info(f"Sync complete: {success_count}/{len(articles)} articles added to Wallabag")
    logging.info(f"Total tracked articles: {len(synced_ids)}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.error(f"FATAL ERROR: {e}")
        raise


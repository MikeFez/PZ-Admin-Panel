"""
Configuration module for Project Zomboid Admin Panel
Handles loading of configuration files and defines application constants
"""

import json
import os

# Define indicators that are application-specific
INDICATORS = {
    "server_started": "*** SERVER STARTED ***",
    "server_already_launched": "RakNet.Startup() return code: 5 (0 means success)",
    "server_quit": ">PAUSE",
    "user_logged_in": "ConnectionManager: [fully-connected]",
    "user_logged_out": "ConnectionManager: [disconnect]"
}

# Define file paths relative to the app directory
BASE_DIR = os.path.dirname(__file__)
CONFIG_DIR = os.path.join(BASE_DIR, '..', 'config')

CONFIG_FILE = os.path.join(CONFIG_DIR, 'config.json')
PLAYER_DB_FILE = os.path.join(CONFIG_DIR, 'players_db.json')
LOCATIONS_DB_FILE = os.path.join(CONFIG_DIR, 'locations_db.json')
MODS_DB_FILE = os.path.join(CONFIG_DIR, 'mods_db.json')

# Load main configuration
def load_config():
    """Load the main configuration from config.json"""
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: Config file {CONFIG_FILE} not found. Please create one at {CONFIG_FILE}")
        raise

# Load player database
def load_player_database():
    """Load player database from players_db.json"""
    try:
        with open(PLAYER_DB_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # Create empty database if it doesn't exist
        empty_db = {}
        save_player_database(empty_db)
        return empty_db

# Save player database
def save_player_database(data):
    """Save player database to players_db.json"""
    with open(PLAYER_DB_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# Load locations database
def load_locations_database():
    """Load locations database from locations_db.json"""
    try:
        with open(LOCATIONS_DB_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # Create empty database if it doesn't exist
        empty_db = {}
        save_locations_database(empty_db)
        return empty_db

# Save locations database
def save_locations_database(data):
    """Save locations database to locations_db.json"""
    with open(LOCATIONS_DB_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# Load mods database
def load_mods_database():
    """Load mods database from mods_db.json"""
    try:
        with open(MODS_DB_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # Create empty database if it doesn't exist
        empty_db = {}
        save_mods_database(empty_db)
        return empty_db

# Save mods database
def save_mods_database(data):
    """Save mods database to mods_db.json"""
    with open(MODS_DB_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# Initialize configuration on module import
CONFIG = load_config()

import subprocess
from time import sleep, time
from threading import Thread
from flask import Flask, redirect, render_template, url_for, request, jsonify, flash
import logging
import json
import os
from datetime import datetime
import re

# Import configuration module
from config import (
    CONFIG, INDICATORS,
    load_player_database, save_player_database,
    load_locations_database, save_locations_database,
    load_mods_database, save_mods_database,
    MODS_DB_FILE
)

# Global variables for server management
SERVER_SHOULD_QUIT = False
PROC = None
SERVER_STATUS = "Stopped"
SERVER_LOG = []
MAX_LOG_LINES = CONFIG['server']['max_log_lines']
SERVER_THREAD = None  # Track the server thread

ZOMBOID_SERVER_DIR = CONFIG['server']['zomboid_server_dir']
ZOMBOID_SERVER_LAUNCH = os.path.join(ZOMBOID_SERVER_DIR, CONFIG['server']['server_launch_file'])
ZOMBOID_SERVER_STARTED_INDICATOR = INDICATORS['server_started']
ZOMBOID_SERVER_ALREADY_LAUNCHED_INDICATOR = INDICATORS['server_already_launched']
ZOMBOID_SERVER_QUIT_INDICATOR = INDICATORS['server_quit']
ZOMBOID_USER_LOGGED_IN_INDICATOR = INDICATORS['user_logged_in']
ZOMBOID_USER_LOGGED_OUT_INDICATOR = INDICATORS['user_logged_out']

USERS = {}
# {
   # "user1": {
   #    "online": True,
   #    "last_seen": "timestamp",
   #    "first_seen": "timestamp"
   # }
# }

# Load databases using the config module
PLAYER_DATABASE = load_player_database()
LOCATIONS_DATABASE = load_locations_database()

# Configure Flask, add blueprints, and reduce logging
FLASK_APP = Flask(__name__)
FLASK_APP.secret_key = 'zomboid-admin-secret-key'
WEKZEUG_LOG = logging.getLogger("werkzeug")
WEKZEUG_LOG.disabled = True

# Add custom Jinja filter for checking mod installation status
@FLASK_APP.template_filter('is_mod_installed')
def is_mod_installed(mod_workshop_ids, current_workshop_ids):
    """Check if any of the mod's workshop IDs are in the current installed list"""
    return any(wid in current_workshop_ids for wid in mod_workshop_ids)

@FLASK_APP.route("/")
def index():
   # Merge current session users with persistent database
   all_players = dict(PLAYER_DATABASE)
   for username, user_data in USERS.items():
      if username in all_players:
         all_players[username].update(user_data)
      else:
         all_players[username] = user_data

   table_data = {
      "player_tp": [],
      "location_tp": []
   }

   # Use online players for teleport options
   online_players = [name for name, data in all_players.items() if data.get('online', False)]

   # Use only database locations (config locations have been migrated)
   all_locations = {}
   for name, data in LOCATIONS_DATABASE.items():
      all_locations[name] = data["coordinates"]

   for user_name in online_players:
      table_data["player_tp"].append({"location": user_name, "players": [player for player in online_players if player != user_name]})

   for location_name in all_locations.keys():
      table_data["location_tp"].append({"location": location_name, "players": online_players})

   return render_template("index.html", table_rows=table_data, players=online_players, server_status=SERVER_STATUS, users=all_players, locations=all_locations)

@FLASK_APP.route('/api/status')
def api_status():
   # Merge current session users with persistent database for API
   all_players = dict(PLAYER_DATABASE)
   for username, user_data in USERS.items():
      if username in all_players:
         all_players[username].update(user_data)
      else:
         all_players[username] = user_data

   return jsonify({
      'server_status': SERVER_STATUS,
      'users': all_players,
      'log_lines': SERVER_LOG[-50:] if SERVER_LOG else []  # Last 50 lines
   })

@FLASK_APP.route('/api/server/start', methods=['POST'])
def api_start_server():
   global PROC, SERVER_STATUS, SERVER_THREAD
   if SERVER_STATUS != "Stopped":
      return jsonify({'error': 'Server is already running or starting'}), 400

   try:
      SERVER_STATUS = "Starting"
      add_to_log("Server start command received - initializing...")
      # Start server in background thread
      SERVER_THREAD = Thread(target=run_server_in_thread, daemon=True)
      SERVER_THREAD.start()
      return jsonify({'message': 'Server start initiated'})
   except Exception as e:
      SERVER_STATUS = "Error"
      add_to_log(f"Failed to start server: {e}")
      return jsonify({'error': str(e)}), 500

@FLASK_APP.route('/api/server/stop', methods=['POST'])
def api_stop_server():
   global SERVER_STATUS
   if SERVER_STATUS == "Stopped":
      return jsonify({'error': 'Server is already stopped'}), 400

   SERVER_STATUS = "Stopping"

   # Try to send quit command if server is running
   if PROC and PROC.poll() is None:
      try:
         send_server_command("quit")
      except Exception as e:
         add_to_log(f"Error sending quit command: {e}")

   return jsonify({'message': 'Server stop initiated'})

@FLASK_APP.route('/api/command', methods=['POST'])
def api_send_command():
   data = request.get_json()
   command = data.get('command', '').strip()

   if not command:
      return jsonify({'error': 'Command cannot be empty'}), 400

   try:
      send_server_command(command)
      return jsonify({'message': f'Command sent: {command}'})
   except Exception as e:
      return jsonify({'error': str(e)}), 500

@FLASK_APP.route('/player_tp/<string:location>/<string:player>')
def player_tp(location, player):
   try:
      command = f'teleport "{player}" "{location}"'
      send_server_command(command)
      flash(f'Teleported {player} to {location}', 'success')
   except Exception as e:
      flash(f'Error sending teleport command: {str(e)}', 'error')
   return redirect(url_for('index'))

@FLASK_APP.route('/location_tp/<string:location>/<string:player>')
def location_tp(location, player):
   # Check if location exists in database
   if location not in LOCATIONS_DATABASE:
      flash(f'Unknown location: {location}', 'error')
      return redirect(url_for('index'))

   try:
      coordinates = LOCATIONS_DATABASE[location]["coordinates"]
      command = f'tpto "{player}" "{coordinates}"'
      send_server_command(command)
      flash(f'Teleported {player} to {location}', 'success')
   except Exception as e:
      flash(f'Error sending teleport command: {str(e)}', 'error')
   return redirect(url_for('index'))

@FLASK_APP.route("/quit")
def quit():
   global SERVER_SHOULD_QUIT
   # This route now shuts down the entire admin panel
   SERVER_SHOULD_QUIT = True

   # Also stop the game server if it's running
   if PROC and PROC.poll() is None:
      try:
         send_server_command("quit")
      except Exception as e:
         print(f"Error stopping server during shutdown: {e}")

   return f"<p>Shutting down Admin Panel...</p>"

@FLASK_APP.route("/mods")
def mods():
   try:
      mod_database = load_mods_database()

      # Get current server mods from ini file
      ini_file = CONFIG['server']['server_ini_file']
      current_workshop_ids, current_mod_ids = parse_ini_mods(ini_file)

      return render_template("mods.html",
                           mod_database=mod_database,
                           current_workshop_ids=current_workshop_ids,
                           current_mod_ids=current_mod_ids)
   except Exception as e:
      flash(f'Error loading mod database: {str(e)}', 'error')
      return redirect(url_for('index'))

@FLASK_APP.route('/api/mods', methods=['GET'])
def api_get_mods():
   try:
      mod_database = load_mods_database()
      
      # Get current server mods from ini file to determine installation status
      ini_file = CONFIG['server']['server_ini_file']
      current_workshop_ids, current_mod_ids = parse_ini_mods(ini_file)
      
      return jsonify({
         'mods': mod_database,
         'current_workshop_ids': current_workshop_ids,
         'current_mod_ids': current_mod_ids
      })
   except Exception as e:
      return jsonify({'error': str(e)}), 500

@FLASK_APP.route('/api/mods/add', methods=['POST'])
def api_add_mod():
   try:
      data = request.get_json()
      workshop_url = data.get('workshop_url', '').strip()
      mod_name = data.get('mod_name', '').strip()
      workshop_ids = [id.strip() for id in data.get('workshop_ids', '').split(',') if id.strip()]
      mod_ids = [id.strip() for id in data.get('mod_ids', '').split(',') if id.strip()]

      if not workshop_url or not mod_name or not workshop_ids or not mod_ids:
         return jsonify({'error': 'All fields are required'}), 400

      # Validate mod data
      validation_errors = validate_mod_data(workshop_ids, mod_ids)
      if validation_errors:
         return jsonify({'error': 'Validation failed', 'details': validation_errors}), 400

      mod_database = load_mods_database()

      mod_database[workshop_url] = {
         'workshop_item_name': mod_name,
         'workshop_ids': workshop_ids,
         'mod_ids': mod_ids,
         'enabled': True
      }

      save_mods_database(mod_database)

      return jsonify({'message': 'Mod added successfully'})
   except Exception as e:
      return jsonify({'error': str(e)}), 500

@FLASK_APP.route('/api/mods/remove', methods=['POST'])
def api_remove_mod():
   try:
      data = request.get_json()
      workshop_url = data.get('workshop_url', '').strip()

      if not workshop_url:
         return jsonify({'error': 'Workshop URL is required'}), 400

      mod_database = load_mods_database()

      if workshop_url not in mod_database:
         return jsonify({'error': 'Mod not found'}), 404

      del mod_database[workshop_url]

      save_mods_database(mod_database)

      return jsonify({'message': 'Mod removed successfully'})
   except Exception as e:
      return jsonify({'error': str(e)}), 500

@FLASK_APP.route('/api/mods/toggle', methods=['POST'])
def api_toggle_mod():
   try:
      data = request.get_json()
      workshop_url = data.get('workshop_url', '').strip()

      if not workshop_url:
         return jsonify({'error': 'Workshop URL is required'}), 400

      mod_database = load_mods_database()

      if workshop_url not in mod_database:
         return jsonify({'error': 'Mod not found'}), 404

      # Toggle the enabled state
      current_state = mod_database[workshop_url].get('enabled', True)
      mod_database[workshop_url]['enabled'] = not current_state

      save_mods_database(mod_database)

      new_state = mod_database[workshop_url]['enabled']
      return jsonify({
         'message': f'Mod {"enabled" if new_state else "disabled"} successfully',
         'enabled': new_state
      })
   except Exception as e:
      return jsonify({'error': str(e)}), 500

@FLASK_APP.route('/api/mods/apply', methods=['POST'])
def api_apply_mods():
   try:
      with open(MODS_DB_FILE, 'r') as f:
         mod_database = json.load(f)

      all_workshop_ids = []
      all_mod_ids = []
      enabled_count = 0

      # Only process enabled mods
      for url, mod_data in mod_database.items():
         if mod_data.get('enabled'):
            all_workshop_ids.extend(mod_data['workshop_ids'])
            all_mod_ids.extend(mod_data['mod_ids'])
            enabled_count += 1

      # Update the ini file
      ini_file = CONFIG['server']['server_ini_file']
      if not os.path.exists(ini_file):
         return jsonify({'error': f'Server ini file not found at: {ini_file}'}), 404

      success, result = update_ini_mods(ini_file, all_workshop_ids, all_mod_ids)

      if not success:
         return jsonify({'error': f'Failed to update ini file: {result}'}), 500

      add_to_log(f"Applied {enabled_count} enabled mods to server configuration")
      add_to_log(f"Created backup: {os.path.basename(result)}")
      
      # Recheck installation status after applying mods
      updated_workshop_ids, updated_mod_ids = parse_ini_mods(ini_file)
      
      return jsonify({
         'message': f'Applied {enabled_count} enabled mods to server configuration',
         'backup': os.path.basename(result),
         'workshop_ids_count': len(all_workshop_ids),
         'mod_ids_count': len(all_mod_ids),
         'current_workshop_ids': updated_workshop_ids,
         'current_mod_ids': updated_mod_ids
      })
   except Exception as e:
      return jsonify({'error': str(e)}), 500

@FLASK_APP.route('/api/mods/fetch-info', methods=['POST'])
def api_fetch_mod_info():
   try:
      import requests
      from bs4 import BeautifulSoup

      data = request.get_json()
      workshop_url = data.get('workshop_url', '').strip()

      if not workshop_url:
         return jsonify({'error': 'Workshop URL is required'}), 400

      # Extract workshop ID from URL
      if 'id=' in workshop_url:
         workshop_id = workshop_url.split('id=')[1].split('&')[0]
      else:
         return jsonify({'error': 'Invalid Steam Workshop URL'}), 400

      # Fetch the Steam Workshop page
      response = requests.get(workshop_url, timeout=10)
      if response.status_code != 200:
         return jsonify({'error': 'Failed to fetch workshop page'}), 400

      soup = BeautifulSoup(response.text, 'html.parser')

      # Extract mod name
      title_element = soup.find("div", class_="workshopItemTitle")
      if not title_element:
         return jsonify({'error': 'Could not find mod title on workshop page'}), 400

      mod_name = title_element.text.strip()

      # Try to extract mod IDs from description
      description_element = soup.find("div", class_="workshopItemDescription")
      mod_ids = []

      if description_element:
         description_text = description_element.get_text()
         # Look for common patterns that might contain mod IDs
         import re
         # This is a basic pattern - you might need to adjust based on your mods
         mod_id_patterns = re.findall(r'Mod\s*ID[:\s]*([a-zA-Z0-9_\-]+)', description_text, re.IGNORECASE)
         if mod_id_patterns:
            mod_ids = mod_id_patterns
         else:
            # Fallback: suggest using the workshop ID as mod ID
            mod_ids = [f"mod_{workshop_id}"]

      return jsonify({
         'mod_name': mod_name,
         'workshop_ids': [workshop_id],
         'mod_ids': mod_ids if mod_ids else [f"mod_{workshop_id}"],
         'suggested': True  # Indicates this is auto-suggested and should be verified
      })

   except ImportError:
      return jsonify({'error': 'Missing required libraries (requests, beautifulsoup4). Please install them.'}), 500
   except Exception as e:
      return jsonify({'error': f'Failed to fetch mod info: {str(e)}'}), 500

@FLASK_APP.route('/api/mods/backup', methods=['POST'])
def api_backup_mod_db():
   try:
      backup_file = os.path.join(os.path.dirname(__file__), '..', f'mod_db_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')

      import shutil
      shutil.copy2(MODS_DB_FILE, backup_file)

      return jsonify({'message': f'Backup created: {os.path.basename(backup_file)}'})
   except Exception as e:
      return jsonify({'error': str(e)}), 500

@FLASK_APP.route('/api/locations', methods=['GET'])
def api_get_locations():
   """Get all saved locations"""
   try:
      # Use only database locations
      all_locations = {}
      for name, data in LOCATIONS_DATABASE.items():
         all_locations[name] = data["coordinates"]

      return jsonify({
         'locations': all_locations,
         'database_locations': LOCATIONS_DATABASE
      })
   except Exception as e:
      return jsonify({'error': str(e)}), 500

@FLASK_APP.route('/api/locations/add', methods=['POST'])
def api_add_location():
   """Add a new location to the database"""
   try:
      data = request.get_json()
      name = data.get('name', '').strip()
      coordinates = data.get('coordinates', '').strip()
      description = data.get('description', '').strip()

      if not name or not coordinates:
         return jsonify({'error': 'Name and coordinates are required'}), 400

      if name in LOCATIONS_DATABASE:
         return jsonify({'error': f'Location "{name}" already exists'}), 400

      add_location_to_database(name, coordinates, description)

      return jsonify({'message': f'Location "{name}" added successfully'})
   except Exception as e:
      return jsonify({'error': str(e)}), 500

@FLASK_APP.route("/locations")
def locations():
   """Location management page"""
   try:
      # Merge current session users with persistent database
      all_players = dict(PLAYER_DATABASE)
      for username, user_data in USERS.items():
         if username in all_players:
            all_players[username].update(user_data)
         else:
            all_players[username] = user_data

      # Use only database locations
      return render_template("locations.html",
                           database_locations=LOCATIONS_DATABASE,
                           users=all_players,
                           server_status=SERVER_STATUS)
   except Exception as e:
      flash(f'Error loading locations: {str(e)}', 'error')
      return redirect(url_for('index'))

def launch_webui():
   def threaded_flask():
      host = CONFIG['server']['web_host']
      port = CONFIG['server']['web_port']
      print(f"Starting Flask @ http://{host}:{port}")
      FLASK_APP.run(host=host, port=port, debug=False)
      print("Flask thread stopped")
      return
   print("Starting webui thread")
   thread = Thread(target=threaded_flask, daemon=True)
   thread.start()
   print("\tWebUI thread configuration complete")
   return


def spawn_server():
   print("Launching server...")
   proc = subprocess.Popen(ZOMBOID_SERVER_LAUNCH, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE, shell=True, cwd=ZOMBOID_SERVER_DIR)
   print("\tServer launched!")
   return proc

def wait_for_server_ready(proc):
   print("Waiting for server to report it's ready...")
   for line in iter(proc.stdout.readline,''):
      decoded_line = line.decode('utf-8').strip()
      print(decoded_line)
      if ZOMBOID_SERVER_STARTED_INDICATOR in decoded_line:
         print("\tServer started!")
         break
      elif ZOMBOID_SERVER_ALREADY_LAUNCHED_INDICATOR in decoded_line:
         print("\tServer already started - killing this instance...")
         raise Exception("Server already started")
   return

def quit_server(proc):
   print("Sending quit command...")
   try:
      send_server_command("quit")
   except Exception as e:
      print(f"Error sending quit command: {e}")

   print("Command sent! Waiting for server to quit...")
   for line in iter(proc.stdout.readline,''):
      decoded_line = line.decode('utf-8').strip()
      print(decoded_line)
      if ZOMBOID_SERVER_QUIT_INDICATOR in decoded_line:
         print("\tServer quit!")
         break

   proc.terminate()
   proc.wait()
   print("Done!")
   return

def monitor_server(proc, kill_after_seconds=0):
   global SERVER_STATUS, SERVER_LOG
   start_time = time()
   SERVER_STATUS = "Running"

   while proc.poll() is None:
      try:
         line = proc.stdout.readline()
         if not line:
            break
         decoded_line = line.decode('utf-8', errors='ignore').strip()
         if decoded_line:
            print(decoded_line)
            add_to_log(decoded_line)
            scan_line(decoded_line)

         if kill_after_seconds != 0 and time() - start_time >= kill_after_seconds:
            break
         if SERVER_SHOULD_QUIT:
            break
      except Exception as e:
         print(f"Error reading server output: {e}")
         add_to_log(f"Monitor error: {e}")
         break

   SERVER_STATUS = "Stopped"
   return

def add_to_log(line):
   global SERVER_LOG
   timestamp = datetime.now().strftime("%H:%M:%S")
   SERVER_LOG.append(f"[{timestamp}] {line}")
   if len(SERVER_LOG) > MAX_LOG_LINES:
      SERVER_LOG = SERVER_LOG[-MAX_LOG_LINES:]

def scan_line(decoded_line):
   global USERS, SERVER_STATUS
   try:
      if ZOMBOID_USER_LOGGED_IN_INDICATOR in decoded_line:
         username = extract_username(decoded_line)
         if username:
            update_player_status(username, online=True)
      elif ZOMBOID_USER_LOGGED_OUT_INDICATOR in decoded_line:
         username = extract_username(decoded_line)
         if username:
            update_player_status(username, online=False)
      elif ZOMBOID_SERVER_STARTED_INDICATOR in decoded_line:
         SERVER_STATUS = "Running"
   except Exception as e:
      print(f"Error scanning line: {e}")

def extract_username(line):
   try:
      if 'username="' in line:
         return line.split('username="')[-1].split('"')[0]
   except:
      pass
   return None

def run_server_in_thread():
   global PROC, SERVER_STATUS
   try:
      add_to_log("Launching Project Zomboid server process...")
      proc = spawn_server()
      PROC = proc
      add_to_log("Server process started, waiting for server to become ready...")
      wait_for_server_ready(proc)
      add_to_log("Server is ready, monitoring output...")
      monitor_server(proc)
   except Exception as e:
      print(f"Server error: {e}")
      add_to_log(f"Server error: {e}")
      SERVER_STATUS = "Error"
   finally:
      # Clean up when server stops
      if PROC:
         if PROC.poll() is None:  # If still running, quit it
            quit_server(PROC)
      SERVER_STATUS = "Stopped"
      PROC = None
      print("Game server thread finished")

def main():
   """Main entry point for the Project Zomboid Admin Panel application"""
   global SERVER_SHOULD_QUIT, USERS, PLAYER_DATABASE
   print("Starting Project Zomboid Admin Panel...")
   print("Note: Game server will not start automatically. Use the web interface to start it.")

   # Load existing players into current session (mark all as offline initially)
   for username, player_data in PLAYER_DATABASE.items():
      USERS[username] = {
         "online": False,
         "last_seen": player_data.get("last_seen", "Unknown"),
         "first_seen": player_data.get("first_seen", "Unknown")
      }

   # Launch the web UI
   launch_webui()

   try:
      # Keep main thread alive (admin panel keeps running)
      while not SERVER_SHOULD_QUIT:
         sleep(1)
   except KeyboardInterrupt:
      print("Shutting down Admin Panel...")
      SERVER_SHOULD_QUIT = True

      # Stop the game server if it's running
      if PROC and PROC.poll() is None:
         try:
            print("Stopping game server...")
            send_server_command("quit")
            PROC.wait(timeout=10)
         except Exception as e:
            print(f"Error stopping game server: {e}")

   print("Admin Panel shut down.")

if __name__ == "__main__":
   main()

def parse_ini_mods(ini_file_path):
   """Parse WorkshopItems and Mods from the ini file safely with encoding detection"""
   current_workshop_ids = []
   current_mod_ids = []

   try:
      if not os.path.exists(ini_file_path):
         return current_workshop_ids, current_mod_ids

      # Try different encodings in order of preference
      encodings = ['utf-8', 'utf-8-sig', 'cp1252', 'iso-8859-1', 'latin1']
      content = None

      for encoding in encodings:
         try:
            with open(ini_file_path, 'r', encoding=encoding) as f:
               content = f.read()
            break
         except UnicodeDecodeError:
            continue

      if content is None:
         # Final fallback - read as binary and decode with error handling
         with open(ini_file_path, 'rb') as f:
            raw_content = f.read()
         content = raw_content.decode('utf-8', errors='replace')
         print("Using fallback encoding with error replacement")

      # Use regex for more robust parsing
      import re

      # Parse WorkshopItems - only match lines that start with WorkshopItems=
      workshop_match = re.search(r'^WorkshopItems\s*=\s*(.*)$', content, re.MULTILINE)
      if workshop_match:
         workshop_text = workshop_match.group(1).strip()
         current_workshop_ids = [id.strip() for id in workshop_text.split(';') if id.strip()]

      # Parse Mods - only match lines that start with Mods=
      mods_match = re.search(r'^Mods\s*=\s*(.*)$', content, re.MULTILINE)
      if mods_match:
         mods_text = mods_match.group(1).strip()
         current_mod_ids = [id.strip() for id in mods_text.split(';') if id.strip()]

   except Exception as e:
      print(f"Error parsing ini file: {e}")
      add_to_log(f"Error parsing ini file: {e}")

   return current_workshop_ids, current_mod_ids

def update_ini_mods(ini_file_path, workshop_ids, mod_ids):
   """Update the ini file with new mod configurations safely"""
   try:
      # Create backup
      import shutil
      backup_path = f"{ini_file_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
      shutil.copy2(ini_file_path, backup_path)

      # Remove duplicates while preserving order
      workshop_ids = list(dict.fromkeys(workshop_ids))
      mod_ids = list(dict.fromkeys(mod_ids))

      # Validate IDs (basic validation)
      workshop_ids = [id for id in workshop_ids if id.isdigit()]
      mod_ids = [id for id in mod_ids if re.match(r'^[a-zA-Z0-9_\-&%\(\)\s]+$', id)]

      # Read file with same encoding detection as parse_ini_mods
      encodings = ['utf-8', 'utf-8-sig', 'cp1252', 'iso-8859-1', 'latin1']
      content = None
      detected_encoding = 'utf-8'

      for encoding in encodings:
         try:
            with open(ini_file_path, 'r', encoding=encoding) as f:
               content = f.read()
            detected_encoding = encoding
            break
         except UnicodeDecodeError:
            continue

      if content is None:
         # Final fallback - read as binary and decode with error handling
         with open(ini_file_path, 'rb') as f:
            raw_content = f.read()
         content = raw_content.decode('utf-8', errors='replace')
         detected_encoding = 'utf-8'

      # Replace WorkshopItems - only match lines that start with WorkshopItems=
      workshop_line = "WorkshopItems=" + ";".join(workshop_ids)
      old_content = content
      content = re.sub(r'^WorkshopItems\s*=.*$', workshop_line, content, flags=re.MULTILINE)
      if old_content != content:
         print(f"Updated WorkshopItems line to: {workshop_line}")

      # Replace Mods - only match lines that start with Mods=
      mods_line = "Mods=" + ";".join(mod_ids)
      old_content = content
      content = re.sub(r'^Mods\s*=.*$', mods_line, content, flags=re.MULTILINE)
      if old_content != content:
         print(f"Updated Mods line to: {mods_line}")

      # Write back with the detected encoding
      with open(ini_file_path, 'w', encoding=detected_encoding) as f:
         f.write(content)

      return True, backup_path
   except Exception as e:
      return False, str(e)

def validate_mod_data(workshop_ids, mod_ids):
   """Validate mod IDs and workshop IDs"""
   errors = []

   # Validate workshop IDs (should be numeric)
   for wid in workshop_ids:
      if not wid.isdigit():
         errors.append(f"Invalid workshop ID: {wid} (must be numeric)")

   # Validate mod IDs (alphanumeric with some special chars)
   for mid in mod_ids:
      if not re.match(r'^[a-zA-Z0-9_\-&%\(\)\s]+$', mid):
         errors.append(f"Invalid mod ID: {mid} (contains invalid characters)")

   return errors

def save_player_database_local():
   """Save the player database to file"""
   try:
      save_player_database(PLAYER_DATABASE)
   except Exception as e:
      print(f"Error saving player database: {e}")

def update_player_status(username, online=True):
   """Update player status in both memory and persistent database"""
   global USERS, PLAYER_DATABASE

   timestamp = datetime.now().isoformat()

   # Update memory (for current session) - includes ephemeral data
   if username not in USERS:
      USERS[username] = {"online": online, "last_seen": timestamp, "is_admin": False}
   else:
      USERS[username]["online"] = online
      USERS[username]["last_seen"] = timestamp
      # Preserve is_admin status if it exists, otherwise default to False
      if "is_admin" not in USERS[username]:
         USERS[username]["is_admin"] = False

   # Update persistent database - only non-ephemeral data
   if username not in PLAYER_DATABASE:
      PLAYER_DATABASE[username] = {
         "first_seen": timestamp,
         "last_seen": timestamp,
         "allow_admin": False
      }
   else:
      PLAYER_DATABASE[username]["last_seen"] = timestamp

   save_player_database_local()
   add_to_log(f"Player {username} {'connected' if online else 'disconnected'}")

def save_locations_database_local():
   """Save the locations database to file"""
   try:
      save_locations_database(LOCATIONS_DATABASE)
   except Exception as e:
      print(f"Error saving locations database: {e}")

def add_location_to_database(name, coordinates, description=""):
   """Add a new location to the database"""
   global LOCATIONS_DATABASE

   LOCATIONS_DATABASE[name] = {
      "coordinates": coordinates,
      "description": description,
      "created": datetime.now().isoformat()
   }

   save_locations_database_local()
   add_to_log(f"Added location '{name}' at coordinates {coordinates}")

@FLASK_APP.route('/api/locations/edit', methods=['POST'])
def api_edit_location():
   """Edit an existing location in the database"""
   try:
      data = request.get_json()
      old_name = data.get('old_name', '').strip()
      new_name = data.get('new_name', '').strip()
      coordinates = data.get('coordinates', '').strip()
      description = data.get('description', '').strip()

      if not old_name or not new_name or not coordinates:
         return jsonify({'error': 'Old name, new name, and coordinates are required'}), 400

      if old_name not in LOCATIONS_DATABASE:
         return jsonify({'error': f'Location "{old_name}" not found'}), 404

      # If name is changing, check if new name already exists
      if old_name != new_name and new_name in LOCATIONS_DATABASE:
         return jsonify({'error': f'Location "{new_name}" already exists'}), 400

      # Update the location
      location_data = LOCATIONS_DATABASE[old_name].copy()
      location_data['coordinates'] = coordinates
      location_data['description'] = description
      location_data['modified'] = datetime.now().isoformat()

      # If name changed, remove old entry and add new one
      if old_name != new_name:
         del LOCATIONS_DATABASE[old_name]
         LOCATIONS_DATABASE[new_name] = location_data
         add_to_log(f"Renamed location '{old_name}' to '{new_name}' and updated coordinates to {coordinates}")
      else:
         LOCATIONS_DATABASE[old_name] = location_data
         add_to_log(f"Updated location '{old_name}' coordinates to {coordinates}")

      save_locations_database_local()

      return jsonify({'message': f'Location updated successfully'})
   except Exception as e:
      return jsonify({'error': str(e)}), 500

@FLASK_APP.route('/api/locations/delete', methods=['POST'])
def api_delete_location():
   """Delete a location from the database"""
   try:
      data = request.get_json()
      name = data.get('name', '').strip()

      if not name:
         return jsonify({'error': 'Location name is required'}), 400

      if name not in LOCATIONS_DATABASE:
         return jsonify({'error': f'Location "{name}" not found'}), 404

      del LOCATIONS_DATABASE[name]
      save_locations_database_local()
      add_to_log(f"Deleted location '{name}'")

      return jsonify({'message': f'Location "{name}" deleted successfully'})
   except Exception as e:
      return jsonify({'error': str(e)}), 500

@FLASK_APP.route('/api/players/grant-admin', methods=['POST'])
def api_grant_admin():
   """Grant admin permissions to a player"""
   try:
      data = request.get_json()
      username = data.get('username', '').strip()

      if not username:
         return jsonify({'error': 'Username is required'}), 400

      if username not in PLAYER_DATABASE:
         return jsonify({'error': f'Player "{username}" not found'}), 404

      # Check if admin management is allowed for this player
      if not PLAYER_DATABASE[username].get('allow_admin', False):
         return jsonify({'error': f'Admin management not enabled for "{username}"'}), 403

      # Check if player is currently online
      if username not in USERS or not USERS[username].get('online', False):
         return jsonify({'error': f'Player "{username}" is not currently online'}), 400

      # Check if server is running
      if SERVER_STATUS != 'Running' or not PROC:
         return jsonify({'error': 'Server must be running to grant admin permissions'}), 400      # Send the actual admin command to the server
      command = f'setaccesslevel "{username}" admin'
      try:
         send_server_command(command)

         # Set admin status in memory
         USERS[username]['is_admin'] = True

         return jsonify({'message': f'Admin status granted to "{username}"'})
      except Exception as e:
         return jsonify({'error': f'Failed to send admin command: {str(e)}'}), 500
   except Exception as e:
      return jsonify({'error': str(e)}), 500

@FLASK_APP.route('/api/players/remove-admin', methods=['POST'])
def api_remove_admin():
   """Remove admin permissions from a player"""
   try:
      data = request.get_json()
      username = data.get('username', '').strip()

      if not username:
         return jsonify({'error': 'Username is required'}), 400

      if username not in PLAYER_DATABASE:
         return jsonify({'error': f'Player "{username}" not found'}), 404

      # Check if admin management is allowed for this player
      if not PLAYER_DATABASE[username].get('allow_admin', False):
         return jsonify({'error': f'Admin management not enabled for "{username}"'}), 403

      # Check if player is currently online
      if username not in USERS or not USERS[username].get('online', False):
         return jsonify({'error': f'Player "{username}" is not currently online'}), 400

      # Check if server is running
      if SERVER_STATUS != 'Running' or not PROC:
         return jsonify({'error': 'Server must be running to remove admin permissions'}), 400      # Send the actual remove admin command to the server
      command = f'setaccesslevel "{username}" none'
      try:
         send_server_command(command)

         # Set admin status in memory
         USERS[username]['is_admin'] = False

         return jsonify({'message': f'Admin status removed from "{username}"'})
      except Exception as e:
         return jsonify({'error': f'Failed to send remove admin command: {str(e)}'}), 500
   except Exception as e:
      return jsonify({'error': str(e)}), 500

def send_server_command(command):
   """Send a command to the Project Zomboid server process"""
   global PROC

   if not PROC or PROC.poll() is not None:
      raise Exception("Server is not running")

   try:
      # Ensure command ends with newline
      if not command.endswith('\n'):
         command += '\n'

      PROC.stdin.write(command.encode('utf-8'))
      PROC.stdin.flush()
      add_to_log(f"Sent command to server: {command.strip()}")
      return True
   except Exception as e:
      add_to_log(f"Failed to send command '{command.strip()}': {e}")
      raise e

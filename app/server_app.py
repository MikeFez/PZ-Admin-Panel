import subprocess
from time import sleep, time
from threading import Thread
from flask import Flask, redirect, render_template, url_for, request, jsonify, flash
import logging
import json
import os
from datetime import datetime
import re

# Load configuration
CONFIG_FILE = os.path.join(os.path.dirname(__file__), '..', 'config.json')
try:
    with open(CONFIG_FILE, 'r') as f:
        CONFIG = json.load(f)
except FileNotFoundError:
    print(f"Warning: Config file {CONFIG_FILE} not found. Please create one at {CONFIG_FILE}")
    raise

# Global variables for server management
SERVER_SHOULD_QUIT = False
PROC = None
SERVER_STATUS = "Stopped"
SERVER_LOG = []
MAX_LOG_LINES = CONFIG['server']['max_log_lines']
SERVER_THREAD = None  # Track the server thread

ZOMBOID_SERVER_DIR = CONFIG['server']['zomboid_server_dir']
ZOMBOID_SERVER_LAUNCH = os.path.join(ZOMBOID_SERVER_DIR, CONFIG['server']['server_launch_file'])
ZOMBOID_SERVER_STARTED_INDICATOR = CONFIG['indicators']['server_started']
ZOMBOID_SERVER_ALREADY_LAUNCHED_INDICATOR = CONFIG['indicators']['server_already_launched']
ZOMBOID_SERVER_QUIT_INDICATOR = CONFIG['indicators']['server_quit']
ZOMBOID_USER_LOGGED_IN_INDICATOR = CONFIG['indicators']['user_logged_in']
ZOMBOID_USER_LOGGED_OUT_INDICATOR = CONFIG['indicators']['user_logged_out']

LOCATIONS = CONFIG['locations']

USERS = {}
# {
   # "user1": {
   #    "online": True,
   # }
# }

# Configure Flask, add blueprints, and reduce logging
FLASK_APP = Flask(__name__)
FLASK_APP.secret_key = 'zomboid-admin-secret-key'
WEKZEUG_LOG = logging.getLogger("werkzeug")
WEKZEUG_LOG.disabled = True

@FLASK_APP.route("/")
def index():
   table_data = {
      "player_tp": [],
      "location_tp": []
   }
   for user_name, user_data in USERS.items():
      table_data["player_tp"].append({"location": user_name, "players": [player for player in USERS.keys() if player != user_name]})

   for location_name in LOCATIONS.keys():
      table_data["location_tp"].append({"location": location_name, "players": USERS.keys()})
   return render_template("index.html", table_rows=table_data, players = USERS.keys(), server_status=SERVER_STATUS, users=USERS)

@FLASK_APP.route('/api/status')
def api_status():
   return jsonify({
      'server_status': SERVER_STATUS,
      'users': USERS,
      'log_lines': SERVER_LOG[-50:] if SERVER_LOG else []  # Last 50 lines
   })

@FLASK_APP.route('/api/server/start', methods=['POST'])
def api_start_server():
   global PROC, SERVER_STATUS, SERVER_THREAD
   if SERVER_STATUS != "Stopped":
      return jsonify({'error': 'Server is already running or starting'}), 400

   try:
      SERVER_STATUS = "Starting"
      # Start server in background thread
      SERVER_THREAD = Thread(target=run_server_in_thread, daemon=True)
      SERVER_THREAD.start()
      return jsonify({'message': 'Server start initiated'})
   except Exception as e:
      SERVER_STATUS = "Error"
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
         PROC.stdin.write("quit\n".encode('utf-8'))
         PROC.stdin.flush()
         add_to_log("Server stop command sent")
      except Exception as e:
         add_to_log(f"Error sending quit command: {e}")

   return jsonify({'message': 'Server stop initiated'})

@FLASK_APP.route('/api/command', methods=['POST'])
def api_send_command():
   global PROC
   data = request.get_json()
   command = data.get('command', '').strip()

   if not command:
      return jsonify({'error': 'Command cannot be empty'}), 400

   if not PROC or PROC.poll() is not None:
      return jsonify({'error': 'Server is not running'}), 400

   try:
      PROC.stdin.write(f"{command}\n".encode('utf-8'))
      PROC.stdin.flush()
      return jsonify({'message': f'Command sent: {command}'})
   except Exception as e:
      return jsonify({'error': str(e)}), 500

@FLASK_APP.route('/player_tp/<string:location>/<string:player>')
def player_tp(location, player):
   if not PROC or PROC.poll() is not None:
      flash('Server is not running!', 'error')
      return redirect(url_for('index'))

   try:
      command = f'teleport "{player}" "{location}"'
      PROC.stdin.write(f"{command}\n".encode('utf-8'))
      PROC.stdin.flush()
      flash(f'Teleported {player} to {location}', 'success')
   except Exception as e:
      flash(f'Error sending teleport command: {str(e)}', 'error')
   return redirect(url_for('index'))

@FLASK_APP.route('/location_tp/<string:location>/<string:player>')
def location_tp(location, player):
   if not PROC or PROC.poll() is not None:
      flash('Server is not running!', 'error')
      return redirect(url_for('index'))

   if location not in LOCATIONS:
      flash(f'Unknown location: {location}', 'error')
      return redirect(url_for('index'))

   try:
      command = f'tpto "{player}" "{LOCATIONS[location]}"'
      PROC.stdin.write(f"{command}\n".encode('utf-8'))
      PROC.stdin.flush()
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
         PROC.stdin.write("quit\n".encode('utf-8'))
         PROC.stdin.flush()
      except Exception as e:
         print(f"Error stopping server during shutdown: {e}")

   return f"<p>Shutting down Admin Panel...</p>"

@FLASK_APP.route("/mods")
def mods():
   try:
      mod_db_file = os.path.join(os.path.dirname(__file__), '..', 'mod_db.json')
      with open(mod_db_file, 'r') as f:
         mod_database = json.load(f)

      # Get current server mods from ini file
      ini_file = CONFIG['server']['server_ini_file']
      current_workshop_ids = []
      current_mod_ids = []

      if os.path.exists(ini_file):
         with open(ini_file, 'r') as f:
            for line in f:
               if line.startswith('WorkshopItems='):
                  current_workshop_ids = [id.strip() for id in line.split('=')[1].strip().split(';') if id.strip()]
               elif line.startswith('Mods='):
                  current_mod_ids = [id.strip() for id in line.split('=')[1].strip().split(';') if id.strip()]

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
      mod_db_file = os.path.join(os.path.dirname(__file__), '..', 'mod_db.json')
      with open(mod_db_file, 'r') as f:
         mod_database = json.load(f)
      return jsonify({'mods': mod_database})
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

      mod_db_file = os.path.join(os.path.dirname(__file__), '..', 'mod_db.json')
      with open(mod_db_file, 'r') as f:
         mod_database = json.load(f)

      mod_database[workshop_url] = {
         'workshop_item_name': mod_name,
         'workshop_ids': workshop_ids,
         'mod_ids': mod_ids,
         'enabled': True
      }

      with open(mod_db_file, 'w') as f:
         json.dump(mod_database, f, indent=4)

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

      mod_db_file = os.path.join(os.path.dirname(__file__), '..', 'mod_db.json')
      with open(mod_db_file, 'r') as f:
         mod_database = json.load(f)

      if workshop_url not in mod_database:
         return jsonify({'error': 'Mod not found'}), 404

      del mod_database[workshop_url]

      with open(mod_db_file, 'w') as f:
         json.dump(mod_database, f, indent=4)

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

      mod_db_file = os.path.join(os.path.dirname(__file__), '..', 'mod_db.json')
      with open(mod_db_file, 'r') as f:
         mod_database = json.load(f)

      if workshop_url not in mod_database:
         return jsonify({'error': 'Mod not found'}), 404

      # Toggle the enabled state
      current_state = mod_database[workshop_url].get('enabled', True)
      mod_database[workshop_url]['enabled'] = not current_state

      with open(mod_db_file, 'w') as f:
         json.dump(mod_database, f, indent=4)

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
      mod_db_file = os.path.join(os.path.dirname(__file__), '..', 'mod_db.json')
      with open(mod_db_file, 'r') as f:
         mod_database = json.load(f)

      all_workshop_ids = []
      all_mod_ids = []
      enabled_count = 0

      # Only process enabled mods
      for url, mod_data in mod_database.items():
         if mod_data.get('enabled', True):  # Default to True for backward compatibility
            all_workshop_ids.extend(mod_data['workshop_ids'])
            all_mod_ids.extend(mod_data['mod_ids'])
            enabled_count += 1

      # Update the ini file
      ini_file = CONFIG['server']['server_ini_file']
      if not os.path.exists(ini_file):
         return jsonify({'error': f'Server ini file not found at: {ini_file}'}), 404

      replacement_data = {
         "WorkshopItems=": "WorkshopItems=" + ";".join(all_workshop_ids) + "\n",
         "Mods=": "Mods=" + ";".join(all_mod_ids) + "\n",
      }

      with open(ini_file, "r") as f:
         lines = f.readlines()
         for i, line in enumerate(lines):
            for identifier, replacement_line in replacement_data.items():
               if line.startswith(identifier):
                  lines[i] = replacement_line

      with open(ini_file, "w") as f:
         f.writelines(lines)

      add_to_log(f"Applied {enabled_count} enabled mods to server configuration")
      return jsonify({'message': f'Applied {enabled_count} enabled mods to server configuration'})
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
      mod_db_file = os.path.join(os.path.dirname(__file__), '..', 'mod_db.json')
      backup_file = os.path.join(os.path.dirname(__file__), '..', f'mod_db_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')

      import shutil
      shutil.copy2(mod_db_file, backup_file)

      return jsonify({'message': f'Backup created: {os.path.basename(backup_file)}'})
   except Exception as e:
      return jsonify({'error': str(e)}), 500

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
   proc.stdin.write("quit\n".encode('utf-8'))
   proc.stdin.flush()
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
            if username not in USERS:
               USERS[username] = {"last_seen": datetime.now().isoformat()}
            USERS[username]["online"] = True
            add_to_log(f"User {username} logged in")
      elif ZOMBOID_USER_LOGGED_OUT_INDICATOR in decoded_line:
         username = extract_username(decoded_line)
         if username and username in USERS:
            USERS[username]["online"] = False
            USERS[username]["last_seen"] = datetime.now().isoformat()
            add_to_log(f"User {username} logged out")
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
      proc = spawn_server()
      PROC = proc
      wait_for_server_ready(proc)
      monitor_server(proc)
   except Exception as e:
      print(f"Server error: {e}")
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
   global SERVER_SHOULD_QUIT
   print("Starting Project Zomboid Admin Panel...")
   print("Note: Game server will not start automatically. Use the web interface to start it.")

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
            PROC.stdin.write("quit\n".encode('utf-8'))
            PROC.stdin.flush()
            PROC.wait(timeout=10)
         except Exception as e:
            print(f"Error stopping game server: {e}")

   print("Admin Panel shut down.")

if __name__ == "__main__":
   main()

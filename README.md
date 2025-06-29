# Project Zomboid Server Admin Panel

A modern, responsive web-based administration panel for managing Project Zomboid dedicated servers.

## Features

### 🎮 Server Management
- **Start/Stop/Restart Server**: Full control over server lifecycle
- **Real-time Status Monitoring**: Live server status updates
- **Command Console**: Send any server command directly
- **Server Log Viewer**: Monitor server output in real-time

### 👥 Player Management
- **Live Player List**: See who's online/offline
- **Player Teleportation**: Teleport players to each other or to predefined locations
- **Player Activity Tracking**: Last seen timestamps for offline players

### 🧩 Mod Management
- **Visual Mod Database**: Browse and manage your mod collection
- **Steam Workshop Integration**: Auto-fetch mod information from Workshop URLs
- **One-Click Mod Application**: Apply selected mods to server configuration
- **Mod Search & Filtering**: Find mods quickly in large collections
- **Backup & Restore**: Create backups of your mod database
- **Active Mod Tracking**: See which mods are currently active on the server

### 🚀 Quick Actions
- **Save World**: Instantly save the game world
- **Server Announcements**: Send messages to all players
- **Time Control**: Set day/night cycle
- **Refresh Status**: Manual status updates

### 🎨 Modern UI
- **Responsive Design**: Works on desktop, tablet, and mobile
- **Real-time Updates**: Auto-refreshing every 5 seconds
- **Beautiful Gradients**: Modern visual design
- **Interactive Elements**: Smooth animations and transitions

## Installation

1. **Install Python Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Initial Setup**:
   On first run, the application will create a `config/` directory with default configuration files.
   
3. **Configure Settings**:
   Edit `config/config.json` to match your server setup:
   ```json
   {
     "server": {
       "zomboid_server_dir": "C:\\Program Files (x86)\\Steam\\steamapps\\common\\Project Zomboid Dedicated Server",
       "server_launch_file": "StartServer64.bat",
       "server_ini_file": "C:\\Users\\YourUser\\Zomboid\\Server\\servertest.ini",
       "web_host": "0.0.0.0",
       "web_port": 5000,
       "max_log_lines": 1000
     }
   }
   ```

3. **Run the Admin Panel**:
   ```bash
   python main.py
   ```

   Or run directly from the app directory:
   ```bash
   cd app
   python server_app.py
   ```

4. **Access the Web Interface**:
   Open your browser to `http://localhost:5000`

## Configuration

### Configuration Files

All configuration and database files are stored in the `config/` directory:

- **`config.json`**: Main application configuration
- **`players_db.json`**: Player database (persistent data)
- **`locations_db.json`**: Saved teleport locations
- **`mods_db.json`**: Mod collection database

### Server Settings (`config/config.json`)

```json
{
  "server": {
    "zomboid_server_dir": "C:\\Path\\To\\Project Zomboid Dedicated Server",
    "server_launch_file": "StartServer64.bat",
    "server_ini_file": "C:\\Users\\YourUser\\Zomboid\\Server\\servertest.ini",
    "web_host": "0.0.0.0",
    "web_port": 5000,
    "max_log_lines": 1000
  }
}
```

**Configuration Options:**
- `zomboid_server_dir`: Path to your Project Zomboid server installation
- `server_launch_file`: Server executable filename (usually `StartServer64.bat`)
- `server_ini_file`: Path to your server's configuration INI file
- `web_host`: Web interface host (`"0.0.0.0"` for network access, `"127.0.0.1"` for local only)
- `web_port`: Web interface port (default: 5000)
- `max_log_lines`: Maximum number of log lines to keep in memory (default: 1000)

### Database Files

#### Player Database (`config/players_db.json`)
Stores persistent player information:
```json
{
  "PlayerName": {
    "first_seen": "2024-01-01T12:00:00",
    "last_seen": "2024-01-01T15:30:00",
    "allow_admin": false
  }
}
```

**Manual Management:**
- **Reset player data**: Delete specific entries or clear the entire file
- **Grant admin privileges**: Set `"allow_admin": true` for specific players
- **Backup**: Copy the file before making manual changes

#### Locations Database (`config/locations_db.json`)
Stores saved teleport locations:
```json
{
  "LocationName": {
    "coordinates": "x,y,z",
    "description": "Optional description",
    "created": "2024-01-01T12:00:00"
  }
}
```

**Manual Management:**
- **Add locations**: Add new entries with coordinates in "x,y,z" format
- **Modify coordinates**: Update existing location coordinates
- **Bulk import**: Add multiple locations from spreadsheets or other sources

#### Mod Database (`config/mods_db.json`)
Stores mod collection and configurations:
```json
{
  "https://steamcommunity.com/sharedfiles/filedetails/?id=123456": {
    "workshop_item_name": "Mod Name",
    "workshop_ids": ["123456"],
    "mod_ids": ["ModID"],
    "enabled": true
  }
}
```

**Manual Management:**
- **Bulk mod import**: Add multiple mods programmatically
- **Enable/disable mods**: Change `"enabled"` status for multiple mods
- **Cleanup**: Remove unused or broken mod entries

## Using the Mod Manager

The integrated mod manager allows you to easily manage your Project Zomboid server mods:

### Adding Mods
1. **Navigate to Mod Manager**: Click "Manage Mods" from the main admin panel
2. **Add Workshop URL**: Paste a Steam Workshop mod URL
3. **Auto-Fill Information**: Click "Auto-Fill" to automatically fetch mod details
4. **Verify Details**: Check that Workshop IDs and Mod IDs are correct
5. **Add to Database**: Click "Add Mod" to save to your mod database

### Applying Mods
1. **Select Mods**: Check the boxes next to mods you want to activate
2. **Apply Configuration**: Click "Apply Selected Mods"
3. **Restart Server**: Restart your server for changes to take effect

### Managing Your Collection
- **Search**: Use the search box to find specific mods
- **Quick Selection**: Use "Select All", "Clear Selection", or "Select Active Mods"
- **Remove Mods**: Click the red "Remove" button to delete mods from database
- **Backup**: Create backups of your mod database before major changes

## Configuration

### Configuration Files

All configuration and database files are stored in the `config/` directory:

- **`config.json`**: Main application configuration
- **`players_db.json`**: Player database (persistent data)
- **`locations_db.json`**: Saved teleport locations
- **`mods_db.json`**: Mod collection database

### Server Settings (`config/config.json`)

```json
{
  "server": {
    "zomboid_server_dir": "C:\\Path\\To\\Project Zomboid Dedicated Server",
    "server_launch_file": "StartServer64.bat",
    "server_ini_file": "C:\\Users\\YourUser\\Zomboid\\Server\\servertest.ini",
    "web_host": "0.0.0.0",
    "web_port": 5000,
    "max_log_lines": 1000
  }
}
```

**Configuration Options:**
- `zomboid_server_dir`: Path to your Project Zomboid server installation
- `server_launch_file`: Server executable filename (usually `StartServer64.bat`)
- `server_ini_file`: Path to your server's configuration INI file
- `web_host`: Web interface host (`"0.0.0.0"` for network access, `"127.0.0.1"` for local only)
- `web_port`: Web interface port (default: 5000)
- `max_log_lines`: Maximum number of log lines to keep in memory (default: 1000)

### Database Files

#### Player Database (`config/players_db.json`)
Stores persistent player information:
```json
{
  "PlayerName": {
    "first_seen": "2024-01-01T12:00:00",
    "last_seen": "2024-01-01T15:30:00",
    "allow_admin": false
  }
}
```

**Manual Management:**
- **Reset player data**: Delete specific entries or clear the entire file
- **Grant admin privileges**: Set `"allow_admin": true` for specific players
- **Backup**: Copy the file before making manual changes

#### Locations Database (`config/locations_db.json`)
Stores saved teleport locations:
```json
{
  "LocationName": {
    "coordinates": "x,y,z",
    "description": "Optional description",
    "created": "2024-01-01T12:00:00"
  }
}
```

**Manual Management:**
- **Add locations**: Add new entries with coordinates in "x,y,z" format
- **Modify coordinates**: Update existing location coordinates
- **Bulk import**: Add multiple locations from spreadsheets or other sources

#### Mod Database (`config/mods_db.json`)
Stores mod collection and configurations:
```json
{
  "https://steamcommunity.com/sharedfiles/filedetails/?id=123456": {
    "workshop_item_name": "Mod Name",
    "workshop_ids": ["123456"],
    "mod_ids": ["ModID"],
    "enabled": true
  }
}
```

**Manual Management:**
- **Bulk mod import**: Add multiple mods programmatically
- **Enable/disable mods**: Change `"enabled"` status for multiple mods
- **Cleanup**: Remove unused or broken mod entries

### Backup and Recovery

Since all configuration is stored in the `config/` directory, backing up your setup is simple:

1. **Create Backup**:
   ```bash
   # Copy entire config directory
   cp -r config/ config_backup_$(date +%Y%m%d)/
   ```

2. **Restore from Backup**:
   ```bash
   # Restore config directory
   cp -r config_backup_20240101/ config/
   ```

3. **Selective Restore**:
   - Replace individual files (e.g., just `players_db.json`)
   - Merge databases manually for partial restores

## API Endpoints

The panel provides a REST API for programmatic access:

- `GET /api/status` - Get server status and recent logs
- `POST /api/server/start` - Start the server
- `POST /api/server/stop` - Stop the server
- `POST /api/command` - Send a command to the server

## Security Notes

- The web interface has no authentication by default
- Only run on trusted networks
- Consider setting up a reverse proxy with authentication for internet access
- The panel has full control over your server

## Troubleshooting

### Server Won't Start
- Check that the `zomboid_server_dir` path is correct in `config/config.json`
- Verify the `server_launch_file` exists in the server directory
- Ensure you have permission to execute the server
- Check that the `server_ini_file` path is correct

### Players Not Showing Up
- Monitor the server log for login/logout messages
- Check if player events are being detected in the admin panel logs
- Verify the server is properly outputting user connection messages

### Web Interface Not Accessible
- Verify the port isn't blocked by firewall
- Check that Flask is binding to the correct host/port in `config/config.json`
- Look for error messages in the console output

### Configuration Issues
- If the application fails to start, check that `config/config.json` exists and is valid JSON
- Missing database files will be created automatically on first run
- Backup your `config/` directory before making manual changes

## Development

The panel is built with:
- **Backend**: Python Flask
- **Frontend**: Bootstrap 5, Font Awesome icons
- **Real-time Updates**: JavaScript fetch API with auto-refresh

### File Structure
```
├── app/                      # Application code directory
│   ├── __init__.py          # Package initialization
│   ├── server_app.py        # Main Flask application
│   ├── config.py            # Configuration and database management
│   ├── ini_file_inject_mods_from_db.py  # Mod injection utility
│   └── templates/           # Web interface templates
│       ├── index.html       # Main admin panel template
│       ├── mods.html        # Mod manager template
│       └── locations.html   # Location management template
├── config/                  # Configuration and database files (gitignored)
│   ├── config.json         # Main application configuration
│   ├── players_db.json     # Player database
│   ├── locations_db.json   # Saved locations
│   └── mods_db.json        # Mod collection database
├── main.py                 # Main entry point
├── requirements.txt        # Python dependencies
├── .gitignore              # Git ignore rules
└── README.md              # This file
```

### Adding New Features
1. Add API endpoints in `app/server_app.py`
2. Update the HTML templates in `app/templates/` for UI changes
3. Modify `config/config.json` for new settings
4. Update `app/config.py` for new configuration options
5. Test thoroughly before deploying

### Configuration Management
- All config/database loading is centralized in `app/config.py`
- Use the provided loader/saver functions instead of direct file operations
- The `config/` directory is gitignored to prevent accidental commits of sensitive data

## Important Notes

### Git and Version Control
- The `config/` directory is included in `.gitignore` to prevent committing sensitive server configuration and player data
- When setting up on a new system, you'll need to manually create your `config/` files or copy them from a backup
- Consider keeping a template version of `config.json` with placeholder values for easy setup

### Security Considerations
- The web interface has no authentication by default
- Only run on trusted networks or behind a reverse proxy with authentication
- Player and server data is stored in plain text JSON files
- The application has full control over your Project Zomboid server

## License

This project is provided as-is for educational and personal use. Use at your own risk.

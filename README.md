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

2. **Configure Settings**:
   Edit `config.json` to match your server setup:
   ```json
   {
     "server": {
       "zomboid_server_dir": "C:\\Program Files (x86)\\Steam\\steamapps\\common\\Project Zomboid Dedicated Server",
       "server_launch_file": "StartServer64.bat",
       "web_host": "0.0.0.0",
       "web_port": 5000
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

### Server Settings
- `zomboid_server_dir`: Path to your Project Zomboid server installation
- `server_launch_file`: Server executable filename
- `web_host`: Web interface host (use "0.0.0.0" for network access)
- `web_port`: Web interface port

### Log Indicators
Customize the text patterns that the panel uses to detect server events:
- Server startup/shutdown messages
- Player login/logout events
- Error conditions

### Locations
Add or modify predefined teleport locations:
```json
"locations": {
  "West Point": "11914,6725,0",
  "Muldraugh": "10635,9845,0",
  "Custom Location": "x,y,z"
}
```

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
- Check that the `zomboid_server_dir` path is correct
- Verify the `server_launch_file` exists
- Ensure you have permission to execute the server

### Players Not Showing Up
- Check the `user_logged_in` and `user_logged_out` indicators match your server's output
- Monitor the server log for login/logout messages

### Web Interface Not Accessible
- Verify the port isn't blocked by firewall
- Check that Flask is binding to the correct host/port
- Look for error messages in the console output

## Development

The panel is built with:
- **Backend**: Python Flask
- **Frontend**: Bootstrap 5, Font Awesome icons
- **Real-time Updates**: JavaScript fetch API with auto-refresh

### File Structure
```
├── app/                     # Application code directory
│   ├── __init__.py         # Package initialization
│   ├── server_app.py       # Main Flask application
│   ├── ini_file_inject_mods_from_db.py  # Mod injection utility
│   └── templates/          # Web interface templates
│       ├── index.html      # Main admin panel template
│       └── mods.html       # Mod manager template
├── main.py                 # Main entry point
├── config.json             # Server configuration
├── mods_db.json             # Mod database
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

### Adding New Features
1. Add API endpoints in `app/server_app.py`
2. Update the HTML templates in `app/templates/` for UI changes
3. Modify `config.json` for new settings
4. Test thoroughly before deploying

## License

This project is provided as-is for educational and personal use. Use at your own risk.

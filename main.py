#!/usr/bin/env python3
"""
Project Zomboid Admin Panel
Main entry point for the application
"""

import sys
import os

# Add the app directory to the Python path
app_dir = os.path.join(os.path.dirname(__file__), 'app')
sys.path.insert(0, app_dir)

def main():
    """Main entry point for the application"""
    # Import and run the app's main function
    from app import main as app_main
    app_main()

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Quantitative Sales Launcher
Launches the application
"""

import os
import sys
import subprocess
import webbrowser
import time
from pathlib import Path

# Print header immediately so users see something right away
print("=" * 70)
print("Quantitative Sales - Launcher")
print("=" * 70)
print()

# Handle PyInstaller one-file executable
# When running from PyInstaller, sys._MEIPASS contains the path to extracted files
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    # Running from PyInstaller executable
    base_path = Path(sys._MEIPASS)
    app_dir = base_path
    scripts_dir = base_path / 'scripts'
else:
    # Running from source
    scripts_dir = Path(__file__).parent
    app_dir = scripts_dir.parent

sys.path.insert(0, str(app_dir))
sys.path.insert(0, str(scripts_dir))


def launch_app():
    """Launch the main application"""
    app_py = app_dir / 'app.py'
    
    if not app_py.exists():
        print(f"Error: {app_py} not found!")
        print(f"App directory: {app_dir}")
        print(f"Contents of app_dir: {list(app_dir.iterdir()) if app_dir.exists() else 'Directory not found'}")
        return False
    
    print("=" * 70)
    print("Quantitative Sales - Starting Application")
    print("=" * 70)
    print()
    
    # Launch the app
    try:
        # Change to app directory
        os.chdir(str(app_dir))
        
        # Import and run the app directly (works with PyInstaller)
        if getattr(sys, 'frozen', False):
            # Running from PyInstaller executable - import directly
            import app
            app.main()
        else:
            # Running from source - use subprocess
            subprocess.run([sys.executable, str(app_py)], cwd=str(app_dir))
    except KeyboardInterrupt:
        print("\nApplication stopped by user")
        return True
    except Exception as e:
        print(f"Error launching application: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_desktop_shortcut():
    """Create desktop shortcut (Windows) or launcher (macOS)"""
    try:
        if sys.platform == "win32":
            # Windows: Create .bat file on desktop
            desktop = Path.home() / 'Desktop'
            if not desktop.exists():
                desktop = Path.home() / 'OneDrive' / 'Desktop'
            
            if desktop.exists():
                shortcut = desktop / 'Quantitative Sales.lnk'
                # For Windows, we'll create a .bat file instead
                bat_file = desktop / 'Quantitative Sales.bat'
                with open(bat_file, 'w') as f:
                    f.write(f'@echo off\n')
                    f.write(f'cd /d "{app_dir}"\n')
                    f.write(f'"{sys.executable}" "{scripts_dir / "launcher.py"}"\n')
                    f.write(f'pause\n')
                print(f"Desktop shortcut created: {bat_file}")
        elif sys.platform == "darwin":
            # macOS: Create .command file
            desktop = Path.home() / 'Desktop'
            if desktop.exists():
                command_file = desktop / 'Quantitative Sales.command'
                with open(command_file, 'w') as f:
                    f.write('#!/bin/bash\n')
                    f.write(f'cd "{app_dir}"\n')
                    f.write(f'"{sys.executable}" "{scripts_dir / "launcher.py"}"\n')
                os.chmod(command_file, 0o755)
                print(f"Desktop launcher created: {command_file}")
    except Exception as e:
        print(f"Warning: Could not create desktop shortcut: {e}")

def main():
    """Main launcher function. Credentials are read from env (Azure App Service / Key Vault)."""
    # Create desktop shortcut if it doesn't exist
    create_desktop_shortcut()
    # Launch the app
    launch_app()

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
B2B Insights Launcher
Auto-updates from GitHub and launches the application
"""

import os
import sys
import subprocess
import webbrowser
import time
from pathlib import Path

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

def check_user_authorization():
    """Check if current user is authorized (Windows username check)"""
    try:
        from config.embedded_credentials_manager import EmbeddedCredentialsManager
        manager = EmbeddedCredentialsManager()
        if manager.is_user_approved():
            username = manager._get_windows_username()
            print(f"Authorized user detected: {username}")
            return True
        else:
            username = manager._get_windows_username()
            print(f"User '{username}' is not authorized")
            print(f"Approved users: {', '.join(manager.approved_users)}")
            return False
    except Exception as e:
        print(f"Warning: Could not check authorization: {e}")
        print("Continuing anyway...")
        return True  # Allow to continue if check fails

def check_credentials_embedded():
    """Check if credentials are embedded"""
    try:
        from config.embedded_credentials import ENCRYPTED_CREDENTIALS
        if ENCRYPTED_CREDENTIALS and ENCRYPTED_CREDENTIALS.strip():
            return True
        return False
    except Exception:
        return False

def check_for_updates():
    """Check for and apply updates from GitHub"""
    try:
        from scripts.auto_updater import AutoUpdater
        
        # When running from PyInstaller, don't pass app_dir so auto_updater uses permanent location
        # When running from source, pass app_dir so updates go to source directory
        update_app_dir = None if getattr(sys, 'frozen', False) else app_dir
        
        # GitHub repository for auto-updates
        updater = AutoUpdater(
            repo_owner='TWS-NZOH',  # GitHub organization/username
            repo_name='Q',  # Repository name
            branch='main',
            app_dir=update_app_dir
        )
        
        print("Checking for updates...")
        updated, message = updater.update()
        print(message)
        return updated
    except Exception as e:
        print(f"Warning: Could not check for updates: {e}")
        print("Continuing with current version...")
        return False

def launch_app():
    """Launch the main application"""
    app_py = app_dir / 'app.py'
    
    if not app_py.exists():
        print(f"Error: {app_py} not found!")
        print(f"App directory: {app_dir}")
        print(f"Contents of app_dir: {list(app_dir.iterdir()) if app_dir.exists() else 'Directory not found'}")
        return False
    
    print("=" * 70)
    print("B2B Insights - Starting Application")
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
                shortcut = desktop / 'B2B Insights.lnk'
                # For Windows, we'll create a .bat file instead
                bat_file = desktop / 'B2B Insights.bat'
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
                command_file = desktop / 'B2B Insights.command'
                with open(command_file, 'w') as f:
                    f.write('#!/bin/bash\n')
                    f.write(f'cd "{app_dir}"\n')
                    f.write(f'"{sys.executable}" "{scripts_dir / "launcher.py"}"\n')
                os.chmod(command_file, 0o755)
                print(f"Desktop launcher created: {command_file}")
    except Exception as e:
        print(f"Warning: Could not create desktop shortcut: {e}")

def main():
    """Main launcher function"""
    print("=" * 70)
    print("B2B Insights - Launcher")
    print("=" * 70)
    print()
    
    # Check user authorization
    if not check_user_authorization():
        print("\n" + "=" * 70)
        print("ACCESS DENIED")
        print("=" * 70)
        print("\nYou are not authorized to use this application.")
        print("Please contact the administrator if you believe this is an error.")
        input("\nPress Enter to exit...")
        return
    
    # Check if credentials are embedded
    if not check_credentials_embedded():
        print("Warning: Credentials not embedded!")
        print("The application may not work correctly.")
        print("Please ensure credentials are embedded in config/embedded_credentials.py")
        response = input("\nContinue anyway? (yes/no) [no]: ").strip().lower()
        if response not in ['yes', 'y']:
            return
    
    # Check for updates (non-blocking)
    try:
        check_for_updates()
    except:
        pass  # Don't fail if update check fails
    
    # Create desktop shortcut if it doesn't exist
    create_desktop_shortcut()
    
    # Launch the app
    launch_app()

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Setup script for configuring Salesforce credentials
Run this once before using the application
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.credentials_manager import CredentialsManager

def main():
    """Main setup function"""
    print("\n" + "=" * 70)
    print("B2B Insights - Initial Setup")
    print("=" * 70)
    print("\nThis script will help you configure your Salesforce credentials.")
    print("Credentials will be encrypted and stored locally on your machine.\n")
    
    manager = CredentialsManager()
    
    if manager.credentials_exist():
        print("⚠️  Credentials already exist!")
        overwrite = input("Do you want to overwrite them? (yes/no) [no]: ").strip().lower()
        if overwrite not in ['yes', 'y']:
            print("Setup cancelled.")
            return
    
    success = manager.setup_credentials_interactive()
    
    if success:
        print("\n" + "=" * 70)
        print("Setup Complete!")
        print("=" * 70)
        print("\nYou can now run the B2B Insights application.")
        print("Credentials are stored securely in:", manager.config_dir)
    else:
        print("\nSetup failed. Please try again.")
        sys.exit(1)

if __name__ == "__main__":
    main()


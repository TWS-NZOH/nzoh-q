# B2B Insights - Beta Testing Guide

## 🚀 Quick Start for Beta Testers

### Installation

1. **Download the executable** from the provided link
2. **Run the executable** - it will:
   - Check for updates automatically
   - Prompt you to set up credentials (first time only)
   - Create a desktop shortcut
   - Launch the application

### First-Time Setup

1. When you first run the application, you'll be prompted to enter Salesforce credentials
2. Enter your Salesforce username, password, and security token
3. Select your environment (Live or UAT)
4. Credentials are encrypted and stored locally on your machine

### Using the Application

1. **Launch**: Double-click the desktop shortcut or the executable
2. **Enter Initials**: Type your initials (e.g., "tws")
3. **Select Account**: Choose an account from the dropdown
4. **View Report**: The report will generate automatically (30-60 seconds)

### Auto-Updates

The application automatically checks for updates when launched:
- If an update is available, it downloads and applies it automatically
- You'll see a message indicating the update status
- No action required from you

### Troubleshooting

**"Credentials not configured"**
- Run the setup script manually: `python scripts/setup_credentials.py`
- Or delete the credentials file and run the app again

**"Update check failed"**
- Check your internet connection
- The app will continue with the current version

**"Application won't start"**
- Make sure you have an internet connection
- Check that port 5000 is available
- Try restarting your computer

### Support

For issues or questions, contact the development team.

## 🔒 Security Notes

- Credentials are encrypted and stored locally
- Credentials are never sent to GitHub or any external service
- Each machine has its own encrypted credential file
- The credential file is excluded from version control

## 📋 System Requirements

- Windows 10/11 or macOS 10.14+
- Internet connection (for updates and Salesforce access)
- 500MB free disk space


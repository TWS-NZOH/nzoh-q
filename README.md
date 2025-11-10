# B2B Insights - Beta Ready Application

## Overview

This is the beta-ready version of the B2B Insights application. It includes:

- ✅ Secure credential management (encrypted, local storage)
- ✅ Auto-updating from GitHub
- ✅ Executable packaging
- ✅ Desktop shortcut creation
- ✅ Simple setup for non-technical users

## Structure

```
appified_report_app/
├── app.py                      # Main Flask application
├── indicators_report.py        # Core analysis logic
├── sales_dashboard.py         # Dashboard generation
├── config/                     # Configuration modules
│   ├── credentials_manager.py # Secure credential management
│   └── __init__.py
├── b2b_insights_core/          # Core modules
│   ├── salesforce_client.py   # Salesforce connection handler
│   └── __init__.py
├── scripts/                    # Utility scripts
│   ├── setup_credentials.py  # Initial credential setup
│   ├── auto_updater.py        # GitHub update checker
│   ├── launcher.py            # Main launcher (auto-updates)
│   └── build_executable.py    # Executable builder
├── static/                     # Web assets
├── requirements.txt            # Python dependencies
├── .gitignore                  # Git ignore rules
└── README_BETA.md             # Beta tester guide
```

## Quick Start

### For Developers

1. **Set up credentials** (first time only)
   ```bash
   python scripts/setup_credentials.py
   ```

2. **Run the application**
   ```bash
   python scripts/launcher.py
   ```
   Or directly:
   ```bash
   python app.py
   ```

3. **Build executable**
   ```bash
   python scripts/build_executable.py
   ```

### For Beta Testers

See `README_BETA.md` for instructions.

## Security

- **Credentials are encrypted** using machine-specific keys
- **Credentials stored locally** in `~/.b2b_insights/`
- **Never committed to Git** (excluded in `.gitignore`)
- **Never sent to GitHub** or any external service

## Auto-Updates

The launcher automatically:
1. Checks GitHub for updates on launch
2. Downloads latest code if available
3. Applies updates automatically
4. Launches the application

## Building Executable

See `BUILD_EXECUTABLE.md` for detailed instructions.

## GitHub Setup

See `SETUP_GITHUB.md` for repository setup instructions.

## Development Workflow

1. **Make changes** to code
2. **Test locally**
3. **Commit and push** to GitHub
4. **Beta testers get updates** automatically on next launch

## Notes

- The `VERSION` file is auto-generated and tracks the current version
- Credentials are machine-specific and cannot be shared
- Each beta tester must run `setup_credentials.py` once
- The executable includes all dependencies (no Python installation needed)

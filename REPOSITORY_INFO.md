# Repository Information

## GitHub Repository

**Repository URL:** https://github.com/TWS-NZOH/Q

**Organization:** TWS-NZOH

**Repository Name:** Q

**Branch:** main

## Quick Setup

### Initialize and Push

```bash
cd appified_report_app
git init
git config user.name "Your Name"
git config user.email "your.email@novozymes.com"
git add .
git commit -m "Initial commit - Beta ready version"
git remote add origin https://github.com/TWS-NZOH/Q.git
git branch -M main
git push -u origin main
```

### Or Use Automated Script

```bash
cd appified_report_app
./scripts/setup_git_repo.sh
```

The script will automatically use: `https://github.com/TWS-NZOH/Q`

## Download Links

### Release Page
```
https://github.com/TWS-NZOH/Q/releases
```

### Direct Download (after creating release)
```
https://github.com/TWS-NZOH/Q/releases/download/v1.0.0-beta/B2B-Insights.exe
```

## Auto-Update

The application automatically checks for updates from:
- Repository: `TWS-NZOH/Q`
- Branch: `main`

No configuration needed - it's already set in `scripts/launcher.py`


# GitHub Repository Setup Guide

## Initial Setup

1. **Create a new GitHub repository** (or use existing)
   - Repository name: `B2B-insights` (or your preferred name)
   - Make it private (recommended for beta testing)
   - Don't initialize with README (we'll add files)

2. **Initialize git in appified_report_app**
   ```bash
   cd appified_report_app
   git init
   git add .
   git commit -m "Initial commit - Beta ready version"
   ```

3. **Add GitHub remote**
   ```bash
   git remote add origin https://github.com/YOUR_USERNAME/B2B-insights.git
   git branch -M main
   git push -u origin main
   ```

## Update Launcher with Your GitHub Info

1. **Edit `scripts/launcher.py`**
   - Replace `YOUR_GITHUB_USERNAME` with your actual GitHub username
   - Replace `B2B-insights` with your actual repository name (if different)

2. **Commit and push**
   ```bash
   git add scripts/launcher.py
   git commit -m "Update GitHub repository info"
   git push
   ```

## Version Management

The auto-updater uses commit SHAs as version identifiers. To create a new version:

1. **Make your changes**
2. **Commit changes**
   ```bash
   git add .
   git commit -m "Description of changes"
   git push
   ```

3. **Beta testers will automatically get the update** on next launch

## Important Notes

- **Never commit credentials**: The `.gitignore` file excludes `credentials.enc` and `.key` files
- **Test updates**: Make sure to test the auto-update mechanism before distributing
- **Version file**: The `VERSION` file is auto-generated and should not be committed

## Distribution

1. **Build executable** (see `BUILD_EXECUTABLE.md`)
2. **Share executable** with beta testers
3. **Beta testers run executable** - it will:
   - Check for updates on launch
   - Download and apply updates automatically
   - Create desktop shortcut

## Security

- Credentials are encrypted and stored locally on each machine
- Credentials are never sent to GitHub
- Each machine has its own encrypted credential file
- The `.gitignore` ensures credentials are never committed


# Complete Setup Walkthrough - Git & Distribution

## Overview

This guide walks you through:
1. Setting up Git repository
2. Pushing code to GitHub
3. Building executable
4. Creating download link for beta testers

## Prerequisites

✅ Git is installed (you have it: version 2.32.1)
✅ GitHub account created
✅ GitHub repository created (private, empty)

## Step-by-Step Instructions

### Step 1: Verify GitHub Repository

**Repository:** https://github.com/TWS-NZOH/Q

✅ Repository already exists - no need to create it!

If you need to verify access:
1. Go to https://github.com/TWS-NZOH/Q
2. Make sure you have write access
3. Verify it's set to Private (recommended for beta testing)

### Step 2: Set Up Git Repository

**Option A: Automated (Easiest)**

```bash
cd /Users/tws/Desktop/NZOH/nzoh-programs/B2B-insights/appified_report_app
./scripts/setup_git_repo.sh
```

Follow the prompts:
- Enter your name and email
- Enter GitHub username
- Enter repository name (or press Enter for default: B2B-insights)
- Confirm to create commit
- Confirm to push to GitHub

**Option B: Manual**

```bash
# Navigate to project directory
cd /Users/tws/Desktop/NZOH/nzoh-programs/B2B-insights/appified_report_app

# Initialize Git
git init

# Configure Git (if first time)
git config user.name "Your Name"
git config user.email "your.email@novozymes.com"

# Add all files
git add .

# Create initial commit
git commit -m "Initial commit - Beta ready version with embedded credentials"

# Add GitHub remote
git remote add origin https://github.com/TWS-NZOH/Q.git

# Rename branch to main
git branch -M main

# Push to GitHub
git push -u origin main
```

**When prompted for credentials:**
- Username: Your GitHub username
- Password: **Use Personal Access Token** (not your GitHub password)
  - Generate token: GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic) → Generate new token (classic)
  - Name: "B2B Insights Setup"
  - Expiration: 90 days (or your preference)
  - Scopes: Check `repo` (full control of private repositories)
  - Click "Generate token"
  - **Copy the token** (you won't see it again!)
  - Use this token as your password

### Step 3: Verify Push

1. Go to your GitHub repository: `https://github.com/YOUR_USERNAME/B2B-insights`
2. Refresh the page
3. You should see all your files

### Step 4: Update Launcher with GitHub Info

1. **Edit `scripts/launcher.py`**
   - Find line with `YOUR_GITHUB_USERNAME`
   - Replace with your actual GitHub username
   - Replace `B2B-insights` with your repository name (if different)

2. **Commit and push:**
   ```bash
   git add scripts/launcher.py
   git commit -m "Update GitHub repository info in launcher"
   git push
   ```

### Step 5: Build Executable

```bash
cd /Users/tws/Desktop/NZOH/nzoh-programs/B2B-insights/appified_report_app

# Install PyInstaller if needed
pip install pyinstaller

# Build executable
python scripts/build_executable.py
```

The executable will be in `dist/` folder:
- Windows: `dist/B2B Insights.exe`
- macOS: `dist/B2B Insights`
- Linux: `dist/B2B Insights`

### Step 6: Create GitHub Release

1. **Tag the release:**
   ```bash
   git tag -a v1.0.0-beta -m "Beta release v1.0.0"
   git push origin v1.0.0-beta
   ```

2. **On GitHub:**
   - Go to your repository
   - Click **Releases** → **Draft a new release**
   - **Tag:** `v1.0.0-beta`
   - **Title:** `B2B Insights - Beta Release v1.0.0`
   - **Description:**
     ```
     Beta testing release for B2B Insights application.
     
     **Approved Users:**
     - BECOB
     - BENM
     - MIYR
     - AOV
     - JETE
     - SACW
     - KYM
     - LEWA
     - CYK
     
     **Installation:**
     1. Download the executable for your platform
     2. Run the executable (no installation required)
     3. Application will auto-detect your Windows username
     4. If approved, application opens automatically
     
     **System Requirements:**
     - Windows 10/11 or macOS 10.14+
     - Internet connection
     - Approved Windows username
     ```
   - **Attach files:** Drag and drop executable from `dist/` folder
   - Click **Publish release**

### Step 7: Get Download Link

After publishing the release, you'll have:

**Release Page:**
```
https://github.com/TWS-NZOH/Q/releases/tag/v1.0.0-beta
```

**Direct Download Link:**
```
https://github.com/TWS-NZOH/Q/releases/download/v1.0.0-beta/B2B-Insights.exe
```

(Replace `B2B-Insights.exe` with actual filename if different)

### Step 8: Share with Beta Testers

**Email Template:**

```
Subject: B2B Insights - Beta Testing Application

Hi Team,

I'm excited to share the B2B Insights application for beta testing!

DOWNLOAD LINK:
https://github.com/TWS-NZOH/Q/releases/download/v1.0.0-beta/B2B-Insights.exe

Or visit the release page:
https://github.com/TWS-NZOH/Q/releases/tag/v1.0.0-beta

APPROVED USERS:
The following Windows usernames are approved:
- BECOB
- BENM
- MIYR
- AOV
- JETE
- SACW
- KYM
- LEWA
- CYK

INSTALLATION:
1. Download the executable from the link above
2. Run the executable (no installation required)
3. The application will automatically detect your Windows username
4. If you're an approved user, the application will open automatically
5. If you're not approved, you'll see an error message - contact me for access

FEATURES:
- Automatic Windows username detection
- Skips initials step for approved users
- Auto-updates from GitHub
- Desktop shortcut creation

SYSTEM REQUIREMENTS:
- Windows 10/11 or macOS 10.14+
- Internet connection (for updates and Salesforce access)
- Approved Windows username

TROUBLESHOOTING:
- If you see "User not authorized": Your Windows username may not match the approved list
- If the application won't start: Check that you have an internet connection
- For other issues: Contact [YOUR_CONTACT_INFO]

FEEDBACK:
Please share any feedback, bugs, or suggestions with me.

Thanks!
[YOUR_NAME]
```

## Updating the Application

When you make changes:

1. **Make changes to code**
2. **Commit and push:**
   ```bash
   git add .
   git commit -m "Description of changes"
   git push
   ```

3. **Build new executable:**
   ```bash
   python scripts/build_executable.py
   ```

4. **Create new release:**
   ```bash
   git tag -a v1.0.1-beta -m "Beta release v1.0.1"
   git push origin v1.0.1-beta
   ```

5. **On GitHub:**
   - Create new release with new tag
   - Attach new executable
   - Beta testers will get update notification

## Quick Reference

### Common Git Commands

```bash
# Check status
git status

# Add files
git add .

# Commit changes
git commit -m "Description"

# Push to GitHub
git push

# Create tag
git tag -a v1.0.0-beta -m "Release message"
git push origin v1.0.0-beta
```

### File Locations

- **Executable:** `dist/B2B Insights.exe` (or `.app` for macOS)
- **Source code:** `appified_report_app/`
- **Git repository:** `appified_report_app/.git/`
- **Credentials:** `config/embedded_credentials.py` (encrypted)

## Troubleshooting

### "Repository not found"
- Check repository name and username
- Verify repository exists on GitHub
- Check remote URL: `git remote -v`

### "Permission denied"
- Use Personal Access Token (not password)
- Verify token has `repo` scope
- Check you have write access

### "Large file" error
- GitHub has 100MB file size limit
- Use Git LFS for large files:
  ```bash
  git lfs install
  git lfs track "*.exe"
  git add .gitattributes
  git add dist/B2B\ Insights.exe
  git commit -m "Add executable with LFS"
  git push
  ```

### Files not showing in repository
- Check `.gitignore` isn't excluding them
- Verify files were added: `git status`
- Check files were committed: `git log --name-only`

## Security Notes

✅ **Repository is private** (for beta testing)
✅ **Credentials are encrypted** and embedded
✅ **Only approved users** can decrypt credentials
✅ **Executable is self-contained** (no credentials needed)
✅ **Download links can be shared** (credentials already embedded)

## Next Steps

1. ✅ Set up Git repository
2. ✅ Push code to GitHub
3. ✅ Build executable
4. ✅ Create release with executable
5. ✅ Share download link with beta testers
6. ✅ Collect feedback
7. ✅ Push updates as needed

## Support

For issues or questions:
- Check `GIT_SETUP_GUIDE.md` for detailed Git instructions
- Check `DISTRIBUTION_GUIDE.md` for distribution options
- Check `README_BETA.md` for beta tester instructions


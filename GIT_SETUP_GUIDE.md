# Git Repository Setup Guide

## Prerequisites

### 1. Install Git (if not already installed)

**macOS:**
```bash
# Check if git is installed
git --version

# If not installed, install via Homebrew:
brew install git

# Or download from: https://git-scm.com/download/mac
```

**Windows:**
- Download Git from: https://git-scm.com/download/win
- Run the installer
- Use default settings

**Linux:**
```bash
# Ubuntu/Debian
sudo apt-get install git

# Fedora
sudo dnf install git
```

### 2. Create GitHub Repository

1. Go to https://github.com
2. Click the **+** icon in top right → **New repository**
3. Repository name: `B2B-insights` (or your preferred name)
4. Description: "B2B Insights - Beta Testing Application"
5. **Make it Private** (recommended for beta testing)
6. **DO NOT** initialize with README, .gitignore, or license
7. Click **Create repository**

## Step-by-Step Setup

### Step 1: Navigate to Project Directory

```bash
cd /Users/tws/Desktop/NZOH/nzoh-programs/B2B-insights/appified_report_app
```

### Step 2: Initialize Git Repository

```bash
# Initialize git repository
git init

# Check status
git status
```

### Step 3: Configure Git (if first time)

```bash
# Set your name and email (replace with your GitHub info)
git config user.name "Your Name"
git config user.email "your.email@novozymes.com"

# Or set globally for all repositories:
git config --global user.name "Your Name"
git config --global user.email "your.email@novozymes.com"
```

### Step 4: Add All Files

```bash
# Add all files to staging
git add .

# Check what will be committed
git status
```

**Note:** The `.gitignore` file will automatically exclude:
- `credentials.enc` and `.key` files
- `__pycache__/` directories
- Generated reports (`*.html`, `*.txt`)
- Build artifacts (`dist/`, `build/`)
- Other sensitive/temporary files

### Step 5: Create Initial Commit

```bash
# Create initial commit
git commit -m "Initial commit - Beta ready version with embedded credentials"

# Verify commit was created
git log
```

### Step 6: Add GitHub Remote

```bash
# Replace YOUR_USERNAME with your GitHub username
# Replace B2B-insights with your repository name if different
git remote add origin https://github.com/YOUR_USERNAME/B2B-insights.git

# Verify remote was added
git remote -v
```

### Step 7: Push to GitHub

```bash
# Rename branch to main (if needed)
git branch -M main

# Push to GitHub
git push -u origin main
```

**If prompted for credentials:**
- Username: Your GitHub username
- Password: Use a **Personal Access Token** (not your GitHub password)
  - Generate token: GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
  - Select scopes: `repo` (full control of private repositories)
  - Copy token and use as password

### Step 8: Verify Push

1. Go to your GitHub repository page
2. Refresh the page
3. You should see all your files

## Updating the Repository

### Making Changes and Pushing Updates

```bash
# After making changes to files:

# 1. Check what changed
git status

# 2. Add changed files
git add .

# 3. Commit changes
git commit -m "Description of changes"

# 4. Push to GitHub
git push
```

### Example: Updating Credentials

```bash
# After running encrypt_credentials.py and updating embedded_credentials.py:

git add config/embedded_credentials.py
git commit -m "Update embedded credentials"
git push
```

## Creating Download Links for Beta Testers

### Option 1: GitHub Releases (Recommended)

1. **Create a Release:**
   ```bash
   # Tag the current version
   git tag -a v1.0.0 -m "Beta release v1.0.0"
   git push origin v1.0.0
   ```

2. **On GitHub:**
   - Go to your repository
   - Click **Releases** → **Create a new release**
   - Tag: `v1.0.0`
   - Title: `Beta Release v1.0.0`
   - Description: Add release notes
   - **Attach executable** (drag and drop the built executable)
   - Click **Publish release**

3. **Share Download Link:**
   - Direct link: `https://github.com/YOUR_USERNAME/B2B-insights/releases/download/v1.0.0/B2B-Insights.exe`
   - Or share the release page: `https://github.com/YOUR_USERNAME/B2B-insights/releases`

### Option 2: Direct File Sharing

1. **Build Executable:**
   ```bash
   python scripts/build_executable.py
   ```

2. **Upload to File Sharing Service:**
   - **Dropbox**: Upload executable, get shareable link
   - **Google Drive**: Upload executable, get shareable link
   - **OneDrive**: Upload executable, get shareable link
   - **WeTransfer**: Upload executable, get temporary link

3. **Share Link with Beta Testers**

### Option 3: Private Download Page

1. **Create a simple HTML page** with download link
2. **Host on private server** or GitHub Pages
3. **Share URL** with beta testers

## Beta Tester Instructions

### For Beta Testers (Include in README_BETA.md)

1. **Download the executable** from the provided link
2. **Run the executable** (first time will check Windows username)
3. **If approved user:**
   - Application opens automatically
   - Skips initials step
   - Auto-populates initials from Windows username
4. **If not approved:**
   - Contact administrator for access

### Download Link Format

Share this format with beta testers:

```
B2B Insights - Beta Testing Application

Download Link: [YOUR_DOWNLOAD_LINK]

System Requirements:
- Windows 10/11 or macOS 10.14+
- Internet connection
- Approved Windows username (BECOB, BENM, MIYR, AOV, JETE, SACW, KYM, LEWA, CYK)

Installation:
1. Download the executable
2. Run the executable
3. Application will auto-detect your Windows username
4. If approved, application opens automatically

For issues or questions, contact [YOUR_CONTACT_INFO]
```

## Troubleshooting

### "Repository not found" error
- Check repository name and username
- Verify repository is not private (or you have access)
- Check remote URL: `git remote -v`

### "Permission denied" error
- Use Personal Access Token instead of password
- Check token has `repo` scope
- Verify you have write access to repository

### "Large file" error
- GitHub has 100MB file size limit
- If executable is too large, use Git LFS:
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

✅ **Credentials are encrypted** and embedded in code
✅ **Credentials excluded from Git** (via .gitignore)
✅ **Repository should be private** for beta testing
✅ **Only approved users** can decrypt credentials
✅ **Executable can be shared** (credentials already embedded)

## Next Steps

1. ✅ Set up Git repository
2. ✅ Push code to GitHub
3. ✅ Build executable
4. ✅ Create release with executable
5. ✅ Share download link with beta testers
6. ✅ Collect feedback
7. ✅ Push updates as needed


# GitHub Authentication Guide

## Your Repository Status

✅ **Repository exists:** https://github.com/TWS-NZOH/Q
✅ **Repository is private** (requires authentication)
✅ **You have access** (you can see it in browser)

## Authentication Methods

You have two options:

### Option 1: Personal Access Token (HTTPS) - Recommended

#### Step 1: Generate Personal Access Token

1. **Go to GitHub Settings:**
   - Click your profile picture (top right of GitHub)
   - Click **"Settings"**
   - In the left sidebar, scroll down to **"Developer settings"** (at the bottom)
   - Click **"Personal access tokens"**
   - Click **"Tokens (classic)"**
   - Click **"Generate new token"** → **"Generate new token (classic)"**

2. **Configure Token:**
   - **Note:** "B2B Insights Setup"
   - **Expiration:** 90 days (or your preference)
   - **Scopes:** Check **`repo`** (full control of private repositories)
   - Click **"Generate token"** at bottom

3. **Copy Token:**
   - The token starts with `ghp_...`
   - **Copy it immediately** (you won't see it again!)
   - Save it somewhere safe

#### Step 2: Use Token to Push

```bash
cd /Users/tws/Desktop/NZOH/nzoh-programs/B2B-insights/appified_report_app
git push -u origin main
```

When prompted:
- **Username:** `TWS-NZOH` (or your GitHub username)
- **Password:** **Paste your Personal Access Token** (NOT your GitHub password)

### Option 2: SSH Key (Alternative)

If you prefer SSH, you can set up SSH keys instead.

#### Step 1: Generate SSH Key

```bash
# Generate SSH key
ssh-keygen -t ed25519 -C "your.email@novozymes.com"

# Press Enter to accept default location
# Press Enter twice for no passphrase (or set one)

# Start SSH agent
eval "$(ssh-agent -s)"

# Add key to SSH agent
ssh-add ~/.ssh/id_ed25519
```

#### Step 2: Add SSH Key to GitHub

1. **Copy your public key:**
   ```bash
   cat ~/.ssh/id_ed25519.pub
   ```
   Copy the entire output (starts with `ssh-ed25519`)

2. **Add to GitHub:**
   - Go to GitHub → Settings → SSH and GPG keys
   - Click **"New SSH key"**
   - **Title:** "B2B Insights Mac"
   - **Key:** Paste your public key
   - Click **"Add SSH key"**

#### Step 3: Change Remote to SSH

```bash
cd /Users/tws/Desktop/NZOH/nzoh-programs/B2B-insights/appified_report_app

# Change remote to SSH
git remote set-url origin git@github.com:TWS-NZOH/Q.git

# Verify
git remote -v

# Push
git push -u origin main
```

## Quick Fix: Get the Correct URL from GitHub

1. **On the GitHub repository page:**
   - Click the green **"Code"** button (top right, above the file list)
   - A dropdown will appear

2. **For HTTPS (with token):**
   - Select **"HTTPS"** tab
   - Copy the URL: `https://github.com/TWS-NZOH/Q.git`
   - Use this with Personal Access Token

3. **For SSH (with key):**
   - Select **"SSH"** tab
   - Copy the URL: `git@github.com:TWS-NZOH/Q.git`
   - Use this with SSH key

## Current Status

Your remote is already set correctly:
```
origin  https://github.com/TWS-NZOH/Q.git (fetch)
origin  https://github.com/TWS-NZOH/Q.git (push)
```

You just need to authenticate!

## Recommended: Use Personal Access Token

1. **Generate token:** GitHub → Your Profile → Settings → Developer settings → Personal access tokens → Tokens (classic) → Generate new token (classic)

2. **Push:**
   ```bash
   git push -u origin main
   ```

3. **When prompted:**
   - Username: `TWS-NZOH` (or your GitHub username)
   - Password: **Paste your token** (starts with `ghp_...`)

## Alternative: Direct Link to Token Page

Try this direct link:
```
https://github.com/settings/tokens
```

Or navigate:
1. Click your profile picture (top right)
2. Click **"Settings"**
3. Scroll down to **"Developer settings"** (bottom of left sidebar)
4. Click **"Personal access tokens"**
5. Click **"Tokens (classic)"**
6. Click **"Generate new token"** → **"Generate new token (classic)"**


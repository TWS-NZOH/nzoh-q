# Authenticate with Personal Access Token

## The Problem

Git is not prompting for credentials, or it's using cached credentials that don't work.

## Solution: Configure Git to Use Token

### Option 1: Include Token in Remote URL (Easiest)

This embeds the token in the remote URL so you don't need to enter it each time.

**Step 1: Get your token**
- You should have a Personal Access Token that starts with `ghp_...`
- Copy the entire token

**Step 2: Update remote URL with token**

```bash
cd /Users/tws/Desktop/NZOH/nzoh-programs/B2B-insights/appified_report_app

# Replace YOUR_TOKEN with your actual token (starts with ghp_...)
# Replace YOUR_USERNAME with your GitHub username (probably TWS-NZOH)
git remote set-url origin https://YOUR_USERNAME:YOUR_TOKEN@github.com/TWS-NZOH/Q.git

# Verify
git remote -v
```

**Example:**
```bash
git remote set-url origin https://TWS-NZOH:ghp_xxxxxxxxxxxxxxxxxxxx@github.com/TWS-NZOH/Q.git
```

**Step 3: Push**

```bash
git push -u origin main
```

This should work without prompting for credentials!

### Option 2: Clear Credentials and Force Prompt

**Step 1: Clear cached credentials**

```bash
# Clear macOS keychain credentials
git credential-osxkeychain erase
host=github.com
protocol=https
# Press Enter twice

# Or clear all credential helpers
git config --global --unset credential.helper
```

**Step 2: Configure to prompt for credentials**

```bash
# Set credential helper to prompt
git config --global credential.helper osxkeychain
```

**Step 3: Push (will prompt for credentials)**

```bash
git push -u origin main
```

When prompted:
- **Username:** `TWS-NZOH` (or your GitHub username)
- **Password:** **Paste your token** (starts with `ghp_...`)

### Option 3: Use Git Credential Helper (Store Token)

**Step 1: Configure credential helper**

```bash
# Store credentials in macOS keychain
git config --global credential.helper osxkeychain
```

**Step 2: Push (will prompt once, then store)**

```bash
git push -u origin main
```

When prompted:
- **Username:** `TWS-NZOH`
- **Password:** **Paste your token** (starts with `ghp_...`)

After first successful push, credentials will be stored and you won't need to enter them again.

## Recommended: Option 1 (Embed Token in URL)

This is the easiest and most reliable method:

```bash
cd /Users/tws/Desktop/NZOH/nzoh-programs/B2B-insights/appified_report_app

# Replace YOUR_TOKEN with your actual token
# Replace YOUR_USERNAME with your GitHub username
git remote set-url origin https://YOUR_USERNAME:YOUR_TOKEN@github.com/TWS-NZOH/Q.git

# Verify
git remote -v

# Push (no credentials needed!)
git push -u origin main
```

## Security Note

⚠️ **Important:** If you embed the token in the URL, it will be visible in:
- `git remote -v` output
- `.git/config` file
- Git history (if you commit the config)

**For security:**
- Use a token with limited scope
- Don't share your `.git/config` file
- Consider using SSH keys for long-term use

## Quick Test

After setting up authentication, test with:

```bash
# This should work without errors
git push -u origin main
```

If successful, you'll see:
```
Enumerating objects: X, done.
Counting objects: 100% (X/X), done.
Writing objects: 100% (X/X), done.
To https://github.com/TWS-NZOH/Q.git
 * [new branch]      main -> main
Branch 'main' set up to track remote branch 'main' from 'origin'.
```

## Still Not Working?

1. **Verify token:**
   - Make sure token starts with `ghp_...`
   - Make sure token has `repo` scope
   - Make sure token hasn't expired

2. **Verify repository:**
   - Go to: https://github.com/TWS-NZOH/Q
   - Can you see it? If not, you don't have access

3. **Try SSH instead:**
   - Set up SSH keys
   - Use `git@github.com:TWS-NZOH/Q.git` as remote URL


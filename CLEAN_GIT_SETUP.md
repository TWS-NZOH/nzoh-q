# Clean Git Setup - Native Git Commands Only

## Step 1: Clean Up Everything

```bash
cd /Users/tws/Desktop/NZOH/nzoh-programs/B2B-insights/appified_report_app

# Remove any existing remote
git remote remove origin 2>/dev/null || true

# Remove credential helpers (so Git will prompt)
git config --global --unset credential.helper 2>/dev/null || true
git config --local --unset credential.helper 2>/dev/null || true

# Verify no remote exists
git remote -v
```

Should show nothing (no remotes).

## Step 2: Add Remote (Clean URL)

```bash
# Add remote with clean URL (no credentials)
git remote add origin https://github.com/TWS-NZOH/Q.git

# Verify
git remote -v
```

Should show:
```
origin  https://github.com/TWS-NZOH/Q.git (fetch)
origin  https://github.com/TWS-NZOH/Q.git (push)
```

## Step 3: Verify You Have Commits

```bash
# Check commits
git log --oneline -1
```

Should show: `605edc2 Initial beta-ready commit`

## Step 4: Make Sure Branch is 'main'

```bash
# Check branch
git branch

# If not 'main', rename it
git branch -M main
```

## Step 5: Push (Will Prompt for Credentials)

```bash
# Push - this will prompt for username and password
git push -u origin main
```

**When prompted:**
- **Username:** Enter `TWS-NZOH` (or your GitHub username)
- **Password:** **Paste your Personal Access Token** (starts with `ghp_...`)

**Important:** 
- Use your **token** as the password (NOT your GitHub password)
- The token starts with `ghp_...`
- Paste the entire token

## Complete Command Sequence

Copy and paste this entire sequence:

```bash
cd /Users/tws/Desktop/NZOH/nzoh-programs/B2B-insights/appified_report_app

# Clean up
git remote remove origin 2>/dev/null || true
git config --global --unset credential.helper 2>/dev/null || true
git config --local --unset credential.helper 2>/dev/null || true

# Verify clean
git remote -v

# Add remote
git remote add origin https://github.com/TWS-NZOH/Q.git

# Verify remote added
git remote -v

# Check branch
git branch -M main

# Check commits
git log --oneline -1

# Push (will prompt for credentials)
git push -u origin main
```

When `git push` prompts you:
- **Username:** `TWS-NZOH`
- **Password:** **Paste your token** (entire `ghp_...` string)

## What to Expect

If successful, you'll see:
```
Enumerating objects: X, done.
Counting objects: 100% (X/X), done.
Writing objects: 100% (X/X), done.
To https://github.com/TWS-NZOH/Q.git
 * [new branch]      main -> main
Branch 'main' set up to track remote branch 'main' from 'origin'.
```

## Verify Success

1. Go to: https://github.com/TWS-NZOH/Q
2. Refresh the page
3. You should see all your files!

## Troubleshooting

### "Repository not found"
- Verify repository exists: https://github.com/TWS-NZOH/Q
- Make sure you have access to the repository

### "Authentication failed"
- Make sure you're using the **token** as password (not your GitHub password)
- Make sure token has `repo` scope
- Make sure token hasn't expired

### Not prompting for credentials
- Make sure credential helper is unset (run cleanup commands again)
- Try: `GIT_TERMINAL_PROMPT=1 git push -u origin main`


# Fresh Start - Git Setup from Scratch

## Step 1: Clean Up Existing Remote

```bash
cd /Users/tws/Desktop/NZOH/nzoh-programs/B2B-insights/appified_report_app

# Remove any existing remote
git remote remove origin 2>/dev/null || true

# Verify remote is removed
git remote -v
```

Should show nothing (no remotes).

## Step 2: Verify Your Repository Exists

1. **Open browser**
2. **Go to:** https://github.com/TWS-NZOH/Q
3. **Verify:**
   - ✅ You can see the repository
   - ✅ You have access (not 404)
   - ✅ Repository is private (has lock icon)

If you can't see it, you need to:
- Create the repository, OR
- Get access from the owner

## Step 3: Get the Correct URL from GitHub

1. **On the repository page:**
   - Click the green **"Code"** button (top right)
   - A dropdown will appear

2. **Select "HTTPS" tab:**
   - You'll see: `https://github.com/TWS-NZOH/Q.git`
   - **Copy this URL exactly as shown**

3. **Note the URL:**
   - GitHub shows: `https://github.com/TWS-NZOH/Q.git`
   - We'll use this exact URL

## Step 4: Add Remote with Correct URL

```bash
cd /Users/tws/Desktop/NZOH/nzoh-programs/B2B-insights/appified_report_app

# Add remote using the URL from GitHub (with .git)
git remote add origin https://github.com/TWS-NZOH/Q.git

# Verify
git remote -v
```

Should show:
```
origin  https://github.com/TWS-NZOH/Q.git (fetch)
origin  https://github.com/TWS-NZOH/Q.git (push)
```

## Step 5: Verify You Have Commits

```bash
# Check commits
git log --oneline -3
```

You should see at least one commit (like "Initial beta-ready commit").

If you don't have commits:
```bash
# Add all files
git add .

# Create commit
git commit -m "Initial commit - Beta ready version"
```

## Step 6: Make Sure Branch is 'main'

```bash
# Check current branch
git branch

# If not 'main', rename it
git branch -M main
```

## Step 7: Generate Personal Access Token (If You Don't Have One)

1. **Go to:** https://github.com/settings/tokens
   - Or: GitHub → Your Profile → Settings → Developer settings → Personal access tokens → Tokens (classic)

2. **Generate Token:**
   - Click **"Generate new token (classic)"**
   - **Note:** "B2B Insights Setup"
   - **Expiration:** 90 days
   - **Scopes:** Check **`repo`** (full control of private repositories)
   - Click **"Generate token"**

3. **Copy Token:**
   - Token starts with `ghp_...`
   - **Copy the entire token** (you won't see it again!)
   - Save it somewhere safe

## Step 8: Push to GitHub

```bash
cd /Users/tws/Desktop/NZOH/nzoh-programs/B2B-insights/appified_report_app

# Push to GitHub
git push -u origin main
```

**When prompted:**
- **Username:** `TWS-NZOH` (or your GitHub username)
- **Password:** **Paste your Personal Access Token** (starts with `ghp_...`)

**Important:** Use the **token** as password, NOT your GitHub password!

## Step 9: Verify Success

1. **Go to:** https://github.com/TWS-NZOH/Q
2. **Refresh the page**
3. **You should see all your files!**

## Complete Command Sequence

Copy and paste this entire sequence:

```bash
cd /Users/tws/Desktop/NZOH/nzoh-programs/B2B-insights/appified_report_app

# Step 1: Remove existing remote
git remote remove origin 2>/dev/null || true

# Step 2: Verify no remote exists
git remote -v

# Step 3: Add remote (using URL with .git as shown on GitHub)
git remote add origin https://github.com/TWS-NZOH/Q.git

# Step 4: Verify remote added correctly
git remote -v

# Step 5: Make sure branch is 'main'
git branch -M main

# Step 6: Check you have commits
git log --oneline -1

# Step 7: Push (will prompt for username and token)
git push -u origin main
```

When `git push` prompts you:
- **Username:** `TWS-NZOH`
- **Password:** **Paste your token** (the entire `ghp_...` string)

## Troubleshooting

### "Repository not found" after following all steps

1. **Verify repository exists:**
   - Go to: https://github.com/TWS-NZOH/Q
   - Can you see it? If not, create it first

2. **Verify token has correct scope:**
   - Token must have `repo` scope
   - Generate a new token if needed

3. **Verify you're using token (not password):**
   - When prompted for password, paste the **entire token**
   - Token starts with `ghp_...`

### "Authentication failed"

- Make sure you're using the **token** as password (not your GitHub password)
- Make sure token hasn't expired
- Generate a new token if needed

### "Remote origin already exists"

- Run: `git remote remove origin`
- Then add it again: `git remote add origin https://github.com/TWS-NZOH/Q.git`

## Success!

After successful push:
- Go to: https://github.com/TWS-NZOH/Q
- You should see all your files
- You're ready to create releases and share with beta testers!


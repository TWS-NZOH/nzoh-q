# Quick Start - Git Setup

## Option 1: Automated Setup (Recommended)

Run the setup script:

```bash
cd appified_report_app
./scripts/setup_git_repo.sh
```

The script will:
1. Check if Git is installed
2. Initialize Git repository (if needed)
3. Configure Git user name/email
4. Add all files
5. Create initial commit
6. Set up GitHub remote
7. Push to GitHub

## Option 2: Manual Setup

### Step 1: Initialize Git

```bash
cd appified_report_app
git init
```

### Step 2: Configure Git (if first time)

```bash
git config user.name "Your Name"
git config user.email "your.email@novozymes.com"
```

### Step 3: Add Files

```bash
git add .
```

### Step 4: Create Initial Commit

```bash
git commit -m "Initial commit - Beta ready version with embedded credentials"
```

### Step 5: Add GitHub Remote

```bash
# Replace YOUR_USERNAME with your GitHub username
git remote add origin https://github.com/YOUR_USERNAME/B2B-insights.git
```

### Step 6: Push to GitHub

```bash
git branch -M main
git push -u origin main
```

**Note:** You'll need a Personal Access Token (not password):
- GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
- Generate new token with `repo` scope
- Use token as password when prompted

## Verify Setup

1. Go to your GitHub repository
2. Refresh the page
3. You should see all your files

## Next Steps

1. **Build executable:**
   ```bash
   python scripts/build_executable.py
   ```

2. **Create release:**
   ```bash
   git tag -a v1.0.0-beta -m "Beta release"
   git push origin v1.0.0-beta
   ```

3. **On GitHub:**
   - Go to Releases → Draft a new release
   - Tag: `v1.0.0-beta`
   - Attach executable from `dist/` folder
   - Publish release

4. **Share download link** with beta testers

## Troubleshooting

**"Repository not found"**
- Check repository name and username
- Verify repository exists on GitHub
- Check remote URL: `git remote -v`

**"Permission denied"**
- Use Personal Access Token (not password)
- Verify token has `repo` scope

**"Large file" error**
- Use Git LFS for large files:
  ```bash
  git lfs install
  git lfs track "*.exe"
  git add .gitattributes
  git add dist/B2B\ Insights.exe
  git commit -m "Add executable with LFS"
  git push
  ```

## Full Documentation

See `GIT_SETUP_GUIDE.md` for detailed instructions.


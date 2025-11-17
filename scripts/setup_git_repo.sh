#!/bin/bash
# Git Repository Setup Script
# This script helps set up the Git repository and push to GitHub

set -e  # Exit on error

echo "=========================================="
echo "Quantitative Sales - Git Repository Setup"
echo "=========================================="
echo ""

# Get current directory
APP_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
cd "$APP_DIR"

echo "Current directory: $APP_DIR"
echo ""

# Check if git is installed
if ! command -v git &> /dev/null; then
    echo "❌ Git is not installed!"
    echo "Please install Git first:"
    echo "  macOS: brew install git"
    echo "  Windows: https://git-scm.com/download/win"
    echo "  Linux: sudo apt-get install git"
    exit 1
fi

echo "✓ Git is installed: $(git --version)"
echo ""

# Check if already a git repository
if [ -d ".git" ]; then
    echo "⚠️  Git repository already initialized"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    # Initialize git repository
    echo "Initializing Git repository..."
    git init
    echo "✓ Git repository initialized"
fi

echo ""

# Check git config
echo "Checking Git configuration..."
if [ -z "$(git config user.name)" ]; then
    echo "⚠️  Git user.name not set"
    read -p "Enter your name: " GIT_NAME
    git config user.name "$GIT_NAME"
fi

if [ -z "$(git config user.email)" ]; then
    echo "⚠️  Git user.email not set"
    read -p "Enter your email: " GIT_EMAIL
    git config user.email "$GIT_EMAIL"
fi

echo "✓ Git configured:"
echo "  Name: $(git config user.name)"
echo "  Email: $(git config user.email)"
echo ""

# Add all files
echo "Adding files to Git..."
git add .
echo "✓ Files added"
echo ""

# Show what will be committed
echo "Files to be committed:"
git status --short
echo ""

# Create initial commit
read -p "Create initial commit? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    git commit -m "Initial commit - Beta ready version with embedded credentials"
    echo "✓ Initial commit created"
else
    echo "Skipping commit"
    exit 0
fi

echo ""

# Add remote
echo "Setting up GitHub remote..."
echo "Repository: https://github.com/TWS-NZOH/Q"
read -p "Use this repository? (y/n) [y]: " USE_REPO
USE_REPO=${USE_REPO:-y}

if [[ $USE_REPO =~ ^[Yy]$ ]]; then
    GITHUB_USER="TWS-NZOH"
    GITHUB_REPO="Q"
    REMOTE_URL="https://github.com/TWS-NZOH/Q.git"
else
    read -p "Enter your GitHub username: " GITHUB_USER
    read -p "Enter your repository name [B2B-insights]: " GITHUB_REPO
    GITHUB_REPO=${GITHUB_REPO:-B2B-insights}
    REMOTE_URL="https://github.com/$GITHUB_USER/$GITHUB_REPO.git"
fi

# Check if remote already exists
if git remote get-url origin &> /dev/null; then
    echo "⚠️  Remote 'origin' already exists: $(git remote get-url origin)"
    read -p "Update remote? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git remote set-url origin "$REMOTE_URL"
        echo "✓ Remote updated"
    fi
else
    git remote add origin "$REMOTE_URL"
    echo "✓ Remote added: $REMOTE_URL"
fi

echo ""

# Rename branch to main
echo "Setting branch to 'main'..."
git branch -M main
echo "✓ Branch set to 'main'"
echo ""

# Push to GitHub
echo "Ready to push to GitHub!"
echo "Repository: $REMOTE_URL"
echo ""
read -p "Push to GitHub now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "Pushing to GitHub..."
    echo "Note: You may be prompted for credentials"
    echo "Use your GitHub username and a Personal Access Token (not password)"
    echo ""
    git push -u origin main
    echo ""
    echo "✓ Successfully pushed to GitHub!"
    echo ""
    echo "Repository URL: https://github.com/$GITHUB_USER/$GITHUB_REPO"
else
    echo "Skipping push"
    echo "To push later, run: git push -u origin main"
fi

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="


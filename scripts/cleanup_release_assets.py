#!/usr/bin/env python3
"""
Script to delete assets from old GitHub releases
Keeps assets only for the release created from commit a5aaa9f
Deletes all other releases and their .exe assets
"""

import os
import sys
import subprocess
import requests
from typing import List, Dict, Optional

REPO = "TWS-NZOH/Q"
API_BASE = f"https://api.github.com/repos/{REPO}"

# Commit hash to identify the release we want to keep
KEEP_COMMIT_HASH = "a5aaa9f"

def get_git_credentials() -> Optional[tuple]:
    """Get git credentials from credential helper (e.g., macOS keychain)"""
    try:
        # Use git credential fill to get stored credentials
        process = subprocess.Popen(
            ['git', 'credential', 'fill'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Send the protocol and host to git credential
        input_data = f"protocol=https\nhost=github.com\n\n"
        stdout, stderr = process.communicate(input=input_data)
        
        if process.returncode == 0:
            # Parse the output
            credentials = {}
            for line in stdout.strip().split('\n'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    credentials[key] = value
            
            username = credentials.get('username')
            password = credentials.get('password')  # This will be the token if using HTTPS with token
            
            if username and password:
                return (username, password)
    except Exception as e:
        print(f"Note: Could not retrieve git credentials: {e}")
    
    return None

def get_github_token() -> str:
    """Get GitHub token from environment, git credentials, or prompt user"""
    # First try environment variable
    token = os.environ.get("GITHUB_TOKEN")
    
    if not token:
        # Try to get from git credentials
        git_creds = get_git_credentials()
        if git_creds:
            username, password = git_creds
            # If using HTTPS with GitHub, the password is typically a Personal Access Token
            token = password
            print(f"Using credentials from git (username: {username})")
    
    if not token:
        print("GitHub token not found in environment or git credentials.")
        print("Please provide your GitHub Personal Access Token:")
        print("1. Create one at: https://github.com/settings/tokens")
        print("2. Required permissions: repo, workflow")
        print()
        token = input("Enter your GitHub token: ").strip()
        
        if not token:
            print("Error: GitHub token is required")
            sys.exit(1)
    
    return token


def get_releases(token: str) -> List[Dict]:
    """Fetch all releases from GitHub API"""
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    url = f"{API_BASE}/releases?per_page=100"
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        error_msg = response.json().get("message", "Unknown error")
        print(f"Error: {error_msg}")
        sys.exit(1)
    
    return response.json()

def get_release_assets(token: str, release_id: int) -> List[Dict]:
    """Get all assets for a release"""
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    url = f"{API_BASE}/releases/{release_id}/assets"
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    return []

def delete_release_asset(token: str, asset_id: int) -> bool:
    """Delete a release asset by ID"""
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    url = f"{API_BASE}/releases/assets/{asset_id}"
    response = requests.delete(url, headers=headers)
    
    return response.status_code == 204

def get_tag_commit_sha(token: str, tag_name: str) -> Optional[str]:
    """Get the commit SHA that a tag points to"""
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # Get tag reference
    url = f"{API_BASE}/git/refs/tags/{tag_name}"
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        obj = data.get("object", {})
        if obj.get("type") == "commit":
            return obj.get("sha", "")
        elif obj.get("type") == "tag":
            # It's an annotated tag, need to get the commit it points to
            tag_url = obj.get("url", "")
            tag_response = requests.get(tag_url, headers=headers)
            if tag_response.status_code == 200:
                tag_data = tag_response.json()
                return tag_data.get("object", {}).get("sha", "")
    
    return None

def main():
    token = get_github_token()
    
    print(f"Finding release for commit {KEEP_COMMIT_HASH}...")
    print(f"Fetching releases for {REPO}...")
    releases = get_releases(token)
    
    print(f"Total releases found: {len(releases)}")
    print()
    
    # Find the release that matches our commit by checking each tag's commit SHA
    keep_release_tag = None
    keep_release_id = None
    
    print(f"Checking releases for commit {KEEP_COMMIT_HASH}...")
    for release in releases:
        tag_name = release.get("tag_name")
        if tag_name:
            tag_commit = get_tag_commit_sha(token, tag_name)
            if tag_commit:
                # Check if this tag's commit matches our commit (support both full and short SHA)
                if tag_commit.startswith(KEEP_COMMIT_HASH) or KEEP_COMMIT_HASH.startswith(tag_commit[:7]):
                    keep_release_tag = tag_name
                    keep_release_id = release.get("id")
                    print(f"  ✓ Found release to keep: {release.get('name')} (tag: {keep_release_tag}, commit: {tag_commit[:7]})")
                    break
    
    if not keep_release_tag:
        print(f"  ⚠ Warning: Could not find release for commit {KEEP_COMMIT_HASH}")
        print("  Will proceed to delete all releases")
    
    print()
    
    assets_deleted = 0
    assets_kept = 0
    total_size_deleted = 0
    total_size_kept = 0
    
    for release in releases:
        release_id = release.get("id")
        release_tag = release.get("tag_name")
        release_name = release.get("name", release_tag)
        
        # Check if this is the release we want to keep
        should_keep = (keep_release_id and release_id == keep_release_id)
        
        # Get assets for this release
        assets = get_release_assets(token, release_id)
        
        if not assets:
            if should_keep:
                print(f"✓ Keeping release: {release_name} (tag: {release_tag}) - No assets")
            continue
        
        if should_keep:
            print(f"✓ Keeping assets for release: {release_name} (tag: {release_tag})")
            for asset in assets:
                asset_name = asset.get("name", "unknown")
                asset_size = asset.get("size", 0)
                size_mb = asset_size / (1024 * 1024)
                total_size_kept += asset_size
                assets_kept += 1
                print(f"    - {asset_name} ({size_mb:.2f} MB) - KEPT")
        else:
            print(f"Deleting assets for release: {release_name} (tag: {release_tag})")
            for asset in assets:
                asset_id = asset["id"]
                asset_name = asset.get("name", "unknown")
                asset_size = asset.get("size", 0)
                size_mb = asset_size / (1024 * 1024)
                
                print(f"    - {asset_name} ({size_mb:.2f} MB)", end=" ... ")
                
                if delete_release_asset(token, asset_id):
                    assets_deleted += 1
                    total_size_deleted += asset_size
                    print("✓ Deleted")
                else:
                    print("✗ Failed to delete")
    
    print()
    print("=" * 60)
    print("Release Asset Cleanup Summary")
    print("=" * 60)
    print(f"Assets kept: {assets_kept} ({total_size_kept / (1024 * 1024):.2f} MB)")
    print(f"Assets deleted: {assets_deleted} ({total_size_deleted / (1024 * 1024):.2f} MB)")
    print(f"Total storage freed: {total_size_deleted / (1024 * 1024):.2f} MB")
    print()

if __name__ == "__main__":
    main()


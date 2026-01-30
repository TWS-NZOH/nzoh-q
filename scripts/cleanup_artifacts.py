#!/usr/bin/env python3
"""
Script to delete artifacts from old GitHub Actions workflow runs
Keeps artifacts only for the specified runs:
  - Build Windows Executable #67
  - Create Release #5
  - Build Windows Executable #66
"""

import os
import sys
import subprocess
import requests
from typing import List, Dict, Optional

REPO = "TWS-NZOH/Q"
API_BASE = f"https://api.github.com/repos/{REPO}"

# Runs to keep artifacts for: (workflow_name, run_number) tuples
KEEP_RUNS = [
    ("Build Windows Executable", 67),
    ("Create Release", 5),
    ("Build Windows Executable", 66),
]

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

def get_workflow_runs(token: str) -> List[Dict]:
    """Fetch all workflow runs from GitHub API"""
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    url = f"{API_BASE}/actions/runs?per_page=100"
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        error_msg = response.json().get("message", "Unknown error")
        print(f"Error: {error_msg}")
        sys.exit(1)
    
    data = response.json()
    return data.get("workflow_runs", [])

def get_workflow_artifacts(token: str, run_id: int) -> List[Dict]:
    """Get all artifacts for a workflow run"""
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    url = f"{API_BASE}/actions/runs/{run_id}/artifacts"
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        return data.get("artifacts", [])
    return []

def delete_artifact(token: str, artifact_id: int) -> bool:
    """Delete an artifact by ID"""
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    url = f"{API_BASE}/actions/artifacts/{artifact_id}"
    response = requests.delete(url, headers=headers)
    
    return response.status_code == 204

def main():
    token = get_github_token()
    
    print(f"Fetching workflow runs for {REPO}...")
    runs = get_workflow_runs(token)
    
    print(f"Total workflow runs found: {len(runs)}")
    print()
    
    artifacts_deleted = 0
    artifacts_kept = 0
    total_size_deleted = 0
    total_size_kept = 0
    
    for run in runs:
        run_id = run["id"]
        run_number = run["run_number"]
        workflow_name = run["name"]
        branch = run.get("head_branch", "unknown")
        
        # Check if this run should keep its artifacts (match both workflow name AND run number)
        should_keep = (workflow_name, run_number) in KEEP_RUNS
        
        # Get artifacts for this run
        artifacts = get_workflow_artifacts(token, run_id)
        
        if not artifacts:
            continue  # Skip runs with no artifacts
        
        if should_keep:
            print(f"✓ Keeping artifacts for: {workflow_name} #{run_number} (ID: {run_id}) - Branch: {branch}")
            for artifact in artifacts:
                artifact_name = artifact.get("name", "unknown")
                artifact_size = artifact.get("size_in_bytes", 0)
                size_mb = artifact_size / (1024 * 1024)
                total_size_kept += artifact_size
                artifacts_kept += 1
                print(f"    - {artifact_name} ({size_mb:.2f} MB) - KEPT")
        else:
            print(f"Deleting artifacts for: {workflow_name} #{run_number} (ID: {run_id}) - Branch: {branch}")
            for artifact in artifacts:
                artifact_id = artifact["id"]
                artifact_name = artifact.get("name", "unknown")
                artifact_size = artifact.get("size_in_bytes", 0)
                size_mb = artifact_size / (1024 * 1024)
                
                print(f"    - {artifact_name} ({size_mb:.2f} MB)", end=" ... ")
                
                if delete_artifact(token, artifact_id):
                    artifacts_deleted += 1
                    total_size_deleted += artifact_size
                    print("✓ Deleted")
                else:
                    print("✗ Failed to delete")
    
    print()
    print("=" * 60)
    print("Artifact Cleanup Summary")
    print("=" * 60)
    print(f"Artifacts kept: {artifacts_kept} ({total_size_kept / (1024 * 1024):.2f} MB)")
    print(f"Artifacts deleted: {artifacts_deleted} ({total_size_deleted / (1024 * 1024):.2f} MB)")
    print(f"Total storage freed: {total_size_deleted / (1024 * 1024):.2f} MB")
    print()

if __name__ == "__main__":
    main()


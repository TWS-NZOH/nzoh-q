#!/usr/bin/env python3
"""
Script to delete old GitHub Actions workflow runs
Keeps only the specified runs: #67, #5, #66
"""

import os
import sys
import json
import subprocess
import requests
from typing import List, Dict, Optional

REPO = "TWS-NZOH/Q"
API_BASE = f"https://api.github.com/repos/{REPO}"

# Runs to keep: (workflow_name, run_number) tuples
# This ensures we keep the correct workflow, not just any workflow with that run number
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

def delete_workflow_run(token: str, run_id: int) -> bool:
    """Delete a workflow run by ID"""
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    url = f"{API_BASE}/actions/runs/{run_id}"
    response = requests.delete(url, headers=headers)
    
    return response.status_code == 204

def main():
    token = get_github_token()
    
    print(f"Fetching workflow runs for {REPO}...")
    runs = get_workflow_runs(token)
    
    print(f"Total workflow runs found: {len(runs)}")
    print()
    
    deleted = 0
    kept = 0
    artifacts_deleted = 0
    
    for run in runs:
        run_id = run["id"]
        run_number = run["run_number"]
        workflow_name = run["name"]
        branch = run.get("head_branch", "unknown")
        
        # Check if this run should be kept (match both workflow name AND run number)
        should_keep = (workflow_name, run_number) in KEEP_RUNS
        
        if should_keep:
            print(f"✓ Keeping Workflow: {workflow_name} #{run_number} (ID: {run_id}) - Branch: {branch}")
            kept += 1
        else:
            print(f"Deleting Workflow: {workflow_name} #{run_number} (ID: {run_id}) - Branch: {branch}")
            
            # First, delete artifacts associated with this run
            artifacts = get_workflow_artifacts(token, run_id)
            if artifacts:
                print(f"  Found {len(artifacts)} artifact(s) to delete:")
                for artifact in artifacts:
                    artifact_name = artifact.get("name", "unknown")
                    artifact_size = artifact.get("size_in_bytes", 0)
                    size_mb = artifact_size / (1024 * 1024)
                    print(f"    - {artifact_name} ({size_mb:.2f} MB)")
                    
                    if delete_artifact(token, artifact["id"]):
                        artifacts_deleted += 1
                        print(f"      ✓ Artifact deleted")
                    else:
                        print(f"      ✗ Failed to delete artifact")
            
            # Then delete the workflow run
            if delete_workflow_run(token, run_id):
                print(f"  ✓ Workflow run deleted successfully")
                deleted += 1
            else:
                print(f"  ✗ Failed to delete workflow run")
    
    print()
    print("Cleanup complete!")
    print(f"Runs kept: {kept}")
    print(f"Runs deleted: {deleted}")
    print(f"Artifacts deleted: {artifacts_deleted}")

if __name__ == "__main__":
    main()


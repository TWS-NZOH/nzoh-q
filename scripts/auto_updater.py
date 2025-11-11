"""
Auto-Updater for B2B Insights
Checks GitHub for updates and downloads latest code
"""

import os
import sys
import json
import shutil
import zipfile
import tempfile
from pathlib import Path
import requests
from datetime import datetime

class AutoUpdater:
    """Handles automatic updates from GitHub"""
    
    def __init__(self, repo_owner, repo_name, branch='main', app_dir=None):
        """
        Initialize auto-updater
        
        Args:
            repo_owner: GitHub repository owner
            repo_name: GitHub repository name
            branch: Branch to check for updates (default: main)
            app_dir: Application directory (default: parent of scripts)
        """
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.branch = branch
        self.github_api = f"https://api.github.com/repos/{repo_owner}/{repo_name}"
        
        if app_dir is None:
            # Default to parent of scripts directory
            if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
                # Running from PyInstaller - use permanent location
                import platform
                if platform.system() == 'Windows':
                    # Use AppData\Local on Windows
                    app_dir = Path(os.getenv('LOCALAPPDATA', Path.home() / 'AppData' / 'Local')) / 'B2BInsights'
                else:
                    # Use ~/.local/share on macOS/Linux
                    app_dir = Path.home() / '.local' / 'share' / 'B2BInsights'
                app_dir.mkdir(parents=True, exist_ok=True)
            else:
                # Running from source
                app_dir = Path(__file__).parent.parent
        self.app_dir = Path(app_dir)
        self.update_dir = self.app_dir / '.updates'
        self.update_dir.mkdir(exist_ok=True)
        
        self.version_file = self.app_dir / 'VERSION'
        self.update_info_file = self.update_dir / 'update_info.json'
    
    def get_current_version(self):
        """Get current version from VERSION file"""
        if self.version_file.exists():
            with open(self.version_file, 'r') as f:
                return f.read().strip()
        return "0.0.0"
    
    def get_latest_version(self):
        """Get latest version from GitHub"""
        try:
            # Get latest commit from GitHub API
            # Try multiple endpoint formats
            urls_to_try = [
                f"{self.github_api}/commits/{self.branch}",  # Standard format
                f"{self.github_api}/commits/heads/{self.branch}",  # Alternative format
                f"{self.github_api}/git/refs/heads/{self.branch}",  # Git refs format
            ]
            
            data = None
            last_error = None
            
            for url in urls_to_try:
                try:
                    response = requests.get(url, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        break
                    elif response.status_code == 404:
                        # Try next URL
                        continue
                    else:
                        response.raise_for_status()
                except requests.exceptions.RequestException as e:
                    last_error = e
                    continue
            
            if not data:
                # If all URLs failed, try to get commit info from refs endpoint
                try:
                    ref_url = f"{self.github_api}/git/refs/heads/{self.branch}"
                    ref_response = requests.get(ref_url, timeout=10)
                    if ref_response.status_code == 200:
                        ref_data = ref_response.json()
                        commit_sha = ref_data['object']['sha']
                        # Get commit details
                        commit_url = f"{self.github_api}/git/commits/{commit_sha}"
                        commit_response = requests.get(commit_url, timeout=10)
                        if commit_response.status_code == 200:
                            commit_data = commit_response.json()
                            return {
                                'version': commit_sha[:7],
                                'date': commit_data['committer']['date'],
                                'message': commit_data['message'],
                                'url': f"https://github.com/{self.repo_owner}/{self.repo_name}/commit/{commit_sha}"
                            }
                except:
                    pass
                
                # If we still don't have data, raise the last error
                if last_error:
                    raise last_error
                else:
                    raise Exception(f"Could not access GitHub API. Tried: {urls_to_try}")
            
            # Handle different response formats
            if isinstance(data, list) and len(data) > 0:
                # If response is a list, get the first commit
                commit = data[0]
                commit_sha = commit['sha'][:7]
                commit_date = commit['commit']['committer']['date']
                commit_message = commit['commit']['message']
                commit_url = commit.get('html_url', f"https://github.com/{self.repo_owner}/{self.repo_name}/commit/{commit['sha']}")
            else:
                # Single commit object
                commit_sha = data['sha'][:7]
                commit_date = data['commit']['committer']['date']
                commit_message = data['commit']['message']
                commit_url = data.get('html_url', f"https://github.com/{self.repo_owner}/{self.repo_name}/commit/{data['sha']}")
            
            return {
                'version': commit_sha,
                'date': commit_date,
                'message': commit_message,
                'url': commit_url
            }
        except Exception as e:
            print(f"Error checking for updates: {e}")
            return None
    
    def check_for_updates(self):
        """Check if updates are available"""
        current_version = self.get_current_version()
        latest_info = self.get_latest_version()
        
        if not latest_info:
            return False, None
        
        # Compare versions
        if latest_info['version'] != current_version:
            return True, latest_info
        
        return False, None
    
    def download_update(self, latest_info):
        """Download latest code from GitHub"""
        try:
            print(f"Downloading update {latest_info['version']}...")
            
            # Download zip archive from GitHub
            zip_url = f"{self.github_api}/zipball/{self.branch}"
            response = requests.get(zip_url, timeout=30, stream=True)
            response.raise_for_status()
            
            # Save to temporary file
            temp_zip = self.update_dir / 'latest.zip'
            with open(temp_zip, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Extract zip
            extract_dir = self.update_dir / 'extracted'
            if extract_dir.exists():
                shutil.rmtree(extract_dir)
            extract_dir.mkdir()
            
            with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            # Find the extracted folder (GitHub adds owner-repo-commit prefix)
            extracted_folders = list(extract_dir.iterdir())
            if not extracted_folders:
                raise Exception("No files extracted from zip")
            
            source_dir = extracted_folders[0]
            
            # Save update info
            update_info = {
                'version': latest_info['version'],
                'date': latest_info['date'],
                'source_dir': str(source_dir),
                'downloaded_at': datetime.now().isoformat()
            }
            
            with open(self.update_info_file, 'w') as f:
                json.dump(update_info, f, indent=2)
            
            # Clean up zip
            temp_zip.unlink()
            
            return source_dir
            
        except Exception as e:
            print(f"Error downloading update: {e}")
            return None
    
    def apply_update(self, source_dir):
        """Apply downloaded update to application directory"""
        try:
            print("Applying update...")
            
            source_path = Path(source_dir)
            
            # Files/directories to update (exclude sensitive files)
            exclude_patterns = [
                '.git',
                '__pycache__',
                '*.pyc',
                '.DS_Store',
                'credentials.enc',
                '.key',
                'VERSION',  # We'll update this separately
                '.updates',
                '*.log'
            ]
            
            # Copy files from source to app directory
            files_updated = 0
            for item in source_path.rglob('*'):
                if item.is_file():
                    # Check if file should be excluded
                    should_exclude = False
                    for pattern in exclude_patterns:
                        if pattern in str(item):
                            should_exclude = True
                            break
                    
                    if should_exclude:
                        continue
                    
                    # Calculate relative path
                    rel_path = item.relative_to(source_path)
                    dest_path = self.app_dir / rel_path
                    
                    # Create parent directories if needed
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Copy file
                    shutil.copy2(item, dest_path)
                    files_updated += 1
            
            # Update version file
            latest_info = self.get_latest_version()
            if latest_info:
                with open(self.version_file, 'w') as f:
                    f.write(latest_info['version'])
            
            print(f"✓ Update applied successfully ({files_updated} files updated)")
            return True
            
        except Exception as e:
            print(f"Error applying update: {e}")
            return False
    
    def update(self, force=False):
        """
        Check for and apply updates
        
        Args:
            force: Force update even if versions match
            
        Returns:
            tuple: (updated: bool, message: str)
        """
        has_update, latest_info = self.check_for_updates()
        
        if not has_update and not force:
            return False, "Already up to date"
        
        if not latest_info:
            return False, "Could not check for updates"
        
        # Download update
        source_dir = self.download_update(latest_info)
        if not source_dir:
            return False, "Failed to download update"
        
        # Apply update
        success = self.apply_update(source_dir)
        if success:
            return True, f"Updated to version {latest_info['version']}"
        else:
            return False, "Failed to apply update"


"""
Secure Credential Management System
Handles encrypted storage and retrieval of Salesforce credentials
"""

import os
import json
import base64
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import getpass

class CredentialsManager:
    """Manages secure storage and retrieval of Salesforce credentials"""
    
    def __init__(self, config_dir=None):
        """
        Initialize credentials manager
        
        Args:
            config_dir: Directory to store encrypted credentials (default: user's home/.b2b_insights)
        """
        if config_dir is None:
            config_dir = Path.home() / '.b2b_insights'
        else:
            config_dir = Path(config_dir)
        
        self.config_dir = config_dir
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.credentials_file = self.config_dir / 'credentials.enc'
        self.key_file = self.config_dir / '.key'
        
    def _get_encryption_key(self):
        """Generate or retrieve encryption key based on machine ID"""
        if self.key_file.exists():
            with open(self.key_file, 'rb') as f:
                return f.read()
        
        # Generate key from machine-specific identifier
        # This ensures credentials are machine-specific
        machine_id = self._get_machine_id()
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'b2b_insights_salt',  # Fixed salt for consistency
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(machine_id.encode()))
        
        # Save key for future use
        with open(self.key_file, 'wb') as f:
            f.write(key)
        
        return key
    
    def _get_machine_id(self):
        """Get a machine-specific identifier"""
        import platform
        import socket
        
        # Combine machine name and platform info
        machine_name = socket.gethostname()
        platform_info = platform.platform()
        return f"{machine_name}_{platform_info}"
    
    def _get_cipher(self):
        """Get Fernet cipher for encryption/decryption"""
        key = self._get_encryption_key()
        return Fernet(key)
    
    def save_credentials(self, username, password, security_token, environment='live'):
        """
        Save credentials to encrypted file
        
        Args:
            username: Salesforce username
            password: Salesforce password
            security_token: Salesforce security token
            environment: 'live' or 'uat'
        """
        credentials = {
            'username': username,
            'password': password,
            'security_token': security_token,
            'environment': environment
        }
        
        cipher = self._get_cipher()
        encrypted_data = cipher.encrypt(json.dumps(credentials).encode())
        
        with open(self.credentials_file, 'wb') as f:
            f.write(encrypted_data)
        
        # Set restrictive permissions (Unix-like systems)
        if os.name != 'nt':
            os.chmod(self.credentials_file, 0o600)
            os.chmod(self.key_file, 0o600)
    
    def load_credentials(self):
        """
        Load credentials from encrypted file
        
        Returns:
            dict with keys: username, password, security_token, environment
        """
        if not self.credentials_file.exists():
            raise FileNotFoundError(
                "Credentials file not found. Please run setup to configure credentials."
            )
        
        with open(self.credentials_file, 'rb') as f:
            encrypted_data = f.read()
        
        cipher = self._get_cipher()
        decrypted_data = cipher.decrypt(encrypted_data)
        credentials = json.loads(decrypted_data.decode())
        
        return credentials
    
    def credentials_exist(self):
        """Check if credentials file exists"""
        return self.credentials_file.exists()
    
    def setup_credentials_interactive(self):
        """Interactive setup for credentials"""
        print("=" * 70)
        print("B2B Insights - Credential Setup")
        print("=" * 70)
        print("\nPlease enter your Salesforce credentials:")
        print("(These will be encrypted and stored locally on your machine)\n")
        
        username = input("Salesforce Username: ").strip()
        password = getpass.getpass("Salesforce Password: ")
        security_token = getpass.getpass("Security Token: ")
        
        print("\nEnvironment:")
        print("1. Live (Production)")
        print("2. UAT (Test)")
        env_choice = input("Select environment (1 or 2) [1]: ").strip() or "1"
        environment = 'live' if env_choice == '1' else 'uat'
        
        try:
            self.save_credentials(username, password, security_token, environment)
            print("\n✓ Credentials saved successfully!")
            print(f"Credentials stored in: {self.config_dir}")
            return True
        except Exception as e:
            print(f"\n✗ Error saving credentials: {e}")
            return False


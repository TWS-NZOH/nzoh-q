"""
Embedded Credentials Manager
Decrypts embedded credentials for approved beta testers
"""

import os
import json
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from config.embedded_credentials import (
    ENCRYPTED_CREDENTIALS,
    APPROVED_USERS,
    ENCRYPTION_PASSWORD,
    ENCRYPTION_SALT
)

class EmbeddedCredentialsManager:
    """Manages embedded encrypted credentials for approved users"""
    
    def __init__(self):
        """Initialize the credentials manager"""
        self.encrypted_credentials = ENCRYPTED_CREDENTIALS
        self.approved_users = APPROVED_USERS
    
    def _get_windows_username(self):
        """Get Windows username"""
        try:
            # Try multiple methods to get username
            username = os.getenv('USERNAME')  # Windows
            if not username:
                username = os.getenv('USER')  # Unix-like
            if not username:
                import getpass
                username = getpass.getuser()
            
            # Convert to uppercase for comparison
            return username.upper()
        except Exception:
            return None
    
    def _is_approved_user(self):
        """Check if current Windows username is in approved list"""
        username = self._get_windows_username()
        if not username:
            return False
        
        # Check if username matches any approved user
        return username in [user.upper() for user in self.approved_users]
    
    def _generate_decryption_key(self):
        """Generate decryption key (must match encryption key)"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=ENCRYPTION_SALT,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(ENCRYPTION_PASSWORD))
        return key
    
    def get_credentials(self):
        """
        Get decrypted credentials if user is approved
        
        Returns:
            dict with keys: username, password, security_token, environment
            None if user not approved or decryption fails
        """
        # Check if user is approved
        if not self._is_approved_user():
            username = self._get_windows_username()
            raise PermissionError(
                f"User '{username}' is not authorized to use this application. "
                f"Approved users: {', '.join(self.approved_users)}"
            )
        
        # Check if credentials are embedded
        if not self.encrypted_credentials or self.encrypted_credentials.strip() == "":
            raise ValueError(
                "Credentials not embedded. Please run encrypt_credentials.py and update embedded_credentials.py"
            )
        
        try:
            # Decrypt credentials
            key = self._generate_decryption_key()
            cipher = Fernet(key)
            
            # Decode from base64
            encrypted_data = base64.b64decode(self.encrypted_credentials.encode())
            
            # Decrypt
            decrypted_data = cipher.decrypt(encrypted_data)
            credentials = json.loads(decrypted_data.decode())
            
            return credentials
            
        except Exception as e:
            raise ValueError(f"Failed to decrypt credentials: {str(e)}")
    
    def get_user_initials(self):
        """
        Get user initials from Windows username
        
        Returns:
            str: User initials (e.g., 'BECOB') or None if not found
        """
        username = self._get_windows_username()
        if not username:
            return None
        
        # TESTING: Map TWS to CYK for testing purposes
        if username == 'TWS':
            username = 'CYK'
            print(f"TESTING: Mapped TWS to CYK for testing")
        
        # Check if username is in approved list
        if username in [user.upper() for user in self.approved_users]:
            return username
        
        return None
    
    def is_user_approved(self):
        """Check if current user is approved"""
        return self._is_approved_user()


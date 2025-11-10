#!/usr/bin/env python3
"""
Encrypt mblintegration credentials for embedding in application
Run this once to generate encrypted credentials that can be embedded in code
"""

import base64
import json
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Approved beta testers
APPROVED_USERS = ['BECOB', 'BENM', 'MIYR', 'AOV', 'JETE', 'SACW', 'KYM', 'LEWA', 'CYK']

def generate_encryption_key():
    """Generate a fixed encryption key for embedding"""
    # Use a fixed salt and password for consistent encryption
    password = b"b2b_insights_beta_2024"  # Fixed password for embedding
    salt = b"b2b_insights_salt_v1"  # Fixed salt
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password))
    return key

def encrypt_credentials(username, password, security_token, environment='live'):
    """Encrypt Salesforce credentials"""
    credentials = {
        'username': username,
        'password': password,
        'security_token': security_token,
        'environment': environment
    }
    
    key = generate_encryption_key()
    cipher = Fernet(key)
    
    encrypted_data = cipher.encrypt(json.dumps(credentials).encode())
    return base64.b64encode(encrypted_data).decode()

def main():
    """Main function to encrypt credentials"""
    print("=" * 70)
    print("B2B Insights - Credential Encryption Tool")
    print("=" * 70)
    print("\nThis tool will encrypt mblintegration credentials for embedding in the application.")
    print("The encrypted credentials will only work for approved beta testers.\n")
    
    # Get credentials
    print("Enter mblintegration Salesforce credentials:")
    username = input("Username [mblintegration@novozymes.com]: ").strip() or "mblintegration@novozymes.com"
    password = input("Password: ").strip()
    security_token = input("Security Token: ").strip()
    
    print("\nEnvironment:")
    print("1. Live (Production)")
    print("2. UAT (Test)")
    env_choice = input("Select environment (1 or 2) [1]: ").strip() or "1"
    environment = 'live' if env_choice == '1' else 'uat'
    
    # Encrypt
    encrypted = encrypt_credentials(username, password, security_token, environment)
    
    print("\n" + "=" * 70)
    print("Encrypted Credentials (copy this to embed in code):")
    print("=" * 70)
    print(encrypted)
    print("\n" + "=" * 70)
    print("Approved Beta Testers:")
    print("=" * 70)
    for user in APPROVED_USERS:
        print(f"  - {user}")
    print("\nThese users will be able to decrypt and use the credentials.")
    print("=" * 70)
    
    # Also save to a file for easy copying
    output_file = "encrypted_credentials.txt"
    with open(output_file, 'w') as f:
        f.write(encrypted)
        f.write("\n\nApproved Users:\n")
        for user in APPROVED_USERS:
            f.write(f"  - {user}\n")
    
    print(f"\n✓ Encrypted credentials also saved to: {output_file}")

if __name__ == "__main__":
    main()


"""
Embedded Encrypted Credentials
This file contains encrypted mblintegration credentials that can only be
decrypted by approved beta testers (verified via Windows username).

To update credentials:
1. Run scripts/encrypt_credentials.py
2. Copy the encrypted string below
3. Update APPROVED_USERS list if needed
"""

# Encrypted mblintegration credentials
# This will be populated by running encrypt_credentials.py
ENCRYPTED_CREDENTIALS = "Z0FBQUFBQnBFaXBRckNHQ1VKYnZ0bmR0Z0wyWUQ1M3V5cldseEg4NTI5SzBLYlhkOGNjNVlNYTliT2lTcU9PeDRjb1BPWlEtbDhockJDMnNGTzU5MHkxT0g5M2xLYUI0MjNnQWVWaDJhYjBXSVlNbkY3aGRwWXh0WnRlSWc2OWZPQV92alBUT3lNbnptUmZ4dGl6bGhVcEtIQUdvQkVkM19FNkJwX1VwUmVoek05TjhwNG9odmlsMmVNaEx4LUNBUGtZamQ1RzU5SWs4dnQtZklJckFwb3dUY015YmNEcnhUWmJtY1VzdlhfQW5FVjFyZDdIQkNPTFZKYzE2cENva1NyYzA3OTZjVUN4MnB0OFZubVdldnphZldqUTYxNnk2R25zWFFUb2pRTTR5ZmFXLUZLYVBNalU9"  # Replace with encrypted string from encrypt_credentials.py

# Approved beta testers (Windows usernames)
APPROVED_USERS = ['BECOB', 'BENM', 'MIYR', 'AOV', 'JETE', 'SACW', 'KYM', 'LEWA', 'CYK', 'TWS', 'AAPO'] # beta testers
# ADMIN_USERS = ['TWS', 'AAPO'] # admin
# Encryption key derivation parameters (must match encrypt_credentials.py)
ENCRYPTION_PASSWORD = b"b2b_insights_beta_2024"
ENCRYPTION_SALT = b"b2b_insights_salt_v1"


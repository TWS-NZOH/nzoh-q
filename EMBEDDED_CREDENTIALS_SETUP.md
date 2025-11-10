# Embedded Credentials Setup Guide

## Overview

This application uses embedded encrypted credentials for the mblintegration Salesforce account. The credentials are encrypted and embedded in the code, but can only be decrypted by approved beta testers (verified via Windows username).

## Setup Process

### Step 1: Encrypt Credentials

1. **Run the encryption script**
   ```bash
   python scripts/encrypt_credentials.py
   ```

2. **Enter mblintegration credentials**
   - Username: `mblintegration@novozymes.com`
   - Password: (your password)
   - Security Token: (your security token)
   - Environment: Live or UAT

3. **Copy the encrypted string** that is output

### Step 2: Embed Credentials

1. **Open `config/embedded_credentials.py`**

2. **Paste the encrypted string** into `ENCRYPTED_CREDENTIALS`:
   ```python
   ENCRYPTED_CREDENTIALS = "YOUR_ENCRYPTED_STRING_HERE"
   ```

3. **Verify approved users list** (should already be correct):
   ```python
   APPROVED_USERS = ['BECOB', 'BENM', 'MIYR', 'AOV', 'JETE', 'SACW', 'KYM', 'LEWA', 'CYK']
   ```

4. **Save the file**

### Step 3: Test

1. **Run the application** on a machine with an approved Windows username
2. **Verify** that:
   - The initials step is skipped automatically
   - User goes directly to account selection
   - Salesforce connection works

## How It Works

1. **On Launch**: Application checks Windows username
2. **If Approved**: 
   - Decrypts embedded credentials
   - Skips initials input step
   - Auto-populates user initials
   - Connects to Salesforce using mblintegration account
3. **If Not Approved**: 
   - Shows error message
   - Application does not start

## Security

- **Encryption**: Credentials encrypted using Fernet (symmetric encryption)
- **Key Derivation**: PBKDF2 with 100,000 iterations
- **Authorization**: Only approved Windows usernames can decrypt
- **No Network**: Decryption happens locally, credentials never sent over network

## Approved Beta Testers

- BECOB
- BENM
- MIYR
- AOV
- JETE
- SACW
- KYM
- LEWA
- CYK

## Updating Credentials

If you need to update the mblintegration credentials:

1. Run `scripts/encrypt_credentials.py` again
2. Copy the new encrypted string
3. Update `ENCRYPTED_CREDENTIALS` in `config/embedded_credentials.py`
4. Commit and push to GitHub
5. Beta testers will get the update automatically

## Adding New Beta Testers

1. **Add username to approved list** in `config/embedded_credentials.py`:
   ```python
   APPROVED_USERS = ['BECOB', 'BENM', 'MIYR', 'AOV', 'JETE', 'SACW', 'KYM', 'LEWA', 'CYK', 'NEWUSER']
   ```

2. **Commit and push** to GitHub

3. **Beta tester gets update** automatically on next launch

## Troubleshooting

**"User not authorized"**
- Check that Windows username matches approved list (case-insensitive)
- Verify username in `config/embedded_credentials.py`

**"Credentials not embedded"**
- Make sure `ENCRYPTED_CREDENTIALS` is not empty in `config/embedded_credentials.py`
- Re-run `scripts/encrypt_credentials.py` and update the file

**"Failed to decrypt credentials"**
- Verify encryption parameters match between `encrypt_credentials.py` and `embedded_credentials_manager.py`
- Re-encrypt credentials if needed


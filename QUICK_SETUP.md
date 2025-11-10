# Quick Setup Guide - Embedded Credentials

## For Developers (One-Time Setup)

### Step 1: Encrypt Credentials

```bash
cd appified_report_app
python scripts/encrypt_credentials.py
```

Enter:
- Username: `mblintegration@novozymes.com`
- Password: (your password)
- Security Token: (your security token)
- Environment: `1` (Live) or `2` (UAT)

### Step 2: Embed Encrypted String

1. Copy the encrypted string from the output
2. Open `config/embedded_credentials.py`
3. Paste into `ENCRYPTED_CREDENTIALS`:
   ```python
   ENCRYPTED_CREDENTIALS = "YOUR_ENCRYPTED_STRING_HERE"
   ```
4. Save the file

### Step 3: Verify Approved Users

The approved users list should already be correct:
```python
APPROVED_USERS = ['BECOB', 'BENM', 'MIYR', 'AOV', 'JETE', 'SACW', 'KYM', 'LEWA', 'CYK']
```

### Step 4: Test

Run the application:
```bash
python scripts/launcher.py
```

On an approved user's machine:
- Should skip initials step
- Should auto-populate initials from Windows username
- Should connect to Salesforce automatically

## How It Works

1. **Windows Username Check**: On launch, checks if Windows username matches approved list
2. **Auto-Skip**: If approved, skips initials input step
3. **Auto-Populate**: Uses Windows username as initials
4. **Decrypt**: Decrypts embedded mblintegration credentials
5. **Connect**: Connects to Salesforce using mblintegration account

## Security

- ✅ Credentials encrypted before embedding
- ✅ Only approved Windows usernames can decrypt
- ✅ Credentials never sent over network
- ✅ Decryption happens locally
- ✅ No user input required for credentials

## Beta Testers

The following Windows usernames are approved:
- BECOB
- BENM
- MIYR
- AOV
- JETE
- SACW
- KYM
- LEWA
- CYK

## Troubleshooting

**"User not authorized"**
- Check Windows username matches approved list (case-insensitive)
- Verify username in `config/embedded_credentials.py`

**"Credentials not embedded"**
- Run `scripts/encrypt_credentials.py` again
- Update `ENCRYPTED_CREDENTIALS` in `config/embedded_credentials.py`

**"Still asking for initials"**
- Check that Windows username is in approved list
- Verify `get_system_initials` API endpoint is working
- Check browser console for errors


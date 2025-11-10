# Distribution Guide for Beta Testers

## Overview

This guide explains how to distribute the B2B Insights application to beta testers and provide them with download links.

## Pre-Distribution Checklist

- [ ] Git repository set up and code pushed
- [ ] Embedded credentials configured
- [ ] Executable built and tested
- [ ] Approved users list verified
- [ ] Download method chosen

## Distribution Methods

### Method 1: GitHub Releases (Recommended)

**Best for:** Version control, easy updates, professional distribution

#### Steps:

1. **Build the executable:**
   ```bash
   cd appified_report_app
   python scripts/build_executable.py
   ```

2. **Create a release tag:**
   ```bash
   git tag -a v1.0.0-beta -m "Beta release v1.0.0"
   git push origin v1.0.0-beta
   ```

3. **On GitHub:**
   - Go to your repository
   - Click **Releases** → **Draft a new release**
   - **Tag:** `v1.0.0-beta`
   - **Title:** `B2B Insights - Beta Release v1.0.0`
   - **Description:** 
     ```
     Beta testing release for B2B Insights application.
     
     Approved users: BECOB, BENM, MIYR, AOV, JETE, SACW, KYM, LEWA, CYK
     
     Installation:
     1. Download the executable for your platform
     2. Run the executable
     3. Application will auto-detect your Windows username
     4. If approved, application opens automatically
     
     System Requirements:
     - Windows 10/11 or macOS 10.14+
     - Internet connection
     - Approved Windows username
     ```
   - **Attach files:** Drag and drop executable from `dist/` folder
   - Click **Publish release**

4. **Share download link:**
   - Release page: `https://github.com/YOUR_USERNAME/B2B-insights/releases/tag/v1.0.0-beta`
   - Direct download: `https://github.com/YOUR_USERNAME/B2B-insights/releases/download/v1.0.0-beta/B2B-Insights.exe`

#### Advantages:
- ✅ Version control
- ✅ Release notes
- ✅ Easy updates (new releases)
- ✅ Professional appearance
- ✅ Download statistics

### Method 2: File Sharing Service

**Best for:** Quick distribution, no GitHub account needed

#### Steps:

1. **Build the executable:**
   ```bash
   python scripts/build_executable.py
   ```

2. **Upload to service:**
   - **Dropbox:** Upload to Dropbox, create shareable link
   - **Google Drive:** Upload to Google Drive, create shareable link
   - **OneDrive:** Upload to OneDrive, create shareable link
   - **WeTransfer:** Upload file, get temporary link (7 days)

3. **Share link with beta testers**

#### Advantages:
- ✅ Quick setup
- ✅ No GitHub required
- ✅ Easy to share

#### Disadvantages:
- ❌ No version control
- ❌ Manual updates needed
- ❌ Link expiration (some services)

### Method 3: Private Server/Website

**Best for:** Custom branding, full control

#### Steps:

1. **Build the executable**
2. **Upload to private server**
3. **Create download page**
4. **Share URL with beta testers**

## Creating Download Instructions

### Email Template for Beta Testers

```
Subject: B2B Insights - Beta Testing Application

Hi Team,

I'm excited to share the B2B Insights application for beta testing!

DOWNLOAD LINK:
[YOUR_DOWNLOAD_LINK]

APPROVED USERS:
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

INSTALLATION:
1. Download the executable from the link above
2. Run the executable (no installation required)
3. The application will automatically detect your Windows username
4. If you're an approved user, the application will open automatically
5. If you're not approved, you'll see an error message - contact me for access

FEATURES:
- Automatic Windows username detection
- Skips initials step for approved users
- Auto-updates from GitHub
- Desktop shortcut creation

SYSTEM REQUIREMENTS:
- Windows 10/11 or macOS 10.14+
- Internet connection (for updates and Salesforce access)
- Approved Windows username

TROUBLESHOOTING:
- If you see "User not authorized": Your Windows username may not match the approved list
- If the application won't start: Check that you have an internet connection
- For other issues: Contact [YOUR_CONTACT_INFO]

FEEDBACK:
Please share any feedback, bugs, or suggestions with me.

Thanks!
[YOUR_NAME]
```

## Update Distribution

### When You Push Updates

1. **Make changes and commit:**
   ```bash
   git add .
   git commit -m "Description of changes"
   git push
   ```

2. **Build new executable:**
   ```bash
   python scripts/build_executable.py
   ```

3. **Create new release:**
   ```bash
   git tag -a v1.0.1-beta -m "Beta release v1.0.1"
   git push origin v1.0.1-beta
   ```

4. **On GitHub:**
   - Create new release with new tag
   - Attach new executable
   - Beta testers will get update notification

### Auto-Update for Beta Testers

The application automatically checks for updates on launch:
- If update available, downloads and applies automatically
- No action required from beta testers
- Works seamlessly in background

## Security Considerations

✅ **Repository should be private** (for beta testing)
✅ **Credentials are encrypted** and embedded
✅ **Only approved users** can decrypt credentials
✅ **Executable is self-contained** (no credentials needed)
✅ **Download links can be shared** (credentials already embedded)

## Download Link Examples

### GitHub Release:
```
https://github.com/YOUR_USERNAME/B2B-insights/releases/download/v1.0.0-beta/B2B-Insights.exe
```

### Dropbox:
```
https://www.dropbox.com/s/[FILE_ID]/B2B-Insights.exe?dl=1
```

### Google Drive:
```
https://drive.google.com/uc?export=download&id=[FILE_ID]
```

### Direct Link (Private Server):
```
https://your-server.com/downloads/B2B-Insights.exe
```

## Beta Tester Onboarding

1. **Send download link** via email
2. **Include instructions** (use email template above)
3. **Provide contact info** for support
4. **Set up feedback channel** (email, Slack, etc.)
5. **Monitor usage** and collect feedback

## Quick Reference

### For Developers:
```bash
# Build executable
python scripts/build_executable.py

# Create release
git tag -a v1.0.0-beta -m "Beta release"
git push origin v1.0.0-beta

# Then create release on GitHub with executable attached
```

### For Beta Testers:
1. Download executable from link
2. Run executable
3. Application auto-detects Windows username
4. If approved, opens automatically
5. Use application as normal

## Support

For issues or questions:
- Check `README_BETA.md` for troubleshooting
- Contact administrator for access issues
- Report bugs via feedback channel


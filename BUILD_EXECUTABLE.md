# Building the Executable

## Prerequisites

1. **Python 3.8+** installed
2. **All dependencies** installed:
   ```bash
   pip install -r requirements.txt
   ```

## Building

1. **Run the build script**
   ```bash
   python scripts/build_executable.py
   ```

2. **Find the executable**
   - Windows: `dist/B2B Insights.exe`
   - macOS: `dist/B2B Insights`
   - Linux: `dist/B2B Insights`

## Distribution

1. **Test the executable** on your machine first
2. **Create a zip file** containing:
   - The executable
   - `README_BETA.md` (instructions for beta testers)

3. **Share with beta testers** via:
   - File sharing service (Dropbox, Google Drive, etc.)
   - Direct download link
   - Email attachment (if small enough)

## Beta Tester Instructions

1. **Download the executable**
2. **Run the executable** (first time will prompt for credentials)
3. **Desktop shortcut** will be created automatically
4. **Future launches** will auto-update from GitHub

## Troubleshooting

**"PyInstaller not found"**
- The build script will install it automatically
- Or manually: `pip install pyinstaller`

**"Build failed"**
- Check that all dependencies are installed
- Make sure Python 3.8+ is being used
- Check error messages for missing modules

**"Executable won't run"**
- Make sure all required files are in the same directory
- Check that credentials are configured
- Try running from command line to see error messages

## Customization

To customize the executable:

1. **Edit `scripts/build_executable.py`**
   - Change icon path
   - Modify included files
   - Adjust PyInstaller options

2. **Rebuild**
   ```bash
   python scripts/build_executable.py
   ```


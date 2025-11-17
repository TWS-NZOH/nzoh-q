#!/usr/bin/env python3
"""
Build executable for Quantitative Sales
Creates a standalone executable using PyInstaller
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def check_pyinstaller():
    """Check if PyInstaller is installed"""
    try:
        import PyInstaller
        return True
    except ImportError:
        return False

def install_pyinstaller():
    """Install PyInstaller"""
    print("Installing PyInstaller...")
    subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyinstaller'], check=True)
    print("PyInstaller installed")

def build_executable():
    """Build the executable"""
    app_dir = Path(__file__).parent.parent
    scripts_dir = Path(__file__).parent
    dist_dir = app_dir / 'dist'
    build_dir = app_dir / 'build'
    spec_file = app_dir / 'b2b_insights.spec'
    
    # Clean previous builds
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    if build_dir.exists():
        shutil.rmtree(build_dir)
    
    # Check if icon exists (Windows needs .ico, macOS/Linux can use .svg)
    import platform
    if platform.system() == 'Windows':
        # Windows requires .ico format - PyInstaller cannot use SVG
        icon_path = app_dir / 'static' / 'images' / 'q-icon.ico'
        print(f"Looking for icon at: {icon_path}")
        if not icon_path.exists():
            print("Warning: q-icon.ico not found. Executable will be built without icon.")
            print(f"Checking directory contents: {list((app_dir / 'static' / 'images').iterdir()) if (app_dir / 'static' / 'images').exists() else 'Directory not found'}")
            icon_path = None
        else:
            print(f"Found icon: {icon_path}")
    else:
        # macOS/Linux can use .svg
        icon_path = app_dir / 'static' / 'images' / 'q-icon.svg'
        if not icon_path.exists():
            icon_path = None
    
    # Convert paths to forward slashes to avoid escape sequence issues on Windows
    def path_to_spec(path):
        """Convert Path object to string with forward slashes for spec file"""
        return str(path).replace('\\', '/')
    
    icon_str = f"r'{path_to_spec(icon_path)}'" if icon_path and icon_path.exists() else 'None'
    
    # Create spec file for PyInstaller
    spec_content = f"""# -*- mode: python ; coding: utf-8 -*-
import os

block_cipher = None

a = Analysis(
    [r'{path_to_spec(scripts_dir / "launcher.py")}'],
    pathex=[r'{path_to_spec(app_dir)}'],
    binaries=[],
    datas=[
        (r'{path_to_spec(app_dir / "static")}', 'static'),
        (r'{path_to_spec(app_dir / "config")}', 'config'),
        (r'{path_to_spec(app_dir / "b2b_insights_core")}', 'b2b_insights_core'),
        (r'{path_to_spec(app_dir / "app.py")}', '.'),
        (r'{path_to_spec(app_dir / "indicators_report.py")}', '.'),
        (r'{path_to_spec(app_dir / "sales_dashboard.py")}', '.'),
        (r'{path_to_spec(app_dir / "vue_dashboard.html")}', '.'),
    ],
    hiddenimports=[
        'flask',
        'flask_cors',
        'pandas',
        'pandas_ta',
        'simple_salesforce',
        'plotly',
        'numpy',
        'cryptography',
        'requests',
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Quantitative Sales',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon={icon_str},
)
"""
    
    with open(spec_file, 'w') as f:
        f.write(spec_content)
    
    print("Building executable...")
    print("This may take several minutes...")
    
    # Run PyInstaller
    try:
        subprocess.run([
            sys.executable, '-m', 'PyInstaller',
            '--clean',
            '--noconfirm',
            str(spec_file)
        ], check=True, cwd=str(app_dir))
        
        print("=" * 70)
        print("Build complete!")
        print("=" * 70)
        print(f"\nExecutable location: {dist_dir / 'Quantitative Sales'}")
        print("\nYou can now distribute this executable to beta testers.")
        
    except subprocess.CalledProcessError as e:
        print(f"Build failed: {e}")
        return False
    
    return True

def main():
    """Main build function"""
    print("=" * 70)
    print("Quantitative Sales - Executable Builder")
    print("=" * 70)
    print()
    
    if not check_pyinstaller():
        install_pyinstaller()
    
    success = build_executable()
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()


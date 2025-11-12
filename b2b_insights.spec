# -*- mode: python ; coding: utf-8 -*-
import os

block_cipher = None

a = Analysis(
    ['/Users/tws/Desktop/NZOH/nzoh-programs/B2B-insights/appified_report_app/scripts/launcher.py'],
    pathex=['/Users/tws/Desktop/NZOH/nzoh-programs/B2B-insights/appified_report_app'],
    binaries=[],
    datas=[
        ('/Users/tws/Desktop/NZOH/nzoh-programs/B2B-insights/appified_report_app/static', 'static'),
        ('/Users/tws/Desktop/NZOH/nzoh-programs/B2B-insights/appified_report_app/config', 'config'),
        ('/Users/tws/Desktop/NZOH/nzoh-programs/B2B-insights/appified_report_app/b2b_insights_core', 'b2b_insights_core'),
        ('/Users/tws/Desktop/NZOH/nzoh-programs/B2B-insights/appified_report_app/app.py', '.'),
        ('/Users/tws/Desktop/NZOH/nzoh-programs/B2B-insights/appified_report_app/indicators_report.py', '.'),
        ('/Users/tws/Desktop/NZOH/nzoh-programs/B2B-insights/appified_report_app/sales_dashboard.py', '.'),
        ('/Users/tws/Desktop/NZOH/nzoh-programs/B2B-insights/appified_report_app/vue_dashboard.html', '.'),
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
    hooksconfig={},
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
    name='B2B Insights',
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
    icon='/Users/tws/Desktop/NZOH/nzoh-programs/B2B-insights/appified_report_app/static/images/q-icon.svg',
)

"""
py2app setup to build Claude Usage Monitor as a macOS .app bundle.

Usage:
    pip install py2app rumps
    python setup.py py2app
"""

from setuptools import setup

APP = ["claude_usage_menubar.py"]

DATA_FILES = []

OPTIONS = {
    "argv_emulation": False,
    "plist": {
        "CFBundleName": "Claude Usage Monitor",
        "CFBundleDisplayName": "Claude Usage Monitor",
        "CFBundleIdentifier": "com.karthikodes.claude-usage-monitor",
        "CFBundleVersion": "1.0.0",
        "CFBundleShortVersionString": "1.0",
        # Menu bar only — no Dock icon
        "LSUIElement": True,
        # Allow sending notifications
        "NSUserNotificationAlertStyle": "alert",
        "NSAppTransportSecurity": {"NSAllowsArbitraryLoads": True},
    },
    "packages": ["rumps"],
    "excludes": [
        "numpy", "scipy", "pandas", "matplotlib", "PIL", "Pillow",
        "tkinter", "test", "unittest", "setuptools", "pkg_resources",
        "wheel", "pip", "distutils",
    ],
    "iconfile": None,  # set to an .icns path if you have one
}

setup(
    app=APP,
    name="Claude Usage Monitor",
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)

#!/usr/bin/env python3
"""
Install EB Garamond fonts for the current user (no admin required on Windows 10+).
Downloads variable TTF files from Google Fonts GitHub mirror and installs them to
the user fonts directory which XeLaTeX/fontspec can find automatically.
"""
import os
import sys
import shutil
import tempfile
import urllib.request
from pathlib import Path

FONT_FILES = {
    "EBGaramond-Regular.ttf":  "https://raw.githubusercontent.com/google/fonts/main/ofl/ebgaramond/EBGaramond%5Bwght%5D.ttf",
    "EBGaramond-Italic.ttf":   "https://raw.githubusercontent.com/google/fonts/main/ofl/ebgaramond/EBGaramond-Italic%5Bwght%5D.ttf",
}

MARKER_FILE = "EBGaramond-Regular.ttf"


def get_user_fonts_dir() -> Path:
    """User-level fonts dir — no admin needed on Windows 10+."""
    if sys.platform == "win32":
        local_app = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return local_app / "Microsoft" / "Windows" / "Fonts"
    elif sys.platform == "darwin":
        return Path.home() / "Library" / "Fonts"
    else:
        return Path.home() / ".local" / "share" / "fonts"


def is_installed() -> bool:
    # Check user dir
    user_dir = get_user_fonts_dir()
    if (user_dir / MARKER_FILE).exists():
        return True
    # Also check system dir
    system_dir = Path(os.environ.get("WINDIR", "C:\\Windows")) / "Fonts"
    if (system_dir / MARKER_FILE).exists():
        return True
    return False


def register_user_font_windows(font_path: Path):
    """Register a per-user font in HKCU (no admin required)."""
    try:
        import winreg
        reg_path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0,
                            winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, font_path.stem + " (TrueType)", 0,
                              winreg.REG_SZ, str(font_path))
    except Exception:
        pass  # Non-fatal


def main():
    if is_installed():
        print("EB Garamond is already installed.")
        return

    fonts_dir = get_user_fonts_dir()
    fonts_dir.mkdir(parents=True, exist_ok=True)
    print(f"Installing to user fonts directory: {fonts_dir}")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        installed_any = False

        for dest_name, url in FONT_FILES.items():
            dest = fonts_dir / dest_name
            if dest.exists():
                print(f"  Already present: {dest_name}")
                installed_any = True
                continue

            tmp_file = tmp / dest_name
            print(f"  Downloading {dest_name}...", end=" ", flush=True)
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=60) as resp, \
                     open(tmp_file, "wb") as f:
                    shutil.copyfileobj(resp, f)
                kb = tmp_file.stat().st_size // 1024
                print(f"({kb} KB)")
            except Exception as e:
                print(f"FAILED: {e}")
                sys.exit(1)

            shutil.copy2(tmp_file, dest)
            if sys.platform == "win32":
                register_user_font_windows(dest)
            print(f"  Installed: {dest_name}")
            installed_any = True

    if installed_any:
        if sys.platform == "win32":
            try:
                import ctypes
                ctypes.windll.user32.SendMessageW(0xFFFF, 0x001D, 0, 0)
            except Exception:
                pass
        elif sys.platform != "darwin":
            os.system("fc-cache -fv > /dev/null 2>&1")
        print("EB Garamond installed successfully.")
    else:
        print("Nothing installed.")
        sys.exit(1)


if __name__ == "__main__":
    main()

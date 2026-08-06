"""
Small persisted settings file -- CSV source URL and the active download
path, editable from the UI. Stored in /app/data so it survives container
rebuilds (as long as ./data is mounted as a volume).
"""

import json
import os

SETTINGS_FILE = os.environ.get("SETTINGS_FILE", "/app/data/settings.json")
DEFAULT_DOWNLOAD_DIR = os.environ.get("BASE_DOWNLOAD_DIR", "/downloads")

DEFAULTS = {
    "csv_url": "",
    "download_dir": DEFAULT_DOWNLOAD_DIR,
}


def load():
    if not os.path.exists(SETTINGS_FILE):
        return dict(DEFAULTS)
    with open(SETTINGS_FILE, "r") as f:
        data = json.load(f)
    merged = {**DEFAULTS, **data}
    if not merged.get("download_dir"):
        merged["download_dir"] = DEFAULT_DOWNLOAD_DIR
    return merged


def save(new_settings):
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    current = load()
    current.update({k: v for k, v in new_settings.items() if k in DEFAULTS})
    if not current.get("download_dir"):
        current["download_dir"] = DEFAULT_DOWNLOAD_DIR
    with open(SETTINGS_FILE, "w") as f:
        json.dump(current, f, indent=2)
    return current

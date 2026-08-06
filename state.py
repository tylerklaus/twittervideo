"""
Since a published CSV is read-only, we can't write status back to the
sheet. Instead we track what's already been downloaded (or failed) in a
local JSON file, keyed by tweet URL. Persisted in /app/data so it survives
container rebuilds.
"""

import json
import os
from datetime import datetime

STATE_FILE = os.environ.get("STATE_FILE", "/app/data/download_state.json")


def load():
    if not os.path.exists(STATE_FILE):
        return {}
    with open(STATE_FILE, "r") as f:
        return json.load(f)


def save(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def mark_done(state, tweet_url, video_name, filepath):
    state[tweet_url] = {
        "video_name": video_name,
        "status": "done",
        "filepath": filepath,
        "error": "",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


def mark_failed(state, tweet_url, video_name, error):
    state[tweet_url] = {
        "video_name": video_name,
        "status": "failed",
        "filepath": "",
        "error": str(error)[:300],
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


def clear(state, tweet_url):
    """Remove an entry so it's picked up as pending again (used by 'Retry')."""
    state.pop(tweet_url, None)

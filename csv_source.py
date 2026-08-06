"""
Reads the queue from a Google Sheet published as CSV
(File > Share > Publish to web > CSV) — no auth required.

Expected header row (case-insensitive, exact names):
    Video Name, Tweet URL
"""

import csv
import io
import requests

COL_VIDEO_NAME = "video name"
COL_TWEET_URL = "tweet url"


def fetch_rows(csv_url):
    if not csv_url:
        raise RuntimeError("No CSV URL configured — set one on the settings page.")

    resp = requests.get(csv_url, timeout=20)
    resp.raise_for_status()

    reader = csv.DictReader(io.StringIO(resp.text))
    if reader.fieldnames is None:
        return []

    # normalize headers for lookup (case-insensitive)
    field_map = {name.strip().lower(): name for name in reader.fieldnames}
    if COL_VIDEO_NAME not in field_map or COL_TWEET_URL not in field_map:
        raise RuntimeError(
            f'CSV must have "Video Name" and "Tweet URL" columns. Found: {reader.fieldnames}'
        )

    rows = []
    for row in reader:
        tweet_url = (row.get(field_map[COL_TWEET_URL]) or "").strip()
        video_name = (row.get(field_map[COL_VIDEO_NAME]) or "").strip()
        if tweet_url:
            rows.append({"video_name": video_name, "tweet_url": tweet_url})
    return rows

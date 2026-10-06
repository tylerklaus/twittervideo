import os
import re
import shutil
import tempfile
import yt_dlp

COOKIES_FILE = os.environ.get("COOKIES_FILE", "/app/config/cookies.txt")


def sanitize_filename(name):
    name = name.strip()
    name = re.sub(r'[\\/:*?"<>|]', "", name)  # strip filesystem-unsafe chars
    name = re.sub(r"\s+", " ", name)
    return name or "untitled"


def resolve_download_dir(path):
    """Any absolute path is allowed -- it only resolves to something real
    if it's inside a volume actually mounted into this container."""
    target = path.strip() if path and path.strip() else "/downloads"
    os.makedirs(target, exist_ok=True)
    return target


def list_subfolders(path):
    """For the UI's convenience chips -- top-level subfolders of the given path."""
    if not path or not os.path.isdir(path):
        return []
    return sorted(
        d for d in os.listdir(path)
        if os.path.isdir(os.path.join(path, d)) and not d.startswith(".")
    )


def download_video(tweet_url, video_name, download_dir, overwrite=False):
    """
    Downloads a single tweet's video, named after video_name, into
    download_dir (a full absolute path). Raises on failure. Returns the filepath.
    """
    out_dir = resolve_download_dir(download_dir)
    safe_name = sanitize_filename(video_name)
    outtmpl = os.path.join(out_dir, f"{safe_name}.%(ext)s")

    ydl_opts = {
        "outtmpl": outtmpl,
        "format": "bv*+ba/b",
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "overwrites": overwrite,
    }

    # yt-dlp writes the cookie jar back to its cookiefile on close, which fails
    # when ./config is mounted read-only -- so hand it a throwaway copy.
    tmp_cookies = None
    if os.path.exists(COOKIES_FILE):
        fd, tmp_cookies = tempfile.mkstemp(suffix=".txt")
        os.close(fd)
        shutil.copyfile(COOKIES_FILE, tmp_cookies)
        ydl_opts["cookiefile"] = tmp_cookies

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(tweet_url, download=True)
            return ydl.prepare_filename(info)
    finally:
        if tmp_cookies and os.path.exists(tmp_cookies):
            os.remove(tmp_cookies)

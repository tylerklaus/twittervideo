import logging
import threading
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from flask import Flask, jsonify, render_template, request

import csv_source
import downloader
import settings as settings_store
import state as state_store

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("x-archiver")

app = Flask(__name__)

run_status = {
    "running": False,
    "last_started": None,
    "last_finished": None,
    "last_results": [],  # list of {video_name, tweet_url, status, error}
}
_lock = threading.Lock()


def run_job(force=False):
    with _lock:
        if run_status["running"]:
            log.info("Run requested but a run is already in progress -- skipping.")
            return
        run_status["running"] = True
        run_status["last_started"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cfg = settings_store.load()
    state = state_store.load()
    results = []

    try:
        rows = csv_source.fetch_rows(cfg["csv_url"])
        if force:
            pending = rows
            log.info(f"{len(rows)} row(s) in sheet, force re-downloading all.")
        else:
            pending = [r for r in rows if state.get(r["tweet_url"], {}).get("status") != "done"]
            log.info(f"{len(rows)} row(s) in sheet, {len(pending)} pending/failed.")

        for item in pending:
            tweet_url = item["tweet_url"]
            video_name = item["video_name"] or tweet_url
            # Skip anything that already failed -- surfaced in the UI for manual retry
            # rather than hammered every run.
            if not force and state.get(tweet_url, {}).get("status") == "failed":
                results.append({
                    "video_name": video_name, "tweet_url": tweet_url,
                    "status": "failed", "error": state[tweet_url]["error"] + " (skipped -- use Retry)",
                })
                continue
            try:
                filepath = downloader.download_video(tweet_url, video_name, cfg["download_dir"], overwrite=force)
                state_store.mark_done(state, tweet_url, video_name, filepath)
                results.append({"video_name": video_name, "tweet_url": tweet_url, "status": "done", "error": "", "filepath": filepath})
                log.info(f"Downloaded: {filepath}")
            except Exception as e:
                state_store.mark_failed(state, tweet_url, video_name, e)
                results.append({"video_name": video_name, "tweet_url": tweet_url, "status": "failed", "error": str(e)[:300]})
                log.error(f"Failed on {tweet_url}: {e}")

        state_store.save(state)

    except Exception as e:
        log.error(f"Run aborted -- could not read CSV: {e}")
        results.append({"video_name": "(CSV error)", "tweet_url": "", "status": "failed", "error": str(e)[:300]})

    finally:
        with _lock:
            run_status["running"] = False
            run_status["last_finished"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            run_status["last_results"] = results


@app.route("/")
def index():
    cfg = settings_store.load()
    return render_template(
        "index.html",
        state=run_status,
        settings=cfg,
        subfolders=downloader.list_subfolders(cfg["download_dir"]),
    )


@app.route("/run", methods=["POST"])
def force_run():
    if run_status["running"]:
        return jsonify({"ok": False, "message": "A run is already in progress."}), 409
    data = request.get_json(silent=True) or {}
    threading.Thread(target=run_job, kwargs={"force": bool(data.get("force"))}, daemon=True).start()
    return jsonify({"ok": True, "message": "Run started."})


@app.route("/status")
def status():
    return jsonify(run_status)


@app.route("/settings", methods=["POST"])
def update_settings():
    data = request.get_json(force=True)
    new_cfg = settings_store.save({
        "csv_url": (data.get("csv_url") or "").strip(),
        "download_dir": (data.get("download_dir") or "").strip(),
    })
    return jsonify({"ok": True, "settings": new_cfg})


@app.route("/retry", methods=["POST"])
def retry():
    """Clear one failed URL (or all failed URLs) so the next run picks it back up."""
    data = request.get_json(force=True)
    state = state_store.load()
    tweet_url = data.get("tweet_url")
    if tweet_url == "__all_failed__":
        for url, entry in list(state.items()):
            if entry.get("status") == "failed":
                state_store.clear(state, url)
    elif tweet_url:
        state_store.clear(state, tweet_url)
    state_store.save(state)
    return jsonify({"ok": True})


scheduler = BackgroundScheduler()
scheduler.add_job(run_job, CronTrigger(hour=2, minute=0), id="nightly_run")
scheduler.start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

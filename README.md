# X Video Archiver

Pulls tweet URLs from a published Google Sheet CSV and downloads the videos
with `yt-dlp`, naming each file from a column you fill in. Runs
automatically every night at 2:00 AM, with a "Run now" button on the web UI
for manual runs, and a settings panel to change the CSV source or download
folder without touching config files.

## 1. Set up the Google Sheet

Create a sheet with two columns (header row, exact names):

| Video Name | Tweet URL |
|---|---|

Then publish it as CSV: **File > Share > Publish to web**, select the
sheet/range, choose **CSV** as the format, and publish. Copy that URL --
you'll paste it into the app's settings page.

No service account, no API key, no sheet sharing needed -- the app just
does a plain HTTP GET.

## 2. How "already downloaded" is tracked

Since a published CSV is read-only, the app can't write a status column
back to the sheet. Instead it keeps its own local record
(`data/download_state.json`) of every tweet URL it's processed and whether
it succeeded or failed. Rows already marked "done" are skipped on future
runs; "failed" rows are skipped too (not retried automatically) until you
hit **Retry** on that row in the UI.

## 3. (Optional) Add cookies for X

X gates a lot of video access behind login. Export your X session cookies
to a Netscape-format `cookies.txt` (e.g. via a browser extension like
"Get cookies.txt") and place it at `config/cookies.txt`. Without this,
downloads from protected/rate-limited content may fail.

## 4. Deploy into a new Proxmox LXC

1. **Create the LXC** (Proxmox web UI): a Debian or Ubuntu template, a
   couple GB RAM is plenty. Under the container's **Options**, enable
   **Nesting** (required to run Docker inside an LXC) -- either at
   creation time (`Advanced` tab) or after, via `pct set <CTID> --features nesting=1`.
2. **Install Docker** inside the LXC:
   ```bash
   curl -fsSL https://get.docker.com | sh
   ```
3. **Get the code onto the LXC.** Push this project to a (private) GitHub
   repo of your own, then on the LXC:
   ```bash
   git clone https://github.com/<you>/x-video-archiver.git
   cd x-video-archiver
   ```
4. **Configure the compose file** -- edit the `/mnt/x-downloads:/downloads`
   line in `docker-compose.yml` to point at wherever you want videos to
   land (e.g. bind-mount your UNAS share into the LXC first via Proxmox,
   same pattern as your Pinchflat CT).
5. **Run it:**
   ```bash
   docker compose up -d --build
   ```
6. Visit `http://<lxc-ip>:5050`, open **Settings**, paste in your published
   CSV URL, and set a download folder if you don't want it landing in the
   mount's root.

## Where do videos download to?

The compose file mounts your UNAS share (or a parent folder covering
several shares) into the container. In the UI's Settings panel, the
**Download path** field takes a full absolute path -- e.g. `/downloads` or
`/downloads/x-clips` -- and creates it if it doesn't exist. Existing
subfolders of the current path are shown as clickable chips for
convenience. Anything you type only actually lands somewhere if it's
inside a path the compose file has mounted in -- there's no other
restriction on it, since this sits behind your Cloudflare Tunnel / NGINX /
Pocket ID stack rather than being open to the internet.

Point it straight at the UNAS mount so other machines on the network can
see the downloaded files immediately, same as your other shares.

## Notes

- Pressing "Run now" while a run is already in progress is a no-op (the
  button disables itself and re-enables when the run finishes).
- Filenames are sanitized (filesystem-unsafe characters stripped) but
  otherwise used exactly as typed in the sheet.
- Settings and download-state persist in `./data` on the host -- back that
  folder up if you care about not re-downloading everything after a rebuild.

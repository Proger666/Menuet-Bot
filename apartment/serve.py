#!/usr/bin/env python3
"""Serve the apartment planner for a Cloudflare quick tunnel and keep it up to date.

    python3 apartment/serve.py            # serve on :8765, pull the branch every 60 s
    python3 apartment/serve.py --tunnel   # same, and start `cloudflared tunnel --url ...`

Every response is sent with `Cache-Control: no-store`, so neither the tunnel nor Safari
keeps an old copy. /version.json reports the commit currently checked out; the page polls
it and shows a "new version" notice when it changes after a pull.
"""
import argparse
import http.server
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)


def git(*args):
    return subprocess.run(["git", "-C", REPO, *args], capture_output=True, text=True)


def current_version():
    head = git("rev-parse", "--short", "HEAD").stdout.strip() or "dev"
    stamp = git("log", "-1", "--format=%cI").stdout.strip()
    # uncommitted edits to the page count as a new version too
    try:
        mtime = int(os.path.getmtime(os.path.join(HERE, "index.html")))
    except OSError:
        mtime = 0
    return {"version": f"{head}-{mtime}", "commit": head, "date": stamp}


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=HERE, **kw)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("Pragma", "no-cache")
        super().end_headers()

    def do_GET(self):
        if self.path.split("?")[0] == "/version.json":
            body = json.dumps(current_version()).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path.split("?")[0].endswith((".py", ".sh")):
            self.send_error(404)
            return
        super().do_GET()

    def log_message(self, fmt, *args):
        pass


def pull_loop(every):
    branch = git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    while True:
        time.sleep(every)
        before = git("rev-parse", "HEAD").stdout.strip()
        res = git("pull", "--ff-only", "--quiet", "origin", branch)
        after = git("rev-parse", "HEAD").stdout.strip()
        if res.returncode != 0:
            print(f"[pull] failed: {res.stderr.strip()}", flush=True)
        elif before != after:
            print(f"[pull] updated {before[:7]} -> {after[:7]}; open pages will offer a reload", flush=True)


def start_tunnel(port):
    exe = shutil.which("cloudflared")
    if not exe:
        print("cloudflared is not installed: brew install cloudflared", file=sys.stderr)
        return
    proc = subprocess.Popen([exe, "tunnel", "--no-autoupdate", "--url", f"http://localhost:{port}"],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    def watch():
        for line in proc.stdout:
            m = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", line)
            if m:
                print(f"\n  Link: {m.group(0)}\n", flush=True)
    threading.Thread(target=watch, daemon=True).start()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--pull", type=int, default=60, help="seconds between git pulls, 0 to disable")
    ap.add_argument("--tunnel", action="store_true", help="also start a trycloudflare quick tunnel")
    args = ap.parse_args()
    if args.pull > 0:
        threading.Thread(target=pull_loop, args=(args.pull,), daemon=True).start()
    if args.tunnel:
        start_tunnel(args.port)
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Serving {HERE} on http://localhost:{args.port}  (version {current_version()['version']})", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
MotoMicX — Top Story Voting + Verified-Email Backend
====================================================
A tiny zero-dependency server (Python stdlib only) that:
  * tracks upvotes per story (one vote per browser, toggle on/off)
  * captures a reader's email and VERIFIES it with a 6-digit code
  * reports the live leaderboard back to verified readers

Run it from your terminal:
    python3 motomicx_server.py

Then open the HTML card sets in your browser. They talk to this server at
http://localhost:8765 automatically. Data is saved to motomicx_data.json
right next to this script, so votes survive restarts.

------------------------------------------------------------------
EMAIL DELIVERY
------------------------------------------------------------------
By default the verification code is printed to THIS TERMINAL window
(look for the big ===> VERIFICATION CODE box). That's perfect for a
local demo — you read the code off your own screen.

To send REAL emails instead, set these environment variables before
launching (standard SMTP, e.g. a Gmail App Password):

    export MOTOMICX_SMTP_HOST=smtp.gmail.com
    export MOTOMICX_SMTP_PORT=587
    export MOTOMICX_SMTP_USER=you@gmail.com
    export MOTOMICX_SMTP_PASS=your_app_password
    export MOTOMICX_SMTP_FROM="MotoMicX <you@gmail.com>"
    python3 motomicx_server.py

If those are set, codes are emailed; otherwise they print to terminal.
"""

import json
import os
import re
import sys
import smtplib
import ssl
import random
import threading
from email.message import EmailMessage
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(HERE, "motomicx_data.json")
PORT = int(os.environ.get("MOTOMICX_PORT", "8765"))
LOCK = threading.Lock()

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Canonical story IDs — must match the HTML card sets.
STORY_IDS = [
    "brother-war",
    "deegan-rising",
    "coenen-invasion",
    "kitchen-heist",
    "first-four-motos",
    "thunder-altitude",
]

DEFAULT_DATA = {
    "votes": {sid: [] for sid in STORY_IDS},  # storyId -> list of voterIds
    "emails": {},   # email -> {"verified": bool, "code": "123456"}
}


# ----------------------------------------------------------------------------
# Persistence
# ----------------------------------------------------------------------------
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
            data.setdefault("votes", {})
            data.setdefault("emails", {})
            for sid in STORY_IDS:
                data["votes"].setdefault(sid, [])
            return data
        except Exception as e:
            print("! Could not read data file, starting fresh:", e)
    return json.loads(json.dumps(DEFAULT_DATA))


def save_data(data):
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, DATA_FILE)


DATA = load_data()


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def tallies():
    return {sid: len(set(v)) for sid, v in DATA["votes"].items()}


def leaderboard():
    t = tallies()
    return sorted(
        [{"id": sid, "votes": n} for sid, n in t.items()],
        key=lambda r: r["votes"],
        reverse=True,
    )


def send_code(email, code):
    """Email the code if SMTP is configured, else print it to the terminal."""
    host = os.environ.get("MOTOMICX_SMTP_HOST")
    if host:
        try:
            msg = EmailMessage()
            msg["Subject"] = "Your MotoMicX verification code"
            msg["From"] = os.environ.get("MOTOMICX_SMTP_FROM", os.environ["MOTOMICX_SMTP_USER"])
            msg["To"] = email
            msg.set_content(
                f"Your MotoMicX code is {code}\n\n"
                "Enter it to lock in your Top Story vote and see the live leaderboard.\n"
                "If you didn't request this, ignore it."
            )
            port = int(os.environ.get("MOTOMICX_SMTP_PORT", "587"))
            ctx = ssl.create_default_context()
            with smtplib.SMTP(host, port) as s:
                s.starttls(context=ctx)
                s.login(os.environ["MOTOMICX_SMTP_USER"], os.environ["MOTOMICX_SMTP_PASS"])
                s.send_message(msg)
            print(f"   -> emailed code to {email}")
            return
        except Exception as e:
            print("! SMTP send failed, falling back to terminal print:", e)

    # Terminal fallback
    bar = "=" * 52
    print("\n" + bar)
    print(f"  ===>  VERIFICATION CODE for {email}")
    print(f"  ===>      {code}")
    print(bar + "\n")


# ----------------------------------------------------------------------------
# HTTP handler
# ----------------------------------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _json(self, obj, status=200):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self._cors()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def _read_json(self):
        try:
            n = int(self.headers.get("Content-Length", 0))
            return json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return {}

    def do_GET(self):
        if self.path.startswith("/api/state"):
            return self._json({"tallies": tallies(), "leaderboard": leaderboard()})
        if self.path.startswith("/api/leaderboard"):
            return self._json({"leaderboard": leaderboard()})
        if self.path == "/" or self.path.startswith("/health"):
            return self._json({"ok": True, "service": "MotoMicX voting", "stories": STORY_IDS})
        return self._json({"error": "not found"}, 404)

    def do_POST(self):
        body = self._read_json()

        if self.path.startswith("/api/vote"):
            sid = body.get("storyId")
            voter = (body.get("voterId") or "").strip()
            if sid not in DATA["votes"] or not voter:
                return self._json({"error": "bad vote"}, 400)
            with LOCK:
                voters = set(DATA["votes"][sid])
                if voter in voters:
                    voters.discard(voter)   # toggle off
                    voted = False
                else:
                    voters.add(voter)       # toggle on
                    voted = True
                DATA["votes"][sid] = list(voters)
                save_data(DATA)
            return self._json({"ok": True, "voted": voted,
                               "tallies": tallies(), "leaderboard": leaderboard()})

        if self.path.startswith("/api/signup"):
            email = (body.get("email") or "").strip().lower()
            if not EMAIL_RE.match(email):
                return self._json({"error": "Enter a valid email."}, 400)
            code = f"{random.randint(0, 999999):06d}"
            with LOCK:
                DATA["emails"][email] = {"verified": False, "code": code}
                save_data(DATA)
            send_code(email, code)
            return self._json({"ok": True,
                               "message": "Code sent. Check the server terminal (or your inbox if SMTP is on)."})

        if self.path.startswith("/api/verify"):
            email = (body.get("email") or "").strip().lower()
            code = (body.get("code") or "").strip()
            rec = DATA["emails"].get(email)
            if not rec:
                return self._json({"error": "No code requested for that email."}, 400)
            if code != rec["code"]:
                return self._json({"error": "Wrong code. Try again."}, 400)
            with LOCK:
                rec["verified"] = True
                save_data(DATA)
            return self._json({"ok": True, "verified": True, "leaderboard": leaderboard()})

        return self._json({"error": "not found"}, 404)

    def log_message(self, fmt, *args):
        # Quieter console — only show our own prints.
        return


def main():
    try:
        sys.stdout.reconfigure(line_buffering=True)  # flush each line so codes show instantly
    except Exception:
        pass
    httpd = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print("\n  MotoMicX voting server is LIVE")
    print(f"  Listening on http://localhost:{PORT}")
    print(f"  Data file:  {DATA_FILE}")
    smtp = "ON (emails will be sent)" if os.environ.get("MOTOMICX_SMTP_HOST") else "OFF (codes print here)"
    print(f"  SMTP email: {smtp}")
    print("  Press Ctrl+C to stop.\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n  Bye! Votes saved.")
        httpd.shutdown()


if __name__ == "__main__":
    main()

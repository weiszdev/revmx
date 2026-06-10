# MotoMicX — This Week in Moto (Pala → Hangtown → Thunder Valley)

A savage, comical roundup card set with **upvoting** and **verified-email** leaderboard reporting.

## Files
- `motomicx_cards_wide.html` — wide / desktop layout (2-column deck)
- `motomicx_cards_vertical.html` — vertical / mobile layout (single column)
- `motomicx_server.py` — local vote + email-verify backend (Python stdlib, zero installs)
- `build_cards.py` — regenerates both HTML files from one template (edit stories here)

## Quick start (the terminal does the voting)
1. Open a terminal in this folder and run:
   ```
   python3 motomicx_server.py
   ```
   You'll see `Listening on http://localhost:8765`.
2. Double-click either `.html` file to open it in your browser.
3. Click **▲ UPVOTE** on stories — votes are saved server-side (shared across browsers on this machine).
4. Bottom bar: enter an email → **Get my code**. The 6-digit code prints **in the server terminal window**.
5. Type the code → **Verify** → the live **Top Story leaderboard** opens.

The header shows a green **● live votes** pill when the server is running. If the
server is off, the cards still work in **demo mode** (votes/codes handled in-browser).

## Send real verification emails (optional)
Set SMTP env vars before launching (e.g. a Gmail App Password) and codes get emailed
instead of printed:
```
export MOTOMICX_SMTP_HOST=smtp.gmail.com
export MOTOMICX_SMTP_PORT=587
export MOTOMICX_SMTP_USER=you@gmail.com
export MOTOMICX_SMTP_PASS=your_app_password
export MOTOMICX_SMTP_FROM="MotoMicX <you@gmail.com>"
python3 motomicx_server.py
```

## Data
Votes and emails persist in `motomicx_data.json` (created on first run). Delete it to reset.

## The 6 stories (each with a comical song hook)
1. **Brother War** — Hunter 1-1 at Pala vs Jett's 1-1 Hangtown sweep (Hunter 94, Jett 88)
2. **Deegan Rising** — 450 rookie, 5th at Pala, first 450 podium at Hangtown
3. **The Coenen Invasion** — KTM's Belgian twins (#104 / #109) wildcard Thunder Valley, Rd 3
4. **Kitchen Heist** — Hammaker wins Pala opener, Kitchen 2-2's his way to the 250 points lead (+13)
5. **First Four Motos** — the outlier data: Prado vanishes, Cooper's 3-6, Ferrandis season-best
6. **Thunder Valley Altitude** — Rd 3 at ~5,800 ft, June 13, everyone gasping

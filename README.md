# Glenride System Map — homelab edition

Interactive system map of the Glenride operating structure. Every card is
editable and every edit is saved to SQLite, so the map grows with the work.

- **Org Chart** — the leadership chain: President → Lead Director → Department
  Directors → Managers → Teams.
- **Departments** — the 7 departments, each with mandate, cost center, and an
  explicit bridge: *today (what exists now)* → *becoming (the vision)*.
- **Budget Cycle** — the 5 annual stages: Plan → Raise & deploy → Allocate →
  Execute → Reallocate.
- **Money & Governance** — how money moves, and the walls that hold it
  (Wyoming LLC + trust).

## Run it

```bash
docker compose up -d --build
```

Then open `http://<your-imac-ip>:8090` in a browser on your network.

Card edits live in the SQLite file on the `glenride-map-data` Docker volume —
they survive container restarts, rebuilds, and reboots.

See `docs/deploy-imac.md` for the full click-by-click iMac setup.

## Project layout

```
app.py                  Flask app + JSON API + seed data
templates/index.html    Page shell
static/                 style.css, app.js, glenride-logo.png (his artwork, unaltered)
docs/deploy-imac.md     Click-by-click iMac deploy guide
data/                   Local dev database location (the container uses /data)
```

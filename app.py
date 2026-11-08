"""Glenride System Map — self-hosted interactive org map.

Single-file Flask app. SQLite storage, tiny JSON API, vanilla frontend.
Edits persist in the SQLite file, which lives on a Docker named volume
so card changes survive container restarts.
"""
import json
import os
import sqlite3
from datetime import datetime, timezone

from flask import Flask, jsonify, request, render_template

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.environ.get("DATABASE_PATH", os.path.join(BASE_DIR, "data", "system-map.db"))
MAX_FIELD_LEN = 20000

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Seed data — taken from the operating-structure concept document.
# Seeded once, on first run, into an empty database. After that the DB rules.
# ---------------------------------------------------------------------------

SEED_CARDS = [
    # -- Leadership chain ----------------------------------------------------
    {"id": "president", "section": "leadership", "ord": 1, "title": "President",
     "fields": {
         "Holder": "D'Vaughn House — Founder & Interim President",
         "Responsibilities": (
             "Raises the think tank's budget and deploys it.\n"
             "Sets the research direction and the venture thesis.\n"
             "The public voice — talks, writing, rooms.\n"
             "Starts new ventures inside the think tank and hands them to operators.\n"
             "Final say on what carries the Glenride name.\n"
             "Holds the standard: Human Primacy in everything shipped, "
             "Cognitive Stewardship in everything published."
         ),
         "Succession": (
             "Interim by design — he's a venture starter, not a day-to-day operator. "
             "When revenue supports it, Glenride hires a permanent President "
             "(title negotiable: Executive Director, CEO — function isn't). "
             "He moves to Founder & Chair: vision, ventures, research direction."
         ),
     }},
    {"id": "lead-director", "section": "leadership", "ord": 2, "title": "Lead Director",
     "fields": {
         "Responsibilities": (
             "Takes the deployed budget from the President and allocates it "
             "across the departments — equally, or weighted by criteria.\n"
             "Allocation criteria: strategic priority, prior-year results, "
             "readiness to execute."
         ),
         "Notes": "First among the directors for budget purposes; not a layer of approval theater — a working allocator.",
     }},
    {"id": "directors", "section": "leadership", "ord": 3, "title": "Department Directors",
     "fields": {
         "Responsibilities": (
             "One director per department.\n"
             "Own their department's allocation and cost center.\n"
             "Run their studies, programs, and product lines.\n"
             "Report spend and results upward."
         ),
         "Notes": "",
     }},
    {"id": "managers", "section": "leadership", "ord": 4, "title": "Managers",
     "fields": {
         "Responsibilities": (
             "Sit under each department director.\n"
             "Manage the teams doing the actual work.\n"
             "Track execution against the annual plan."
         ),
         "Notes": "",
     }},
    {"id": "teams", "section": "leadership", "ord": 5, "title": "Teams",
     "fields": {
         "Who": "Researchers, engineers, writers, operators — the hands.",
         "Notes": "",
     }},
    # -- Departments ----------------------------------------------------------
    {"id": "dept-research", "section": "departments", "ord": 1, "title": "Research",
     "fields": {
         "Tagline": "The think tank's core. Ask the hard questions, publish the answers.",
         "Mandate": (
             "Supply-chain vulnerability research, pharmaceutical data evaluation, "
             "enterprise systems analysis. The drug-shortage digest lives here. "
             "The council convenes here."
         ),
         "Cost center": "Researcher time, data feeds and subscriptions, compute for analysis, peer review and editing.",
         "Done looks like": "Published findings with receipts, cited and standing up to scrutiny.",
         "Today — what exists now": "Glenride's supply-chain work, drug-shortage digest, council charter.",
         "Becoming — the vision": "A cited, peer-respected research arm whose findings move markets and policy.",
         "Notes": "",
     }},
    {"id": "dept-policy", "section": "departments", "ord": 2, "title": "Policy & Government Affairs",
     "fields": {
         "Tagline": "The reason Glenride is a think tank. Turn breakthroughs into policy.",
         "Mandate": "When research produces a breakthrough, carry it to the people who write the rules — lobbying, testimony, regulatory comments, legislative drafting support. Combat systems that seek to harm you by moving the alternative into law.",
         "Cost center": "Lobbyist registration and compliance, policy counsel, travel to capitals, policy staff.",
         "Today — what exists now": "To be built — the lobbying arm activates with the first breakthrough.",
         "Becoming — the vision": "Policy moved — bills introduced, rules changed, testimony on the record. A breakthrough that stays a paper is a failure of this department.",
         "Notes": "Added 2026-10-09: lobbying the government when breakthroughs occur is why Glenride was created."
     }},
    {"id": "dept-lab", "section": "departments", "ord": 3, "title": "Applied AI Lab",
     "fields": {
         "Tagline": "Turn answers into software.",
         "Mandate": (
             "The token systems ($SPIN, $WAVY infrastructure), the Vapor Wire bot, "
             "the job scraper, the content factory, OSINT tooling. Everything that "
             "runs — on Cloudflare or the homelab — is built and maintained here."
         ),
         "Cost center": "Engineering time, infrastructure (Cloudflare, hardware upkeep), third-party security audits, API and data costs.",
         "Done looks like": "Shipped software with users, documented and auditable.",
         "Today — what exists now": "Token systems, Vapor Wire bot, job scraper, content factory scaffold.",
         "Becoming — the vision": "A product lab whose tools are licensed and revenue-generating.",
         "Notes": "",
     }},
    {"id": "dept-pubs", "section": "departments", "ord": 4, "title": "Publications & Story",
     "fields": {
         "Tagline": "The think tank's voice in long form.",
         "Mandate": (
             "Essays (cornerstone, Borrowed Spell), the STARBORN screenplay, "
             "the newsletter, the personal brand campaign. This department makes "
             "Glenride legible to the world."
         ),
         "Cost center": "Writing time, editing, design and layout, publishing and distribution.",
         "Done looks like": "Published work with his name on it, selling or licensed.",
         "Today — what exists now": "Cornerstone essay, Borrowed Spell, STARBORN, 12-piece campaign spec.",
         "Becoming — the vision": "A publishing arm with books and essays that sell on their own.",
         "Notes": "",
     }},
    {"id": "dept-commerce", "section": "departments", "ord": 5, "title": "Commerce",
     "fields": {
         "Tagline": "The cash register.",
         "Mandate": "Reynard's, the WAVY Ship's Store, the Glenride app store. Every product regular people can buy or license.",
         "Cost center": "Cost of goods, fulfillment and shipping, payment processing, samples and quality control.",
         "Done looks like": "Revenue. This department funds the others.",
         "Today — what exists now": "Reynard's, Ship's Store, Glenride app store.",
         "Becoming — the vision": "The revenue engine that makes the think tank independent — money from the work, not from sponsors.",
         "Notes": "",
     }},
    {"id": "dept-treasury", "section": "departments", "ord": 6, "title": "Treasury",
     "fields": {
         "Tagline": "The think tank's financial backbone.",
         "Mandate": "The treasury Safe, token vesting schedules, fee streams, reserves. Boring, exact, and untouchable without process.",
         "Cost center": "Transaction costs, audits, counsel for classification and compliance.",
         "Done looks like": "Every movement logged, every allocation matching the published tokenomics.",
         "Today — what exists now": "The Safe, frozen tokenomics, fairness audit.",
         "Becoming — the vision": "The think tank's endowment logic — fee streams accrue here, departments draw budgets from it.",
         "Notes": "",
     }},
    {"id": "dept-community", "section": "departments", "ord": 7, "title": "Community & Channels",
     "fields": {
         "Tagline": "The people, gathered.",
         "Mandate": (
             "The Vapor Wire channels, the Glenride Council on AI & Supply-Chain "
             "Resilience, public programs. The warm audience — the book of "
             "supporters every future build draws on."
         ),
         "Cost center": "Moderation tooling, event costs, community programs.",
         "Done looks like": "Active rooms, a council that meets, members who bring others.",
         "Today — what exists now": "Vapor Wire channels, council concept.",
         "Becoming — the vision": "A convening power — the rooms where the industry's serious people gather.",
         "Notes": "",
     }},
    {"id": "dept-ops", "section": "departments", "ord": 8, "title": "Operations",
     "fields": {
         "Tagline": "The structure that holds the structure.",
         "Mandate": (
             "Finance and books, legal and compliance, the Wyoming LLC and trust "
             "paperwork, HR when there is an H to R. Nothing glamorous; "
             "everything load-bearing."
         ),
         "Cost center": "Registered agent, accounting, counsel, insurance, filings.",
         "Done looks like": "Clean books, current filings, no surprises.",
         "Today — what exists now": "The business-structure system map, the operating concept.",
         "Becoming — the vision": "Invisible excellence — the think tank just works.",
         "Notes": "",
     }},
    # -- Budget cycle ----------------------------------------------------------
    {"id": "budget-plan", "section": "budget", "ord": 1, "title": "1 · Plan (year prior)",
     "fields": {
         "What happens": (
             "Departments propose the next year's trials and research studies — "
             "including the data licenses, compute, and staffing each study needs."
         ),
         "Notes": "",
     }},
    {"id": "budget-raise", "section": "budget", "ord": 2, "title": "2 · Raise & deploy",
     "fields": {
         "What happens": "The President raises the think tank's budget and deploys it to the Lead Director.",
         "Notes": "",
     }},
    {"id": "budget-allocate", "section": "budget", "ord": 3, "title": "3 · Allocate",
     "fields": {
         "What happens": (
             "The Lead Director divides the budget across the departments — "
             "equally, or weighted by criteria: strategic priority, prior-year "
             "results, readiness to execute."
         ),
         "Notes": "",
     }},
    {"id": "budget-execute", "section": "budget", "ord": 4, "title": "4 · Execute",
     "fields": {
         "What happens": (
             "Directors and managers run the planned studies. Spend is tracked "
             "against the plan as each study completes."
         ),
         "Notes": "",
     }},
    {"id": "budget-reallocate", "section": "budget", "ord": 5, "title": "5 · Reallocate",
     "fields": {
         "What happens": (
             "Leftover budget doesn't sit idle and doesn't vanish — it's "
             "reallocated to another project. Every dollar stays in motion "
             "until the work is done."
         ),
         "Notes": "",
     }},
    # -- Money & governance ----------------------------------------------------
    {"id": "money-flow", "section": "structure", "ord": 1, "title": "How money moves",
     "fields": {
         "The model": (
             "Commerce and licensing are the revenue centers. Publications sell. "
             "The lab licenses. The think tank's research is funded by the studio's "
             "products — not by grants that come with strings, not by sponsors "
             "who want a say. Independent means the money comes from the work.\n\n"
             "Treasury functions as the think tank's endowment logic: fee streams "
             "and reserves accrue there, and departments draw budgets from it. "
             "Each department head owns their cost center — they know their "
             "number, they stay inside it, they report on it. No department "
             "spends the think tank's future."
         ),
         "Notes": "",
     }},
    {"id": "governance", "section": "structure", "ord": 2, "title": "Governance",
     "fields": {
         "The walls": (
             "The Wyoming LLC owns all of it — every department, every product, "
             "every stream. The revocable living trust holds the LLC. He holds "
             "the trust. Clean lines: the think tank is an asset of the company, "
             "the company answers to the trust's instructions, and the "
             "instructions outlive all of us.\n\n"
             "Departments don't change that. They organize the work inside the "
             "walls; the walls themselves are already drawn."
         ),
         "Notes": "",
     }},
]


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

def get_db():
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute(
        "CREATE TABLE IF NOT EXISTS cards ("
        "id TEXT PRIMARY KEY, "
        "section TEXT NOT NULL, "
        "ord INTEGER NOT NULL, "
        "title TEXT NOT NULL, "
        "fields TEXT NOT NULL, "
        "updated_at TEXT NOT NULL)"
    )
    count = conn.execute("SELECT COUNT(*) AS c FROM cards").fetchone()["c"]
    if count == 0:
        now = datetime.now(timezone.utc).isoformat()
        for card in SEED_CARDS:
            conn.execute(
                "INSERT INTO cards (id, section, ord, title, fields, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (card["id"], card["section"], card["ord"], card["title"],
                 json.dumps(card["fields"]), now),
            )
        conn.commit()
    conn.close()


def row_to_card(row):
    return {
        "id": row["id"],
        "section": row["section"],
        "ord": row["ord"],
        "title": row["title"],
        "fields": json.loads(row["fields"]),
        "updated_at": row["updated_at"],
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/health")
def health():
    return jsonify({"ok": True})


@app.route("/api/cards", methods=["GET"])
def list_cards():
    conn = get_db()
    rows = conn.execute("SELECT * FROM cards ORDER BY section, ord").fetchall()
    conn.close()
    return jsonify({"cards": [row_to_card(r) for r in rows]})


@app.route("/api/cards/<card_id>", methods=["PUT"])
def update_card(card_id):
    data = request.get_json(silent=True) or {}
    fields = data.get("fields")
    if not isinstance(fields, dict):
        return jsonify({"error": "fields must be an object"}), 400
    for key, value in fields.items():
        if not isinstance(key, str) or not isinstance(value, str):
            return jsonify({"error": "field names and values must be strings"}), 400
        if len(value) > MAX_FIELD_LEN:
            return jsonify({"error": "field value too long"}), 400

    conn = get_db()
    row = conn.execute("SELECT * FROM cards WHERE id = ?", (card_id,)).fetchone()
    if row is None:
        conn.close()
        return jsonify({"error": "card not found"}), 404

    merged = json.loads(row["fields"])
    merged.update(fields)
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "UPDATE cards SET fields = ?, updated_at = ? WHERE id = ?",
        (json.dumps(merged), now, card_id),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM cards WHERE id = ?", (card_id,)).fetchone()
    conn.close()
    return jsonify({"card": row_to_card(row)})


init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    app.run(host="0.0.0.0", port=port)

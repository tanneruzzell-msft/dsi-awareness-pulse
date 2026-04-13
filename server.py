"""
DSI Awareness Pulse — Dashboard Server
Serves the interactive dashboard and provides REST API for curation.

Usage:
    python server.py              # Start on http://localhost:5100
    python server.py --port 8080  # Custom port
"""

import sqlite3
import json
import hashlib
import argparse
from datetime import datetime
from pathlib import Path
from flask import Flask, jsonify, request, send_file, send_from_directory

SCRIPT_DIR = Path(__file__).parent
DB_PATH = SCRIPT_DIR / "dsi_awareness.db"

app = Flask(__name__, static_folder=str(SCRIPT_DIR))


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # Ensure columns exist
    for tbl in ["articles", "reddit_mentions"]:
        for col, default in [("flagged", "0"), ("flag_reason", "NULL"), ("manually_added", "0")]:
            try:
                conn.execute(f"ALTER TABLE {tbl} ADD COLUMN {col} DEFAULT {default}")
            except Exception:
                pass
    try:
        conn.execute("ALTER TABLE articles ADD COLUMN published_date TEXT")
    except Exception:
        pass
    conn.commit()
    return conn


def make_id(text):
    return hashlib.md5(text.encode()).hexdigest()[:12]


# --- Pages ---

@app.route("/")
def index():
    return send_file(SCRIPT_DIR / "app.html")


# --- API ---

@app.route("/api/data")
def api_data():
    conn = get_db()
    c = conn.cursor()

    snapshots = [dict(r) for r in c.execute("SELECT * FROM pulse_snapshots ORDER BY snapshot_date ASC").fetchall()]
    articles = [dict(r) for r in c.execute("SELECT * FROM articles ORDER BY COALESCE(published_date, discovered) DESC").fetchall()]
    reddit = [dict(r) for r in c.execute("SELECT * FROM reddit_mentions ORDER BY created_utc DESC").fetchall()]
    trends = [dict(r) for r in c.execute("SELECT keyword, date, interest FROM google_trends ORDER BY date ASC").fetchall()]
    logs = [dict(r) for r in c.execute("SELECT * FROM collection_log ORDER BY run_date DESC LIMIT 50").fetchall()]

    latest = snapshots[-1] if snapshots else {}

    data = {
        "generated_at": datetime.now().isoformat(),
        "latest_snapshot": latest,
        "snapshots": snapshots,
        "articles": articles,
        "reddit_mentions": reddit,
        "google_trends": trends,
        "collection_log": logs,
        "summary": {
            "total_articles": len([a for a in articles if not a.get("flagged")]),
            "third_party_articles": len([a for a in articles if a.get("type") == "third_party" and not a.get("flagged")]),
            "microsoft_articles": len([a for a in articles if a.get("type") == "microsoft" and not a.get("flagged")]),
            "reddit_total": len([r for r in reddit if not r.get("flagged")]),
            "reddit_flagged": len([r for r in reddit if r.get("flagged")]),
            "reddit_unique_subs": len(set(r["subreddit"] for r in reddit if not r.get("flagged"))) if reddit else 0,
            "youtube_total": 0,
            "trend_keywords_tracked": len(set(t["keyword"] for t in trends)) if trends else 0,
            "snapshots_count": len(snapshots),
            "total_flagged": len([a for a in articles if a.get("flagged")]) + len([r for r in reddit if r.get("flagged")])
        }
    }
    conn.close()
    return jsonify(data)


@app.route("/api/flag", methods=["POST"])
def api_flag():
    body = request.json
    entry_id = body.get("id")
    reason = body.get("reason", "false positive")

    conn = get_db()
    cur = conn.execute("UPDATE articles SET flagged = 1, flag_reason = ? WHERE id = ?", (reason, entry_id))
    if cur.rowcount == 0:
        cur = conn.execute("UPDATE reddit_mentions SET flagged = 1, flag_reason = ? WHERE id = ?", (reason, entry_id))

    conn.commit()
    conn.close()
    return jsonify({"ok": cur.rowcount > 0, "id": entry_id})


@app.route("/api/unflag", methods=["POST"])
def api_unflag():
    body = request.json
    entry_id = body.get("id")

    conn = get_db()
    conn.execute("UPDATE articles SET flagged = 0, flag_reason = NULL WHERE id = ?", (entry_id,))
    conn.execute("UPDATE reddit_mentions SET flagged = 0, flag_reason = NULL WHERE id = ?", (entry_id,))
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "id": entry_id})


@app.route("/api/add", methods=["POST"])
def api_add():
    body = request.json
    url = body.get("url", "").strip()
    if not url:
        return jsonify({"ok": False, "error": "URL is required"}), 400

    title = body.get("title", url)
    source = body.get("source", "unknown")
    sentiment = body.get("sentiment", "unknown")
    published = body.get("published_date")
    art_type = body.get("type", "microsoft" if "microsoft.com" in url else "third_party")

    aid = make_id(url)
    conn = get_db()

    existing = conn.execute("SELECT id FROM articles WHERE id = ?", (aid,)).fetchone()
    if not existing:
        existing = conn.execute("SELECT id FROM reddit_mentions WHERE id = ?", (aid,)).fetchone()
    if existing:
        conn.close()
        return jsonify({"ok": False, "error": "Already tracked"})

    is_reddit = "reddit.com" in url
    if is_reddit:
        conn.execute(
            "INSERT INTO reddit_mentions (id, subreddit, title, url, author, score, num_comments, created_utc, discovered, search_term, manually_added) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (aid, source, title, url, "", 0, 0, 0, datetime.now().strftime("%Y-%m-%d"), "manual", 1)
        )
    else:
        conn.execute(
            "INSERT INTO articles (id, url, title, source, type, sentiment, discovered, last_checked, published_date, manually_added) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (aid, url, title, source, art_type, sentiment,
             datetime.now().strftime("%Y-%m-%d"), datetime.now().strftime("%Y-%m-%d"), published, 1)
        )

    conn.commit()
    conn.close()
    return jsonify({"ok": True, "id": aid, "type": "reddit" if is_reddit else "article"})


@app.route("/api/refresh", methods=["POST"])
def api_refresh():
    """Trigger a data collection run."""
    import subprocess
    python = str(Path(__file__).parent / "collector.py")
    result = subprocess.run(
        ["python", python],
        capture_output=True, text=True, cwd=str(SCRIPT_DIR), timeout=120
    )
    return jsonify({"ok": result.returncode == 0, "output": result.stdout, "errors": result.stderr})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5100)
    args = parser.parse_args()

    print(f"\n  DSI Awareness Pulse Dashboard")
    print(f"  http://localhost:{args.port}")
    print(f"  Press Ctrl+C to stop\n")

    app.run(host="127.0.0.1", port=args.port, debug=False)

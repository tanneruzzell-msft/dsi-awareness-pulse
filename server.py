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
import re
import argparse
from datetime import datetime
from pathlib import Path
from flask import Flask, jsonify, request, send_file, send_from_directory

SCRIPT_DIR = Path(__file__).parent
DB_PATH = SCRIPT_DIR / "dsi_awareness.db"
CONFIG_PATH = SCRIPT_DIR / "config.json"
LEARNED_PATH = SCRIPT_DIR / "learned.json"

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


def load_json(path):
    with open(path, "r") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=4)


def learn_from_flag(entry_id, reason, entry_data):
    """Update learned.json when a false positive is flagged."""
    learned = load_json(LEARNED_PATH)
    config = load_json(CONFIG_PATH)

    title = entry_data.get("title", "")
    subreddit = entry_data.get("subreddit", "")

    # Extract distinctive words from the title to build exclusion patterns
    stop_words = {"the", "a", "an", "in", "on", "at", "to", "for", "of", "and", "or", "is", "it",
                  "this", "that", "with", "from", "by", "are", "was", "were", "be", "has", "have",
                  "had", "do", "does", "did", "will", "would", "could", "should", "may", "might",
                  "not", "no", "if", "but", "so", "as", "what", "how", "who", "which", "when",
                  "where", "why", "can", "all", "each", "every", "my", "your", "our", "their",
                  "its", "i", "you", "he", "she", "we", "they", "me", "him", "her", "us", "them",
                  "new", "about", "just", "get", "got", "here", "there", "been", "being", "up",
                  "out", "any", "some", "more", "most", "other", "than", "then", "also", "after",
                  "before", "between", "through", "into", "over", "under", "does", "anyone"}

    # Only learn from titles that are clearly not about DSI
    title_words = set(re.findall(r'\b[a-zA-Z]{3,}\b', title.lower())) - stop_words
    # Remove words that ARE related to DSI to avoid excluding good results
    dsi_words = {"purview", "dsi", "security", "investigation", "investigations", "data",
                 "microsoft", "compliance", "insider", "threat", "breach", "ediscovery"}
    distinctive_words = title_words - dsi_words

    # If the title has very distinctive non-DSI words, add them as exclusion patterns
    if distinctive_words and len(distinctive_words) <= 6:
        # Use multi-word patterns to avoid over-filtering
        pattern_candidates = [w for w in distinctive_words if len(w) >= 4]
        for word in pattern_candidates[:3]:
            if word not in learned.get("exclude_title_patterns", []):
                learned.setdefault("exclude_title_patterns", []).append(word)

    # Track subreddit flag rates
    if subreddit:
        conn = get_db()
        total_from_sub = conn.execute(
            "SELECT COUNT(*) FROM reddit_mentions WHERE subreddit = ?", (subreddit,)
        ).fetchone()[0]
        flagged_from_sub = conn.execute(
            "SELECT COUNT(*) FROM reddit_mentions WHERE subreddit = ? AND flagged = 1", (subreddit,)
        ).fetchone()[0]
        conn.close()

        flag_rate = flagged_from_sub / max(total_from_sub, 1)
        # If >75% of posts from this sub are flagged, exclude it
        if flag_rate > 0.75 and total_from_sub >= 3:
            if subreddit not in learned.get("exclude_subreddits", []):
                learned.setdefault("exclude_subreddits", []).append(subreddit)
            # Also remove from config if it's there
            if subreddit in config.get("reddit_subreddits", []):
                config["reddit_subreddits"].remove(subreddit)
                save_json(CONFIG_PATH, config)

    save_json(LEARNED_PATH, learned)


def learn_from_add(url, title, source, subreddit=None):
    """Update config when a missed entry is added."""
    learned = load_json(LEARNED_PATH)
    config = load_json(CONFIG_PATH)
    changed = False

    # If it's a Reddit post from a sub we don't monitor, add it
    if subreddit and subreddit not in config.get("reddit_subreddits", []):
        if subreddit not in learned.get("exclude_subreddits", []):
            config.setdefault("reddit_subreddits", []).append(subreddit)
            learned.setdefault("include_subreddits", []).append(subreddit)
            changed = True

    # If it's an article from a source we haven't seen, track it
    if source and source != "unknown":
        known_sources = [a.get("source", "") for a in config.get("known_articles", [])]
        if source not in known_sources:
            if source not in learned.get("include_sources", []):
                learned.setdefault("include_sources", []).append(source)

    # Add to known_articles in config so it persists across DB resets
    existing_urls = [a["url"] for a in config.get("known_articles", [])]
    if url not in existing_urls:
        config.setdefault("known_articles", []).append({
            "url": url,
            "title": title or url,
            "source": source or "unknown",
            "type": "microsoft" if "microsoft.com" in url else "third_party",
            "sentiment": "unknown",
            "discovered": datetime.now().strftime("%Y-%m-%d")
        })
        changed = True

    if changed:
        save_json(CONFIG_PATH, config)
    save_json(LEARNED_PATH, learned)


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
    linkedin = []
    try:
        linkedin = [dict(r) for r in c.execute("SELECT * FROM linkedin_posts ORDER BY COALESCE(published_date, discovered) DESC").fetchall()]
    except Exception:
        pass
    trends = [dict(r) for r in c.execute("SELECT keyword, date, interest FROM google_trends ORDER BY date ASC").fetchall()]
    logs = [dict(r) for r in c.execute("SELECT * FROM collection_log ORDER BY run_date DESC LIMIT 50").fetchall()]

    latest = snapshots[-1] if snapshots else {}

    data = {
        "generated_at": datetime.now().isoformat(),
        "latest_snapshot": latest,
        "snapshots": snapshots,
        "articles": articles,
        "reddit_mentions": reddit,
        "linkedin_posts": linkedin,
        "google_trends": trends,
        "collection_log": logs,
        "summary": {
            "total_articles": len([a for a in articles if not a.get("flagged")]),
            "third_party_articles": len([a for a in articles if a.get("type") == "third_party" and not a.get("flagged")]),
            "microsoft_articles": len([a for a in articles if a.get("type") == "microsoft" and not a.get("flagged")]),
            "reddit_total": len([r for r in reddit if not r.get("flagged")]),
            "reddit_flagged": len([r for r in reddit if r.get("flagged")]),
            "reddit_unique_subs": len(set(r["subreddit"] for r in reddit if not r.get("flagged"))) if reddit else 0,
            "linkedin_total": len([p for p in linkedin if not p.get("flagged")]),
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

    # Get entry data before flagging (for learning)
    entry = conn.execute("SELECT * FROM articles WHERE id = ?", (entry_id,)).fetchone()
    table = "articles"
    if not entry:
        entry = conn.execute("SELECT * FROM reddit_mentions WHERE id = ?", (entry_id,)).fetchone()
        table = "reddit_mentions"
    if not entry:
        try:
            entry = conn.execute("SELECT * FROM linkedin_posts WHERE id = ?", (entry_id,)).fetchone()
            table = "linkedin_posts"
        except Exception:
            pass

    cur = conn.execute(f"UPDATE {table} SET flagged = 1, flag_reason = ? WHERE id = ?", (reason, entry_id))
    conn.commit()

    # Learn from this flag
    if entry:
        learn_from_flag(entry_id, reason, dict(entry))

    conn.close()
    return jsonify({"ok": cur.rowcount > 0, "id": entry_id, "learned": True})


@app.route("/api/unflag", methods=["POST"])
def api_unflag():
    body = request.json
    entry_id = body.get("id")

    conn = get_db()
    conn.execute("UPDATE articles SET flagged = 0, flag_reason = NULL WHERE id = ?", (entry_id,))
    conn.execute("UPDATE reddit_mentions SET flagged = 0, flag_reason = NULL WHERE id = ?", (entry_id,))
    try:
        conn.execute("UPDATE linkedin_posts SET flagged = 0, flag_reason = NULL WHERE id = ?", (entry_id,))
    except Exception:
        pass
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
    is_linkedin = "linkedin.com" in url
    subreddit = None
    if is_reddit:
        # Extract subreddit from URL
        import re as re_mod
        m = re_mod.search(r'/r/([^/]+)', url)
        subreddit = m.group(1) if m else source
        conn.execute(
            "INSERT INTO reddit_mentions (id, subreddit, title, url, author, score, num_comments, created_utc, discovered, search_term, manually_added) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (aid, subreddit or source, title, url, "", 0, 0, 0, datetime.now().strftime("%Y-%m-%d"), "manual", 1)
        )
    elif is_linkedin:
        # Ensure table exists
        conn.execute("""CREATE TABLE IF NOT EXISTS linkedin_posts (
            id TEXT PRIMARY KEY, url TEXT UNIQUE, title TEXT, author TEXT, author_title TEXT,
            post_type TEXT, discovered DATE, published_date TEXT,
            manually_added INTEGER DEFAULT 0, flagged INTEGER DEFAULT 0, flag_reason TEXT)""")
        conn.execute(
            "INSERT INTO linkedin_posts (id, url, title, author, post_type, discovered, published_date, manually_added) VALUES (?,?,?,?,?,?,?,?)",
            (aid, url, title, source, "post", datetime.now().strftime("%Y-%m-%d"), published, 1)
        )
    else:
        conn.execute(
            "INSERT INTO articles (id, url, title, source, type, sentiment, discovered, last_checked, published_date, manually_added) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (aid, url, title, source, art_type, sentiment,
             datetime.now().strftime("%Y-%m-%d"), datetime.now().strftime("%Y-%m-%d"), published, 1)
        )

    conn.commit()
    conn.close()

    # Learn from this addition
    learn_from_add(url, title, source, subreddit)

    return jsonify({"ok": True, "id": aid, "type": "reddit" if is_reddit else "article", "learned": True})


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


@app.route("/api/learned")
def api_learned():
    """Return the current learned patterns."""
    learned = load_json(LEARNED_PATH)
    return jsonify(learned)


@app.route("/api/benchmark")
def api_benchmark():
    """Return competitive benchmark data."""
    bench_path = SCRIPT_DIR / "benchmark.json"
    if bench_path.exists():
        return jsonify(load_json(bench_path))
    return jsonify({"competitors": {}})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5100)
    parser.add_argument("--share", action="store_true", help="Bind to all interfaces so teammates can access")
    args = parser.parse_args()

    host = "0.0.0.0" if args.share else "127.0.0.1"

    import socket
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)

    print(f"\n  DSI Awareness Pulse Dashboard")
    print(f"  Local:   http://localhost:{args.port}")
    if args.share:
        print(f"  Network: http://{local_ip}:{args.port}")
        print(f"  Share this URL with your team ^")
    print(f"  Press Ctrl+C to stop\n")

    app.run(host=host, port=args.port, debug=False)

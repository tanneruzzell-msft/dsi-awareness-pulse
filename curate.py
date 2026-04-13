"""
DSI Awareness Pulse — Manual Entry & Curation Tool

Usage:
    python curate.py add --url URL [--title TITLE] [--source SOURCE] [--type TYPE] [--sentiment SENTIMENT] [--published DATE]
    python curate.py flag --id ID [--reason REASON]
    python curate.py unflag --id ID
    python curate.py list-flagged
    python curate.py learn

Examples:
    python curate.py add --url "https://reddit.com/r/sysadmin/comments/abc123/dsi_review" --title "DSI Review" --source "Reddit" --type third_party --sentiment positive
    python curate.py flag --id a1b2c3d4e5f6 --reason "Not about DSI, just mentions 'investigations' generically"
    python curate.py list-flagged
    python curate.py learn
"""

import argparse
import sqlite3
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "dsi_awareness.db"
CONFIG_PATH = Path(__file__).parent / "config.json"


def make_id(text):
    return hashlib.md5(text.encode()).hexdigest()[:12]


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Ensure flagged columns exist
    try:
        conn.execute("ALTER TABLE articles ADD COLUMN flagged INTEGER DEFAULT 0")
    except Exception:
        pass
    try:
        conn.execute("ALTER TABLE articles ADD COLUMN flag_reason TEXT")
    except Exception:
        pass
    try:
        conn.execute("ALTER TABLE reddit_mentions ADD COLUMN flagged INTEGER DEFAULT 0")
    except Exception:
        pass
    try:
        conn.execute("ALTER TABLE reddit_mentions ADD COLUMN flag_reason TEXT")
    except Exception:
        pass
    try:
        conn.execute("ALTER TABLE articles ADD COLUMN manually_added INTEGER DEFAULT 0")
    except Exception:
        pass
    try:
        conn.execute("ALTER TABLE reddit_mentions ADD COLUMN manually_added INTEGER DEFAULT 0")
    except Exception:
        pass
    conn.commit()
    return conn


def cmd_add(args):
    conn = get_conn()
    url = args.url
    aid = make_id(url)

    # Check if already exists
    existing = conn.execute("SELECT id FROM articles WHERE id = ?", (aid,)).fetchone()
    if not existing:
        existing = conn.execute("SELECT id FROM reddit_mentions WHERE id = ?", (aid,)).fetchone()

    if existing:
        print(f"Already tracked: {url}")
        return

    # Determine if this is a Reddit post
    is_reddit = "reddit.com" in url

    if is_reddit:
        conn.execute(
            "INSERT INTO reddit_mentions (id, subreddit, title, url, author, score, num_comments, created_utc, discovered, search_term, manually_added) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (aid, args.source or "unknown", args.title or url, url,
             "", 0, 0, 0, datetime.now().strftime("%Y-%m-%d"), "manual", 1)
        )
        print(f"Added Reddit mention: {args.title or url}")
    else:
        art_type = args.type or ("microsoft" if "microsoft.com" in url else "third_party")
        conn.execute(
            "INSERT INTO articles (id, url, title, source, type, sentiment, discovered, last_checked, published_date, manually_added) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (aid, url, args.title or url, args.source or "unknown", art_type,
             args.sentiment or "unknown", datetime.now().strftime("%Y-%m-%d"),
             datetime.now().strftime("%Y-%m-%d"), args.published or None, 1)
        )
        print(f"Added article: {args.title or url}")

    conn.commit()

    # Log what was added so learn() can analyze gaps
    _log_manual_addition(conn, url, args.title, args.source)
    conn.close()
    print("Run .\\refresh-pulse.ps1 to update the dashboard.")


def cmd_flag(args):
    conn = get_conn()
    entry_id = args.id
    reason = args.reason or "false positive"

    # Try articles first, then reddit
    cur = conn.execute("UPDATE articles SET flagged = 1, flag_reason = ? WHERE id = ?", (reason, entry_id))
    if cur.rowcount == 0:
        cur = conn.execute("UPDATE reddit_mentions SET flagged = 1, flag_reason = ? WHERE id = ?", (reason, entry_id))

    if cur.rowcount > 0:
        conn.commit()
        print(f"Flagged {entry_id}: {reason}")
        print("Flagged entries are excluded from scores. Run .\\refresh-pulse.ps1 to update.")
    else:
        print(f"No entry found with ID: {entry_id}")
        print("Use the dashboard to find entry IDs, or run: python curate.py list-flagged")

    conn.close()


def cmd_unflag(args):
    conn = get_conn()
    entry_id = args.id

    conn.execute("UPDATE articles SET flagged = 0, flag_reason = NULL WHERE id = ?", (entry_id,))
    conn.execute("UPDATE reddit_mentions SET flagged = 0, flag_reason = NULL WHERE id = ?", (entry_id,))
    conn.commit()
    print(f"Unflagged {entry_id}")
    conn.close()


def cmd_list_flagged(args):
    conn = get_conn()

    print("FLAGGED ARTICLES:")
    for r in conn.execute("SELECT id, title, flag_reason FROM articles WHERE flagged = 1").fetchall():
        print(f"  [{r['id']}] {r['title'][:60]} -- {r['flag_reason']}")

    print("\nFLAGGED REDDIT:")
    for r in conn.execute("SELECT id, title, subreddit, flag_reason FROM reddit_mentions WHERE flagged = 1").fetchall():
        print(f"  [{r['id']}] r/{r['subreddit']}: {r['title'][:50]} -- {r['flag_reason']}")

    total = conn.execute("SELECT COUNT(*) FROM articles WHERE flagged = 1").fetchone()[0]
    total += conn.execute("SELECT COUNT(*) FROM reddit_mentions WHERE flagged = 1").fetchone()[0]
    print(f"\nTotal flagged: {total}")
    conn.close()


def cmd_learn(args):
    """Analyze manual additions and flagged items to suggest config improvements."""
    conn = get_conn()

    print("LEARNING FROM YOUR FEEDBACK")
    print("=" * 50)

    # Check manually added entries for patterns we should search for
    manual_articles = conn.execute("SELECT * FROM articles WHERE manually_added = 1").fetchall()
    manual_reddit = conn.execute("SELECT * FROM reddit_mentions WHERE manually_added = 1").fetchall()

    if manual_articles or manual_reddit:
        print(f"\n{len(manual_articles)} manually added articles, {len(manual_reddit)} manually added Reddit posts")
        print("\nSuggested config improvements based on what you found that I missed:")

        with open(CONFIG_PATH, "r") as f:
            config = json.load(f)

        current_terms = set(config.get("search_terms", []))
        current_subs = set(config.get("reddit_subreddits", []))
        suggested_terms = set()
        suggested_subs = set()

        for r in manual_reddit:
            sub = r["subreddit"]
            if sub and sub not in current_subs:
                suggested_subs.add(sub)

        for a in manual_articles:
            source = a["source"]
            if source:
                suggested_terms.add(source)

        if suggested_subs:
            print(f"\n  New subreddits to add: {', '.join(suggested_subs)}")
            print("  → Add to config.json under reddit_subreddits")
        if suggested_terms:
            print(f"\n  Sources you found that I didn't: {', '.join(suggested_terms)}")
            print("  → Consider adding source-specific search terms")
    else:
        print("\nNo manually added entries yet. When you add entries I missed,")
        print("run 'python curate.py learn' to see suggested improvements.")

    # Check flagged entries for false positive patterns
    flagged_articles = conn.execute("SELECT * FROM articles WHERE flagged = 1").fetchall()
    flagged_reddit = conn.execute("SELECT * FROM reddit_mentions WHERE flagged = 1").fetchall()

    if flagged_articles or flagged_reddit:
        print(f"\n{len(flagged_articles)} flagged articles, {len(flagged_reddit)} flagged Reddit posts")
        print("\nFalse positive patterns detected:")

        flagged_subs = {}
        for r in flagged_reddit:
            sub = r["subreddit"]
            flagged_subs[sub] = flagged_subs.get(sub, 0) + 1

        for sub, count in sorted(flagged_subs.items(), key=lambda x: -x[1]):
            total_from_sub = conn.execute(
                "SELECT COUNT(*) FROM reddit_mentions WHERE subreddit = ?", (sub,)
            ).fetchone()[0]
            pct = (count / max(total_from_sub, 1)) * 100
            if pct > 50:
                print(f"  r/{sub}: {count}/{total_from_sub} flagged ({pct:.0f}%) → consider removing from config")
            else:
                print(f"  r/{sub}: {count}/{total_from_sub} flagged ({pct:.0f}%)")

        reasons = {}
        for item in list(flagged_articles) + list(flagged_reddit):
            reason = item["flag_reason"] or "unspecified"
            reasons[reason] = reasons.get(reason, 0) + 1

        if reasons:
            print("\n  Flag reasons:")
            for reason, count in sorted(reasons.items(), key=lambda x: -x[1]):
                print(f"    - {reason} ({count}x)")
    else:
        print("\nNo flagged entries. Flag false positives with:")
        print("  python curate.py flag --id ENTRY_ID --reason 'not about DSI'")

    conn.close()


def _log_manual_addition(conn, url, title, source):
    """Log manual additions for the learn command to analyze."""
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS manual_additions_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT, title TEXT, source TEXT, added_at DATETIME
            )
        """)
        conn.execute(
            "INSERT INTO manual_additions_log (url, title, source, added_at) VALUES (?,?,?,?)",
            (url, title, source, datetime.now().isoformat())
        )
        conn.commit()
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="DSI Awareness Pulse — Curate entries")
    sub = parser.add_subparsers(dest="command")

    add_p = sub.add_parser("add", help="Add a missed article, video, or Reddit post")
    add_p.add_argument("--url", required=True, help="URL of the content")
    add_p.add_argument("--title", help="Title")
    add_p.add_argument("--source", help="Source name (e.g. 'TechCrunch', 'r/sysadmin')")
    add_p.add_argument("--type", choices=["third_party", "microsoft"], help="Content type")
    add_p.add_argument("--sentiment", choices=["positive", "mixed", "negative"], help="Sentiment")
    add_p.add_argument("--published", help="Publish date (YYYY-MM-DD)")

    flag_p = sub.add_parser("flag", help="Flag a false positive")
    flag_p.add_argument("--id", required=True, help="Entry ID (shown in dashboard)")
    flag_p.add_argument("--reason", help="Why this is a false positive")

    unflag_p = sub.add_parser("unflag", help="Remove a flag")
    unflag_p.add_argument("--id", required=True, help="Entry ID")

    sub.add_parser("list-flagged", help="Show all flagged entries")
    sub.add_parser("learn", help="Analyze feedback and suggest config improvements")

    args = parser.parse_args()

    if args.command == "add":
        cmd_add(args)
    elif args.command == "flag":
        cmd_flag(args)
    elif args.command == "unflag":
        cmd_unflag(args)
    elif args.command == "list-flagged":
        cmd_list_flagged(args)
    elif args.command == "learn":
        cmd_learn(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

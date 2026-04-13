"""
DSI Awareness Pulse — Data Collector
Collects publicly available awareness signals for Microsoft Purview DSI.
Stores results in SQLite for historical tracking + dashboard rendering.

Usage:
    python collector.py              # Full collection run
    python collector.py --reddit     # Reddit only
    python collector.py --trends     # Google Trends only
    python collector.py --articles   # Articles only
    python collector.py --seed       # Seed known articles from config
"""

import sqlite3
import json
import os
import sys
import time
import hashlib
from datetime import datetime, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup

SCRIPT_DIR = Path(__file__).parent
DB_PATH = SCRIPT_DIR / "dsi_awareness.db"
CONFIG_PATH = SCRIPT_DIR / "config.json"
LEARNED_PATH = SCRIPT_DIR / "learned.json"
DASHBOARD_DATA_PATH = SCRIPT_DIR / "dashboard_data.json"

HEADERS = {
    "User-Agent": "DSI-Awareness-Pulse/1.0 (internal PM tool; tanneruzzell@microsoft.com)"
}


def load_config():
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


def load_learned():
    if LEARNED_PATH.exists():
        with open(LEARNED_PATH, "r") as f:
            return json.load(f)
    return {"exclude_title_patterns": [], "exclude_subreddits": []}


def is_false_positive(title, subreddit=None):
    """Check if an entry matches learned false positive patterns."""
    learned = load_learned()
    title_lower = title.lower()

    for pattern in learned.get("exclude_title_patterns", []):
        if pattern.lower() in title_lower:
            return True

    if subreddit and subreddit in learned.get("exclude_subreddits", []):
        return True

    return False


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id TEXT PRIMARY KEY,
            url TEXT UNIQUE,
            title TEXT,
            source TEXT,
            type TEXT,
            sentiment TEXT,
            discovered DATE,
            last_checked DATE
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS reddit_mentions (
            id TEXT PRIMARY KEY,
            subreddit TEXT,
            title TEXT,
            url TEXT,
            author TEXT,
            score INTEGER,
            num_comments INTEGER,
            created_utc REAL,
            discovered DATE,
            search_term TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS youtube_videos (
            id TEXT PRIMARY KEY,
            title TEXT,
            channel TEXT,
            url TEXT,
            discovered DATE,
            last_checked DATE
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS google_trends (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT,
            date TEXT,
            interest INTEGER,
            collected_at DATE
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS pulse_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_date DATE,
            total_articles INTEGER,
            third_party_articles INTEGER,
            microsoft_articles INTEGER,
            reddit_mentions INTEGER,
            reddit_total_score INTEGER,
            youtube_videos INTEGER,
            google_trends_avg INTEGER,
            composite_score REAL,
            awareness_pct REAL,
            favorability_pct REAL,
            notes TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS collection_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_date DATETIME,
            collector TEXT,
            status TEXT,
            items_found INTEGER,
            items_new INTEGER,
            error TEXT
        )
    """)

    conn.commit()
    return conn


def log_collection(conn, collector, status, items_found=0, items_new=0, error=None):
    conn.execute(
        "INSERT INTO collection_log (run_date, collector, status, items_found, items_new, error) VALUES (?,?,?,?,?,?)",
        (datetime.now().isoformat(), collector, status, items_found, items_new, error)
    )
    conn.commit()


def make_id(text):
    return hashlib.md5(text.encode()).hexdigest()[:12]


# --- Article Collection ---

def seed_known_articles(conn, config):
    """Seed the database with known articles from config."""
    c = conn.cursor()
    new_count = 0
    for art in config.get("known_articles", []):
        aid = make_id(art["url"])
        existing = c.execute("SELECT id FROM articles WHERE id = ?", (aid,)).fetchone()
        if not existing:
            c.execute(
                "INSERT INTO articles (id, url, title, source, type, sentiment, discovered, last_checked) VALUES (?,?,?,?,?,?,?,?)",
                (aid, art["url"], art["title"], art["source"], art["type"],
                 art["sentiment"], art["discovered"], datetime.now().strftime("%Y-%m-%d"))
            )
            new_count += 1
    conn.commit()
    log_collection(conn, "seed_articles", "success", len(config.get("known_articles", [])), new_count)
    print(f"  Articles: seeded {new_count} new from config ({len(config.get('known_articles', []))} total known)")
    return new_count


def discover_articles_bing(conn, config):
    """Search Bing for new DSI articles."""
    new_count = 0
    total_found = 0
    c = conn.cursor()

    for term in config.get("search_terms", []):
        try:
            url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(term)}"
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                continue

            soup = BeautifulSoup(resp.text, "html.parser")
            results = soup.select(".result__a")

            for r in results[:15]:
                href = r.get("href", "")
                title = r.get_text(strip=True)
                if not href or "duckduckgo" in href:
                    continue

                # Resolve DuckDuckGo redirect URLs
                if "uddg=" in href:
                    from urllib.parse import parse_qs, urlparse
                    parsed = urlparse(href)
                    params = parse_qs(parsed.query)
                    href = params.get("uddg", [href])[0]

                total_found += 1
                aid = make_id(href)
                existing = c.execute("SELECT id FROM articles WHERE id = ?", (aid,)).fetchone()
                if not existing:
                    source = urlparse(href).netloc.replace("www.", "")
                    art_type = "microsoft" if "microsoft.com" in href else "third_party"
                    c.execute(
                        "INSERT INTO articles (id, url, title, source, type, sentiment, discovered, last_checked) VALUES (?,?,?,?,?,?,?,?)",
                        (aid, href, title, source, art_type, "unknown",
                         datetime.now().strftime("%Y-%m-%d"), datetime.now().strftime("%Y-%m-%d"))
                    )
                    new_count += 1

            time.sleep(2)  # be nice
        except Exception as e:
            log_collection(conn, "discover_articles", "error", 0, 0, str(e))
            print(f"  Articles: error searching '{term}': {e}")

    conn.commit()
    log_collection(conn, "discover_articles", "success", total_found, new_count)
    print(f"  Articles: found {total_found} results, {new_count} new")
    return new_count


# --- Reddit Collection ---

def collect_reddit(conn, config):
    """Search Reddit for DSI mentions. Uses PRAW (OAuth) if credentials exist, falls back to JSON API."""
    new_count = 0
    total_found = 0
    c = conn.cursor()

    # Try PRAW first (requires credentials in config.json under "reddit_credentials")
    creds = config.get("reddit_credentials", {})
    if creds.get("client_id") and creds.get("client_secret"):
        try:
            import praw
            reddit = praw.Reddit(
                client_id=creds["client_id"],
                client_secret=creds["client_secret"],
                user_agent="DSI-Awareness-Pulse/1.0 (by /u/dsi-pulse-bot)"
            )
            for term in config.get("search_terms", []):
                for sub_name in config.get("reddit_subreddits", []):
                    try:
                        subreddit = reddit.subreddit(sub_name)
                        for post in subreddit.search(term, sort="new", limit=25):
                            total_found += 1
                            rid = make_id(post.id)
                            existing = c.execute("SELECT id FROM reddit_mentions WHERE id = ?", (rid,)).fetchone()
                            if not existing:
                                c.execute(
                                    "INSERT INTO reddit_mentions (id, subreddit, title, url, author, score, num_comments, created_utc, discovered, search_term) VALUES (?,?,?,?,?,?,?,?,?,?)",
                                    (rid, sub_name, post.title, f"https://reddit.com{post.permalink}",
                                     str(post.author), post.score, post.num_comments,
                                     post.created_utc, datetime.now().strftime("%Y-%m-%d"), term)
                                )
                                new_count += 1
                        time.sleep(1)
                    except Exception as e:
                        print(f"  Reddit: error on r/{sub_name} for '{term}': {e}")

            conn.commit()
            log_collection(conn, "reddit_praw", "success", total_found, new_count)
            print(f"  Reddit (PRAW): found {total_found} posts, {new_count} new")
            return new_count
        except ImportError:
            print("  Reddit: PRAW not installed, falling back to JSON API")
        except Exception as e:
            print(f"  Reddit: PRAW error ({e}), falling back to JSON API")

    # Fallback: JSON API (often blocked by Reddit, but worth trying)
    for term in config.get("search_terms", []):
        for sub in config.get("reddit_subreddits", []):
            try:
                url = f"https://www.reddit.com/r/{sub}/search.json?q={requests.utils.quote(term)}&restrict_sr=1&sort=new&limit=25"
                resp = requests.get(url, headers=HEADERS, timeout=15)
                if resp.status_code == 429:
                    print(f"  Reddit: rate limited on r/{sub}, waiting 60s...")
                    time.sleep(60)
                    resp = requests.get(url, headers=HEADERS, timeout=15)
                if resp.status_code != 200:
                    continue

                data = resp.json()
                posts = data.get("data", {}).get("children", [])

                for post in posts:
                    pd = post.get("data", {})
                    total_found += 1
                    rid = make_id(pd.get("id", str(time.time())))
                    existing = c.execute("SELECT id FROM reddit_mentions WHERE id = ?", (rid,)).fetchone()
                    if not existing:
                        c.execute(
                            "INSERT INTO reddit_mentions (id, subreddit, title, url, author, score, num_comments, created_utc, discovered, search_term) VALUES (?,?,?,?,?,?,?,?,?,?)",
                            (rid, sub, pd.get("title", ""), f"https://reddit.com{pd.get('permalink', '')}",
                             pd.get("author", ""), pd.get("score", 0), pd.get("num_comments", 0),
                             pd.get("created_utc", 0), datetime.now().strftime("%Y-%m-%d"), term)
                        )
                        new_count += 1

                time.sleep(3)
            except Exception as e:
                print(f"  Reddit: error on r/{sub} for '{term}': {e}")

    if total_found == 0 and not creds.get("client_id"):
        print("  Reddit: JSON API blocked. Trying PullPush archive...")
        total_found, new_count = _collect_reddit_pullpush(conn, config)

    conn.commit()
    log_collection(conn, "reddit", "success", total_found, new_count)
    print(f"  Reddit: found {total_found} posts, {new_count} new")
    return new_count


def _collect_reddit_pullpush(conn, config):
    """Fallback: use PullPush Reddit archive API (no auth needed, indexes all of Reddit)."""
    new_count = 0
    total_found = 0
    skipped = 0
    c = conn.cursor()

    for term in config.get("search_terms", []):
        try:
            url = f"https://api.pullpush.io/reddit/search/submission/?q={requests.utils.quote(term)}&size=50"
            resp = requests.get(url, headers=HEADERS, timeout=30)
            if resp.status_code != 200:
                print(f"  PullPush: HTTP {resp.status_code} for '{term}'")
                continue

            posts = resp.json().get("data", [])
            for p in posts:
                total_found += 1
                title = p.get("title", "")
                subreddit = p.get("subreddit", "")

                # Skip learned false positive patterns
                if is_false_positive(title, subreddit):
                    skipped += 1
                    continue

                rid = make_id(p.get("id", str(time.time())))
                existing = c.execute("SELECT id FROM reddit_mentions WHERE id = ?", (rid,)).fetchone()
                if not existing:
                    c.execute(
                        "INSERT INTO reddit_mentions (id, subreddit, title, url, author, score, num_comments, created_utc, discovered, search_term) VALUES (?,?,?,?,?,?,?,?,?,?)",
                        (rid, subreddit, title,
                         f"https://reddit.com{p.get('permalink', '')}",
                         p.get("author", ""), p.get("score", 0), p.get("num_comments", 0),
                         p.get("created_utc", 0), datetime.now().strftime("%Y-%m-%d"), term)
                    )
                    new_count += 1

            time.sleep(2)
        except Exception as e:
            print(f"  PullPush: error for '{term}': {e}")

    if skipped:
        print(f"  PullPush: skipped {skipped} entries matching learned false-positive patterns")

    conn.commit()
    return total_found, new_count


# --- Google Trends Collection ---

def collect_google_trends(conn, config):
    """Collect Google Trends interest data."""
    try:
        from pytrends.request import TrendReq
        pytrends = TrendReq(hl="en-US", tz=480)
        keywords = config.get("google_trends_keywords", ["data security investigations"])

        for kw in keywords:
            try:
                pytrends.build_payload([kw], cat=0, timeframe="today 3-m", geo="", gprop="")
                df = pytrends.interest_over_time()
                if df.empty:
                    print(f"  Trends: no data for '{kw}'")
                    continue

                rows_added = 0
                for idx, row in df.iterrows():
                    date_str = idx.strftime("%Y-%m-%d")
                    interest = int(row[kw])
                    existing = conn.execute(
                        "SELECT id FROM google_trends WHERE keyword = ? AND date = ?",
                        (kw, date_str)
                    ).fetchone()
                    if not existing:
                        conn.execute(
                            "INSERT INTO google_trends (keyword, date, interest, collected_at) VALUES (?,?,?,?)",
                            (kw, date_str, interest, datetime.now().strftime("%Y-%m-%d"))
                        )
                        rows_added += 1

                conn.commit()
                print(f"  Trends: '{kw}' → {rows_added} new data points")
                time.sleep(5)
            except Exception as e:
                print(f"  Trends: error for '{kw}': {e}")

        log_collection(conn, "google_trends", "success")
    except ImportError:
        print("  Trends: pytrends not installed, skipping")
        log_collection(conn, "google_trends", "skipped", error="pytrends not installed")
    except Exception as e:
        print(f"  Trends: error: {e}")
        log_collection(conn, "google_trends", "error", error=str(e))


# --- Snapshot Generation ---

def generate_snapshot(conn):
    """Calculate current awareness metrics and save a snapshot."""
    c = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")

    # Check if we already have a snapshot today
    existing = c.execute("SELECT id FROM pulse_snapshots WHERE snapshot_date = ?", (today,)).fetchone()
    if existing:
        c.execute("DELETE FROM pulse_snapshots WHERE snapshot_date = ?", (today,))

    total_articles = c.execute("SELECT COUNT(*) FROM articles WHERE COALESCE(flagged, 0) = 0").fetchone()[0]
    third_party = c.execute("SELECT COUNT(*) FROM articles WHERE type = 'third_party' AND COALESCE(flagged, 0) = 0").fetchone()[0]
    microsoft = c.execute("SELECT COUNT(*) FROM articles WHERE type = 'microsoft' AND COALESCE(flagged, 0) = 0").fetchone()[0]

    reddit_count = c.execute("SELECT COUNT(*) FROM reddit_mentions WHERE COALESCE(flagged, 0) = 0").fetchone()[0]
    reddit_score = c.execute("SELECT COALESCE(SUM(score), 0) FROM reddit_mentions WHERE COALESCE(flagged, 0) = 0").fetchone()[0]

    youtube_count = c.execute("SELECT COUNT(*) FROM youtube_videos").fetchone()[0]

    trends_avg = c.execute(
        "SELECT COALESCE(AVG(interest), 0) FROM google_trends WHERE date >= date('now', '-30 days')"
    ).fetchone()[0]

    # Composite score (weighted)
    # Articles: 0-10 (1 pt per 3rd party article, capped at 10)
    art_score = min(third_party * 2.5, 10)
    # Reddit: 0-10 (2 pts per mention, capped at 10)
    reddit_score_val = min(reddit_count * 2, 10)
    # Trends: 0-10 (scale from 0-100 index)
    trends_score = min(trends_avg / 10, 10)
    # Microsoft content: 0-10 (1.5 pts per post, capped at 10)
    ms_score = min(microsoft * 1.5, 10)
    # YouTube: 0-10 (3 pts per video, capped at 10)
    yt_score = min(youtube_count * 3, 10)

    composite = (art_score * 0.25) + (reddit_score_val * 0.20) + (trends_score * 0.20) + (ms_score * 0.20) + (yt_score * 0.15)
    awareness_pct = (composite / 10) * 100

    # Favorability (from sentiment on articles)
    pos = c.execute("SELECT COUNT(*) FROM articles WHERE sentiment = 'positive' AND COALESCE(flagged, 0) = 0").fetchone()[0]
    mixed = c.execute("SELECT COUNT(*) FROM articles WHERE sentiment = 'mixed' AND COALESCE(flagged, 0) = 0").fetchone()[0]
    neg = c.execute("SELECT COUNT(*) FROM articles WHERE sentiment = 'negative' AND COALESCE(flagged, 0) = 0").fetchone()[0]
    total_rated = pos + mixed + neg
    favorability = ((pos * 1.0 + mixed * 0.5) / max(total_rated, 1)) * 100

    c.execute("""
        INSERT INTO pulse_snapshots 
        (snapshot_date, total_articles, third_party_articles, microsoft_articles,
         reddit_mentions, reddit_total_score, youtube_videos, google_trends_avg,
         composite_score, awareness_pct, favorability_pct, notes)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
    """, (today, total_articles, third_party, microsoft, reddit_count, reddit_score,
          youtube_count, int(trends_avg), round(composite, 2), round(awareness_pct, 1),
          round(favorability, 1), f"Auto-generated {datetime.now().isoformat()}"))

    conn.commit()
    print(f"\n  Snapshot saved: {awareness_pct:.0f}% awareness, {favorability:.0f}% favorability")
    print(f"    Articles: {total_articles} ({third_party} 3rd party, {microsoft} Microsoft)")
    print(f"    Reddit: {reddit_count} mentions ({reddit_score} total score)")
    print(f"    Trends avg (30d): {trends_avg:.0f}")
    print(f"    Composite: {composite:.1f}/10")

    return {
        "date": today,
        "awareness_pct": round(awareness_pct, 1),
        "favorability_pct": round(favorability, 1),
        "composite": round(composite, 2)
    }


# --- Dashboard Data Export ---

def export_dashboard_data(conn):
    """Export all data to JSON for the HTML dashboard."""
    c = conn.cursor()

    snapshots = [dict(r) for r in c.execute(
        "SELECT * FROM pulse_snapshots ORDER BY snapshot_date ASC"
    ).fetchall()]

    articles = [dict(r) for r in c.execute(
        "SELECT * FROM articles ORDER BY COALESCE(published_date, discovered) DESC"
    ).fetchall()]

    reddit = [dict(r) for r in c.execute(
        "SELECT * FROM reddit_mentions ORDER BY created_utc DESC"
    ).fetchall()]

    trends = [dict(r) for r in c.execute(
        "SELECT keyword, date, interest FROM google_trends ORDER BY date ASC"
    ).fetchall()]

    videos = [dict(r) for r in c.execute(
        "SELECT * FROM youtube_videos ORDER BY discovered DESC"
    ).fetchall()]

    logs = [dict(r) for r in c.execute(
        "SELECT * FROM collection_log ORDER BY run_date DESC LIMIT 50"
    ).fetchall()]

    # Summary stats
    latest = snapshots[-1] if snapshots else {}

    dashboard = {
        "generated_at": datetime.now().isoformat(),
        "latest_snapshot": latest,
        "snapshots": snapshots,
        "articles": articles,
        "reddit_mentions": reddit,
        "google_trends": trends,
        "youtube_videos": videos,
        "collection_log": logs,
        "summary": {
            "total_articles": len(articles),
            "third_party_articles": len([a for a in articles if a["type"] == "third_party"]),
            "microsoft_articles": len([a for a in articles if a["type"] == "microsoft"]),
            "reddit_total": len(reddit),
            "reddit_unique_subs": len(set(r["subreddit"] for r in reddit)) if reddit else 0,
            "youtube_total": len(videos),
            "trend_keywords_tracked": len(set(t["keyword"] for t in trends)) if trends else 0,
            "snapshots_count": len(snapshots)
        }
    }

    with open(DASHBOARD_DATA_PATH, "w") as f:
        json.dump(dashboard, f, indent=2, default=str)

    # Generate self-contained HTML with embedded data
    generate_standalone_dashboard(dashboard)

    print(f"\n  Dashboard data exported to {DASHBOARD_DATA_PATH}")
    return dashboard


def generate_standalone_dashboard(data):
    """Inject data into dashboard HTML so it works from file:// without a server."""
    template_path = SCRIPT_DIR / "dashboard.html"
    output_path = SCRIPT_DIR / "pulse.html"

    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()

    data_json = json.dumps(data, indent=2, default=str)

    # Replace the fetch-based loader with inline data
    html = html.replace(
        "async function loadData() {\n"
        "            try {\n"
        "                const resp = await fetch('dashboard_data.json');\n"
        "                DATA = await resp.json();\n"
        "                render();\n"
        "            } catch (e) {\n"
        "                document.body.innerHTML += `<div class=\"card full\" style=\"margin-top:20px\"><div class=\"empty-state\"><div class=\"emoji\">⚠️</div><p>Could not load dashboard_data.json</p><p style=\"font-size:12px\">Run <code>python collector.py</code> first to generate data.</p></div></div>`;\n"
        "            }\n"
        "        }",
        f"async function loadData() {{\n"
        f"            DATA = {data_json};\n"
        f"            render();\n"
        f"        }}"
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"  Standalone dashboard written to {output_path}")


# --- Main ---

def main():
    args = sys.argv[1:]
    config = load_config()
    conn = init_db()

    print(f"DSI Awareness Pulse — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 50)

    run_all = len(args) == 0

    if run_all or "--seed" in args:
        print("\n[1/5] Seeding known articles...")
        seed_known_articles(conn, config)

    if run_all or "--articles" in args:
        print("\n[2/5] Discovering new articles...")
        discover_articles_bing(conn, config)

    if run_all or "--reddit" in args:
        print("\n[3/5] Collecting Reddit mentions...")
        collect_reddit(conn, config)

    if run_all or "--trends" in args:
        print("\n[4/5] Collecting Google Trends...")
        collect_google_trends(conn, config)

    print("\n[5/5] Generating snapshot & dashboard data...")
    generate_snapshot(conn)
    export_dashboard_data(conn)

    conn.close()
    print("\n✅ Collection complete!")


if __name__ == "__main__":
    main()

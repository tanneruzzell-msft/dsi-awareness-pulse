"""Generate a single shareable HTML file with all dashboard data + benchmark embedded.
No server needed — open in any browser, share via Teams/SharePoint/email.

Usage: python export_shareable.py
Output: shareable-pulse.html
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
DB_PATH = SCRIPT_DIR / "dsi_awareness.db"
BENCHMARK_PATH = SCRIPT_DIR / "benchmark.json"
APP_HTML_PATH = SCRIPT_DIR / "app.html"
OUTPUT_PATH = SCRIPT_DIR / "shareable-pulse.html"


def get_data():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
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

    latest = snapshots[-1] if snapshots else {}
    data = {
        "generated_at": datetime.now().isoformat(),
        "latest_snapshot": latest,
        "snapshots": snapshots,
        "articles": articles,
        "reddit_mentions": reddit,
        "linkedin_posts": linkedin,
        "google_trends": trends,
        "summary": {
            "total_articles": len([a for a in articles if not a.get("flagged")]),
            "third_party_articles": len([a for a in articles if a.get("type") == "third_party" and not a.get("flagged")]),
            "microsoft_articles": len([a for a in articles if a.get("type") == "microsoft" and not a.get("flagged")]),
            "reddit_total": len([r for r in reddit if not r.get("flagged")]),
            "reddit_unique_subs": len(set(r["subreddit"] for r in reddit if not r.get("flagged"))) if reddit else 0,
            "linkedin_total": len([p for p in linkedin if not p.get("flagged")]),
            "snapshots_count": len(snapshots),
            "total_flagged": len([a for a in articles if a.get("flagged")]) + len([r for r in reddit if r.get("flagged")])
        }
    }
    conn.close()
    return data


def get_benchmark():
    if BENCHMARK_PATH.exists():
        with open(BENCHMARK_PATH, "r") as f:
            return json.load(f)
    return {"competitors": {}}


def generate():
    data = get_data()
    benchmark = get_benchmark()

    with open(APP_HTML_PATH, "r", encoding="utf-8") as f:
        html = f.read()

    data_json = json.dumps(data, indent=2, default=str)
    bench_json = json.dumps(benchmark, indent=2, default=str)

    # Replace fetch-based data loading with inline data
    html = html.replace(
        "async function loadData() {\n"
        "    try {\n"
        "        const resp = await fetch('/api/data');\n"
        "        DATA = await resp.json();\n"
        "        render();\n"
        "    } catch (e) {\n"
        "        showToast('Failed to load data: ' + e.message, true);\n"
        "    }\n"
        "}",
        f"async function loadData() {{\n"
        f"    DATA = {data_json};\n"
        f"    render();\n"
        f"}}"
    )

    # Replace fetch-based benchmark loading
    html = html.replace(
        "async function loadBenchmark() {\n"
        "    try {\n"
        "        const resp = await fetch('/api/benchmark');\n"
        "        BENCHMARK = await resp.json();\n"
        "        renderBenchmark();\n"
        "    } catch(e) {}\n"
        "}",
        f"async function loadBenchmark() {{\n"
        f"    BENCHMARK = {bench_json};\n"
        f"    renderBenchmark();\n"
        f"}}"
    )

    # Make flag/add/refresh buttons show "read-only" toast instead of hitting API
    html = html.replace(
        "async function flagEntry(id) {",
        "async function flagEntry(id) { showToast('Read-only view. Use the live dashboard (start-dashboard.ps1) to flag entries.', true); return; /* "
    )
    html = html.replace(
        "async function unflagEntry(id) {",
        "async function unflagEntry(id) { showToast('Read-only view. Use the live dashboard to unflag.', true); return; /* "
    )
    html = html.replace(
        "async function addEntry() {",
        "async function addEntry() { showToast('Read-only view. Use the live dashboard to add entries.', true); return; /* "
    )
    html = html.replace(
        "async function refreshData() {",
        "async function refreshData() { showToast('Read-only view. Use the live dashboard to refresh data.', true); return; /* "
    )

    # Add a "read-only" indicator to the topbar
    html = html.replace(
        '<button class="btn primary" onclick="refreshData()" id="refresh-btn">🔄 Refresh Data</button>',
        '<span class="badge unknown" style="padding:6px 12px">📤 Shared View (read-only)</span>'
    )

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)

    size_kb = OUTPUT_PATH.stat().st_size / 1024
    print(f"Shareable dashboard exported: {OUTPUT_PATH}")
    print(f"Size: {size_kb:.0f} KB")
    print(f"Share via Teams, SharePoint, or email — opens in any browser, no server needed.")


if __name__ == "__main__":
    generate()

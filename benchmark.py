"""Quick competitive awareness benchmark — same signals as DSI pulse."""
import requests
import json
import time
from datetime import datetime

HEADERS = {"User-Agent": "DSI-Awareness-Benchmark/1.0"}

COMPETITORS = {
    "DSI (Purview)": {
        "search_terms": ["Microsoft Purview Data Security Investigations"],
        "trends_keyword": "data security investigations",
    },
    "Relativity": {
        "search_terms": ["Relativity eDiscovery", "RelativityOne"],
        "trends_keyword": "Relativity eDiscovery",
    },
    "Nuix": {
        "search_terms": ["Nuix investigation", "Nuix eDiscovery"],
        "trends_keyword": "Nuix",
    },
    "Everlaw": {
        "search_terms": ["Everlaw eDiscovery", "Everlaw litigation"],
        "trends_keyword": "Everlaw",
    },
    "Exterro": {
        "search_terms": ["Exterro eDiscovery", "Exterro legal"],
        "trends_keyword": "Exterro",
    },
    "DTEX": {
        "search_terms": ["DTEX insider threat", "DTEX Systems"],
        "trends_keyword": "DTEX Systems",
    },
    "Varonis": {
        "search_terms": ["Varonis data security", "Varonis investigation"],
        "trends_keyword": "Varonis",
    },
    "Cyberhaven": {
        "search_terms": ["Cyberhaven data security", "Cyberhaven insider"],
        "trends_keyword": "Cyberhaven",
    },
}

results = {}

for name, config in COMPETITORS.items():
    print(f"\n{'='*50}")
    print(f"  {name}")
    print(f"{'='*50}")

    # Reddit via PullPush
    reddit_total = 0
    reddit_score = 0
    for term in config["search_terms"]:
        try:
            url = f"https://api.pullpush.io/reddit/search/submission/?q={requests.utils.quote(term)}&size=100"
            resp = requests.get(url, headers=HEADERS, timeout=30)
            if resp.status_code == 200:
                posts = resp.json().get("data", [])
                reddit_total += len(posts)
                reddit_score += sum(p.get("score", 0) for p in posts)
                subs = set(p.get("subreddit", "") for p in posts)
                print(f"  Reddit [{term[:40]}]: {len(posts)} posts, {sum(p.get('score',0) for p in posts)} score")
                if posts:
                    top = sorted(posts, key=lambda x: x.get("score", 0), reverse=True)[:3]
                    for t in top:
                        print(f"    [{t.get('score',0)} pts] r/{t.get('subreddit','')} : {t.get('title','')[:60]}")
            time.sleep(1)
        except Exception as e:
            print(f"  Reddit error: {e}")

    # Google Trends
    trends_avg = 0
    try:
        from pytrends.request import TrendReq
        pytrends = TrendReq(hl="en-US", tz=480)
        kw = config["trends_keyword"]
        pytrends.build_payload([kw], timeframe="today 3-m")
        df = pytrends.interest_over_time()
        if not df.empty:
            trends_avg = int(df[kw].mean())
            trends_max = int(df[kw].max())
            print(f"  Google Trends [{kw}]: avg={trends_avg}, max={trends_max}")
        else:
            print(f"  Google Trends [{kw}]: no data")
        time.sleep(5)
    except Exception as e:
        print(f"  Google Trends error: {e}")

    # Calculate composite (same formula as DSI pulse)
    # Using reddit_total as proxy for both articles + reddit since we can't search articles reliably
    reddit_score_val = min(reddit_total * 0.5, 10)  # scaled down since these have more posts
    trends_score_val = min(trends_avg / 10, 10)

    composite = (reddit_score_val * 0.5) + (trends_score_val * 0.5)
    awareness_pct = (composite / 10) * 100

    results[name] = {
        "reddit_posts": reddit_total,
        "reddit_score": reddit_score,
        "trends_avg": trends_avg,
        "composite": round(composite, 1),
        "awareness_pct": round(awareness_pct, 0),
    }

    print(f"  → Reddit: {reddit_total} posts, {reddit_score} total score")
    print(f"  → Trends: {trends_avg} avg interest")
    print(f"  → Awareness proxy: {awareness_pct:.0f}%")


print(f"\n\n{'='*70}")
print(f"  COMPETITIVE BENCHMARK SUMMARY")
print(f"{'='*70}")
print(f"{'Product':<20} {'Reddit Posts':>12} {'Reddit Score':>12} {'Trends Avg':>10} {'Awareness':>10}")
print(f"{'-'*20} {'-'*12} {'-'*12} {'-'*10} {'-'*10}")

for name in sorted(results.keys(), key=lambda x: results[x]["reddit_posts"], reverse=True):
    r = results[name]
    print(f"{name:<20} {r['reddit_posts']:>12} {r['reddit_score']:>12} {r['trends_avg']:>10} {r['awareness_pct']:>9.0f}%")

# Save for dashboard
with open("benchmark.json", "w") as f:
    json.dump({"generated_at": datetime.now().isoformat(), "competitors": results}, f, indent=2)
print(f"\nSaved to benchmark.json")

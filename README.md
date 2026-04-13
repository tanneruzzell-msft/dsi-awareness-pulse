# DSI Awareness Pulse — Guide

**Owner:** Tanner Uzzell
**Purpose:** Track public awareness and sentiment for Microsoft Purview Data Security Investigations (DSI) over time.
**Location:** `Documents/DSI-PM-Vault/dsi-awareness-pulse/`

---

## What This Is

A lightweight awareness tracking system that answers two questions weekly:

1. **How visible is DSI?** (awareness score)
2. **What do people think of it?** (favorability score)

It collects publicly available signals — articles, Reddit mentions, Google Trends — stores them in a local SQLite database, calculates a composite score, and renders a dashboard you can share with your team.

---

## Quick Start

### Refresh data + open the dashboard:

```powershell
cd ~\Documents\DSI-PM-Vault\dsi-awareness-pulse
.\refresh-pulse.ps1
```

This runs the collector, updates the database, generates a new `pulse.html`, and opens it in your browser.

### Refresh data without opening:

```powershell
.\refresh-pulse.ps1 -SkipOpen
```

### Automation:

A Windows Scheduled Task (`DSI-Awareness-Pulse`) is already registered and runs **every Monday at 8 AM**. To re-register or change the schedule:

```powershell
.\refresh-pulse.ps1 -Schedule
```

To check the task: `Get-ScheduledTask -TaskName 'DSI-Awareness-Pulse'`

---

## What Gets Collected

| Signal | Source | Method | Needs API Key? |
|--------|--------|--------|----------------|
| **Articles** | DuckDuckGo search | Web scraping search results for DSI keywords | No |
| **Known Articles** | `config.json` | Manually verified articles seeded into the database | No |
| **Reddit Mentions** | Reddit JSON API | Public search across 7 security subreddits | No |
| **Google Trends** | Google Trends via `pytrends` | Interest-over-time data for DSI keywords | No |
| **YouTube** | Planned (manual seed for now) | Future: YouTube Data API | Yes (free) |

All sources are public and require no authentication. Rate limits are handled with automatic backoff.

---

## How Scores Are Calculated

### Awareness Score (0-100%)

Weighted composite of 5 sub-scores, each 0-10:

| Component | Weight | How It's Scored |
|-----------|--------|----------------|
| Third-party articles | 25% | 2.5 points per article, max 10 |
| Reddit mentions | 20% | 2 points per mention, max 10 |
| Google Trends interest | 20% | 30-day average interest / 10, max 10 |
| Microsoft-authored content | 20% | 1.5 points per post, max 10 |
| YouTube videos | 15% | 3 points per video, max 10 |

**Formula:** `(articles * 0.25) + (reddit * 0.20) + (trends * 0.20) + (microsoft * 0.20) + (youtube * 0.15)` then scaled to percentage.

### Favorability Score (0-100%)

Based on sentiment of tracked articles:
- Positive articles count as 1.0
- Mixed articles count as 0.5
- Negative articles count as 0.0
- Formula: `(positive + mixed * 0.5) / total_rated * 100`

---

## Data Verification

Every data point in the dashboard is verifiable:

- **Articles**: Each has a clickable URL you can open to confirm it exists. Source, title, and sentiment are logged when discovered.
- **Reddit**: Each mention links to the actual Reddit post. Score and comment count come from Reddit's public API.
- **Google Trends**: Data comes from the same source as [trends.google.com](https://trends.google.com/trends/explore?q=%22data+security+investigations%22). You can verify any data point there.
- **Collection Log**: Every collection run is logged with timestamp, items found, and any errors. Check the "Collection Log" tab in the dashboard.

### Manual Verification Checklist

If you want to spot-check the data:

1. **Articles** — Click any article link in the dashboard. It should open the real article.
2. **Reddit** — Go to [reddit.com/search?q="data security investigations"](https://www.reddit.com/search/?q=%22data+security+investigations%22) and confirm the count matches.
3. **Google Trends** — Go to [Google Trends](https://trends.google.com/trends/explore?q=%22data+security+investigations%22) and compare the interest curve to the dashboard chart.
4. **Database** — Open `dsi_awareness.db` with any SQLite viewer (e.g., [DB Browser for SQLite](https://sqlitebrowser.org/)) to see raw data.

---

## File Reference

| File | Purpose |
|------|---------|
| `collector.py` | Main data collection script — run manually or via scheduled task |
| `config.json` | Configuration: search terms, subreddits, known articles, competitors |
| `pulse.html` | **Self-contained dashboard** — open this in any browser, works offline, shareable |
| `dashboard.html` | Dashboard template (used by collector to generate pulse.html) |
| `dashboard_data.json` | Raw JSON data export (used by dashboard.html if served from a web server) |
| `dsi_awareness.db` | SQLite database with all historical data |
| `refresh-pulse.ps1` | PowerShell script to run collector + open dashboard |
| `data-accessibility-matrix.md` | Reference doc mapping all possible awareness signals by accessibility tier |
| `2026-04-07.md` | Original manual awareness pulse (pre-automation baseline) |

---

## Sharing the Dashboard

### Option 1: GitHub Pages (recommended for team sharing)

The dashboard is published at: **[See URL after push]**

To update after a collection run:
```powershell
cd ~\Documents\DSI-PM-Vault\dsi-awareness-pulse
git add pulse.html dashboard_data.json
git commit -m "Weekly pulse update"
git push
```

GitHub Pages will automatically serve the updated dashboard.

### Option 2: SharePoint

1. After running `.\refresh-pulse.ps1`, copy `pulse.html` to your SharePoint site
2. The file is fully self-contained — no dependencies, no server needed
3. Anyone with access to the SharePoint folder can open it in a browser

### Option 3: Email / Teams

`pulse.html` is a single file (~38KB). You can attach it to an email or drop it in a Teams channel. Recipients open it in their browser.

---

## Customizing

### Add a new search term

Edit `config.json` → `search_terms` array:
```json
"search_terms": [
    "Microsoft Purview Data Security Investigations",
    "Purview DSI",
    "your new term here"
]
```

### Add a new subreddit to monitor

Edit `config.json` → `reddit_subreddits` array.

### Add a known article manually

Edit `config.json` → `known_articles` array:
```json
{
    "url": "https://example.com/article",
    "title": "Article Title",
    "source": "Publication Name",
    "type": "third_party",
    "sentiment": "positive",
    "discovered": "2026-04-13"
}
```

Then run `python collector.py --seed` to import it.

### Change the scoring weights

Edit the weights in `collector.py` → `generate_snapshot()` function.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Google Trends returns 429 errors | Rate limited — wait 10 minutes and retry, or it'll work on the next scheduled run |
| Reddit returns 0 results | This may be accurate — DSI has minimal Reddit presence. Verify at reddit.com/search |
| DuckDuckGo returns 0 articles | DuckDuckGo sometimes blocks automated requests. Known articles from config.json are still tracked. |
| Dashboard shows no data | Run `python collector.py` first to populate the database |
| Scheduled task not running | Check: `Get-ScheduledTask -TaskName 'DSI-Awareness-Pulse'` — re-register with `.\refresh-pulse.ps1 -Schedule` |
| Python not found | Run: `$env:PATH = "$env:LOCALAPPDATA\Programs\Python\Python312;$env:PATH"` or reinstall Python |

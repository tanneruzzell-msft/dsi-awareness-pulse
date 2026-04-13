# How the Best Marketing Teams Track Awareness — Research Summary

**For:** Tanner Uzzell | **Date:** April 13, 2026
**Context:** Validating the DSI Awareness Pulse methodology against industry standards

---

## The One Metric That Matters: Share of Voice (SOV)

This is the industry standard. Per Ahrefs, Brandwatch, and decades of marketing research:

> **Share of Voice = Your brand's visibility / Total market visibility**

SOV has a proven correlation with market share (Harvard Business Review). If you have 17% SOV, your market share trends toward 17% over time. Every 10 extra percentage points of SOV above your market share ("excess SOV") drives ~0.7% annual market share growth.

**What this means for your dashboard:** Instead of an abstract "awareness score," you should track **DSI's share of the conversation compared to competitors**. That's what the benchmark tab is actually showing — it just needs to be labeled as SOV.

---

## What Each Type of Firm Tracks

### SEO Firms (Ahrefs, Semrush, Moz)

| Metric | What It Is | Can You Get It? |
|--------|-----------|----------------|
| **Branded search volume** | Monthly Google searches for "Purview DSI" or "data security investigations" | ✅ Google Trends (you have this) |
| **Organic traffic share** | Your site's traffic vs competitors' for industry keywords | ❌ Needs Ahrefs/Semrush paid tool |
| **Keyword visibility / rank tracking** | Where you rank for key terms like "insider threat investigation tool" | ❌ Needs Ahrefs Rank Tracker |
| **Referring domains** | How many sites link to your content vs competitors | ❌ Needs Ahrefs/Semrush |
| **SERP feature presence** | Do you show up in featured snippets, People Also Ask, etc. | ❌ Manual or paid tool |

**Bottom line:** The SEO version of SOV is "what % of search traffic for your industry keywords lands on your site vs competitors." You'd need an Ahrefs or Semrush subscription (~$100-200/mo) to track this properly.

### Social Listening / UGC Firms (Brandwatch, Sprout Social, Mention)

| Metric | What It Is | Can You Get It? |
|--------|-----------|----------------|
| **Mention volume** | Total online mentions of your brand across social + web | ✅ You have this (Reddit, articles) |
| **Mention volume over time** | Trend of mentions week-over-week | ✅ Your snapshots track this |
| **Share of voice** | Your mentions / (your mentions + competitor mentions) | ✅ Your benchmark tab shows this! |
| **Sentiment** | Positive / negative / neutral breakdown | ✅ You have this for articles |
| **Reach** | Total potential audience exposed to mentions | 🟡 Partial (Reddit score is a proxy) |
| **Engagement rate** | Likes + comments + shares per mention | 🟡 Partial (Reddit score + comments) |
| **Influencer amplification** | High-follower accounts mentioning you | ❌ Would need social listening tool |

**Bottom line:** You're actually tracking most of what Brandwatch charges $1000+/mo for. Your Reddit + article tracking IS social listening, just narrower in scope. The gap is Twitter/X, LinkedIn (you added manual tracking), and influencer identification.

### Content / UGC Marketing Teams

| Metric | What It Is | Can You Get It? |
|--------|-----------|----------------|
| **Earned media value (EMV)** | Dollar-equivalent of unpaid coverage | 🟡 Could estimate from article count × avg CPM |
| **Content velocity** | New content about your brand per week | ✅ Your collection tracks this |
| **Community growth** | Forum/subreddit subscriber growth | ❌ Can't track subreddit growth without API |
| **User-generated content count** | Posts/reviews/videos by non-brand accounts | ✅ Your third-party article + Reddit tracking |
| **Advocacy ratio** | % of mentions from non-brand vs brand accounts | ✅ You separate Microsoft vs third-party |

### B2B SaaS Marketing Teams (HubSpot, Drift, Snowflake model)

| Metric | What It Is | Can You Get It? |
|--------|-----------|----------------|
| **Branded search volume** | Google searches for your product name | ✅ Google Trends |
| **Direct website traffic** | Users who type your URL directly | 🟡 Need learn.microsoft.com analytics |
| **Share of voice (organic)** | Your visibility for industry keywords | ❌ Needs SEO tool |
| **G2/PeerSpot reviews** | Review count + rating over time | ✅ Manual (you have PeerSpot) |
| **Analyst coverage** | Gartner/Forrester mentions | ✅ Manual (you track this) |
| **Event/conference presence** | RSA, Ignite session mentions | ✅ Manual |

---

## What Your Dashboard Does Well vs. What's Missing

### ✅ You already track (industry-standard)

1. **Mention volume** — articles + Reddit posts
2. **Mention trend** — snapshots over time
3. **Share of voice** — your benchmark tab (Reddit + Trends vs competitors)
4. **Sentiment** — positive/mixed/negative on articles
5. **Content velocity** — new articles discovered per collection run
6. **Third-party vs brand content ratio** — the advocacy ratio

### 🟡 You could add cheaply

1. **Labeled SOV %** — Rename the benchmark score to "Share of Voice" (it already is SOV, just not labeled that way)
2. **Week-over-week delta** — Show Δ% change on each scorecard
3. **G2/PeerSpot review count** — Add to the weekly manual check
4. **Learn.microsoft.com page views** — Ask the docs team for a monthly number

### ❌ You'd need paid tools for

1. **Organic search SOV** — Ahrefs Rank Tracker ($99/mo)
2. **Twitter/X mention tracking** — X API ($100/mo for Basic)
3. **LinkedIn mention tracking** — No public API (manual only, which you're doing)
4. **Full social listening** — Brandwatch ($1000+/mo), Sprout Social ($249/mo)
5. **Influencer identification** — Part of Brandwatch/Sprout

---

## Recommendation: Rebrand the Dashboard Metrics

Based on this research, here's how to make your scores more industry-standard:

| Current Label | Better Label | Why |
|--------------|-------------|-----|
| "Awareness Score (58%)" | **"Brand Awareness Index"** or keep but add context | Fine as-is, just explain the components |
| Benchmark tab "Awareness" column | **"Share of Voice"** | This IS SOV — your mentions / total mentions. Industry standard term. |
| "Favorability (92%)" | **"Net Sentiment"** | Standard term in social listening |
| "Reddit Mentions" | **"Community Mentions"** | More professional for marketing audience |
| "Third-party articles" | **"Earned Media"** | Industry term for unpaid coverage |

The methodology is sound. The main gap vs. paid tools is breadth (you cover Reddit + web, they cover all social). But for a security B2B product where Reddit and tech blogs are the actual discovery channels, your coverage is well-targeted.

---

## Sources

- [Ahrefs: Share of Voice](https://ahrefs.com/blog/share-of-voice/) — SOV methodology for organic search, ads, social
- [Brandwatch: How to Measure Brand Awareness](https://www.brandwatch.com/blog/how-to-measure-brand-awareness/) — Surveys, traffic, search volume, social listening
- [Harvard Business Review: The relationship between SOV and market share](https://hbr.org/1990/01/ad-spending-maintaining-market-share)
- [LinkedIn B2B Institute: SOV drives 0.7% annual market share growth per 10 eSOV points](https://business.linkedin.com/content/dam/me/business/en-us/amp/marketing-solutions/images/lms-b2b-institute/pdf/LIN_B2B-Marketing-Report-Digital.pdf)

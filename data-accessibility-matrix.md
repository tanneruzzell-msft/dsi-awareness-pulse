# DSI Awareness & Favorability — Data Accessibility Matrix

## Tier 1: I Can Get Right Now (No Setup Needed)

| Signal | How | Frequency |
|---|---|---|
| Third-party article count + links | Web search for DSI keywords | Weekly |
| Third-party article sentiment | Read articles, classify pos/neg/mixed | Weekly |
| Reddit mention count | Web search across security/sysadmin subs | Weekly |
| Tech Community post existence + titles | Web search / fetch | Weekly |
| PeerSpot review themes + quotes | Web fetch (got it working today) | Monthly |
| YouTube video existence + titles | Web search | Weekly |
| Competitor mention tracking | Web search for "DSI vs X", competitor coverage | Weekly |
| Analyst report mentions | Web search for Gartner/Forrester/IDC + DSI | Monthly |
| Conference session mentions | Web search Ignite/RSA/BlackHat session catalogs | Quarterly |

**Coverage: ~9 signals. Mostly existence/count — no engagement depth.**

---

## Tier 2: Could Get With Creds / Auth (You Give Me Access)

| Signal | What I Need | How |
|---|---|---|
| DSI provisioning / customer count | Kusto cluster URL + your AAD auth | Azure CLI `az kusto query` |
| Customer activation funnel | Kusto (same cluster) | KQL queries — sign-up → first investigation → first AI job |
| Provisioning-to-first-visit time | Kusto | KQL query on telemetry events |
| AI job run rates | Kusto | KQL on job execution telemetry |
| Microsoft Learn page views | Learn analytics portal (if you have access) or Kusto if telemetry is piped there | Query or manual export |
| Tech Community post view counts | Microsoft internal — TC analytics or API | Would need an internal API endpoint or manual check |
| In-product feedback (Floodgate) | Kusto or internal dashboard | KQL if Floodgate events are in your telemetry cluster |
| Support ticket themes | ServiceNow / IcM — may be in Kusto | KQL if escalations are logged |
| MC post read/reaction counts | M365 Admin Center analytics | Manual or API if available |

**Coverage: ~9 signals. This is the high-value internal data. Kusto is the unlock for most of it.**

---

## Tier 3: Could Get With Scripts / Automation (We Build It)

| Signal | What We'd Build | Effort |
|---|---|---|
| Google Trends index | Python script using `pytrends` library | Small — 30 min |
| Reddit post count + upvotes + comments | Python script using Reddit API (PRAW) — free, needs a Reddit app key | Small — 1 hr |
| Twitter/X mention volume + sentiment | Python script using X API (paid tier, ~$100/mo for Basic) | Medium — API cost + setup |
| LinkedIn post volume | No public API for search — would need a scraping approach or manual | Hard — LinkedIn blocks scraping |
| G2 review count + rating | Python scraper or manual (G2 blocks automated access) | Medium — may need manual fallback |
| YouTube view counts | Python script using YouTube Data API (free, needs API key) | Small — 1 hr |
| Microsoft Q&A question count | Web scrape of learn.microsoft.com/answers filtered to DSI tags | Small — 1 hr |
| Automated weekly pulse report | Cron job / scheduled task that runs all Tier 1 + Tier 3 scripts, generates markdown, drops in Obsidian | Medium — half day to wire together |
| Sentiment scoring on articles | Python script with a simple LLM call to classify each article | Small — uses existing AI |
| New article alerts | Scheduled web search, diff against previous week's results | Small — 1 hr |

**Coverage: ~10 signals. These make the pulse automated and quantitative.**

---

## Tier 4: Probably Can't Get Programmatically

| Signal | Why Not | Workaround |
|---|---|---|
| Seller pitch count (CRM) | Lives in Dynamics/Salesforce, no API access from here | Ask sales ops for a monthly export |
| Win/loss data | Sales-owned, likely in a CRM or SharePoint list | Ask competitive intelligence team |
| Customer advisory board sentiment | Qualitative, from meetings | You already attend these — log notes |
| Partner blog/webinar count | No central registry of partner content | Manual tracking or ask partner team |
| CSAT / NPS scores | Usually in a survey tool (Qualtrics, etc.) | Ask CX team for monthly export |
| Gartner/Forrester analyst ratings | Paywalled, no API | Manual check when reports publish |
| Churn / de-provisioning data | May be in Kusto (moves to Tier 2 if so) | Check with eng if this is telemetry'd |
| Learn page unique visitors + time on page | Microsoft internal Learn analytics, likely no external API | Ask the Learn content team |

**Coverage: ~8 signals. These require human relationships, not code.**

---

## Summary

| Tier | Signals | Status |
|---|---|---|
| **1: Right now** | 9 | Running — first pulse done today |
| **2: With Kusto auth** | 9 | Monday — get cluster URL, connect via Azure CLI |
| **3: With scripts** | 10 | Build over 1-2 sessions — Python + APIs |
| **4: Manual/human** | 8 | Monthly asks to other teams |

**Total addressable signals: ~36**
**Automatable: ~28 (Tiers 1-3)**
**Manual: ~8 (Tier 4)**

### Recommended Build Order
1. **Monday:** Connect Kusto → unlock Tier 2 (biggest value)
2. **This week:** Install Python + build Google Trends + Reddit + YouTube scripts → unlock core Tier 3
3. **Next week:** Wire into automated weekly pulse → one command generates full report
4. **Ongoing:** Collect Tier 4 manually, log in Obsidian monthly

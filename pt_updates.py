import os
import feedparser
import requests
from datetime import datetime, timedelta
from html import unescape
import re

# ── Telegram config ──────────────────────────────────────────────────────────

TELEGRAM_BOT_TOKEN = os.environ[“TELEGRAM_BOT_TOKEN_PT”]
TELEGRAM_CHAT_ID   = os.environ[“TELEGRAM_CHAT_ID_PT”]

# ── RSS / PubMed feed sources by topic ──────────────────────────────────────

FEEDS = {
“🏛️ APTA News”: [
“https://www.apta.org/feed/”,
“https://www.apta.org/news/feed/”,
],
“📚 Journals (JOSPT / PTJ)”: [
“https://www.jospt.org/action/showFeed?type=etoc&feed=rss&jc=jospt”,
“https://academic.oup.com/rss/site_6030/advanceAccess.xml”,
],
“📋 Clinical Guidelines & Scope of Practice”: [
“https://pubmed.ncbi.nlm.nih.gov/rss/search/?term=physical+therapy+clinical+practice+guideline&format=rss&limit=5”,
“https://pubmed.ncbi.nlm.nih.gov/rss/search/?term=physiotherapy+rehabilitation+guideline&format=rss&limit=5”,
“https://pubmed.ncbi.nlm.nih.gov/rss/search/?term=physical+therapist+assistant+scope+practice&format=rss&limit=5”,
],
“🏃 Return to Sport”: [
“https://pubmed.ncbi.nlm.nih.gov/rss/search/?term=return+to+sport+rehabilitation&format=rss&limit=5”,
“https://pubmed.ncbi.nlm.nih.gov/rss/search/?term=return+to+play+physical+therapy&format=rss&limit=5”,
“https://www.sciencedaily.com/rss/health_medicine/sports_medicine.xml”,
],
“🧠 Pain Science & Pain Neuroscience”: [
“https://pubmed.ncbi.nlm.nih.gov/rss/search/?term=pain+neuroscience+education+rehabilitation&format=rss&limit=5”,
“https://pubmed.ncbi.nlm.nih.gov/rss/search/?term=chronic+pain+physical+therapy+treatment&format=rss&limit=5”,
“https://www.sciencedaily.com/rss/health_medicine/pain_and_anxiety.xml”,
],
“🤖 AI in Physical Therapy”: [
“https://pubmed.ncbi.nlm.nih.gov/rss/search/?term=artificial+intelligence+rehabilitation&format=rss&limit=5”,
“https://pubmed.ncbi.nlm.nih.gov/rss/search/?term=machine+learning+physical+therapy+outcomes&format=rss&limit=5”,
],
“💉 Dry Needling”: [
“https://pubmed.ncbi.nlm.nih.gov/rss/search/?term=dry+needling+trigger+point&format=rss&limit=5”,
“https://pubmed.ncbi.nlm.nih.gov/rss/search/?term=intramuscular+stimulation+dry+needling&format=rss&limit=5”,
],
“📊 Evidence-Based Outcome Measures”: [
“https://pubmed.ncbi.nlm.nih.gov/rss/search/?term=outcome+measures+rehabilitation+validity&format=rss&limit=5”,
“https://pubmed.ncbi.nlm.nih.gov/rss/search/?term=patient+reported+outcomes+physical+therapy&format=rss&limit=5”,
],
“🙌 Manual Therapy”: [
“https://pubmed.ncbi.nlm.nih.gov/rss/search/?term=manual+therapy+randomized+controlled+trial&format=rss&limit=5”,
“https://pubmed.ncbi.nlm.nih.gov/rss/search/?term=joint+mobilization+manipulation+rehabilitation&format=rss&limit=5”,
],
“💪 Blood Flow Restriction (BFR)”: [
“https://pubmed.ncbi.nlm.nih.gov/rss/search/?term=blood+flow+restriction+rehabilitation&format=rss&limit=5”,
“https://pubmed.ncbi.nlm.nih.gov/rss/search/?term=occlusion+training+muscle+strength&format=rss&limit=5”,
],
“🌐 Physiopedia & Science Daily”: [
“https://www.physio-pedia.com/feed/”,
“https://www.sciencedaily.com/rss/health_medicine/physical_therapy.xml”,
],
}

MAX_ITEMS_PER_TOPIC = 5   # cap per section
RECENCY_DAYS        = 7   # only show items from the last 7 days

# ── Helpers ───────────────────────────────────────────────────────────────────

def clean_html(text: str) -> str:
text = re.sub(r”<[^>]+>”, “”, text or “”)
text = unescape(text)
text = re.sub(r”\s+”, “ “, text).strip()
return text

def is_recent(entry) -> bool:
for attr in (“published_parsed”, “updated_parsed”):
t = getattr(entry, attr, None)
if t:
pub = datetime(*t[:6])
return pub >= datetime.utcnow() - timedelta(days=RECENCY_DAYS)
return True  # no date → include anyway

def fetch_items_from_feeds(label: str, urls: list[str]) -> list[dict]:
“”“Fetch one or more RSS feeds for a topic and return deduplicated recent items.”””
seen_titles = set()
items = []

```
for url in urls:
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            if not is_recent(entry):
                continue
            title = clean_html(entry.get("title", "No title"))
            if title in seen_titles:
                continue
            seen_titles.add(title)

            summary = clean_html(entry.get("summary", ""))
            # Trim to ~400 chars at a sentence boundary where possible
            if len(summary) > 400:
                cut = summary[:400].rfind(". ")
                summary = summary[: cut + 1] if cut > 200 else summary[:400] + "…"

            link = entry.get("link", "")
            items.append({"title": title, "summary": summary, "link": link})

            if len(items) >= MAX_ITEMS_PER_TOPIC:
                return items
    except Exception as e:
        print(f"  ⚠️  Error fetching [{label}] from {url}: {e}")

return items
```

# ── Message builder ───────────────────────────────────────────────────────────

def build_message(all_items: dict) -> str:
today = datetime.now().strftime(”%B %d, %Y”)
lines = [
“🩺 *PT Professional Updates*”,
f”*Week of {today}*”,
“”,
]

```
link_index = []   # collect (title, url) for bottom reference list
any_content = False

for label, items in all_items.items():
    lines.append(f"*{label}*")
    if not items:
        lines.append("  _No new updates this week for this topic._")
    else:
        any_content = True
        for item in items:
            lines.append(f"• *{item['title']}*")
            if item["summary"]:
                lines.append(f"  {item['summary']}")
            if item["link"]:
                link_index.append((item["title"], item["link"]))
    lines.append("")

if not any_content:
    lines.append("_No new updates found across all topics this week. Check back next Monday!_\n")

# ── Links section at bottom ──────────────────────────────────────────────
if link_index:
    lines.append("─────────────────────")
    lines.append("🔗 *Links*")
    for i, (title, url) in enumerate(link_index, 1):
        short_title = title[:60] + "…" if len(title) > 60 else title
        lines.append(f"{i}. [{short_title}]({url})")
    lines.append("")

lines += [
    "─────────────────────",
    "📌 *Quick References*",
    "• [APTA](https://www.apta.org)  |  [JOSPT](https://www.jospt.org)  |  [PTJ](https://academic.oup.com/ptj)",
    "• [PubMed PT Search](https://pubmed.ncbi.nlm.nih.gov/?term=physical+therapy)  |  [Physiopedia](https://www.physio-pedia.com)",
]

return "\n".join(lines)
```

# ── Telegram sender ───────────────────────────────────────────────────────────

def send_telegram(text: str) -> None:
“”“Send message to Telegram, splitting if over 4096 chars.”””
url = f”https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage”
chunk_size = 4000
chunks = [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]

```
for idx, chunk in enumerate(chunks, 1):
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": chunk,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }
    resp = requests.post(url, json=payload, timeout=30)
    if not resp.ok:
        print(f"  ❌ Telegram error {resp.status_code}: {resp.text}")
        resp.raise_for_status()
    else:
        print(f"  ✅ Chunk {idx}/{len(chunks)} sent.")
```

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
print(f”[{datetime.now()}] PT Updates bot starting…”)

```
all_items = {}
for label, urls in FEEDS.items():
    print(f"  Fetching: {label}")
    all_items[label] = fetch_items_from_feeds(label, urls)

message = build_message(all_items)
print("\n── Preview (first 600 chars) ──────────────────────")
print(message[:600])
print("───────────────────────────────────────────────────\n")

send_telegram(message)
print(f"[{datetime.now()}] Done.")
```

if **name** == “**main**”:
main()

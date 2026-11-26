import os
import json
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

# 6 Micro Sectors & Google News RSS Search Queries
SECTOR_CONFIGS = [
    {"id": "ai-chips", "title": "AI & Chips", "query": "AI semiconductors NVIDIA HBM foundry"},
    {"id": "rates-bonds", "title": "Rates & Bonds", "query": "Federal Reserve Treasury yields bond market"},
    {"id": "power-grid", "title": "Power & Grid", "query": "data center power grid electricity transformer utility"},
    {"id": "biotech", "title": "Biotech", "query": "biotech pharma FDA clinical trial M&A"},
    {"id": "quantum", "title": "Quantum", "query": "quantum computing qubit cryptography"},
    {"id": "defense", "title": "Defense", "query": "defense aerospace military drone Pentagon contracts"}
]

def fetch_google_news_rss(query, limit=4):
    """Fetch top 4 English headlines from Google News RSS without external dependencies."""
    encoded_query = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded_query}+when:2d&hl=en-US&gl=US&ceid=US:en"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})

    items = []
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            xml_data = resp.read()
        root = ET.fromstring(xml_data)
        for item in root.findall("./channel/item")[:limit]:
            raw_title = item.findtext("title") or ""
            link = item.findtext("link") or "https://news.google.com"
            source_el = item.find("source")
            source = source_el.text if source_el is not None else "Global Wire"

            # Strip trailing " - Source Name" from Google News titles
            clean_title = raw_title.rsplit(" - ", 1)[0].strip()
            items.append({
                "title": clean_title,
                "url": link,
                "source": source
            })
    except Exception as e:
        print(f"[WARN] RSS fetch failed for '{query}': {e}")

    while len(items) < limit:
        items.append({
            "title": f"Monitoring latest {query.split()[0]} institutional developments",
            "url": "https://news.google.com",
            "source": "ee Wire"
        })
    return items

def generate_ai_thesis(sector_title, headlines, api_key):
    """Generate a 3-sentence institutional AI briefing via Gemini API (REST)."""
    if not api_key:
        return (
            f"Institutional flows in {sector_title} remain anchored around supply-chain bottlenecks and capital allocation discipline. "
            f"Recent headlines highlight shifting pricing power and policy sensitivity across market leaders. "
            f"Monitor upcoming macro rate prints for near-term valuation multiple expansion or compression."
        )

    headline_bullets = "\n".join([f"- {h['title']}" for h in headlines])
    prompt = (
        f"You are an institutional macro-equity strategist writing a concise 3-sentence briefing for the '{sector_title}' sector.\n"
        f"Based on today's headlines below, write exactly 3 crisp, analytical sentences explaining the core structural bottleneck, "
        f"capital flow trend, and macro rate/liquidity sensitivity. Do not use bullet points or markdown.\n\n"
        f"Headlines:\n{headline_bullets}"
    )

    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 180}
    }).encode("utf-8")

    req = urllib.request.Request(endpoint, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            return " ".join(text.split())
    except Exception as e:
        print(f"[WARN] Gemini API fallback for '{sector_title}': {e}")
        return (
            f"Capital allocation across {sector_title} continues to favor operators with durable pricing power and backlog visibility. "
            f"Near-term sector dispersion reflects evolving rate expectations and physical supply constraints."
        )

def main():
    kst = timezone(timedelta(hours=9))
    now_kst = datetime.now(kst)
    updated_at = now_kst.strftime("%b %d · %H:%M KST")
    month_label = now_kst.strftime("%b %Y").upper()

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()

    # Load existing macroEvents if data.json exists so custom macro edits are preserved
    existing_macro = []
    if os.path.exists("data.json"):
        try:
            with open("data.json", "r", encoding="utf-8") as f:
                old = json.load(f)
                existing_macro = old.get("macroEvents", [])
        except Exception:
            pass

    updated_sectors = []
    for idx, cfg in enumerate(SECTOR_CONFIGS):
        print(f"Syncing sector: {cfg['title']}...")
        news_items = fetch_google_news_rss(cfg["query"], limit=4)
        thesis = generate_ai_thesis(cfg["title"], news_items, api_key)
        updated_sectors.append({
            "id": cfg["id"],
            "title": cfg["title"],
            "active": True,
            "isFresh": idx < 3,
            "news": news_items,
            "thesis": thesis
        })

    output = {
        "monthLabel": month_label,
        "updatedAt": updated_at,
        "macroEvents": existing_macro,
        "sectors": updated_sectors
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"[OK] data.json updated successfully at {updated_at}")

if __name__ == "__main__":
    main()

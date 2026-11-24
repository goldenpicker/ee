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
    
    articles = []
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            xml_data = resp.read()
        root = ET.fromstring(xml_data)
        for item in root.findall("./channel/item")[:limit]:
            raw_title = item.findtext("title", default="").strip()
            link = item.findtext("link", default="https://news.google.com").strip()
            source = item.findtext("source", default="Google News").strip()
            
            # Clean trailing " - Source Name" from Google News RSS title
            if " - " in raw_title:
                clean_title = raw_title.rsplit(" - ", 1)[0].strip()
            else:
                clean_title = raw_title

            articles.append({
                "title": clean_title,
                "url": link,
                "source": source
            })
    except Exception as e:
        print(f"[RSS Error] {query}: {e}")
    return articles

def generate_ai_briefing(sector_title, articles, api_key):
    """Call Gemini API (Free Tier) to synthesize a crisp 3-sentence institutional thesis."""
    if not api_key or not articles:
        return f"Institutional capital flows in {sector_title} remain anchored around supply-chain bottlenecks, capex durability, and rate-path sensitivity."

    headlines_text = "\n".join([f"- {a['title']} ({a['source']})" for a in articles])
    prompt = (
        f"You are a senior macro-equity strategist writing a concise briefing for '{sector_title}'. "
        f"Based strictly on these 4 headlines:\n{headlines_text}\n\n"
        f"Write a sharp, institutional 2-to-3 sentence synthesis (max 45 words total). "
        f"No bullet points, no markdown, no intro fluff. Focus on bottlenecks, pricing power, or rate sensitivity."
    )

    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 120}
    }).encode("utf-8")

    req = urllib.request.Request(endpoint, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
            return text.replace("\n", " ")
    except Exception as e:
        print(f"[Gemini API Error] {sector_title}: {e}")
        return f"Market focus in {sector_title} centers on supply constraints and earnings durability amid evolving macro liquidity."

def main():
    kst = timezone(timedelta(hours=9))
    now_kst = datetime.now(kst)
    updated_at = now_kst.strftime("%b %d").upper()  # e.g., "NOV 24"
    month_label = now_kst.strftime("%b %Y").upper() # e.g., "NOV 2026"
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()

    # Load existing data.json to preserve manually curated macroEvents
    existing_data = {}
    if os.path.exists("data.json"):
        with open("data.json", "r", encoding="utf-8") as f:
            existing_data = json.load(f)

    updated_sectors = []
    for idx, cfg in enumerate(SECTOR_CONFIGS):
        print(f"Syncing sector: {cfg['title']}...")
        news_items = fetch_google_news_rss(cfg["query"], limit=4)
        thesis = generate_ai_briefing(cfg["title"], news_items, api_key)

        updated_sectors.append({
            "id": cfg["id"],
            "title": cfg["title"],
            "active": True,
            "isFresh": len(news_items) > 0 and idx < 3, # Highlight top 3 active movers
            "news": news_items,
            "thesis": thesis
        })

    output = {
        "monthLabel": existing_data.get("monthLabel", month_label),
        "updatedAt": updated_at,
        "macroEvents": existing_data.get("macroEvents", []),
        "sectors": updated_sectors
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"Successfully updated data.json at {updated_at} KST.")

if __name__ == "__main__":
    main()

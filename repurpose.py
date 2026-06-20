import os
import sys
import json
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv(override=True)

ZERNIO_BASE = "https://zernio.com/api/v1"
ZERNIO_KEY = os.environ["ZERNIO_API_KEY"]
openai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

ZERNIO_HEADERS = {
    "Authorization": f"Bearer {ZERNIO_KEY}",
    "Content-Type": "application/json",
}


# ── 1. Scrape Medium ────────────────────────────────────────────────────────

def scrape_medium(url: str) -> tuple[str, str]:
    # Try Medium's unofficial JSON API first (more reliable than HTML scraping)
    json_url = url.split("?")[0] + "?format=json"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://medium.com/",
    }
    resp = requests.get(json_url, headers=headers, timeout=15)

    if resp.status_code == 200 and resp.text.startswith("])}while(1);</p>"):
        raw = resp.text[len("])}while(1);</p>"):].strip()
        data = json.loads(raw)
        post = data["payload"]["value"]
        title = post.get("title", "Article")
        paragraphs = post.get("content", {}).get("bodyModel", {}).get("paragraphs", [])
        body = "\n".join(p["text"] for p in paragraphs if p.get("text"))
        return title, body[:5000]

    # Fallback: HTML scraping with realistic browser headers
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    title_tag = soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else "Article"

    article = soup.find("article") or soup.find("div", {"class": "meteredContent"})
    tags = article.find_all(["p", "h1", "h2", "h3"]) if article else soup.find_all("p")
    body = "\n".join(t.get_text(strip=True) for t in tags if t.get_text(strip=True))

    return title, body[:5000]


# ── 2. Generate posts with GPT-4o ──────────────────────────────────────────

def generate_posts(title: str, content: str) -> dict:
    prompt = f"""You are a social media expert. Based on the article below, create 3 platform-specific posts.

Article Title: {title}
Article Content:
{content}

Return ONLY valid JSON with this exact structure (no markdown, no explanation):
{{
  "linkedin": "Professional post max 1200 chars. Use line breaks. Add 3-5 hashtags at the end. Highlight 2-3 key insights.",
  "twitter": "Punchy tweet max 270 chars. Hook in the first line. Include 2 hashtags.",
  "reddit": {{
    "title": "Compelling Reddit post title max 300 chars. No clickbait.",
    "body": "Conversational Reddit body 200-400 words. Add real value. NO hashtags. Reference the article naturally."
  }}
}}"""

    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    raw = response.choices[0].message.content.strip()

    # Strip markdown code fences if GPT wraps the JSON anyway
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


# ── 3. Zernio helpers ──────────────────────────────────────────────────────

def get_accounts() -> dict[str, str]:
    """Return {platform_name: account_id} for all connected accounts."""
    resp = requests.get(f"{ZERNIO_BASE}/accounts", headers=ZERNIO_HEADERS, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    print(f"[DEBUG] Zernio /accounts response: {json.dumps(data, indent=2)[:500]}")
    if isinstance(data, list):
        accounts = data
    elif isinstance(data, dict):
        accounts = data.get("data") or data.get("accounts") or data.get("items") or []
    else:
        accounts = []
    return {acc["platform"].lower(): acc["_id"] for acc in accounts}


def schedule_post(content: str, platform: str, account_id: str, hours_from_now: int) -> dict:
    scheduled = (datetime.now(timezone.utc) + timedelta(hours=hours_from_now)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    payload = {
        "content": content,
        "platforms": [{"platform": platform, "accountId": account_id}],
        "scheduledFor": scheduled,
        "timezone": "UTC",
    }
    resp = requests.post(f"{ZERNIO_BASE}/posts", json=payload, headers=ZERNIO_HEADERS, timeout=10)
    resp.raise_for_status()
    return resp.json()


# ── 4. Main ────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("Usage: python repurpose.py <medium_url>")
        sys.exit(1)

    url = sys.argv[1]

    # --- Step 1: Scrape ---
    print(f"\n Scraping: {url}")
    title, body = scrape_medium(url)
    print(f" Title   : {title}")
    print(f" Content : {len(body)} chars extracted\n")

    # --- Step 2: Generate ---
    print(" Generating posts with GPT-4o...")
    posts = generate_posts(title, body)

    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("[LinkedIn]\n" + posts["linkedin"])
    print("\n[Twitter]\n" + posts["twitter"])
    print(f"\n[Reddit]\nTitle: {posts['reddit']['title']}\n{posts['reddit']['body']}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

    # --- Step 3: Zernio ---
    print(" Fetching Zernio accounts...")
    accounts = get_accounts()
    print(f" Connected: {list(accounts.keys())}\n")

    # Stagger posts across the day (1h, 4h, 8h from now)
    schedule = [
        ("linkedin", posts["linkedin"], 1),
        ("twitter", posts["twitter"], 4),
        ("reddit", f"{posts['reddit']['title']}\n\n{posts['reddit']['body']}", 8),
    ]

    scheduled = 0
    for platform, content, offset in schedule:
        if platform not in accounts:
            print(f"  ✗ {platform.capitalize()} — no account connected, skipping")
            continue
        result = schedule_post(content, platform, accounts[platform], offset)
        print(f"  ✓ {platform.capitalize()} scheduled in {offset}h — id: {result.get('_id')}")
        scheduled += 1

    print(f"\n Done! {scheduled}/3 posts scheduled.")


if __name__ == "__main__":
    main()

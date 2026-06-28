# Social Media Automation Script — Repurpose Medium Articles to LinkedIn, Twitter & Reddit

Automatically turn any Medium article into platform-optimized social media posts and schedule them — powered by GPT-4o and [Zernio](https://zernio.com).

## Demo Video

[![Watch the demo](https://img.youtube.com/vi/SUHQCamX2QU/maxresdefault.jpg)](https://youtu.be/SUHQCamX2QU)

## What It Does

1. **Scrapes** a Medium article (title + body)
2. **Generates** tailored posts for LinkedIn, Twitter and Reddit using GPT-4o
3. **Schedules** the posts via the [Zernio](https://zernio.com) API, staggered across the day

## Requirements

- Python 3.10+
- An [OpenAI API key](https://platform.openai.com/api-keys) (GPT-4o access)
- A [Zernio](https://zernio.com) account with LinkedIn, Twitter and/or Reddit connected

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure your keys
cp .env.example .env
# Edit .env and fill in OPENAI_API_KEY and ZERNIO_API_KEY
```

## Usage

```bash
python repurpose.py <medium_article_url>
```

**Example:**

```bash
python repurpose.py https://medium.com/@author/your-article-slug
```

### Output

```
Scraping: https://medium.com/...
Title   : The 10 Best Financial APIs for AI Coding Tools 2026
Content : 4821 chars extracted

Generating posts with GPT-4o...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[LinkedIn]  Professional post with key insights + hashtags
[Twitter]   Punchy hook tweet
[Reddit]    Title + conversational long-form body
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Fetching Zernio accounts...
✓ LinkedIn scheduled in 1h
✓ Twitter  scheduled in 4h
✓ Reddit   scheduled in 8h

Done! 3/3 posts scheduled.
```

## Environment Variables

| Variable | Description |
|---|---|
| `OPENAI_API_KEY` | Your OpenAI API key |
| `ZERNIO_API_KEY` | Your Zernio API key |

## Schedule Zernio to Auto-Post

Posts are scheduled via [Zernio](https://zernio.com) at:
- **+1 hour** — LinkedIn
- **+4 hours** — Twitter
- **+8 hours** — Reddit

Sign up at [zernio.com](https://zernio.com) and connect your social accounts to get your API key.

## Tech Stack

- [`openai`](https://pypi.org/project/openai/) — GPT-4o for content generation
- [`beautifulsoup4`](https://pypi.org/project/beautifulsoup4/) — Medium scraping
- [`requests`](https://pypi.org/project/requests/) — HTTP client
- [`python-dotenv`](https://pypi.org/project/python-dotenv/) — Environment variable management
- [Zernio](https://zernio.com) — Social media scheduling API

## License

MIT

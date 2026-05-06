"""
Screenshot Event Extractor
--------------------------
Reads screenshots from res/screenshots/, extracts SA event details via Groq vision,
and returns a list of event dicts compatible with the sa_events_scraper structure.
"""

import base64
import json
from pathlib import Path

import requests

import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Get API key
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found in environment variables")

print("Key loaded:", GROQ_API_KEY[:6] + "...")  # optional debug
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
SCREENSHOTS_DIR = Path("assets/screenshots")
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

PROMPT = (
    "This is a screenshot of a South African event listing (e.g. from Quicket, Computicket, "
    "Webtickets, a venue website, or a social media post). "
    "Extract the following fields: "
    "1. 'title': Full event name. "
    "2. 'date': Event date as shown (e.g. 'Saturday, 10 May 2026'). "
    "3. 'time': Start time (e.g. '19:00' or '7:30 PM'). "
    "4. 'location': Venue name (e.g. 'Loftus Versfeld', 'Joburg Theatre'). "
    "5. 'address': Full street address if visible, including suburb and city. Append ', South Africa'. "
    "6. 'price': Ticket price (e.g. 'R150', 'Free'). If multiple tiers, list the lowest. "
    "7. 'url': Ticket or event URL if visible, else ''. "
    "8. 'category': One of: Sports, Concert/Music, Festival, Comedy, Musical/Theatre, Other. "
    "If a field is not visible, use ''. "
    "Respond ONLY with JSON — no explanation, no markdown. "
    "Format: {\"title\":\"\",\"date\":\"\",\"time\":\"\",\"location\":\"\","
    "\"address\":\"\",\"price\":\"\",\"url\":\"\",\"category\":\"\"}"
)


def encode_image(path: Path) -> tuple[str, str]:
    suffix = path.suffix.lower()
    media_type = "image/jpeg" if suffix in (".jpg", ".jpeg") else "image/png"
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8"), media_type


def extract_json(raw_content: str) -> dict:
    """Extract the first valid JSON object from the model response."""
    # Strip markdown fences
    cleaned = raw_content.replace("```json", "").replace("```", "").strip()

    # Find first { ... } block
    start = cleaned.find("{")
    if start == -1:
        raise ValueError("No JSON object found in response")

    # Walk forward to find the matching closing brace
    depth = 0
    end = -1
    for i, ch in enumerate(cleaned[start:], start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i
                break

    if end == -1:
        raise ValueError("Unmatched braces in response")

    raw = cleaned[start:end + 1]
    parsed = json.loads(raw)
    return {k: ("" if v == "null" else str(v).strip()) for k, v in parsed.items()}


def extract_event_from_screenshot(image_path: Path) -> dict:
    b64, media_type = encode_image(image_path)

    payload = {
        "model": "meta-llama/llama-4-scout-17b-16e-instruct",
        "max_tokens": 500,
        "temperature": 0.1,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{media_type};base64,{b64}"},
                    },
                    {"type": "text", "text": PROMPT},
                ],
            }
        ],
    }

    response = requests.post(
        GROQ_API_URL,
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=60,
    )
    response.raise_for_status()

    raw_content = response.json()["choices"][0]["message"]["content"]
    data = extract_json(raw_content)

    return {
        "title":    data.get("title", ""),
        "date":     data.get("date", ""),
        "time":     data.get("time", ""),
        "location": data.get("location", ""),
        "address":  data.get("address", ""),
        "price":    data.get("price", "Check website"),
        "source":   "Screenshot",
        "url":      data.get("url", ""),
        "category": data.get("category", "Other"),
    }


def scrape_screenshots() -> list[dict]:
    """
    Entry point called by sa_events_scraper.scrape_all_sources().
    Returns a list of event dicts in the standard scraper format.
    """
    if not SCREENSHOTS_DIR.exists():
        print(f"[Screenshots] Directory not found: {SCREENSHOTS_DIR} — skipping")
        return []

    files = [
        f for f in sorted(SCREENSHOTS_DIR.iterdir())
        if f.suffix.lower() in IMAGE_EXTENSIONS
    ]

    if not files:
        print(f"[Screenshots] No images found in {SCREENSHOTS_DIR}")
        return []

    print(f"[Screenshots] Found {len(files)} image(s)")
    events = []

    for i, path in enumerate(files, 1):
        print(f"[Screenshots] [{i}/{len(files)}] {path.name} ...", end=" ", flush=True)
        try:
            event = extract_event_from_screenshot(path)
            if event["title"]:
                events.append(event)
                print(f"OK  ->  {event['title']} @ {event['location']}")
            else:
                print("skipped (no title extracted)")
        except Exception as e:
            print(f"FAILED — {e}")

    print(f"[Screenshots] Extracted {len(events)} event(s)")
    return events
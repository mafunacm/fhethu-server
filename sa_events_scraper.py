import json
import logging
import os
import time
import sys
from dataclasses import dataclass
from datetime import datetime
import re

from pathlib import Path
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout


# ---------------------------------------------
# LOGGING SETUP
# ---------------------------------------------

log = logging.getLogger("sa_events")
log.setLevel(logging.INFO)

if not log.handlers:
    _fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    _sh = logging.StreamHandler(sys.stdout)
    _sh.setFormatter(_fmt)
    log.addHandler(_sh)
    log.propagate = False


# ---------------------------------------------
# CONFIG
# ---------------------------------------------

CACHE_FILE = "cache_events.json"
OUTPUT_FILE = "sa_events.json"
CACHE_MAX_AGE_HOURS = 6


# ---------------------------------------------
# DATA MODEL
# ---------------------------------------------

@dataclass
class Event:
    title: str
    date: str
    location: str
    url: str
    price: str
    source: str
    time: str = ""
    category: str = "Other"
    address: str = ""


# ---------------------------------------------
# CACHE UTILITIES
# ---------------------------------------------

def is_cache_valid():
    if not os.path.exists(CACHE_FILE):
        return False
    age = time.time() - os.path.getmtime(CACHE_FILE)
    return age < CACHE_MAX_AGE_HOURS * 3600


def load_cache():
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_cache(events):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(events, f, indent=2)


def serialize_event(event):
    cleaned = parse_event_title(event.title)

    # Only override fields that the scraper didn't already populate
    title   = cleaned["title"]   or event.title.strip()
    date    = cleaned["date"]    or event.date.strip()
    ev_time = cleaned["time"]    or event.time.strip()
    venue   = cleaned["venue"]   or event.location.strip()

    # Geocode if we have a venue but no address yet
    address = event.address.strip()
    if venue and (not address or address == "Check website"):
        address = geocode_venue(venue)

    return {
        "title":    title,
        "date":     date,
        "time":     ev_time,
        "location": venue,
        "address":  address,
        "price":    event.price.strip(),
        "source":   event.source,
        "url":      event.url,
        "category": event.category,
    }


# ---------------------------------------------
# TITLE PARSER
# ---------------------------------------------

# Months used for date detection
_MONTHS = r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
_DAYS   = r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)"

# Pattern: "Runs from", "Runs until", "From", etc.
_RUNS_FROM = re.compile(r"Runs\s+from\s*", re.IGNORECASE)

# Time pattern: 19:00 or 7:30 PM
_TIME_RE = re.compile(r"\b(\d{1,2}:\d{2}(?:\s*[APap][Mm])?)\b")

# Date pattern: Tuesday, May 5, 2026  OR  5 May 2026  OR  May 5 2026
_DATE_RE = re.compile(
    rf"\b(?:{_DAYS},?\s*)?{_MONTHS}\s+\d{{1,2}},?\s*\d{{4}}"
    rf"|\b\d{{1,2}}\s+{_MONTHS}\s+\d{{4}}"
    rf"|\b(?:{_DAYS},?\s*)?\d{{1,2}}\s+{_MONTHS}\s+\d{{4}}",
    re.IGNORECASE,
)


def _split_camel_concat(text: str) -> str:
    """
    Insert a newline at camelCase and digit→uppercase boundaries.
    Fixes concatenation like 'AfricaThe', 'MusicalElkanah', '202609:00'.
    """
    # lowercase → UPPERCASE: "AfricaThe" → "Africa\nThe"
    text = re.sub(r"([a-z])([A-Z])", r"\1\n\2", text)
    # digit → UPPERCASE: "2026The" → "2026\nThe"
    text = re.sub(r"(\d)([A-Z])", r"\1\n\2", text)
    return text


def parse_event_title(raw: str) -> dict:
    """
    Given a raw messy title string, extract:
      title, venue, date, time
    Returns a dict with those four keys (empty string if not found).
    """
    result = {"title": "", "venue": "", "date": "", "time": ""}

    if not raw or not raw.strip():
        return result

    # 1. Extract and strip time
    time_match = _TIME_RE.search(raw)
    if time_match:
        result["time"] = time_match.group(1).strip()
        raw = raw[:time_match.start()] + raw[time_match.end():]

    # 2. Extract and strip date
    date_match = _DATE_RE.search(raw)
    if date_match:
        result["date"] = date_match.group(0).strip()
        raw = raw[:date_match.start()] + raw[date_match.end():]

    # 3. Remove "Runs from / Runs until / From" boilerplate
    raw = _RUNS_FROM.sub("", raw).strip()

    # 4. Split on explicit pipe "|" first
    if "|" in raw:
        parts = [p.strip() for p in raw.split("|")]
        result["title"] = parts[0].strip()
        if len(parts) > 1:
            # Remaining parts may still be camel-concatenated
            remainder = " | ".join(parts[1:])
            remainder = _split_camel_concat(remainder)
            sub_parts = [p.strip() for p in remainder.split("\n") if p.strip()]
            result["venue"] = sub_parts[0] if sub_parts else ""
        return result

    # 5. No pipe — use camelCase split to find boundaries
    split_text = _split_camel_concat(raw)
    lines = [l.strip() for l in split_text.split("\n") if l.strip()]

    if lines:
        result["title"] = lines[0]
    if len(lines) > 1:
        result["venue"] = lines[1]

    return result


# ---------------------------------------------
# GEOCODER (Nominatim / OpenStreetMap)
# ---------------------------------------------

_geocode_cache: dict[str, str] = {}

def geocode_venue(venue: str, country_hint: str = "South Africa") -> str:
    """
    Look up a venue address via Nominatim (OpenStreetMap).
    Returns a formatted address string, or empty string on failure.
    Caches results in-memory to avoid repeat requests.
    """
    key = f"{venue}, {country_hint}"
    if key in _geocode_cache:
        return _geocode_cache[key]

    try:
        params = {
            "q": key,
            "format": "json",
            "limit": 1,
            "countrycodes": "za",
        }
        headers = {"User-Agent": "SAEventsApp/1.0 (contact@saevents.local)"}
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params=params,
            headers=headers,
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()

        if data:
            address = data[0].get("display_name", "")
            _geocode_cache[key] = address
            time.sleep(1)  # Nominatim rate limit: 1 req/sec
            return address
    except Exception as e:
        log.warning(f"[Geocode] failed for '{venue}': {e}")

    _geocode_cache[key] = ""
    return ""




# ---------------------------------------------
# BROWSER UTILITIES
# ---------------------------------------------

def safe_goto(page, url, wait_time=3):
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        time.sleep(wait_time)
        return True
    except Exception as e:
        log.error(f"[goto error] {e}")
        return False


def scroll(page, pause_time=1):
    """Scroll down page to load lazy content"""
    try:
        page.evaluate("""
            async () => {
                const distance = 300;
                const delay = 100;
                while (document.scrollingElement.scrollTop + window.innerHeight < document.scrollingElement.scrollHeight) {
                    document.scrollingElement.scrollBy(0, distance);
                    await new Promise(resolve => { setTimeout(resolve, delay) });
                }
            }
        """)
        time.sleep(pause_time)
    except:
        pass


_SCREENSHOT_DIR = Path("src/main/assets/screenshots")

def take_screenshot(page, source: str, index: int = 0, viewport_shots: int = 6):
    """
    Scroll through the page and save a viewport-sized screenshot at each
    position. More shots = more events captured for Groq extraction.
    viewport_shots: how many evenly-spaced screenshots to take per page.
    """
    try:
        _SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        src = source.lower().replace(" ", "_")
        ts = int(time.time())

        total_height = page.evaluate("document.body.scrollHeight")
        viewport_height = page.evaluate("window.innerHeight")
        step = max(total_height // viewport_shots, viewport_height)

        shot_count = 0
        y = 0
        while y < total_height:
            page.evaluate(f"window.scrollTo(0, {y})")
            time.sleep(0.4)
            filename = _SCREENSHOT_DIR / f"{src}_{index}_{ts}_{shot_count}.png"
            page.screenshot(path=str(filename))
            shot_count += 1
            y += step

        log.info(f"[Screenshot] {source} page {index} — {shot_count} shots saved")
    except Exception as e:
        log.warning(f"[Screenshot] failed for {source}: {e}")


# ---------------------------------------------
# SITE-SPECIFIC SCRAPERS
# ---------------------------------------------

def scrape_quicket(page):
    """Scrape Quicket.co.za events"""
    events = []
    log.info("[Quicket] scraping...")

    if not safe_goto(page, "https://www.quicket.co.za/events", wait_time=5):
        return events

    scroll(page, pause_time=2)
    take_screenshot(page, "quicket")
    soup = BeautifulSoup(page.content(), "lxml")

    event_cards = soup.select("div.event-card, article.event, div[class*='event']")

    for card in event_cards:
        try:
            title_elem = card.select_one("h3, h4, .event-title, .title")
            date_elem = card.select_one(".date, .event-date, time")
            venue_elem = card.select_one(".venue, .location, .event-location")
            price_elem = card.select_one(".price, .event-price")
            link_elem = card.select_one("a[href*='/events/']")

            if title_elem and link_elem:
                title = title_elem.get_text(strip=True)
                url = link_elem.get("href")
                if not url.startswith("http"):
                    url = "https://www.quicket.co.za" + url

                date = date_elem.get_text(strip=True) if date_elem else ""
                location = venue_elem.get_text(strip=True) if venue_elem else ""
                price = price_elem.get_text(strip=True) if price_elem else "Check website"

                events.append(Event(
                    title=title,
                    date=date,
                    location=location,
                    url=url,
                    price=price,
                    source="Quicket"
                ))
        except:
            continue

    if not events:
        for a in soup.select("a[href*='/events/'][href*='-']"):
            title = a.get_text(strip=True)
            if title and len(title) > 5:
                url = a.get("href")
                if not url.startswith("http"):
                    url = "https://www.quicket.co.za" + url

                events.append(Event(
                    title=title,
                    date="Check website",
                    location="Check website",
                    url=url,
                    price="Check website",
                    source="Quicket"
                ))

    log.info(f"[Quicket] found {len(events)} events")
    return events


def scrape_computicket(page):
    """Scrape Computicket.com events — JS-rendered, wait for cards to load"""
    events = []
    log.info("[Computicket] scraping...")

    urls = [
        "https://computicket.com/event/list",
        "https://computicket.com/event/list?stateprovince=Gauteng",
    ]

    seen_urls = set()

    for target_url in urls:
        try:
            page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
            # Wait for at least one event card/link to appear
            try:
                page.wait_for_selector(
                    "a[href*='/event/'], [class*='event'], [class*='card']",
                    timeout=15000
                )
            except:
                log.warning(f"[Computicket] timeout waiting for events at {target_url}")
            time.sleep(3)
            scroll(page, pause_time=2)
            take_screenshot(page, "computicket", urls.index(target_url))
        except Exception as e:
            log.error(f"[Computicket] goto error: {e}")
            continue

        soup = BeautifulSoup(page.content(), "lxml")

        # Primary: structured event cards
        for item in soup.select("[class*='event-card'], [class*='EventCard'], [class*='event-item'], [class*='EventItem']"):
            try:
                title_elem = item.select_one("h2, h3, h4, [class*='title'], [class*='name']")
                date_elem  = item.select_one("[class*='date'], [class*='Date'], time")
                venue_elem = item.select_one("[class*='venue'], [class*='Venue'], [class*='location']")
                price_elem = item.select_one("[class*='price'], [class*='Price']")
                link_elem  = item.select_one("a[href*='/event/']") or item.find_parent("a")

                if not title_elem:
                    continue

                title = title_elem.get_text(strip=True)
                url = ""
                if link_elem:
                    url = link_elem.get("href", "")
                    if not url.startswith("http"):
                        url = "https://computicket.com" + url
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)

                events.append(Event(
                    title=title,
                    date=date_elem.get_text(strip=True) if date_elem else "Check website",
                    location=venue_elem.get_text(strip=True) if venue_elem else "Check website",
                    url=url,
                    price=price_elem.get_text(strip=True) if price_elem else "Check website",
                    source="Computicket"
                ))
            except:
                continue

        # Fallback: any event links on the page
        if not events:
            for a in soup.select("a[href*='/event/']"):
                text = a.get_text(strip=True)
                if not text or len(text) < 5:
                    continue
                if any(skip in text.lower() for skip in ["browse", "view all", "see more", "load more"]):
                    continue
                url = a.get("href", "")
                if not url.startswith("http"):
                    url = "https://computicket.com" + url
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                events.append(Event(
                    title=text,
                    date="Check website",
                    location="Check website",
                    url=url,
                    price="Check website",
                    source="Computicket"
                ))

    log.info(f"[Computicket] found {len(events)} events")
    return events


def scrape_ticketpro(page):
    """Scrape Ticketpro.co.za events"""
    events = []
    log.info("[Ticketpro] scraping...")

    urls = [
        "https://www.ticketpro.co.za/events?category=&q=&category_filter=music&date_filter=next_30_days&city=&min_price=&max_price=&featured_only=0&free_only=0",
        "https://www.ticketpro.co.za/events?category=&q=&category_filter=lifestyle&date_filter=next_30_days&city=&min_price=&max_price=&featured_only=0&free_only=0",
    ]

    for url in urls:
        if not safe_goto(page, url, wait_time=5):
            continue

        scroll(page, pause_time=3)
        take_screenshot(page, "ticketpro", urls.index(url))
        soup = BeautifulSoup(page.content(), "lxml")

        event_cards = soup.select("div[class*='event-card'], article[class*='event'], a[href*='/events/']")

        for card in event_cards:
            try:
                card_text = card.get_text(" ", strip=True)
                link = card.get("href") if card.name == "a" else card.select_one("a")

                if link:
                    href = link if isinstance(link, str) else link.get("href")
                    if not href.startswith("http"):
                        href = "https://www.ticketpro.co.za" + href

                    lines = [line.strip() for line in card_text.split("\n") if line.strip()]

                    title = lines[0] if lines else "Event"
                    date = ""
                    location = ""
                    price = "Check website"

                    for line in lines:
                        if any(month in line for month in ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]):
                            date = line
                            break

                    for line in lines:
                        if "•" in line:
                            parts = line.split("•")
                            if len(parts) > 1:
                                location = parts[1].strip()
                                break

                    for line in lines:
                        if "R" in line and any(char.isdigit() for char in line):
                            price = line
                            break

                    events.append(Event(
                        title=title,
                        date=date,
                        location=location,
                        url=href,
                        price=price,
                        source="Ticketpro"
                    ))
            except:
                continue

    log.info(f"[Ticketpro] found {len(events)} events")
    return events


def _parse_howler_link(a_tag) -> dict | None:
    """
    Howler renders each event as a single <a> tag whose text contains:
      "Title  Venue  Date  Price"
    We split on the unicode narrow no-break space (\u202f) that Howler
    uses as a separator, then fall back to double-space splitting.
    """
    text = a_tag.get_text(" ", strip=True)
    if not text or len(text) < 5:
        return None

    # Howler uses \u202f (narrow no-break space) as field separator
    parts = [p.strip() for p in text.split("\u202f") if p.strip()]

    # Fallback: split on 2+ spaces
    if len(parts) < 2:
        parts = [p.strip() for p in re.split(r"  +", text) if p.strip()]

    title    = parts[0] if len(parts) > 0 else text
    location = parts[1] if len(parts) > 1 else ""
    date     = parts[2] if len(parts) > 2 else ""
    price    = parts[3] if len(parts) > 3 else "Check website"

    # Clean up price: "From R100.00" → "R100.00", "Free" stays
    price = re.sub(r"^(From|Tickets)\s*", "", price).strip()
    if price == "R0.00":
        price = "Free"

    return {
        "title":    title,
        "location": location,
        "date":     date,
        "price":    price,
    }


def scrape_howler(page):
    """Scrape Howler.co.za events across multiple category pages"""
    events = []
    log.info("[Howler] scraping...")

    urls = [
        "https://www.howler.co.za/categories/51",  # Festival
        "https://www.howler.co.za/categories/30",  # Nightlife
        "https://www.howler.co.za/categories/6",   # Comedy
        "https://www.howler.co.za/categories/35",  # Arts & Theatre
        "https://www.howler.co.za/categories/17",  # Sports
    ]

    seen_urls = set()

    for target_url in urls:
        if not safe_goto(page, target_url, wait_time=5):
            continue

        scroll(page, pause_time=2)
        take_screenshot(page, "howler", urls.index(target_url))
        soup = BeautifulSoup(page.content(), "lxml")

        # Howler events are plain <a> tags linking to howler.co.za or subdomains
        for a in soup.select("a[href*='howler.co.za']"):
            try:
                url = a.get("href", "")
                if not url.startswith("http"):
                    url = "https://www.howler.co.za" + url

                # Skip nav/footer links
                if any(skip in url for skip in [
                    "/categories/", "/contact", "/terms", "/privacy",
                    "/legal", "/users/", "organisers.", "help."
                ]):
                    continue

                if url in seen_urls:
                    continue
                seen_urls.add(url)

                parsed = _parse_howler_link(a)
                if not parsed or not parsed["title"]:
                    continue

                events.append(Event(
                    title=parsed["title"],
                    date=parsed["date"],
                    location=parsed["location"],
                    url=url,
                    price=parsed["price"],
                    source="Howler"
                ))
            except:
                continue

    log.info(f"[Howler] found {len(events)} events")
    return events


def scrape_webtickets(page):
    """Scrape Webtickets.co.za events"""
    events = []
    log.info("[Webtickets] scraping...")

    urls = [
        "https://www.webtickets.co.za/v2/category.aspx?itemid=1184158&location=0&when=anytime",
        "https://www.webtickets.co.za/v2/category.aspx?itemid=1184163&location=0&when=anytime",
    ]

    seen_urls = set()

    for target_url in urls:
        if not safe_goto(page, target_url, wait_time=5):
            continue

        scroll(page, pause_time=2)
        take_screenshot(page, "webtickets", urls.index(target_url))
        soup = BeautifulSoup(page.content(), "lxml")

        for item in soup.select("div[class*='event'], a[href*='Event.aspx']"):
            try:
                text = item.get_text(strip=True)
                link = item.get("href") if item.name == "a" else item.select_one("a[href*='Event.aspx']")

                if link and text:
                    url = link if isinstance(link, str) else link.get("href")
                    if not url.startswith("http"):
                        url = "https://www.webtickets.co.za" + url
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)

                    events.append(Event(
                        title=text,
                        date="Check website",
                        location="Check website",
                        url=url,
                        price="Check website",
                        source="Webtickets"
                    ))
            except:
                continue

    log.info(f"[Webtickets] found {len(events)} events")
    return events


# ---------------------------------------------
# CATEGORIZATION
# ---------------------------------------------

def categorize_event(event):
    """Categorize events based on title, location, and other indicators."""
    # Sports sources are always Sports
    if event.source in ("SA Rugby", "SuperSport"):
        return "Sports"

    text = f"{event.title} {event.location}".lower()

    if any(kw in text for kw in ["musical", "theatre", "theater", "drama", "opera", "ballet"]):
        return "Musical/Theatre"
    elif any(kw in text for kw in ["concert", "live music", "jazz", "band", "dj", "music festival"]):
        return "Concert/Music"
    elif any(kw in text for kw in ["rugby", "soccer", "cricket", "match", "stadium", "bulls", "chiefs", "lions", "sharks", "psl", "premier league"]):
        return "Sports"
    elif any(kw in text for kw in ["comedy", "comedian", "stand up", "laugh"]):
        return "Comedy"
    elif any(kw in text for kw in ["festival", "fest", "carnival"]):
        return "Festival"
    else:
        return "Other"


# ---------------------------------------------
# SA GEO FILTER
# ---------------------------------------------

# SA cities, provinces, venues, and common abbreviations
SA_WHITELIST = {
    # Provinces
    "gauteng", "western cape", "eastern cape", "northern cape", "north west",
    "limpopo", "mpumalanga", "free state", "kwazulu-natal", "kzn",
    # Major cities & towns
    "johannesburg", "joburg", "jozi", "cape town", "durban", "pretoria",
    "tshwane", "ekurhuleni", "soweto", "sandton", "midrand", "centurion",
    "randburg", "roodepoort", "benoni", "boksburg", "germiston", "kempton park",
    "port elizabeth", "gqeberha", "east london", "bloemfontein", "polokwane",
    "nelspruit", "mbombela", "kimberley", "rustenburg", "witbank", "emalahleni",
    "pietermaritzburg", "pmb", "newcastle", "richards bay", "umhlanga",
    "stellenbosch", "paarl", "george", "mossel bay", "knysna", "hermanus",
    "springbok", "upington", "vryburg", "mahikeng", "mafikeng",
    # Venues / areas
    "fnb stadium", "loftus", "ellis park", "newlands", "kings park",
    "moses mabhida", "dhl newlands", "sun city", "emperors palace",
    "ticketpro dome", "jo'burg", "jhb", "pta", "cpt", "dbn",
    # Country identifiers
    "south africa", "south african", "s.a.", " sa ",
}

# Foreign country/city keywords — hard exclude
FOREIGN_BLACKLIST = {
    # Countries
    "china", "chinese", "beijing", "shanghai", "guangzhou", "shenzhen",
    "hong kong", "taiwan", "united states", "usa", "u.s.a", "new york",
    "los angeles", "chicago", "miami", "las vegas", "san francisco",
    "washington", "houston", "atlanta", "boston", "seattle",
    "uk", "united kingdom", "london", "manchester", "birmingham",
    "australia", "sydney", "melbourne", "brisbane",
    "canada", "toronto", "vancouver", "montreal",
    "germany", "berlin", "munich", "france", "paris",
    "japan", "tokyo", "osaka", "india", "mumbai", "delhi",
    "brazil", "sao paulo", "rio de janeiro", "argentina", "mexico",
    "uae", "dubai", "abu dhabi", "saudi", "qatar",
    "new zealand", "auckland", "amsterdam", "netherlands",
    "korea", "seoul", "singapore", "thailand", "bangkok",
    "italy", "rome", "milan", "spain", "madrid", "barcelona",
}

# URL domains that are SA-specific (trust their events unconditionally)
SA_TRUSTED_SOURCES = {"Quicket", "Computicket", "Ticketpro", "Howler", "Webtickets", "SA Rugby", "SuperSport"}


def is_sa_event(event: Event) -> bool:
    """
    Returns True if the event is likely South African.
    Logic:
    1. If source is a trusted SA platform AND location/title contain no foreign blacklist terms → keep.
    2. If any SA whitelist term is found in title/location/address → keep.
    3. If any foreign blacklist term is found → drop.
    4. If source is trusted SA platform and no geo info at all → keep (benefit of the doubt).
    5. Otherwise → drop.
    """
    text = f"{event.title} {event.location} {event.address}".lower()

    # Hard exclude on any foreign keyword
    if any(foreign in text for foreign in FOREIGN_BLACKLIST):
        return False

    # Explicit SA mention
    if any(sa in text for sa in SA_WHITELIST):
        return True

    # Trusted SA source with no geo info → keep
    if event.source in SA_TRUSTED_SOURCES and event.location in ("", "Check website"):
        return True

    # Trusted SA source with some location that passed blacklist → keep
    if event.source in SA_TRUSTED_SOURCES:
        return True

    return False


# ---------------------------------------------
# MAIN SCRAPER
# ---------------------------------------------

def scrape_all_sources():
    log.info("Starting comprehensive event scraping...")
    log.info("This will take time to properly extract all event details.")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        all_events = []

        scrapers = [
            ("Quicket", scrape_quicket),
            ("Computicket", scrape_computicket),
            ("Ticketpro", scrape_ticketpro),
            ("Howler", scrape_howler),
            ("Webtickets", scrape_webtickets),
        ]

        for name, scraper_func in scrapers:
            try:
                time.sleep(2)
                events = scraper_func(page)
                for event in events:
                    event.category = categorize_event(event)
                sa_events = [e for e in events if is_sa_event(e)]
                dropped = len(events) - len(sa_events)
                if dropped:
                    log.info(f"[{name}] dropped {dropped} non-SA events")
                for event in sa_events:
                    log.info(f"  [{name}] {event.title[:50]:<50} {event.url}")
                all_events.extend(sa_events)
            except Exception as e:
                log.error(f"[ERROR] {name}: {e}", exc_info=True)

        browser.close()

    # Serialize web-scraped events
    serialized = [serialize_event(event) for event in all_events]

    # Merge screenshot-extracted events
    try:
        from screenshot_extractor import scrape_screenshots
        screenshot_events = scrape_screenshots()
        log.info(f"[Screenshots] merging {len(screenshot_events)} event(s) into results")
        serialized.extend(screenshot_events)
    except ImportError:
        log.warning("[Screenshots] screenshot_extractor.py not found — skipping")
    except Exception as e:
        log.error(f"[Screenshots] ERROR: {e}", exc_info=True)

    return serialized


# ---------------------------------------------
# MAIN
# ---------------------------------------------

def main():
    force_refresh = "--refresh" in sys.argv

    if not force_refresh and is_cache_valid():
        log.info("Using cached data")
        events = load_cache()
    else:
        log.info("Scraping fresh data")
        events = scrape_all_sources()
        save_cache(events)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(events, f, indent=2)

    log.info(f"Total events found: {len(events)}")

    categories = {}
    for event in events:
        cat = event.get("category", "Other")
        categories[cat] = categories.get(cat, 0) + 1

    log.info("Events by category:")
    for cat, count in sorted(categories.items()):
        log.info(f"  {cat}: {count}")


if __name__ == "__main__":
    main()
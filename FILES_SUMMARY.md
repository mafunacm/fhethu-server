# File Summary

## Core System Files

### `main.py`
**Purpose**: Unified controller script
**What it does**:
- Checks cache validity
- Loads from cache OR runs scraper
- Saves events to `sa_events.json`
- Starts HTTP server (port 8000)
- Automatically opens browser

**Key Functions**:
- `is_cache_valid()` – Check cache freshness
- `load_cache()` – Load cached events
- `save_cache(events)` – Save to cache file
- `scrape_events()` – Scraper hook (tries importing sa_events_scraper)
- `get_events()` – Smart loader
- `save_output(events)` – Write to sa_events.json
- `start_server()` – Launch HTTP server
- `open_browser()` – Open browser to local URL

**Usage**:
```bash
python main.py
```

---

### `index.html`
**Purpose**: Event display page (runs in browser)
**What it does**:
- Loads `sa_events.json` via fetch
- Groups events by category
- Renders category filter buttons
- Displays event cards with all details
- Sorts events by date ascending
- Shows "Today" badge for current-day events
- Responsive mobile-friendly layout

**Features**:
- Pure HTML/CSS/JavaScript (no frameworks)
- Fallback message if JSON fails to load
- Lightweight (~8 KB)
- Works on all modern browsers

**When it runs**:
Automatically opens in browser when `python main.py` is executed

---

### `sa_events_scraper.py`
**Purpose**: Multi-source event scraper
**What it does**:
- Scrapes 15+ South African ticketing platforms
- Normalizes event data
- Caches results locally
- Implements cache checking logic

**Platforms Scraped**:
- Quicket
- Computicket
- Ticketpro
- Webtickets
- iTickets
- Plankton
- Tixsa
- Big Concerts
- Nedbank Box Office
- SuperSport Tickets
- SA Rugby Ticket Office
- PSL Tickets
- Viagogo
- StubHub
- Howler

**Key Functions**:
- `scrape_quicket()`, `scrape_computicket()`, etc. – Platform-specific scrapers
- `scrape_all_sources()` – Aggregate all scrapers
- `serialize_event()` – Normalize event format
- `is_cache_valid()` – Check cache freshness
- `load_cache()` / `save_cache()` – Cache management

**Usage** (optional, main.py handles this):
```bash
python sa_events_scraper.py
```

---

## Data Files

### `sa_events.json`
**Purpose**: Final event output
**Created by**: `main.py` or `sa_events_scraper.py`
**Format**: JSON array of event objects

**Example**:
```json
[
  {
    "title": "Event Name",
    "category": "Music",
    "date": "2026-05-10",
    "time": "18:00",
    "location": "City",
    "address": "Venue Address",
    "price": "R100",
    "source": "Quicket"
  }
]
```

**Used by**: index.html (fetches and displays)

---

### `cache_events.json`
**Purpose**: Cached event data
**Created by**: `main.py` when scraping
**Lifespan**: 6 hours (configurable)
**Deleted by**: User (optional)

**When used**:
- If valid (< 6 hours old): loaded instead of scraping
- If stale (> 6 hours old): scraper runs again
- If missing: scraper runs

---

### `sa_events_sample.json`
**Purpose**: Example/test data
**Usage**: Reference for JSON structure
**When used**: Testing without real scraper

---

## Documentation Files

### `README_EVENTS.md`
**Purpose**: Comprehensive system guide
**Contains**:
- Features overview
- Installation instructions
- Usage workflows
- How it works explanation
- Troubleshooting guide
- Advanced configuration
- File references
- Performance notes

**When to read**: First-time setup, troubleshooting

---

### `QUICKSTART.md`
**Purpose**: Quick reference guide
**Contains**:
- One-command startup
- Step-by-step alternative
- What happens during startup
- Common issues & solutions
- File checklist

**When to read**: Ready to use, need quick reference

---

## File Relationships

```
┌─────────────────────────────────────────┐
│         User runs: python main.py       │
└────────────────┬────────────────────────┘
                 │
                 ├─→ Check cache (cache_events.json)
                 │    ├─ If valid: load from cache
                 │    └─ If stale: run scraper
                 │
                 ├─→ Run scraper (sa_events_scraper.py)
                 │    ├─ Scrapes all platforms
                 │    └─ Saves to cache_events.json
                 │
                 ├─→ Save output (sa_events.json)
                 │
                 ├─→ Start HTTP server (port 8000)
                 │
                 ├─→ Open browser
                 │
                 └─→ Browser loads index.html
                      ├─ Fetch sa_events.json
                      ├─ Parse and group by category
                      └─ Display events
```

---

## File Sizes (Approximate)

| File | Size | Notes |
|------|------|-------|
| main.py | ~8 KB | Lightweight controller |
| index.html | ~12 KB | Complete UI with styles |
| sa_events_scraper.py | ~45 KB | Multi-source scraper |
| sa_events.json | ~20-50 KB | Event data (varies) |
| cache_events.json | ~20-50 KB | Cached events (varies) |
| README_EVENTS.md | ~8 KB | Full documentation |
| QUICKSTART.md | ~3 KB | Quick reference |
| sa_events_sample.json | ~1 KB | Example data |

---

## Execution Flow

```
1. User: python main.py
   ↓
2. main.py starts
   ├─ Print header
   ├─ Check cache existence & age
   │  ├─ Valid? → Print "✓ Using cached data"
   │  └─ Invalid? → Print "○ Scraping fresh data"
   ├─ Load or scrape events
   ├─ Save to cache_events.json
   ├─ Save to sa_events.json
   ├─ Start HTTP server
   ├─ Print "✓ Server started at http://127.0.0.1:8000"
   ├─ Open browser automatically
   ├─ Print "✓ Opening browser: http://127.0.0.1:8000"
   └─ Keep server running (Ctrl+C to stop)
   
3. Browser loads index.html
   ├─ Page renders
   ├─ JavaScript runs
   ├─ Fetch sa_events.json
   ├─ Parse event data
   ├─ Group by category
   ├─ Render event cards
   └─ Show category filters
   
4. User interacts
   ├─ Click category filter → Events filtered
   ├─ See all events sorted by date
   ├─ Refresh page → Reloads data
   └─ Close browser or Ctrl+C in terminal → Server stops
```

---

## Configuration

### Cache Duration
**File**: `main.py` or `sa_events_scraper.py`
**Line**: `CACHE_MAX_AGE_HOURS = 6`
**Modify to change cache validity duration**

### Server Port
**File**: `main.py`
**Line**: `PORT = 8000`
**Modify to run on different port**

### Server Host
**File**: `main.py`
**Line**: `HOST = "127.0.0.1"`
**Modify to allow external connections (e.g., "0.0.0.0")**

---

## Dependencies

### Required Packages
```
playwright>=1.40.0      # Browser automation
beautifulsoup4>=4.12.0  # HTML parsing
lxml>=4.9.0             # XML/HTML parser
requests>=2.31.0        # HTTP library
```

### System Requirements
- Python 3.7+
- 100+ MB disk space
- Internet connection (for scraping)

### Optional
- Virtual environment (recommended)

---

## Getting Started

1. **First time?**
   - Read `QUICKSTART.md`

2. **Need details?**
   - Read `README_EVENTS.md`

3. **Ready to run?**
   ```bash
   python main.py
   ```

4. **Issues?**
   - Check Troubleshooting in `README_EVENTS.md`

---

**System created**: May 2026
**All files ready to use**

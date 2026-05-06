# SA Events System

A unified Python + HTML system for scraping, caching, and displaying South African events.

## Features

- **Smart Caching**: Reuses data if cache is less than 6 hours old
- **Web Scraping**: Fetches events from multiple SA ticketing platforms
- **Local Server**: Serves events via built-in Python HTTP server
- **Auto Browser**: Automatically opens the events page
- **Responsive UI**: Clean, modern card-based design
- **Category Filtering**: Filter events by Party, Music, Sports, Comedy, Expo
- **Sorting**: Events sorted by date (earliest first)
- **Mobile-Friendly**: Responsive grid layout

## Project Structure

```
project/
├── main.py                    # Controller (cache, scrape, server, browser)
├── sa_events_scraper.py       # Event scraper (from multiple sources)
├── index.html                 # Events display page
├── sa_events.json             # Final event output
├── cache_events.json          # Cache file (auto-created)
├── sa_events_sample.json      # Example data for reference
└── README.md                  # This file
```

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

Dependencies:
- `playwright` – browser automation
- `beautifulsoup4` – HTML parsing
- `lxml` – XML/HTML parser

### 2. Verify Files

Ensure these files exist:
- `main.py`
- `index.html`
- `sa_events_scraper.py` (optional, for real scraping)

## Usage

### Quick Start (Recommended)

Run the controller script:

```bash
python main.py
```

This will:
1. Check if cache exists and is valid
2. Load from cache OR scrape fresh events
3. Save to `sa_events.json`
4. Start HTTP server on `http://127.0.0.1:8000`
5. Automatically open your browser to the events page

### Manual Workflow

**Step 1: Scrape Events**
```bash
python sa_events_scraper.py
```
Output: `sa_events.json` and `cache_events.json`

**Step 2: Start Server**
```bash
python -m http.server 8000
```

**Step 3: Open Browser**
Navigate to: `http://localhost:8000`

## How It Works

### Cache System

- Cache file: `cache_events.json`
- Valid for: 6 hours
- On startup:
  - If cache exists AND is fresh → load from cache
  - Otherwise → run scraper → save to cache

### Event Structure

Each event is a dictionary with:

```json
{
  "title": "Event Name",
  "category": "Music",
  "date": "2026-05-10",
  "time": "18:00",
  "location": "Soweto",
  "address": "Zone 6 – Eyethu Lifestyle Centre",
  "price": "R120",
  "source": "Quicket"
}
```

### Supported Categories

- All (no filter)
- Party
- Music
- Sports
- Comedy
- Expo

### Supported Sources

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

## Troubleshooting

### "ModuleNotFoundError" for playwright, beautifulsoup4, etc.

**Solution**: Install dependencies
```bash
pip install playwright beautifulsoup4 lxml requests
```

### HTML page shows "Unable to load sa_events.json"

**Possible causes**:
1. Browser opened before server was ready
2. Direct file:// access (doesn't work due to CORS)
3. `sa_events.json` doesn't exist

**Solution**:
- Use `python main.py` (recommended)
- Or manually start server: `python -m http.server 8000`
- Wait a few seconds before opening browser
- Refresh the page (Ctrl+R or Cmd+R)

### Server won't start on port 8000

**Solution**: Specify a different port
```bash
python -m http.server 9000
```

Then open: `http://localhost:9000`

## File Reference

### main.py

**Key Functions**:
- `is_cache_valid()` – Check if cache is fresh
- `load_cache()` – Load events from cache
- `save_cache(events)` – Save events to cache
- `scrape_events()` – Placeholder scraper (tries to import sa_events_scraper)
- `get_events()` – Smart loader (cache or scrape)
- `save_output(events)` – Write final JSON
- `start_server()` – Launch HTTP server
- `open_browser()` – Open browser to local server

### index.html

**Features**:
- Fetches `sa_events.json` on load
- Groups events by category
- Category filter buttons
- Auto-sorts by date
- "Today" badge for current-day events
- Responsive grid layout
- Fallback message for missing data

### sa_events_scraper.py

**Key Functions**:
- `scrape_quicket()` – Quicket events
- `scrape_computicket()` – Computicket events
- `scrape_ticketpro()` – Ticketpro events
- (+ 11 more scrapers for other platforms)
- `scrape_all_sources()` – Aggregate all sources
- `serialize_event()` – Normalize event format

## Example Output

```
==================================================
SA Events Controller
==================================================

Loading events...
✓ Using cached data
✓ Saved 43 events to sa_events.json

✓ Server started at http://127.0.0.1:8000
✓ Opening browser: http://127.0.0.1:8000

Server is running. Press Ctrl+C to stop.
```

## Advanced

### Modify Cache Age

Edit `main.py` or `sa_events_scraper.py`:

```python
CACHE_MAX_AGE_HOURS = 12  # Cache for 12 hours instead of 6
```

### Use Custom Scraper

Replace `scrape_events()` in `main.py` with your own logic:

```python
def scrape_events():
    """Custom scraper"""
    # Your scraping code here
    return [
        {
            "title": "My Event",
            "category": "Music",
            "date": "2026-05-10",
            "time": "18:00",
            "location": "Johannesburg",
            "address": "Address",
            "price": "R100",
            "source": "MySource"
        }
    ]
```

### Add More Categories

Edit `index.html`:

```javascript
const categories = ["All", "Party", "Music", "Sports", "Comedy", "Expo", "Workshop"];
```

## Performance

- **First run**: ~30-60 seconds (scrapes all platforms)
- **Cached run**: ~2 seconds (loads from cache)
- **Refresh browser**: <1 second

## License

Public domain. Modify and distribute freely.

## Support

For issues or questions:
1. Check the Troubleshooting section above
2. Verify all files are present and readable
3. Check console output for error messages
4. Ensure Python 3.7+ is installed

---

**Last Updated**: May 2026

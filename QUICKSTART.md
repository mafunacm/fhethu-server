# Quick Start Guide

## Installation (One Time)

```bash
# 1. Install Python packages
pip install playwright beautifulsoup4 lxml requests

# 2. Download Playwright browsers
python -m playwright install
```

## Running the System

### Option 1: One Command (Recommended)

```bash
python main.py
```

That's it! The browser will open automatically with your events.

### Option 2: Step by Step

```bash
# Terminal 1: Scrape events
python sa_events_scraper.py

# Terminal 2: Start server
python -m http.server 8000

# Browser: Open manually
# http://localhost:8000
```

### Option 3: Use Cache Only

If you already have `cache_events.json`:

```python
python -c "
import main
import json
with open('cache_events.json') as f:
    events = json.load(f)
main.save_output(events)
main.start_server(8000, '127.0.0.1')
main.open_browser()
"
```

## What Happens

1. ✓ Cache checked (loads if <6 hours old)
2. ✓ Events scraped (if cache is stale)
3. ✓ Results saved to `sa_events.json`
4. ✓ Server started on port 8000
5. ✓ Browser opens automatically
6. ✓ Events displayed grouped by category

## Keyboard Shortcuts

**In Browser**:
- Press `F5` or `Ctrl+R` – Refresh events
- Look for category filter buttons at top

**In Terminal**:
- Press `Ctrl+C` – Stop server

## Common Issues

| Issue | Solution |
|-------|----------|
| "Module not found" | `pip install playwright beautifulsoup4 lxml requests` |
| Port 8000 in use | `python -m http.server 9000` |
| Browser won't open | Open `http://localhost:8000` manually |
| No events showing | Wait 30 seconds (scraping takes time) then refresh |
| Cache errors | Delete `cache_events.json` and run again |

## Next Steps

- Review events in the browser
- Use category filters to narrow results
- Check `sa_events.json` for raw data
- Modify `main.py` to customize behavior

## File Checklist

Verify these files exist before running:

- [ ] `main.py`
- [ ] `index.html`
- [ ] `sa_events_scraper.py`
- [ ] `sa_events_sample.json`
- [ ] `README_EVENTS.md`

---

Ready? Run `python main.py` and enjoy!

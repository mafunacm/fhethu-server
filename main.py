#!/usr/bin/env python3
"""
SA Events Controller
Scrapes/caches events, serves them locally, and opens a browser.
"""

import json
import os
import time
import webbrowser
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from datetime import datetime, timedelta
from threading import Thread
import sys

# Configuration
CACHE_FILE = "cache_events.json"
OUTPUT_FILE = "sa_events.json"
CACHE_MAX_AGE_HOURS = 6
PORT = 8000
HOST = "127.0.0.1"


# ============================================================================
# CACHE FUNCTIONS
# ============================================================================

def is_cache_valid(max_age_hours: int = CACHE_MAX_AGE_HOURS) -> bool:
    """Check if cache file exists and is recent."""
    if not os.path.exists(CACHE_FILE):
        return False
    age_seconds = time.time() - os.path.getmtime(CACHE_FILE)
    return age_seconds < max_age_hours * 3600


def load_cache():
    """Load events from cache file."""
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading cache: {e}")
        return []


def save_cache(events):
    """Save events to cache file."""
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(events, f, indent=2)
    except Exception as e:
        print(f"Error saving cache: {e}")


# ============================================================================
# SCRAPER HOOK
# ============================================================================

def scrape_events():
    """
    Placeholder function to scrape events.
    
    Replace this with actual scraping logic or import from sa_events_scraper.py
    
    Returns:
        list: Event dictionaries with keys:
            - title (str)
            - date (str, YYYY-MM-DD)
            - time (str, HH:mm)
            - location (str)
            - address (str)
            - price (str)
            - source (str)
            - category (str)
    """
    print("[Scraper] Starting event scraping...")
    
    # Try importing from existing scraper
    try:
        from sa_events_scraper import scrape_all_sources
        events = scrape_all_sources()
        print(f"[Scraper] Fetched {len(events)} events")
        return events
    except Exception as e:
        print(f"[Scraper] Could not import scraper: {e}")
        print("[Scraper] Using sample data instead")
        return get_sample_events()


def get_sample_events():
    """Return sample events for testing."""
    return [
        {
            "title": "Soweto Sound Festival",
            "category": "Music",
            "date": (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d"),
            "time": "18:00",
            "location": "Soweto",
            "address": "Zone 6 – Eyethu Lifestyle Centre",
            "price": "R120",
            "source": "Quicket"
        },
        {
            "title": "Comedy Open Mic",
            "category": "Comedy",
            "date": (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d"),
            "time": "20:30",
            "location": "Johannesburg",
            "address": "Braamfontein – The Laugh Lounge",
            "price": "R80",
            "source": "Ticketpro"
        },
        {
            "title": "Victory Soccer Derby",
            "category": "Sports",
            "date": (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d"),
            "time": "15:00",
            "location": "Pretoria",
            "address": "Loftus Versfeld Stadium",
            "price": "R320",
            "source": "SuperSport Tickets"
        },
        {
            "title": "Rooftop Party After Dark",
            "category": "Party",
            "date": (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d"),
            "time": "22:00",
            "location": "Durban",
            "address": "Pier 10 Rooftop",
            "price": "Free entry",
            "source": "Plankton"
        },
        {
            "title": "City Expo 2026",
            "category": "Expo",
            "date": (datetime.now() + timedelta(days=28)).strftime("%Y-%m-%d"),
            "time": "10:00",
            "location": "Cape Town",
            "address": "CTICC – Hall 2",
            "price": "R250",
            "source": "Webtickets"
        }
    ]


# ============================================================================
# EVENT MANAGEMENT
# ============================================================================

def get_events():
    """Load or scrape events based on cache validity."""
    if is_cache_valid():
        print("✓ Using cached data")
        return load_cache()
    else:
        print("○ Scraping fresh data")
        events = scrape_events()
        save_cache(events)
        return events


def save_output(events):
    """Save events to output file."""
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(events, f, indent=2)
        print(f"✓ Saved {len(events)} events to {OUTPUT_FILE}")
    except Exception as e:
        print(f"✗ Error saving output: {e}")


# ============================================================================
# HTTP SERVER
# ============================================================================

class CustomHTTPRequestHandler(SimpleHTTPRequestHandler):
    """HTTP request handler with logging."""

    def log_message(self, format, *args):
        """Log HTTP requests."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {format % args}")

    def end_headers(self):
        """Add CORS headers to allow fetch from different origins."""
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        super().end_headers()


def start_server(port=PORT, host=HOST):
    """Start HTTP server in background thread."""
    server_address = (host, port)
    httpd = HTTPServer(server_address, CustomHTTPRequestHandler)
    print(f"✓ Server started at http://{host}:{port}")
    
    # Run server in thread so it doesn't block
    server_thread = Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()
    
    return httpd


def open_browser(port=PORT, host=HOST):
    """Open browser to local server."""
    url = f"http://{host}:{port}"
    print(f"✓ Opening browser: {url}")
    
    # Small delay to ensure server is ready
    time.sleep(1)
    webbrowser.open(url)


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main entry point."""
    print("\n" + "=" * 50)
    print("SA Events Controller")
    print("=" * 50 + "\n")

    # Get events
    print("Loading events...")
    events = get_events()
    
    if not events:
        print("✗ No events found. Using sample data.")
        events = get_sample_events()

    # Save to output file
    save_output(events)

    # Start server
    print()
    httpd = start_server()

    # Open browser
    print()
    open_browser()

    # Keep server running
    print("\nServer is running. Press Ctrl+C to stop.\n")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n✓ Shutting down server...")
        httpd.shutdown()
        print("✓ Server stopped.")
        sys.exit(0)


if __name__ == "__main__":
    main()

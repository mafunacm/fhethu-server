"""
SA Events API Server
--------------------
Run:  uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload
Docs: http://localhost:8000/docs
"""

import json
import logging
import os
import sys
import threading
import time
from typing import Optional

log = logging.getLogger("sa_events.api")

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import the scraper module (must be in the same directory)
import sa_events_scraper as scraper


# ---------------------------------------------
# APP SETUP
# ---------------------------------------------

app = FastAPI(
    title="SA Events API",
    description="Scraped South African event listings from Quicket, Computicket, Ticketpro, Howler, Webtickets, SuperSport, and SA Rugby.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lock to prevent concurrent scrape jobs
_scrape_lock = threading.Lock()
_scrape_running = False


# ---------------------------------------------
# RESPONSE MODELS
# ---------------------------------------------

class EventOut(BaseModel):
    title: str
    date: str
    time: str
    location: str
    address: str
    price: str
    source: str
    url: str
    category: str


class EventsResponse(BaseModel):
    total: int
    scraped_at: Optional[str]
    events: list[EventOut]


class StatusResponse(BaseModel):
    status: str
    cache_valid: bool
    cache_age_minutes: Optional[float]
    total_events: int
    scrape_running: bool


class RefreshResponse(BaseModel):
    message: str
    scrape_running: bool


# ---------------------------------------------
# HELPERS
# ---------------------------------------------

def load_events() -> list[dict]:
    """Load events from the output JSON file."""
    if not os.path.exists(scraper.OUTPUT_FILE):
        return []
    with open(scraper.OUTPUT_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def get_cache_age_minutes() -> Optional[float]:
    if not os.path.exists(scraper.CACHE_FILE):
        return None
    age_seconds = time.time() - os.path.getmtime(scraper.CACHE_FILE)
    return round(age_seconds / 60, 1)


def get_scraped_at() -> Optional[str]:
    if not os.path.exists(scraper.CACHE_FILE):
        return None
    mtime = os.path.getmtime(scraper.CACHE_FILE)
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mtime))


def run_scrape_background():
    """Run the scraper in a background thread."""
    global _scrape_running
    try:
        _scrape_running = True
        events = scraper.scrape_all_sources()
        scraper.save_cache(events)
        with open(scraper.OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(events, f, indent=2)
    finally:
        _scrape_running = False


def filter_events(
    events: list[dict],
    category: Optional[str],
    source: Optional[str],
    location: Optional[str],
    search: Optional[str],
    free_only: bool,
) -> list[dict]:
    results = events

    if category:
        results = [e for e in results if e.get("category", "").lower() == category.lower()]

    if source:
        results = [e for e in results if e.get("source", "").lower() == source.lower()]

    if location:
        results = [
            e for e in results
            if location.lower() in e.get("location", "").lower()
            or location.lower() in e.get("address", "").lower()
        ]

    if search:
        term = search.lower()
        results = [
            e for e in results
            if term in e.get("title", "").lower()
            or term in e.get("location", "").lower()
        ]

    if free_only:
        results = [
            e for e in results
            if "free" in e.get("price", "").lower() or e.get("price", "") == "R0"
        ]

    return results


# ---------------------------------------------
# ROUTES
# ---------------------------------------------

@app.on_event("startup")
def on_startup():
    """Auto-trigger a scrape on startup if output file is missing or cache is stale."""
    global _scrape_running
    if not os.path.exists(scraper.OUTPUT_FILE) or not scraper.is_cache_valid():
        reason = "file missing" if not os.path.exists(scraper.OUTPUT_FILE) else "cache stale"
        log.info(f"[Startup] {reason} — triggering background scrape")
        if not _scrape_running and _scrape_lock.acquire(blocking=False):
            try:
                thread = threading.Thread(target=run_scrape_background, daemon=True)
                thread.start()
            finally:
                _scrape_lock.release()
    else:
        log.info("[Startup] Cache valid — skipping scrape")


@app.get("/", include_in_schema=False)
def root():
    return {"message": "SA Events API. See /docs for usage."}


@app.get("/status", response_model=StatusResponse, summary="Server and cache status")
def status():
    events = load_events()
    return StatusResponse(
        status="ok",
        cache_valid=scraper.is_cache_valid(),
        cache_age_minutes=get_cache_age_minutes(),
        total_events=len(events),
        scrape_running=_scrape_running,
    )


@app.get("/events", response_model=EventsResponse, summary="Get all events with optional filters")
def get_events(
    category: Optional[str] = Query(None, description="Filter by category: Sports, Concert/Music, Festival, Comedy, Musical/Theatre, Other"),
    source: Optional[str] = Query(None, description="Filter by source: Quicket, Computicket, Ticketpro, Howler, Webtickets, SuperSport, SA Rugby"),
    location: Optional[str] = Query(None, description="Filter by city or venue substring, e.g. 'johannesburg'"),
    search: Optional[str] = Query(None, description="Search by title or location keyword"),
    free_only: bool = Query(False, description="Return only free events"),
    limit: int = Query(100, ge=1, le=500, description="Max results to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    # Auto-scrape if no data exists yet
    if not os.path.exists(scraper.OUTPUT_FILE):
        if not _scrape_running and _scrape_lock.acquire(blocking=False):
            try:
                thread = threading.Thread(target=run_scrape_background, daemon=True)
                thread.start()
            finally:
                _scrape_lock.release()
        raise HTTPException(
            status_code=503,
            detail="No data available yet. Scrape triggered — retry in ~2 minutes."
        )

    events = load_events()
    filtered = filter_events(events, category, source, location, search, free_only)
    page = filtered[offset: offset + limit]

    return EventsResponse(
        total=len(filtered),
        scraped_at=get_scraped_at(),
        events=[EventOut(**e) for e in page],
    )



@app.get("/all", summary="Return every event with no filters or limits")
def get_all():
    if not os.path.exists(scraper.OUTPUT_FILE):
        status = "Scraping in progress — retry in ~2 minutes." if _scrape_running else "No data yet. POST /refresh to trigger a scrape."
        raise HTTPException(status_code=503, detail=status)
    events = load_events()
    return {"total": len(events), "scraped_at": get_scraped_at(), "events": events}


@app.get("/events/all", summary="Return every event with no filters or limits (alias)")
def get_events_all():
    return get_all()


@app.get("/events/categories", summary="List all available categories and their counts")
def get_categories():
    events = load_events()
    counts: dict[str, int] = {}
    for e in events:
        cat = e.get("category", "Other")
        counts[cat] = counts.get(cat, 0) + 1
    return {"categories": counts}


@app.get("/events/sources", summary="List all sources and their counts")
def get_sources():
    events = load_events()
    counts: dict[str, int] = {}
    for e in events:
        src = e.get("source", "Unknown")
        counts[src] = counts.get(src, 0) + 1
    return {"sources": counts}


@app.get("/events/sports", response_model=EventsResponse, summary="Shortcut — Sports events only")
def get_sports_events(
    source: Optional[str] = Query(None, description="Filter by source: SuperSport, SA Rugby, Computicket, etc."),
    location: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    events = load_events()
    filtered = filter_events(events, category="Sports", source=source, location=location, search=None, free_only=False)
    page = filtered[offset: offset + limit]
    return EventsResponse(
        total=len(filtered),
        scraped_at=get_scraped_at(),
        events=[EventOut(**e) for e in page],
    )


@app.post("/refresh", response_model=RefreshResponse, summary="Trigger a fresh scrape in the background")
def refresh(background_tasks: BackgroundTasks, force: bool = Query(False, description="Force scrape even if cache is still valid")):
    global _scrape_running

    if _scrape_running:
        return RefreshResponse(message="Scrape already in progress.", scrape_running=True)

    if not force and scraper.is_cache_valid():
        age = get_cache_age_minutes()
        return RefreshResponse(
            message=f"Cache is still valid ({age} min old). Use ?force=true to override.",
            scrape_running=False,
        )

    if _scrape_lock.acquire(blocking=False):
        try:
            background_tasks.add_task(run_scrape_background)
            return RefreshResponse(message="Scrape started in background.", scrape_running=True)
        finally:
            _scrape_lock.release()

    return RefreshResponse(message="Could not acquire scrape lock.", scrape_running=_scrape_running)
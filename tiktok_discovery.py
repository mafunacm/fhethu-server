import re
import urllib.parse
import requests
from bs4 import BeautifulSoup

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

PLATFORM_DOMAINS = {
    "tiktok": "tiktok.com",
    "instagram": "instagram.com",
    "facebook": "facebook.com",
}

COMMUNITY_KEYWORDS = {
    "Soweto Urban": ["soweto events", "soweto party", "soweto lifestyle"],
    "Alex News": ["alexandra events", "alex gigs", "alexandra lifestyle"],
    "Tembisa Pulse": ["tembisa events", "tembisa party", "tembisa music"],
    "Joburg Events": ["joburg events", "joburg party", "joburg nightlife"],
}


def google_search(query: str, headers: dict | None = None) -> str:
    headers = headers or DEFAULT_HEADERS
    url = f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}"
    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()
    return response.text


def parse_google_results(html: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    links = []

    for a in soup.select("a"):
        href = a.get("href")
        if not href:
            continue

        if href.startswith("/url?q="):
            parsed = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
            target = parsed.get("q", [None])[0]
            if target:
                links.append(target)
        elif href.startswith("http"):
            links.append(href)

    return links


def filter_links_by_domain(links: list[str], domains: list[str]) -> list[str]:
    filtered = []
    for link in links:
        if any(domain in link for domain in domains):
            filtered.append(link)
    return filtered


def extract_username_from_url(url: str) -> str | None:
    url = urllib.parse.unquote(url)

    tiktok_match = re.search(r"tiktok\.com/@([\w\.-]+)", url)
    if tiktok_match:
        return tiktok_match.group(1)

    instagram_match = re.search(r"instagram\.com/([\w\._]+)/?", url)
    if instagram_match:
        return instagram_match.group(1)

    facebook_match = re.search(r"facebook\.com/([\w\.-]+)(?:/|\?|$)", url)
    if facebook_match:
        return facebook_match.group(1)

    return None


def build_discovery_queries(keywords_map: dict[str, list[str]], platforms: list[str] | None = None) -> list[str]:
    platforms = platforms or ["tiktok", "instagram", "facebook"]
    queries = []

    for source, keywords in keywords_map.items():
        for keyword in keywords:
            for platform in platforms:
                domain = PLATFORM_DOMAINS.get(platform, platform)
                queries.append(f"site:{domain} {keyword}")

    return queries


def google_discover(query: str, domains: list[str] | None = None, max_results: int = 50) -> list[str]:
    html = google_search(query)
    links = parse_google_results(html)
    domains = domains or list(PLATFORM_DOMAINS.values())
    filtered = filter_links_by_domain(links, domains)
    return filtered[:max_results]


def discover_usernames_from_queries(queries: list[str]) -> dict[str, set[str]]:
    discovery = {}

    for query in queries:
        links = google_discover(query)
        usernames = set()
        for link in links:
            username = extract_username_from_url(link)
            if username:
                usernames.add(username)

        print(f"\nQuery: {query}")
        print(f"  Pages found: {len(links)}")
        for link in links:
            print(f"    {link}")
        print(f"  Usernames extracted: {len(usernames)}")
        for username in sorted(usernames):
            print(f"    {username}")

        discovery[query] = usernames

    return discovery


def collect_tiktok_usernames(keywords_map: dict[str, list[str]]) -> set[str]:
    queries = build_discovery_queries(keywords_map, platforms=["tiktok"])
    discovery = discover_usernames_from_queries(queries)

    usernames = set()
    for found in discovery.values():
        usernames.update(found)

    return usernames


if __name__ == "__main__":
    queries = build_discovery_queries(COMMUNITY_KEYWORDS)
    print("Discovery queries:")
    for query in queries[:12]:
        print(" -", query)

    print("\nSearching Google for TikTok usernames...")
    usernames = collect_tiktok_usernames(COMMUNITY_KEYWORDS)
    print(f"Found {len(usernames)} candidate usernames:")
    for username in sorted(usernames):
        print(" -", username)

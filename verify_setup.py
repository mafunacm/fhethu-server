#!/usr/bin/env python3
"""
Setup Verification Script
Checks if all required files and dependencies are in place.
"""

import sys
import os
from pathlib import Path


def check_file_exists(filepath, description=""):
    """Check if a file exists."""
    exists = Path(filepath).exists()
    status = "✓" if exists else "✗"
    desc = f" - {description}" if description else ""
    print(f"  {status} {filepath}{desc}")
    return exists


def check_import(module_name):
    """Check if a Python module can be imported."""
    try:
        __import__(module_name)
        print(f"  ✓ {module_name}")
        return True
    except ImportError:
        print(f"  ✗ {module_name} (not installed)")
        return False


def main():
    print("\n" + "=" * 60)
    print("SA Events System - Setup Verification")
    print("=" * 60 + "\n")

    all_good = True

    # Check Python version
    print("Python Version:")
    py_version = sys.version_info
    if py_version.major >= 3 and py_version.minor >= 7:
        print(f"  ✓ Python {py_version.major}.{py_version.minor}")
    else:
        print(f"  ✗ Python {py_version.major}.{py_version.minor} (requires 3.7+)")
        all_good = False

    # Check required files
    print("\nRequired Files:")
    required_files = [
        ("main.py", "Controller script"),
        ("index.html", "Web page"),
        ("sa_events_scraper.py", "Scraper (optional for main.py)"),
    ]
    for filepath, desc in required_files:
        if not check_file_exists(filepath, desc):
            all_good = False

    # Check optional files
    print("\nOptional Files (for reference):")
    optional_files = [
        ("sa_events_sample.json", "Sample data"),
        ("README_EVENTS.md", "Full documentation"),
        ("QUICKSTART.md", "Quick start guide"),
        ("FILES_SUMMARY.md", "File descriptions"),
    ]
    for filepath, desc in optional_files:
        check_file_exists(filepath, desc)

    # Check Python dependencies
    print("\nPython Dependencies:")
    dependencies = ["json", "os", "webbrowser", "http.server", "threading"]
    for module in dependencies:
        check_import(module)

    # Optional but recommended
    print("\nOptional Python Packages (for scraping):")
    optional_packages = [
        "playwright",
        "bs4",  # beautifulsoup4
        "lxml",
        "requests",
    ]
    optional_status = {}
    for package in optional_packages:
        optional_status[package] = check_import(package)

    if "playwright" in optional_status and not optional_status["playwright"]:
        print("\n  Note: Playwright not found. Install with:")
        print("  $ pip install playwright")
        print("  $ python -m playwright install")

    # Check if data files exist
    print("\nData Files (auto-created):")
    data_files = [
        ("sa_events.json", "Will be created by main.py"),
        ("cache_events.json", "Will be created when scraping"),
    ]
    for filepath, desc in data_files:
        if Path(filepath).exists():
            print(f"  ✓ {filepath} - {desc}")
        else:
            print(f"  ○ {filepath} - {desc} (not yet created)")

    # Summary
    print("\n" + "=" * 60)
    if all_good:
        print("✓ Setup looks good! Ready to run:")
        print("\n  $ python main.py\n")
    else:
        print("✗ Some issues found. Please fix and try again.\n")
        print("Missing files:")
        print("  - Create main.py with: python -c \"import main\"")
        print("  - Ensure index.html is in project directory")
        sys.exit(1)

    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()

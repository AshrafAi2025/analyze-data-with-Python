#!/usr/bin/env python3
"""Job‑Posting Web Scraper

Scrapes search‑result pages (e.g. Indeed) for job listings and saves them to a CSV/JSON/Parquet file.

Usage (examples):
    python scraper.py --query "python developer" --pages 3
    python scraper.py --query "data engineer" --pages 5 --output jobs.parquet
"""
from __future__ import annotations

import argparse
import random
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List

import pandas as pd
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
HEADERS: dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
}
BASE_URL = "https://www.indeed.com/jobs"
COLUMNS = [
    "title",
    "company",
    "location",
    "posted_date",
    "summary",
    "salary",
    "url",
    "scraped_at",
]

# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------

def fetch_page(url: str, *, timeout: int = 15) -> str:
    """Download HTML for a single page."""
    resp = requests.get(url, headers=HEADERS, timeout=timeout)
    resp.raise_for_status()
    return resp.text


def parse_jobs(html: str) -> List[dict]:
    """Extract job cards from HTML and return as list of dicts."""
    soup = BeautifulSoup(html, "lxml")
    cards = soup.select("div.job_seen_beacon")
    jobs: List[dict] = []

    for card in cards:
        title_el = card.select_one("h2 a")
        if not title_el:
            continue  # defensive: skip malformed card
        jobs.append(
            {
                "title": title_el.get_text(strip=True),
                "company": card.select_one(".companyName").get_text(strip=True)
                if card.select_one(".companyName")
                else None,
                "location": card.select_one(".companyLocation").get_text(strip=True)
                if card.select_one(".companyLocation")
                else None,
                "posted_date": card.select_one(".date").get_text(strip=True)
                if card.select_one(".date")
                else None,
                "summary": card.select_one(".job-snippet").get_text(" ", strip=True)
                if card.select_one(".job-snippet")
                else None,
                "salary": card.select_one(".salary-snippet").get_text(strip=True)
                if card.select_one(".salary-snippet")
                else None,
                "url": f"https://indeed.com{title_el['href']}",
                "scraped_at": datetime.utcnow().isoformat(timespec="seconds"),
            }
        )
    return jobs


def crawl(query: str, pages: int, delay_min: float, delay_max: float) -> pd.DataFrame:
    """Iterate through search‑result pages and accumulate job rows."""
    all_rows: List[dict] = []
    for page in tqdm(range(pages), desc="Pages"):
        start = page * 10  # Indeed: 10 results per page
        url = f"{BASE_URL}?q={query.replace(' ', '+')}&start={start}"
        html = fetch_page(url)
        all_rows.extend(parse_jobs(html))
        # Randomised polite delay
        time.sleep(random.uniform(delay_min, delay_max))
    return pd.DataFrame(all_rows, columns=COLUMNS)


# ---------------------------------------------------------------------------
# Command‑line interface
# ---------------------------------------------------------------------------

def _positive_int(value: str) -> int:
    ivalue = int(value)
    if ivalue < 1:
        raise argparse.ArgumentTypeError("must be >= 1")
    return ivalue


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Job‑Posting Web Scraper (Indeed)")
    p.add_argument(
        "--query",
        default="python developer",
        help="Search phrase (default: 'python developer')",
    )
    p.add_argument(
        "--pages",
        type=_positive_int,
        default=3,
        help="Number of result pages to scrape (default: 3)",
    )
    p.add_argument(
        "--delay",
        nargs=2,
        metavar=("MIN", "MAX"),
        type=float,
        default=[2.0, 5.0],
        help="Random wait range between requests in seconds (default: 2 5)",
    )
    p.add_argument(
        "--output",
        type=Path,
        default=Path("jobs.csv"),
        help="Output file path (csv / json / parquet inferred by extension)",
    )
    return p


def save_dataframe(df: pd.DataFrame, path: Path) -> None:
    path = path.expanduser().resolve()
    if path.suffix == ".csv":
        df.to_csv(path, index=False)
    elif path.suffix == ".json":
        df.to_json(path, orient="records", lines=True)
    elif path.suffix == ".parquet":
        df.to_parquet(path, index=False)
    else:
        raise ValueError("Unsupported output format: " + path.suffix)
    print(f"✅ Saved {len(df):,} rows → {path}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv: List[str] | None = None) -> None:
    args = build_arg_parser().parse_args(argv)
    delay_min, delay_max = args.delay
    if delay_min > delay_max:
        print("Error: --delay MIN must be <= MAX", file=sys.stderr)
        sys.exit(1)

    df = crawl(args.query, args.pages, delay_min, delay_max)
    if df.empty:
        print("No results scraped. Try a different query or check your network.")
        sys.exit(2)

    save_dataframe(df, args.output)


if __name__ == "__main__":
    main()

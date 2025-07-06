import requests, time, random
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
from tqdm import tqdm

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        " AppleWebKit/537.36 (KHTML, like Gecko)"
        " Chrome/126.0.0.0 Safari/537.36"
    )
}

def fetch_page(url):
    r = requests.get(url, headers=HEADERS, timeout=15)
    r.raise_for_status()
    return r.text

def parse_jobs(html):
    soup = BeautifulSoup(html, "lxml")
    cards = soup.select("div.job_seen_beacon")
    rows = []
    for c in cards:
        rows.append({
            "title": c.select_one("h2 a").get_text(strip=True),
            "company": c.select_one(".companyName").get_text(strip=True),
            "location": c.select_one(".companyLocation").get_text(strip=True),
            "posted_date": c.select_one(".date").get_text(strip=True),
            "summary": c.select_one(".job-snippet").get_text(" ", strip=True),
            "salary": (c.select_one(".salary-snippet") or {}).get_text(strip=True) if c.select_one(".salary-snippet") else None,
            "url": "https://indeed.com" + c.select_one("h2 a")["href"],
            "scraped_at": datetime.utcnow().isoformat()
        })
    return rows

def crawl(query="python developer", pages=3):
    all_rows = []
    base = "https://www.indeed.com/jobs"
    for page in tqdm(range(pages), desc="Pages"):
        start = page * 10
        url = f"{base}?q={query.replace(' ', '+')}&start={start}"
        html = fetch_page(url)
        all_rows.extend(parse_jobs(html))
        time.sleep(random.uniform(2, 5))  # لطفاً مع الخادم
    return pd.DataFrame(all_rows, columns=COLUMNS)

if __name__ == "__main__":
    df = crawl()
    df.to_csv("jobs.csv", index=False)
    print(f"Saved {len(df)} rows.")
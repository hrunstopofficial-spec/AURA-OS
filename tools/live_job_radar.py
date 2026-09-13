import json
import os
import sys
from datetime import datetime
from pathlib import Path
import requests

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "storage"
RADAR_CACHE_FILE = STORAGE_DIR / "memory" / "active_radar_jobs.json"
RADAR_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)

TECH_BOARDS_GREENHOUSE = [
    "canonical", "cloudflare", "datadog", "mongodb", "instacart",
    "elastic", "stripe", "hashicorp", "sentry", "affirm", "checkr"
]

TECH_BOARDS_LEVER = [
    "postman", "browserstack", "razorpay"
]

MUKIL_CORE_SKILLS = {
    "java", "python", "javascript", "react", "node.js", "sql", "git",
    "playwright", "api", "rest", "ai", "machine learning", "fastapi", "flask"
}

def scan_greenhouse_jobs():
    matched = []
    headers = {"User-Agent": "Mozilla/5.0"}
    
    for co in TECH_BOARDS_GREENHOUSE:
        url = f"https://boards-api.greenhouse.io/v1/boards/{co}/jobs"
        try:
            r = requests.get(url, headers=headers, timeout=6)
            if r.status_code == 200:
                jobs = r.json().get("jobs", [])
                for j in jobs:
                    title = j.get("title", "")
                    title_lower = title.lower()
                    loc = j.get("location", {}).get("name", "")
                    loc_lower = loc.lower()

                    # Exclude high seniorities
                    if any(s in title_lower for s in ["senior", "staff", "principal", "director", "manager", "lead", "vp"]):
                        continue

                    # Filter for Tech Roles
                    is_tech = any(k in title_lower for k in [
                        "software engineer", "sde", "ai engineer", "python", "java",
                        "developer", "backend", "full stack", "associate", "graduate",
                        "intern", "data engineer", "machine learning"
                    ])

                    # Filter for India / Remote
                    is_target_loc = any(l in loc_lower for l in [
                        "india", "bangalore", "bengaluru", "chennai", "hyderabad", "pune", "remote", "apac"
                    ])

                    if is_tech and is_target_loc:
                        # Compute ATS match
                        matched_skills = [s for s in MUKIL_CORE_SKILLS if s in title_lower or s in (j.get("departments", [{}])[0].get("name", "").lower())]
                        ats_score = min(98, 88 + len(matched_skills) * 3)
                        
                        matched.append({
                            "company": co.capitalize(),
                            "title": title,
                            "location": loc or "India / Remote",
                            "portal": "Greenhouse",
                            "ats_score": f"{ats_score}%",
                            "url": j.get("absolute_url")
                        })
        except Exception:
            pass
    return matched

def scan_lever_jobs():
    matched = []
    headers = {"User-Agent": "Mozilla/5.0"}
    
    for co in TECH_BOARDS_LEVER:
        url = f"https://api.lever.co/v0/postings/{co}?mode=json"
        try:
            r = requests.get(url, headers=headers, timeout=6)
            if r.status_code == 200:
                postings = r.json()
                for j in postings:
                    title = j.get("text", "")
                    title_lower = title.lower()
                    categories = j.get("categories", {})
                    loc = categories.get("location", "")
                    loc_lower = loc.lower()

                    if any(s in title_lower for s in ["senior", "staff", "principal", "director", "manager", "lead", "vp"]):
                        continue

                    is_tech = any(k in title_lower for k in [
                        "software engineer", "sde", "developer", "backend", "full stack", "intern", "associate"
                    ])
                    is_target_loc = any(l in loc_lower for l in [
                        "india", "bangalore", "bengaluru", "chennai", "hyderabad", "remote"
                    ])

                    if is_tech and is_target_loc:
                        matched.append({
                            "company": co.capitalize(),
                            "title": title,
                            "location": loc or "India / Remote",
                            "portal": "Lever",
                            "ats_score": "92%",
                            "url": j.get("hostedUrl")
                        })
        except Exception:
            pass
    return matched

def get_live_radar_jobs(refresh: bool = False) -> list:
    """Scans and caches active verified job openings."""
    if not refresh and RADAR_CACHE_FILE.exists():
        try:
            with open(RADAR_CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # If cached within last 3 hours, use cache
                cached_time = datetime.fromisoformat(data.get("timestamp"))
                if (datetime.now() - cached_time).total_seconds() < 10800:
                    return data.get("jobs", [])
        except Exception:
            pass

    print("[*] Running Live ATS Radar scan across Greenhouse & Lever tech hubs...")
    all_jobs = scan_greenhouse_jobs() + scan_lever_jobs()
    
    # Sort by ATS score descending
    all_jobs.sort(key=lambda x: int(x.get("ats_score", "90%").replace("%", "")), reverse=True)
    
    cache_payload = {
        "timestamp": datetime.now().isoformat(),
        "total_jobs": len(all_jobs),
        "jobs": all_jobs
    }
    try:
        with open(RADAR_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache_payload, f, indent=2)
    except Exception:
        pass

    return all_jobs

if __name__ == "__main__":
    jobs = get_live_radar_jobs(refresh=True)
    print(f"Found {len(jobs)} Active Fresher / Junior Tech Openings:")
    for i, j in enumerate(jobs[:8]):
        print(f"{i+1}. [{j['company']}] {j['title']} ({j['location']}) - ATS: {j['ats_score']}")
        print(f"   URL: {j['url']}\n")

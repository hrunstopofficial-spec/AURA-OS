import requests

companies = ['cloudflare', 'datadog', 'gitlab', 'canonical', 'mongodb', 'instacart']
for co in companies:
    try:
        r = requests.get(f"https://boards-api.greenhouse.io/v1/boards/{co}/jobs", timeout=5)
        if r.status_code == 200:
            jobs = r.json().get("jobs", [])
            for j in jobs:
                loc = j.get("location", {}).get("name", "").lower()
                title = j.get("title", "").lower()
                if ("india" in loc or "remote" in loc) and any(k in title for k in ["ai", "python", "software", "machine learning"]):
                    print(f"[{co.upper()}] {j.get('title')} | {j.get('location', {}).get('name')} -> {j.get('absolute_url')}")
    except Exception:
        pass

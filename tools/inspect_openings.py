import requests

r = requests.get('https://boards-api.greenhouse.io/v1/boards/scaleai/jobs', timeout=10)
jobs = r.json().get('jobs', [])
print(f"Total Scale AI jobs: {len(jobs)}")
for j in jobs[:20]:
    title = j.get('title', '')
    loc = j.get('location', {}).get('name', '')
    url = j.get('absolute_url', '')
    if any(k in title.lower() for k in ['software', 'engineer', 'ai', 'full stack', 'python']):
        print(f"[{title}] in [{loc}] -> {url}")

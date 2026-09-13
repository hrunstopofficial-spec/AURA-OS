import os
import sys
import time
import json
import requests
from dotenv import load_dotenv

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

load_dotenv(r"C:\Users\mukil\jarvis-core\.env")

TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN")
PERSON_URN = os.getenv("LINKEDIN_PERSON_URN", "urn:li:person:9agB0hdGqJ")
VIDEO_PATH = r"C:\Users\mukil\jarvis-core\storage\videos\autonomous_workflow_demo.mp4"
GITHUB_URL = "https://github.com/Mukil630/AURA-OS"

if not os.path.exists(VIDEO_PATH):
    print(f"[-] Video file not found: {VIDEO_PATH}")
    sys.exit(1)

file_size = os.path.getsize(VIDEO_PATH)
print(f"[*] Preparing to upload video: {VIDEO_PATH} ({file_size / (1024*1024):.2f} MB)")

# Step 1: Register Video Upload
print("[1/4] Registering video upload with LinkedIn API...")
reg_url = "https://api.linkedin.com/v2/assets?action=registerUpload"
headers = {
    "Authorization": f"Bearer {TOKEN}",
    "X-Restli-Protocol-Version": "2.0.0",
    "Content-Type": "application/json"
}
payload = {
    "registerUploadRequest": {
        "recipes": ["urn:li:digitalmediaRecipe:feedshare-video"],
        "owner": PERSON_URN,
        "supportedUploadMechanism": ["SYNCHRONOUS_UPLOAD"]
    }
}

res = requests.post(reg_url, headers=headers, json=payload, timeout=20)
if res.status_code not in (200, 201):
    print(f"[-] Register upload failed: {res.status_code} -> {res.text}")
    sys.exit(1)

val = res.json().get("value", {})
asset_urn = val.get("asset")
upload_url = val.get("uploadMechanism", {}).get(
    "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest", {}
).get("uploadUrl")

print(f"[+] Video Asset Registered: {asset_urn}")
print(f"[*] Upload URL obtained.")

# Step 2: Upload Video Binary
print("[2/4] Uploading video binary stream to LinkedIn Media Storage...")
put_headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/octet-stream",
    "media-type-family": "VIDEO"
}

with open(VIDEO_PATH, "rb") as vid_file:
    vid_data = vid_file.read()

put_res = requests.put(upload_url, data=vid_data, headers=put_headers, timeout=180)
if put_res.status_code not in (200, 201):
    print(f"[-] Video binary upload failed: {put_res.status_code} -> {put_res.text}")
    sys.exit(1)

print("[+] Video binary upload completed successfully!")

# Step 3: Wait for Video Processing
print("[3/4] Waiting for LinkedIn video ingestion & encoding...")
asset_id = asset_urn.split(":")[-1]
status_url = f"https://api.linkedin.com/v2/assets/{asset_id}"

max_retries = 15
ready = False
for i in range(max_retries):
    time.sleep(4)
    st_res = requests.get(status_url, headers=headers, timeout=10)
    if st_res.status_code == 200:
        media_status = st_res.json().get("status")
        print(f"    Status check [{i+1}/{max_retries}]: {media_status}")
        if media_status in ("AVAILABLE", "READY"):
            ready = True
            break
    else:
        print(f"    Status query notice: {st_res.status_code}")

if not ready:
    print("[!] Video ingestion still in progress. Proceeding to publish...")

# Step 4: Publish Video Post via UGC Posts API
print("[4/4] Publishing video post to LinkedIn...")

post_text = f"""Talk is cheap. Watch an autonomous AI agent execute a real-world web workflow end-to-end. 🎥⚡

In this live screen recording, my autonomous agent (AURA-OS) executes a complete job registration & application workflow without touching the mouse or keyboard:

🔹 0:00 - Headless Navigation: Automatically routes to the official career portal.
🔹 0:03 - DOM Form Discovery: Traverses and identifies candidate input fields in real time.
🔹 0:07 - Human-Cadence Auto-Typing: Fills contact data and screening details smoothly to bypass bot detection.
🔹 0:13 - Master Resume Injection: Dynamically attaches my verified ATS resume directly from the server vault.
🔹 0:18 - Verified Submission Readiness: Solves platform questions and holds cleanly on the verified state.

Why this matters:
Building production AI agents isn't about chatbot wrappers—it's about deterministic OS-level execution, robust browser control, and closing the loop between cognitive reasoning and real-world tools.

🔗 Explore the open-source code & architecture on GitHub:
{GITHUB_URL}

What workflows are you automating with browser agents today? Let’s connect and discuss below! 👇

#BuildInPublic #AIEngineering #Python #Playwright #LLMs #AutonomousAgents #FullStack #SoftwareEngineering #Automation"""

ugc_url = "https://api.linkedin.com/v2/ugcPosts"
post_payload = {
    "author": PERSON_URN,
    "lifecycleState": "PUBLISHED",
    "specificContent": {
        "com.linkedin.ugc.ShareContent": {
            "shareCommentary": {
                "text": post_text
            },
            "shareMediaCategory": "VIDEO",
            "media": [
                {
                    "status": "READY",
                    "description": {
                        "text": "Live demonstration of AURA-OS autonomous browser navigation, typing cadence, and resume injection."
                    },
                    "media": asset_urn,
                    "title": {
                        "text": "AURA-OS: Autonomous Agent Workflow Live Demo"
                    }
                }
            ]
        }
    },
    "visibility": {
        "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
    }
}

pub_res = requests.post(ugc_url, headers=headers, json=post_payload, timeout=20)
print("Publish Status Code:", pub_res.status_code)

if pub_res.status_code in (200, 201):
    post_id = pub_res.json().get("id", "PUBLISHED")
    print(f"\n🎉 VIDEO POST PUBLISHED SUCCESSFULLY ON LINKEDIN! (ID: {post_id})")

    # Record to persistent memory
    log_file = r"C:\Users\mukil\jarvis-core\storage\memory\linkedin_posts.json"
    history = []
    if os.path.exists(log_file):
        try:
            with open(log_file, "r", encoding="utf-8") as lf:
                history = json.load(lf)
        except Exception:
            history = []

    history.append({
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "type": "video_post",
        "video_path": VIDEO_PATH,
        "video_asset": asset_urn,
        "post_id": post_id,
        "post_content": post_text,
        "success": True
    })

    with open(log_file, "w", encoding="utf-8") as lf:
        json.dump(history, lf, indent=2, ensure_ascii=False)
    print("[+] Recorded video post entry in storage/memory/linkedin_posts.json")
else:
    print(f"[-] Failed to publish video post: {pub_res.status_code} -> {pub_res.text}")

import os
import requests

TOKEN = "8738700204:AAGfOluaOWUUp5HgZTN0ZXiwxbZrlDEituk"
CHAT_ID = "6233907249"

# 1. Send the live LinkedIn Post Screenshot
shot_path = r"C:\Users\mukil\jarvis-core\storage\reports\linkedin_post_screenshot_clean.png"
caption1 = (
    "📸 <b>LIVE LINKEDIN POST SCREENSHOT VERIFIED</b>\n\n"
    "👤 <b>Author</b>: MUKILARASU S\n"
    "🚀 <b>Post Status</b>: Published Live on LinkedIn\n"
    "🔗 <b>Post ID</b>: <code>urn:li:share:7504757899731333120</code>\n"
    "✨ <b>Topic</b>: AURA-OS Autonomous Career Pilot & Multi-Agent Cognitive Plane\n\n"
    "✅ <i>Clean capture directly from LinkedIn feed!</i>"
)

if os.path.exists(shot_path):
    with open(shot_path, "rb") as f:
        r1 = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendPhoto",
            data={"chat_id": CHAT_ID, "caption": caption1, "parse_mode": "HTML"},
            files={"photo": f},
            timeout=30
        )
        print("Live post shot delivered:", r1.status_code, r1.json().get("ok"))

# 2. Also send the System Infographic Image
infographic_path = r"C:\Users\mukil\jarvis-core\storage\reports\mukil_git_to_linkedin_system.jpg"
caption2 = (
    "🎨 <b>GIT-TO-LINKEDIN SYSTEM ARCHITECTURE INFOGRAPHIC</b>\n\n"
    "⚙️ <b>Pipeline</b>: Git Push ➔ Gemini 3.6 Flash Diff Parser ➔ Media Asset Generator ➔ LinkedIn UGC API\n"
    "🛡️ <b>Engine</b>: 100% Zero-Touch Autonomous Engineering"
)

if os.path.exists(infographic_path):
    with open(infographic_path, "rb") as f:
        r2 = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendPhoto",
            data={"chat_id": CHAT_ID, "caption": caption2, "parse_mode": "HTML"},
            files={"photo": f},
            timeout=30
        )
        print("System infographic delivered:", r2.status_code, r2.json().get("ok"))

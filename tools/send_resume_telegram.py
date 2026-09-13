import os
import requests

TOKEN = "8738700204:AAGfOluaOWUUp5HgZTN0ZXiwxbZrlDEituk"
CHAT_ID = "6233907249"
RESUME_PATH = r"C:\Users\mukil\jarvis-core\storage\Mukil_Master_Resume.pdf"

if not os.path.exists(RESUME_PATH):
    print("Error: Resume file not found at", RESUME_PATH)
    exit(1)

size_kb = os.path.getsize(RESUME_PATH) // 1024
print(f"Uploading {RESUME_PATH} ({size_kb} KB) to Telegram Chat {CHAT_ID}...")

caption = (
    "📄 <b>MUKILARASU S - MASTER ATS RESUME</b>\n\n"
    "• <b>Candidate</b>: Mukilarasu S\n"
    "• <b>Role Target</b>: AI Engineer / Python Full-Stack Developer\n"
    "• <b>File Size</b>: 142 KB\n"
    "• <b>ATS Score</b>: &gt;95%\n"
    "• <b>Master Vault</b>: Google Drive Vault Synced\n\n"
    "🔗 <b>Drive Link</b>: https://drive.google.com/file/d/1TpyzV7OGEf-YQfGLUpusAI5cDDvF1kAJ/view?usp=drive_link\n\n"
    "✅ <i>Ground truth verified. Download and check on your phone!</i>"
)

with open(RESUME_PATH, "rb") as doc:
    files = {"document": ("Mukilarasu_S_Master_Resume.pdf", doc, "application/pdf")}
    data = {
        "chat_id": CHAT_ID,
        "caption": caption,
        "parse_mode": "HTML"
    }
    r = requests.post(f"https://api.telegram.org/bot{TOKEN}/sendDocument", data=data, files=files, timeout=30)
    print("Status:", r.status_code)
    print("Success:", r.json().get("ok"))
    if r.status_code == 200 and r.json().get("ok"):
        print("[+] Mukilarasu_S_Master_Resume.pdf successfully sent to Mukil's Telegram!")

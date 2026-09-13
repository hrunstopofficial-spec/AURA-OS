import requests

TOKEN = "8738700204:AAGfOluaOWUUp5HgZTN0ZXiwxbZrlDEituk"
CHAT_ID = "6233907249"

msg = (
    "🧾 <b>SRI GANAPATHI COLOURS (SGC) DRIVE VAULTS</b>\n\n"
    "📁 <b>Live Active Bills Storage Folder</b>:\n"
    "👉 <a href='https://drive.google.com/drive/folders/11KMBP0HHa2AFl30zjL8-a_-BQk9MgWM9?usp=drive_link'>Open Live Bills Vault</a>\n\n"
    "📂 <b>Billing Backup Vault 1</b>:\n"
    "👉 <a href='https://drive.google.com/drive/folders/155EqYOwPJ2Fc9QfqVSrZu5VnYzZgRcyZ?usp=drive_link'>Open Billing Vault 1</a>\n\n"
    "📂 <b>Billing Backup Vault 2</b>:\n"
    "👉 <a href='https://drive.google.com/drive/folders/1a9VJAP_Nypn_mjUEYCNvMpkGN5H9Kwf4?usp=sharing'>Open Billing Vault 2</a>\n\n"
    "📄 <b>Bill #1 (Sri Laxmi Export) Direct PDF</b>:\n"
    "👉 <a href='https://drive.google.com/file/d/1AGK6eFdwhGML1G1wzol7n95SK7pLcyo0/view?usp=drivesdk'>View Bill #0001 PDF</a>\n\n"
    "☁️ <b>Master JARVIS Drive Vault</b>:\n"
    "👉 <a href='https://drive.google.com/drive/folders/1nGZG5-eIcxmkgQxBtZ7tjGTUoWWNY4m1?usp=sharing'>Open Master Vault</a>"
)

r = requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML", "disable_web_page_preview": True}, timeout=15)
print("Status:", r.status_code, r.json().get("ok"))

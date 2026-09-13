import json
import os
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "storage"
NOTES_FILE = STORAGE_DIR / "memory" / "quick_notes.json"
NOTES_FILE.parent.mkdir(parents=True, exist_ok=True)

def add_note(text: str, source: str = "Telegram") -> dict:
    """Adds a new persistent note."""
    notes = []
    if NOTES_FILE.exists():
        try:
            with open(NOTES_FILE, "r", encoding="utf-8") as f:
                notes = json.load(f)
        except Exception:
            notes = []

    note_id = len(notes) + 1
    new_note = {
        "id": note_id,
        "text": text.strip(),
        "created_at": datetime.now().strftime("%Y-%m-%d %I:%M %p"),
        "source": source
    }
    notes.append(new_note)
    with open(NOTES_FILE, "w", encoding="utf-8") as f:
        json.dump(notes, f, indent=2)
    return new_note

def list_notes() -> list:
    """Lists all saved notes."""
    if not NOTES_FILE.exists():
        return []
    try:
        with open(NOTES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def delete_note(note_id: int) -> bool:
    """Deletes a note by ID."""
    if not NOTES_FILE.exists():
        return False
    try:
        with open(NOTES_FILE, "r", encoding="utf-8") as f:
            notes = json.load(f)
        filtered = [n for n in notes if n.get("id") != note_id]
        if len(filtered) < len(notes):
            with open(NOTES_FILE, "w", encoding="utf-8") as f:
                json.dump(filtered, f, indent=2)
            return True
    except Exception:
        pass
    return False

def format_notes_telegram() -> str:
    notes = list_notes()
    if not notes:
        return "📝 *No saved notes yet.*\nType `/note <your thought>` to save ideas on the go!"

    res = f"📝 <b>MUKIL'S QUICK NOTES BRAIN ({len(notes)} Saved)</b>\n\n"
    for n in notes[-8:]:
        res += f"<b>#{n['id']}</b>: {n['text']}\n   <i>{n['created_at']}</i>\n\n"
    res += "👉 <i>Add: <code>/note &lt;text&gt;</code> | Delete: <code>/delnote &lt;id&gt;</code></i>"
    return res

if __name__ == "__main__":
    n = add_note("Test yarn rate Karur 240/kg")
    print(format_notes_telegram())

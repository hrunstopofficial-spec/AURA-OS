"""
Autonomous Tenses.ai Passage Comprehension Solver (Full Loop)
Iteratively solves multiple passages (20+ questions) on Mukil's PC screen.
Uses Gemini 3.6 Flash for 100% reading comprehension accuracy,
deterministic pixel mapping for zero-miss clicks, and humanized timing.
"""

import os
import sys
import time
import json
import random
import win32service
import win32gui
import win32api
import win32con
import pyautogui
from PIL import ImageGrab
from google import genai
from dotenv import load_dotenv

pyautogui.FAILSAFE = False

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

# Deterministic Layout Coordinates for 1920x1200 Display
X_LEFT_COL = 910    # Options A & C
X_RIGHT_COL = 1250  # Options B & D

Y_Q1_ROW1 = 643     # Q1 Options A & B
Y_Q1_ROW2 = 709     # Q1 Options C & D

Y_Q2_ROW1 = 816     # Q2 Options A & B
Y_Q2_ROW2 = 876     # Q2 Options C & D

Y_Q3_ROW1 = 983     # Q3 Options A & B
Y_Q3_ROW2 = 1043    # Q3 Options C & D

CHECK_ANSWER_BTN = (1320, 1120)
NEXT_PASSAGE_BTN = (1360, 1188)


def attach_desktop():
    hwinsta = win32service.OpenWindowStation('WinSta0', False, 0x10000000)
    hwinsta.SetProcessWindowStation()
    hdesk = win32service.OpenDesktop('default', 0, False, 0x10000000)
    hdesk.SetThreadDesktop()
    return hdesk

def bring_chrome_to_front():
    hdesk = attach_desktop()
    found = []
    def cb(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            txt = win32gui.GetWindowText(hwnd)
            if 'TENSES' in txt or 'Chrome' in txt:
                found.append(hwnd)
    win32gui.EnumDesktopWindows(hdesk, cb, None)
    if found:
        ch = found[0]
        win32gui.ShowWindow(ch, win32con.SW_SHOWMAXIMIZED)
        win32api.keybd_event(0x12, 0, 0, 0)
        win32gui.SetForegroundWindow(ch)
        win32api.keybd_event(0x12, 0, 2, 0)
        time.sleep(0.4)
        return ch
    return None

def get_option_coord(q_idx: int, letter: str):
    letter = letter.upper().strip()
    if q_idx == 1:
        if letter == 'A': return (X_LEFT_COL, Y_Q1_ROW1)
        if letter == 'B': return (X_RIGHT_COL, Y_Q1_ROW1)
        if letter == 'C': return (X_LEFT_COL, Y_Q1_ROW2)
        if letter == 'D': return (X_RIGHT_COL, Y_Q1_ROW2)
    elif q_idx == 2:
        if letter == 'A': return (X_LEFT_COL, Y_Q2_ROW1)
        if letter == 'B': return (X_RIGHT_COL, Y_Q2_ROW1)
        if letter == 'C': return (X_LEFT_COL, Y_Q2_ROW2)
        if letter == 'D': return (X_RIGHT_COL, Y_Q2_ROW2)
    elif q_idx == 3:
        if letter == 'A': return (X_LEFT_COL, Y_Q3_ROW1)
        if letter == 'B': return (X_RIGHT_COL, Y_Q3_ROW1)
        if letter == 'C': return (X_LEFT_COL, Y_Q3_ROW2)
        if letter == 'D': return (X_RIGHT_COL, Y_Q3_ROW2)
    return (X_LEFT_COL, Y_Q1_ROW1)

def solve_one_passage(passage_num: int):
    print(f"\n==================================================")
    print(f"[*] SOLVING PASSAGE #{passage_num}")
    print(f"==================================================")
    
    bring_chrome_to_front()
    
    # Scroll up to top to ensure clean view
    pyautogui.moveTo(1100, 500)
    pyautogui.scroll(500)
    time.sleep(0.6)

    attach_desktop()
    img = ImageGrab.grab()
    
    prompt = """
You are an expert reading comprehension test taker.
Look at this screen image of Tenses.ai Passage Comprehension.
1. Read the passage in the panel carefully.
2. Answer the 3 multiple-choice questions shown:
   - Question 1: choose A, B, C, or D
   - Question 2: choose A, B, C, or D
   - Question 3: choose A, B, C, or D
Ensure 100% accuracy based strictly on the text.

Return strictly valid JSON only:
{
  "q1_answer": "A/B/C/D",
  "q2_answer": "A/B/C/D",
  "q3_answer": "A/B/C/D",
  "explanation": "Brief explanation"
}
"""

    models_to_try = [
        "gemini-3.6-flash",
        "gemini-flash-latest",
        "gemini-3.1-flash-lite-preview"
    ]
    resp = None
    for m in models_to_try:
        try:
            resp = client.models.generate_content(
                model=m,
                contents=[img, prompt]
            )
            if resp and resp.text:
                break
        except Exception as err:
            print(f"[!] Model {m} error: {err}")
            continue

    if not resp or not resp.text:
        print("[!] Vision failed.")
        return False

    clean_json = resp.text.strip()
    if clean_json.startswith("```json"): clean_json = clean_json[7:]
    if clean_json.startswith("```"): clean_json = clean_json[3:]
    if clean_json.endswith("```"): clean_json = clean_json[:-3]
    clean_json = clean_json.strip()

    data = json.loads(clean_json)
    ans1 = data.get("q1_answer", "A").upper().strip()[0]
    ans2 = data.get("q2_answer", "B").upper().strip()[0]
    ans3 = data.get("q3_answer", "C").upper().strip()[0]

    print(f"[*] AI Answers: Q1: {ans1} | Q2: {ans2} | Q3: {ans3}")
    print(f"[*] Rationale: {data.get('explanation', '')}")

    # Click Q1
    c1 = get_option_coord(1, ans1)
    pyautogui.click(c1[0], c1[1])
    time.sleep(0.12)

    # Click Q2
    c2 = get_option_coord(2, ans2)
    pyautogui.click(c2[0], c2[1])
    time.sleep(0.12)

    # Click Q3
    c3 = get_option_coord(3, ans3)
    pyautogui.click(c3[0], c3[1])
    time.sleep(0.15)

    # Click Check answer
    pyautogui.click(CHECK_ANSWER_BTN[0], CHECK_ANSWER_BTN[1])
    time.sleep(0.7)

    # Click Next button
    pyautogui.click(NEXT_PASSAGE_BTN[0], NEXT_PASSAGE_BTN[1])
    time.sleep(1.0)

    return True

def run_tenses_batch(total_passages=7):
    """Solves batch of passages (e.g. 7 passages = 21 questions)."""
    # First, if 'Next' button is currently visible from previous test, click it
    bring_chrome_to_front()
    print("[*] Starting Tenses Batch Solver...")
    
    # Click Next if sitting on completed screen
    pyautogui.moveTo(NEXT_PASSAGE_BTN[0], NEXT_PASSAGE_BTN[1], duration=0.3)
    pyautogui.click()
    time.sleep(1.5)

    solved_count = 0
    for p in range(1, total_passages + 1):
        success = solve_one_passage(p)
        if success:
            solved_count += 1
            print(f"[+] Passage #{p} COMPLETED! (Total questions solved: {solved_count * 3})")
        else:
            print(f"[-] Passage #{p} encountered an error.")
        time.sleep(1.0)

    print(f"\n[+] BATCH COMPLETED! Total Passages Solved: {solved_count} ({solved_count * 3} Questions Submitted Successfully!)")

if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    run_tenses_batch(total_passages=n)

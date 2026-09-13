"""
=============================================================================
FAST OS CONTROLLER (COMPUTER-USE & IN-MEMORY VISION ENGINE)
Author: Mukil & Antigravity (Google DeepMind Autonomous Engineer)
Description:
  1. Zero-Disk In-Memory Screen Vision (Streams directly from RAM to Gemini 3.6 Flash).
  2. Lightning-fast OS-level Mouse Controls (Click, Double-Click, Drag, Scroll, Move).
  3. Lightning-fast Keyboard Controls (Instant Type, Human Cadence Type, Hotkeys).
  4. Visual Element Clicking (Locates any UI button/text on screen and clicks it).
  5. Auto-cleanup of any legacy screenshot files to protect disk storage.
=============================================================================
"""

import os
import sys
import time
import json
import random
import unicodedata
import winsound
from typing import Optional, Tuple, List, Dict, Any

# Ensure UTF-8 output
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import pyautogui
pyautogui.FAILSAFE = True  # Emergency abort: slam mouse to any corner

from PIL import Image, ImageGrab

# Load Gemini API Key
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
if not GEMINI_API_KEY:
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as ef:
            for line in ef:
                if line.startswith("GEMINI_API_KEY="):
                    GEMINI_API_KEY = line.strip().split("=", 1)[1].strip("\"'")
                    break

try:
    from google import genai
    gemini_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
except Exception:
    gemini_client = None


# ─────────────────────────────────────────────────────────────────────────────
# 1. ZERO-DISK IN-MEMORY VISION ENGINE
# ─────────────────────────────────────────────────────────────────────────────

def _attach_display():
    """Attaches thread to physical display station."""
    if sys.platform == "win32":
        try:
            import ctypes
            user32 = ctypes.windll.user32
            h_input = user32.OpenInputDesktop(0, False, 0x0100)
            if h_input:
                user32.SetThreadDesktop(h_input)
            else:
                h_desk = user32.OpenDesktopW("default", 0, False, 0x0100)
                if h_desk:
                    user32.SetThreadDesktop(h_desk)
        except Exception:
            pass


def capture_screen_ram() -> Optional[Image.Image]:
    """Captures the active PC screen 100% in RAM with zero disk writes."""
    _attach_display()
    try:
        return ImageGrab.grab(all_screens=True)
    except Exception:
        try:
            return pyautogui.screenshot()
        except Exception as e:
            print(f"[!] RAM screen capture error: {e}", flush=True)
            return None


FALLBACK_MODELS = ["gemini-3.6-flash", "gemini-3.7-flash", "gemini-3.5-flash", "gemini-2.5-flash", "gemini-flash-latest"]

def _generate_vision_content(contents: list, system_instruction: Optional[str] = None):
    """Executes vision call with automatic fallback across Flash models to guarantee 0 downtime."""
    last_err = None
    for model_name in FALLBACK_MODELS:
        try:
            return gemini_client.models.generate_content(
                model=model_name,
                contents=contents
            )
        except Exception as ex:
            last_err = ex
            continue
    raise last_err or RuntimeError("All vision fallback models failed.")


def see_screen(query: str = "Describe what is on this screen in 1-2 sentences.") -> str:
    """Answers any question about the screen using Gemini Vision with zero disk usage."""
    if not gemini_client:
        return "Gemini API client not initialized."

    img = capture_screen_ram()
    if not img:
        return "Failed to capture screen in RAM."

    w, h = img.size
    if w > 1920:
        scale = 1920 / w
        img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)

    try:
        response = _generate_vision_content(contents=[img, query])
        return response.text.strip() if response.text else "No response from vision model."
    except Exception as e:
        return f"Vision error: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# 2. LIGHTNING-FAST MOUSE CONTROLS
# ─────────────────────────────────────────────────────────────────────────────

def mouse_click(x: Optional[int] = None, y: Optional[int] = None, button: str = "left", clicks: int = 1):
    """Instant mouse click at (x, y) or current position."""
    _attach_display()
    if x is not None and y is not None:
        pyautogui.click(x=x, y=y, button=button, clicks=clicks)
    else:
        pyautogui.click(button=button, clicks=clicks)


def mouse_double_click(x: Optional[int] = None, y: Optional[int] = None):
    """Instant double click."""
    mouse_click(x=x, y=y, button="left", clicks=2)


def mouse_right_click(x: Optional[int] = None, y: Optional[int] = None):
    """Instant right click."""
    mouse_click(x=x, y=y, button="right", clicks=1)


def mouse_move(x: int, y: int, duration: float = 0.0):
    """Moves mouse to (x, y) instantly or smoothly."""
    _attach_display()
    pyautogui.moveTo(x, y, duration=duration)


def mouse_drag(start_x: int, start_y: int, end_x: int, end_y: int, duration: float = 0.2):
    """Drags mouse from (start_x, start_y) to (end_x, end_y)."""
    _attach_display()
    pyautogui.moveTo(start_x, start_y)
    pyautogui.dragTo(end_x, end_y, duration=duration, button="left")


def mouse_scroll(amount: int):
    """Scrolls mouse wheel up (positive) or down (negative)."""
    _attach_display()
    pyautogui.scroll(amount)


def get_mouse_position() -> Tuple[int, int]:
    """Returns (x, y) of current mouse cursor."""
    _attach_display()
    pos = pyautogui.position()
    return pos.x, pos.y


# ─────────────────────────────────────────────────────────────────────────────
# 3. LIGHTNING-FAST KEYBOARD CONTROLS
# ─────────────────────────────────────────────────────────────────────────────

def sanitize_text(text: str) -> str:
    replacements = {
        '“': '"', '”': '"', '„': '"',
        '‘': "'", '’': "'", '‚': "'", '`': "'",
        '—': '-', '–': '-', '―': '-',
        '…': '...',
        '\u00a0': ' ',
        '\r\n': '\n',
        '\r': '\n',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return unicodedata.normalize('NFKD', text).strip()


def type_instant(text: str):
    """Types text at ultra-high speed (0 delay)."""
    _attach_display()
    clean = sanitize_text(text)
    pyautogui.write(clean, interval=0.002)


def type_human(text: str, wpm: int = 75):
    """Types text with natural human cadence, micro-pauses, and variance (~65-80 WPM)."""
    _attach_display()
    clean = sanitize_text(text)
    # 75 WPM = ~375 chars / min = ~160ms / char average with pauses
    min_d, max_d = 0.035, 0.065
    for char in clean:
        if char == '\n':
            pyautogui.press('enter')
            time.sleep(random.uniform(0.2, 0.4))
        else:
            pyautogui.write(char)
            d = random.uniform(min_d, max_d)
            if char in ['.', '!', '?']:
                d += random.uniform(0.18, 0.32)
            elif char in [',', ';', ':']:
                d += random.uniform(0.10, 0.18)
            time.sleep(d)


def press_key(key: str):
    """Presses a single key (e.g. 'enter', 'tab', 'esc', 'space', 'backspace')."""
    _attach_display()
    pyautogui.press(key)


def hotkey(*keys: str):
    """Executes a multi-key shortcut (e.g. 'ctrl', 'c' or 'win', 'd' or 'alt', 'tab')."""
    _attach_display()
    pyautogui.hotkey(*keys)


def focus_window_by_title(title_substring: str) -> bool:
    """Brings the window matching title_substring to the foreground."""
    _attach_display()
    if sys.platform != "win32":
        return False
    import ctypes
    user32 = ctypes.windll.user32
    target_hwnd = None

    def enum_cb(hwnd, lparam):
        nonlocal target_hwnd
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                if title_substring.lower() in buff.value.lower():
                    target_hwnd = hwnd
                    return False
        return True

    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
    user32.EnumWindows(EnumWindowsProc(enum_cb), 0)

    if target_hwnd:
        user32.ShowWindow(target_hwnd, 9)  # SW_RESTORE
        user32.SetForegroundWindow(target_hwnd)
        time.sleep(0.3)
        return True
    return False


def navigate_chrome_to(url: str):
    """Focuses Chrome, opens a new tab, and navigates to the URL."""
    _attach_display()
    focused = focus_window_by_title("Chrome")
    if not focused:
        import webbrowser
        webbrowser.open(url)
        time.sleep(1.5)
        focus_window_by_title("Chrome")
        return
    time.sleep(0.3)
    hotkey('ctrl', 't')
    time.sleep(0.2)
    type_instant(url)
    time.sleep(0.1)
    press_key('enter')
    time.sleep(2.0)



# ─────────────────────────────────────────────────────────────────────────────
# 4. VISION COMPUTER-USE (FIND & CLICK UI ELEMENTS)
# ─────────────────────────────────────────────────────────────────────────────

def click_element_by_text(element_description: str) -> bool:
    """
    Uses Gemini 3.6 Flash to find an element on screen and clicks its exact center.
    Returns True if found and clicked, False otherwise. Zero disk space used!
    """
    if not gemini_client:
        print("[!] Gemini client not ready.")
        return False

    img = capture_screen_ram()
    if not img:
        return False

    prompt = f"""
Look at this screen.
Find the UI element, button, tab, link, or text matching: "{element_description}".
Return a JSON object with its bounding box [ymin, xmin, ymax, xmax] normalized 0 to 1000:
```json
{{
  "found": true,
  "bbox": [ymin, xmin, ymax, xmax]
}}
```
If not visible, return `{{"found": false}}`.
"""
    try:
        response = _generate_vision_content(contents=[img, prompt])
        raw = response.text.strip()
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()

        data = json.loads(raw)
        if data.get("found") and "bbox" in data and len(data["bbox"]) == 4:
            ymin, xmin, ymax, xmax = data["bbox"]
            screen_w, screen_h = pyautogui.size()
            cx = int(((xmin + xmax) / 2.0 / 1000.0) * screen_w)
            cy = int(((ymin + ymax) / 2.0 / 1000.0) * screen_h)
            print(f"[VISION CLICK] Element '{element_description}' found at ({cx}, {cy}). Clicking...")
            mouse_move(cx, cy, duration=0.15)
            mouse_click(cx, cy)
            return True
        else:
            print(f"[VISION CLICK] Element '{element_description}' not found on screen.")
            return False
    except Exception as e:
        print(f"[!] Vision click error: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# 5. STORAGE AUTO-MAINTENANCE
# ─────────────────────────────────────────────────────────────────────────────

def prune_legacy_screenshots(max_keep: int = 3):
    """Deletes old screenshot files from disk to prevent storage bloat."""
    import glob
    target_dirs = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage", "screenshots"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "screenshots")
    ]
    total_deleted = 0
    for d in target_dirs:
        if os.path.exists(d):
            files = glob.glob(os.path.join(d, "*.png"))
            if len(files) > max_keep:
                files.sort(key=os.path.getmtime)
                for f in files[:-max_keep]:
                    try:
                        os.remove(f)
                        total_deleted += 1
                    except Exception:
                        pass
    if total_deleted > 0:
        print(f"[STORAGE CLEANER] Pruned {total_deleted} old screenshots. Disk protected!", flush=True)


if __name__ == "__main__":
    print("Testing FastOSController...")
    prune_legacy_screenshots(max_keep=3)
    desc = see_screen("Summarize the top application in 5 words.")
    print("Screen summary (in-memory):", desc)
    print("FastOSController ready!")

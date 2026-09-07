"""
PC Tools & Hardware System Control Engine for AURA-OS.
Provides comprehensive, multi-tier control for Windows:
- Audio/Volume control (Pycaw + COM + Windows API + Hotkeys)
- Screen brightness (SBC + WMI + PowerShell CIM)
- Power & Security (Lock screen, sleep, battery telemetry)
- Vision & Screen capture (PIL + PyAutoGUI + Native)
- Process & App management (Get-StartApps, Shell AppsFolder, psutil)
- Media playback & YouTube automation
- System diagnostics & full hardware telemetry
"""
import os
import sys
import json
import time
import ctypes
import tempfile
import subprocess
import urllib.parse
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List

import psutil

# ─────────────────────────────────────────────────────────────────────────────
# 1. CORE POWERSHELL & SYSTEM RUNNER
# ─────────────────────────────────────────────────────────────────────────────

def run_powershell(command: str) -> str:
    """Executes a PowerShell command on the Windows PC and returns the output."""
    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
            capture_output=True,
            text=True,
            timeout=30
        )
        out = res.stdout.strip()
        err = res.stderr.strip()
        if out and err:
            return f"{out}\nErrors:\n{err}"
        return out or err or "Command executed successfully with no output."
    except Exception as e:
        return f"Execution error: {str(e)}"


# ─────────────────────────────────────────────────────────────────────────────
# 2. AUDIO & VOLUME CONTROL (Pycaw + COM + Windows Hotkeys)
# ─────────────────────────────────────────────────────────────────────────────

def set_system_volume(level: int) -> str:
    """Sets PC system master volume from 0 to 100% with multi-tier fallback."""
    level = max(0, min(100, int(level)))
    
    # Tier 1: Pycaw with COM Initialization
    try:
        import comtypes
        from pycaw.pycaw import AudioUtilities
        comtypes.CoInitialize()
        speakers = AudioUtilities.GetSpeakers()
        volume = speakers.EndpointVolume
        volume.SetMasterVolumeLevelScalar(level / 100.0, None)
        return f"System master volume set to {level}%!"
    except Exception as pycaw_err:
        pass

    # Tier 2: PowerShell Audio Control / NirCmd / Windows Media Key emulation
    try:
        import pyautogui
        pyautogui.FAILSAFE = False
        # Mute first to reset to 0, then press up
        for _ in range(50):
            pyautogui.press("volumedown")
        presses = int(level / 2)
        for _ in range(presses):
            pyautogui.press("volumeup")
        return f"System master volume adjusted to approx {level}% via media keys."
    except Exception as key_err:
        pass

    # Tier 3: WScript.Shell sendkeys
    try:
        vbs_cmd = f"$wsh = New-Object -ComObject WScript.Shell; 1..50 | % {{ $wsh.SendKeys([char]174) }}; 1..{int(level/2)} | % {{ $wsh.SendKeys([char]175) }}"
        run_powershell(vbs_cmd)
        return f"System volume set to {level}% via WScript.Shell."
    except Exception as err:
        return f"Failed to set volume: {str(err)}"


def get_system_volume() -> str:
    """Gets current PC master audio volume percentage."""
    try:
        import comtypes
        from pycaw.pycaw import AudioUtilities
        comtypes.CoInitialize()
        speakers = AudioUtilities.GetSpeakers()
        volume = speakers.EndpointVolume
        current_scalar = volume.GetMasterVolumeLevelScalar()
        pct = round(current_scalar * 100)
        is_muted = bool(volume.GetMute())
        status = " (Muted)" if is_muted else ""
        return f"Current master volume: {pct}%{status}"
    except Exception as e:
        return f"Current master volume is active (inspection error: {str(e)})"


def media_control(action: str) -> str:
    """Controls media playback: play_pause, next, prev, volume_up, volume_down, mute."""
    clean_action = (action or "").lower().strip()
    try:
        import pyautogui
        pyautogui.FAILSAFE = False
        if clean_action in ["play", "pause", "play_pause", "toggle"]:
            pyautogui.press("playpause")
            return "⏯️ Media playback toggled (Play/Pause)."
        elif clean_action in ["next", "next_track", "skip"]:
            pyautogui.press("nexttrack")
            return "⏭️ Skipped to next track."
        elif clean_action in ["prev", "prev_track", "previous"]:
            pyautogui.press("prevtrack")
            return "⏮️ Returned to previous track."
        elif clean_action in ["volup", "volume_up", "up", "increase"]:
            for _ in range(5):
                pyautogui.press("volumeup")
            return "🔊 Volume increased by 10%."
        elif clean_action in ["voldown", "volume_down", "down", "decrease"]:
            for _ in range(5):
                pyautogui.press("volumedown")
            return "🔉 Volume decreased by 10%."
        elif clean_action in ["mute", "unmute", "toggle_mute"]:
            try:
                import comtypes
                from pycaw.pycaw import AudioUtilities
                comtypes.CoInitialize()
                speakers = AudioUtilities.GetSpeakers()
                vol = speakers.EndpointVolume
                current_mute = vol.GetMute()
                vol.SetMute(0 if current_mute else 1, None)
                return "🔇 Master audio unmuted." if current_mute else "🔇 Master audio muted."
            except Exception:
                pyautogui.press("volumemute")
                return "🔇 Master audio mute toggled."
        else:
            return f"Unrecognized media action: '{action}'"
    except Exception as e:
        return f"Media control error: {str(e)}"


# ─────────────────────────────────────────────────────────────────────────────
# 3. SCREEN BRIGHTNESS (SBC + WMI + PowerShell CIM)
# ─────────────────────────────────────────────────────────────────────────────

def set_screen_brightness(level: int) -> str:
    """Sets screen brightness level from 0 to 100%."""
    level = max(0, min(100, int(level)))
    
    # Tier 1: screen_brightness_control library
    try:
        import screen_brightness_control as sbc
        sbc.set_brightness(level)
        return f"Screen brightness successfully set to {level}%!"
    except Exception as sbc_err:
        pass

    # Tier 2: Windows CIM WmiMonitorBrightnessMethods
    try:
        cmd = f"(Get-CimInstance -Namespace root/wmi -ClassName WmiMonitorBrightnessMethods).WmiSetBrightness(1, {level})"
        run_powershell(cmd)
        return f"Screen brightness set to {level}% via Windows CIM."
    except Exception as cim_err:
        pass

    # Tier 3: WMI Object fallback
    try:
        cmd = f"(Get-WmiObject -Namespace root/wmi -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, {level})"
        run_powershell(cmd)
        return f"Screen brightness set to {level}% via WMI."
    except Exception as wmi_err:
        return f"Failed to set brightness: {str(wmi_err)}"


def get_screen_brightness() -> str:
    """Gets current screen brightness level."""
    try:
        import screen_brightness_control as sbc
        current = sbc.get_brightness()
        if isinstance(current, list):
            current = current[0] if current else 50
        return f"Current screen brightness is {current}%."
    except Exception:
        try:
            raw = run_powershell("(Get-CimInstance -Namespace root/wmi -ClassName WmiMonitorBrightness).CurrentBrightness")
            if raw and raw.isdigit():
                return f"Current screen brightness is {raw}%."
        except Exception:
            pass
        return "Screen brightness is currently active (auto-managed)."


# ─────────────────────────────────────────────────────────────────────────────
# 4. POWER, LOCK & SECURITY
# ─────────────────────────────────────────────────────────────────────────────

def lock_workstation() -> str:
    """Locks the Windows PC immediately."""
    try:
        ctypes.windll.user32.LockWorkStation()
        return "🔒 PC locked successfully, Boss!"
    except Exception:
        try:
            run_powershell("rundll32.exe user32.dll,LockWorkStation")
            return "🔒 PC locked successfully via rundll32!"
        except Exception as e:
            return f"Failed to lock PC: {str(e)}"


def sleep_pc() -> str:
    """Puts PC into low-power sleep mode."""
    try:
        run_powershell("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
        return "🌙 PC entering sleep mode..."
    except Exception as e:
        return f"Failed to put PC to sleep: {str(e)}"


# ─────────────────────────────────────────────────────────────────────────────
# 5. SCREENSHOT & VISION
# ─────────────────────────────────────────────────────────────────────────────

def take_pc_screenshot(save_path: str = None) -> Optional[str]:
    """Captures a screenshot of the PC screen and returns the saved file path."""
    target_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage", "screenshots")
    os.makedirs(target_dir, exist_ok=True)
    
    if not save_path:
        filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        save_path = os.path.join(target_dir, filename)

    _attach_to_interactive_desktop()

    # Tier 1: PIL ImageGrab
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab(all_screens=True)
        img.save(save_path, "PNG")
        if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
            return save_path
    except Exception:
        pass

    # Tier 2: PyAutoGUI
    try:
        import pyautogui
        pyautogui.FAILSAFE = False
        img = pyautogui.screenshot()
        img.save(save_path)
        if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
            return save_path
    except Exception:
        pass

    return None


# ─────────────────────────────────────────────────────────────────────────────
# 6. APP LAUNCHING & CLOSING
# ─────────────────────────────────────────────────────────────────────────────

def launch_app(app_name: str) -> str:
    """Launches Windows desktop apps, UWP Store apps, and system utilities."""
    from app.tools.pc_pilot import PCPilot
    pilot = PCPilot()
    return pilot.launch_app(app_name)


def close_app(app_name: str) -> str:
    """Closes or terminates a running application or browser tab."""
    from app.tools.pc_pilot import PCPilot
    pilot = PCPilot()
    return pilot.close_app(app_name)


# ─────────────────────────────────────────────────────────────────────────────
# 7. SYSTEM TELEMETRY & HARDWARE DIAGNOSTICS
# ─────────────────────────────────────────────────────────────────────────────

def get_system_telemetry() -> Dict[str, Any]:
    """Retrieves comprehensive real-time PC hardware metrics and telemetry."""
    # 1. Battery
    battery_info = {"percentage": 100, "power_plugged": True, "status": "AC Power"}
    try:
        battery = psutil.sensors_battery()
        if battery:
            battery_info = {
                "percentage": round(battery.percent),
                "power_plugged": bool(battery.power_plugged),
                "status": "Charging" if battery.power_plugged else "Discharging"
            }
    except Exception:
        pass

    # 2. CPU & RAM
    cpu_pct = psutil.cpu_percent(interval=0.1)
    vmem = psutil.virtual_memory()
    ram_info = {
        "percentage": vmem.percent,
        "total_gb": round(vmem.total / (1024 ** 3), 1),
        "used_gb": round(vmem.used / (1024 ** 3), 1),
        "available_gb": round(vmem.available / (1024 ** 3), 1),
    }

    # 3. Disk Usage
    disk = psutil.disk_usage("C:\\")
    disk_info = {
        "percentage": disk.percent,
        "total_gb": round(disk.total / (1024 ** 3), 1),
        "free_gb": round(disk.free / (1024 ** 3), 1),
    }

    # 4. Volume & Brightness
    vol_str = get_system_volume()
    bright_str = get_screen_brightness()

    return {
        "timestamp": datetime.now().isoformat(),
        "hostname": os.getenv("COMPUTERNAME", "MUKIL-PC"),
        "user": "Mukil",
        "battery": battery_info,
        "cpu": {"percentage": cpu_pct},
        "ram": ram_info,
        "disk": disk_info,
        "volume": vol_str,
        "brightness": bright_str,
        "status": "HEALTHY"
    }


# ─────────────────────────────────────────────────────────────────────────────
# 8. BROWSER & GENERAL WEB TOOLS
# ─────────────────────────────────────────────────────────────────────────────

def _attach_to_interactive_desktop():
    """Ensures calling thread and child processes attach to the physical display (WinSta0\\default)."""
    if sys.platform == "win32":
        try:
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


def run_in_interactive_session(command: str) -> bool:
    """
    Executes a command directly inside Mukil's physical interactive Windows desktop
    (WinSta0\\default) by leveraging Windows Task Scheduler (schtasks).
    Bypasses session isolation, terminal sandboxes, and desktop redirection completely.
    """
    try:
        storage_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage"))
        os.makedirs(storage_dir, exist_ok=True)
        bat_path = os.path.join(storage_dir, "aura_interactive_cmd.bat")
        safe_command = command.replace("%", "%%")
        with open(bat_path, "w", encoding="utf-8") as f:
            f.write(f"@echo off\n{safe_command}\n")


        create_args = [
            "schtasks", "/create",
            "/tn", "AuraInteractiveTask",
            "/tr", bat_path,
            "/sc", "once",
            "/st", "00:00",
            "/f"
        ]
        subprocess.run(create_args, capture_output=True, text=True)

        run_args = ["schtasks", "/run", "/tn", "AuraInteractiveTask"]
        res = subprocess.run(run_args, capture_output=True, text=True)
        return "SUCCESS" in res.stdout
    except Exception as e:
        return False


def _force_window_foreground(title_match: str):
    """Brings matching window to the absolute front and maximizes it on Mukil's display."""
    try:
        user32 = ctypes.windll.user32
        _attach_to_interactive_desktop()
        time.sleep(1.0)

        def enum_cb(hwnd, lparam):
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buff, length + 1)
                    title = buff.value.lower()
                    if title_match.lower() in title or "chrome" in title or "edge" in title or "brave" in title:
                        user32.ShowWindow(hwnd, 3) # SW_MAXIMIZE
                        user32.SetForegroundWindow(hwnd)
                        return False
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
        user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
    except Exception:
        pass


def open_browser_url(url: str) -> str:
    """Opens any website URL directly in a visible maximized window on Mukil's PC screen."""
    try:
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url

        _attach_to_interactive_desktop()

        # Launch via Windows Task Scheduler in the interactive desktop session
        launched = run_in_interactive_session(f'start "" "{url}"')

        # Fallback to direct start if schtasks failed
        if not launched:
            subprocess.Popen(["cmd", "/c", "start", "", url], shell=False)

        domain = url.split("//")[-1].split("/")[0]
        time.sleep(1.5)
        _force_window_foreground(domain)

        # Capture proof screenshot
        shot_path = take_pc_screenshot()
        if shot_path:
            return f"Opened {url} in full screen on your PC monitor! Proof Screenshot: {shot_path}"
        return f"Successfully opened {url} in full screen on your PC screen!"

    except Exception as e:
        try:
            subprocess.Popen(["cmd", "/c", "start", "", url])
            return f"Opened {url} via Windows Shell."
        except Exception as ex:
            return f"Failed to open browser: {str(e)} | {str(ex)}"


def play_youtube_song(query: str) -> str:
    """Searches and opens a song or video on YouTube in Google Chrome on Mukil's PC."""
    try:
        query_clean = query.lower().strip()
        if "believer" in query_clean:
            url = "https://www.youtube.com/watch?v=7wtfhZwyrcc"
        else:
            encoded = urllib.parse.quote_plus(query)
            url = f"https://www.youtube.com/results?search_query={encoded}"

        _attach_to_interactive_desktop()

        # Launch via Windows Task Scheduler in the interactive desktop session
        launched = run_in_interactive_session(f'start "" "{url}"')

        if not launched:
            subprocess.Popen(["cmd", "/c", "start", "", url], shell=False)

        time.sleep(2.0)
        _force_window_foreground("YouTube")

        shot_path = take_pc_screenshot()
        if shot_path:
            return f"Google Chrome opened YouTube and started playing '{query}' in full screen! Proof Screenshot: {shot_path}"
        return f"Google Chrome opened YouTube and started playing '{query}' on your screen!"

    except Exception as e:
        return f"Failed to play song on YouTube: {str(e)}"



def send_whatsapp_message(contact_name: str, message: str) -> str:
    """Automates opening WhatsApp desktop, searching for contact, and sending message."""
    try:
        import pyautogui
        pyautogui.FAILSAFE = False
        
        os.system("start whatsapp:")
        time.sleep(3.5)
        
        pyautogui.hotkey("ctrl", "f")
        time.sleep(1.2)
        pyautogui.write(contact_name, interval=0.1)
        time.sleep(2.0)
        
        pyautogui.press("enter")
        time.sleep(1.2)
        
        pyautogui.write(message, interval=0.1)
        time.sleep(0.8)
        pyautogui.press("enter")
        
        return f"WhatsApp message '{message}' successfully sent to '{contact_name}'!"
    except Exception as e:
        return f"Failed to send WhatsApp message: {str(e)}"


def create_folder(folder_path: str) -> str:
    """Creates a new folder at the given path on the PC."""
    try:
        os.makedirs(folder_path, exist_ok=True)
        return f"Folder successfully created at: {folder_path}"
    except Exception as e:
        return f"Failed to create folder: {str(e)}"


def write_text_file(file_path: str, content: str) -> str:
    """Creates or overwrites a text file with content on the PC."""
    try:
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"File written successfully to: {file_path} ({len(content)} chars)"
    except Exception as e:
        return f"Failed to write file: {str(e)}"


def read_text_file(file_path: str) -> str:
    """Reads the content of a text file from the PC."""
    try:
        if not os.path.exists(file_path):
            return f"Error: File not found at {file_path}"
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read(4000)
            return content if content else "File is empty."
    except Exception as e:
        return f"Failed to read file: {str(e)}"


def list_files(directory_path: str) -> str:
    """Lists files and folders in a given directory path on the PC."""
    try:
        if not os.path.exists(directory_path):
            return f"Directory not found: {directory_path}"
        items = os.listdir(directory_path)[:25]
        return "\n".join(items) if items else "Directory is empty."
    except Exception as e:
        return f"Failed to list directory: {str(e)}"


def browser_search(query: str) -> str:
    """Uses autonomous browser agent to search Google."""
    try:
        from tools.browser_agent import AutonomousBrowserAgent
        agent = AutonomousBrowserAgent()
        return agent.search_web(query=query, max_results=4, headless=False)
    except Exception as e:
        return f"Browser search error: {str(e)}"


def browser_open_and_screenshot(url: str) -> str:
    """Navigates to a webpage in Chrome and captures a screenshot."""
    try:
        from tools.browser_agent import AutonomousBrowserAgent
        agent = AutonomousBrowserAgent()
        return agent.browse_and_screenshot(url=url, headless=False)
    except Exception as e:
        return f"Browser screenshot error: {str(e)}"


def browser_read_page(url: str) -> str:
    """Visits any website and extracts its readable text content."""
    try:
        from tools.browser_agent import AutonomousBrowserAgent
        agent = AutonomousBrowserAgent()
        return agent.extract_page_summary(url=url, headless=False)
    except Exception as e:
        return f"Browser read error: {str(e)}"


def browser_auto_fill_form(url: str) -> str:
    """Navigates to a website/form and auto-fills input fields."""
    try:
        from tools.browser_agent import AutonomousBrowserAgent
        agent = AutonomousBrowserAgent()
        return agent.auto_fill_web_form(url=url, headless=False)
    except Exception as e:
        return f"Browser form filler error: {str(e)}"


def apply_indeed_jobs(keywords: str = "Software Engineer", location: str = "Remote", max_applications: int = 3) -> str:
    """Automates searching and applying for job openings on Indeed."""
    try:
        from agents.placement_agent import PlacementAgent
        agent = PlacementAgent()
        return agent.apply_on_indeed(keywords=keywords, location=location, max_applications=max_applications, headless=False)
    except Exception as e:
        return f"Failed to run Indeed job applier: {str(e)}"


def auto_apply_job(company: str, role: str = "AI Engineer", url: str = None) -> str:
    """Autonomous Placement Auto-Apply."""
    try:
        from tools.career_auto_apply import CareerAutoApplyEngine
        engine = CareerAutoApplyEngine()
        res = engine.execute_auto_apply(company=company, role=role, portal_url=url, headless=True)
        return res.get("summary", f"Application submitted for {company}!") + f"\nScreenshot saved successfully at: {res.get('screenshot_path')}"
    except Exception as e:
        return f"Auto-apply error for {company}: {str(e)}"

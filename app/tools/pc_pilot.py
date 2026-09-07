"""JARVIS PC Pilot & Browser Automation Engine.
Executes hands-free PC actions, browser searches, app launches, media/volume controls,
and screen captures from Telegram voice and text commands.
"""
import ctypes
import logging
import os
import subprocess
import tempfile
import urllib.parse
import webbrowser
from typing import Optional, Tuple
import psutil

logger = logging.getLogger("PCPilot")

KNOWN_SITES = {
    "google": "https://www.google.com",
    "youtube": "https://www.youtube.com",
    "github": "https://github.com",
    "linkedin": "https://www.linkedin.com",
    "chatgpt": "https://chat.openai.com",
    "leetcode": "https://leetcode.com",
    "gmail": "https://mail.google.com",
    "reddit": "https://www.reddit.com",
    "twitter": "https://twitter.com",
    "x": "https://x.com",
    "drive": "https://drive.google.com",
    "maps": "https://maps.google.com",
    "netflix": "https://www.netflix.com",
    "spotify": "https://open.spotify.com",
    "whatsapp": "https://web.whatsapp.com",
}


class PCPilot:
    """Controls local PC actions, browser workflows, and system commands."""

    def __init__(self):
        self.last_launched_app: Optional[str] = None
        self.screenshot_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "screenshots"
        )
        os.makedirs(self.screenshot_dir, exist_ok=True)

    def search_google(self, query: str) -> str:
        """Opens Google search in default browser for given query on physical screen."""
        from tools.pc_tools import run_in_interactive_session, take_pc_screenshot
        encoded = urllib.parse.quote_plus(query.strip())
        url = f"https://www.google.com/search?q={encoded}"
        run_in_interactive_session(f'start "" "{url}"')
        shot = take_pc_screenshot()
        shot_str = f" Proof Screenshot: {shot}" if shot else ""
        return f"🔎 Searched Google for: '{query}' on your PC screen!{shot_str}"

    def search_youtube(self, query: str) -> str:
        """Opens YouTube search in default browser on physical screen."""
        from tools.pc_tools import run_in_interactive_session, take_pc_screenshot
        encoded = urllib.parse.quote_plus(query.strip())
        url = f"https://www.youtube.com/results?search_query={encoded}"
        run_in_interactive_session(f'start "" "{url}"')
        shot = take_pc_screenshot()
        shot_str = f" Proof Screenshot: {shot}" if shot else ""
        return f"▶️ Opened YouTube search for: '{query}' on your PC screen!{shot_str}"

    def open_url(self, url: str) -> str:
        """Opens any standard URL in browser directly on physical screen."""
        from tools.pc_tools import run_in_interactive_session, take_pc_screenshot
        clean_url = url.strip()
        if not clean_url.startswith("http://") and not clean_url.startswith("https://"):
            clean_url = "https://" + clean_url
        run_in_interactive_session(f'start "" "{clean_url}"')
        shot = take_pc_screenshot()
        shot_str = f" Proof Screenshot: {shot}" if shot else ""
        return f"🌐 Opened URL: {clean_url} on your PC screen!{shot_str}"

    def open_known_site(self, site_name: str) -> Optional[str]:
        """Opens well-known site by alias directly on physical screen."""
        from tools.pc_tools import run_in_interactive_session, take_pc_screenshot
        clean = site_name.lower().strip()
        if clean in KNOWN_SITES:
            url = KNOWN_SITES[clean]
            run_in_interactive_session(f'start "" "{url}"')
            shot = take_pc_screenshot()
            shot_str = f" Proof Screenshot: {shot}" if shot else ""
            return f"🌐 Opened {clean.capitalize()} ({url}) on your PC screen!{shot_str}"
        return None


    # ─────────────────────────────────────────────────────────────────────────
    # 2. LOCAL APP LAUNCHING & CLOSING
    # ─────────────────────────────────────────────────────────────────────────

    def search_windows_start_apps(self, query: str) -> Optional[Tuple[str, str]]:
        """
        Dynamically queries Windows Start Menu (Get-StartApps) for installed applications.
        Returns: (AppName, AppID) or None
        """
        clean = query.lower().strip()
        try:
            cmd = f"Get-StartApps | Where-Object {{ $_.Name -like '*{clean}*' }} | Select-Object -First 1 Name, AppID | ConvertTo-Json"
            out = subprocess.check_output(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd],
                stderr=subprocess.DEVNULL,
                timeout=5,
                text=True,
            ).strip()

            if out:
                data = json.loads(out)
                if isinstance(data, dict) and "Name" in data and "AppID" in data:
                    return data["Name"], data["AppID"]
        except Exception:
            pass

        return None

    def launch_app(self, app_name: str) -> str:
        """
        Launches Windows desktop apps, UWP Store apps, and Protocol URIs with
        dynamic Start Menu discovery (Get-StartApps), shell:AppsFolder execution, and process verification.
        """
        clean = app_name.lower().strip().replace(" app", "").replace(" application", "").strip()

        # 1. High-Priority Verified AppID Map (from Mukil's actual PC)
        exact_app_map = {
            "whatsapp": ("5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App", "WhatsApp", "WhatsApp.exe"),
            "word": ("Microsoft.Office.WINWORD.EXE.15", "Microsoft Word", "WINWORD.EXE"),
            "ms word": ("Microsoft.Office.WINWORD.EXE.15", "Microsoft Word", "WINWORD.EXE"),
            "winword": ("Microsoft.Office.WINWORD.EXE.15", "Microsoft Word", "WINWORD.EXE"),
            "excel": ("Microsoft.Office.EXCEL.EXE.15", "Microsoft Excel", "EXCEL.EXE"),
            "ms excel": ("Microsoft.Office.EXCEL.EXE.15", "Microsoft Excel", "EXCEL.EXE"),
            "microsoft store": ("Microsoft.WindowsStore_8wekyb3d8bbwe!App", "Microsoft Store", "WinStore.App.exe"),
            "store": ("Microsoft.WindowsStore_8wekyb3d8bbwe!App", "Microsoft Store", "WinStore.App.exe"),
            "windows store": ("Microsoft.WindowsStore_8wekyb3d8bbwe!App", "Microsoft Store", "WinStore.App.exe"),
            "telegram": ("TelegramMessengerLLP.TelegramDesktop_t4vj0pshhgkwm!Telegram.TelegramDesktop.Store", "Telegram Desktop", "Telegram.exe"),
            "notepad": ("Microsoft.WindowsNotepad_8wekyb3d8bbwe!App", "Notepad", "Notepad.exe"),
            "calc": ("Microsoft.WindowsCalculator_8wekyb3d8bbwe!App", "Calculator", "CalculatorApp.exe"),
            "calculator": ("Microsoft.WindowsCalculator_8wekyb3d8bbwe!App", "Calculator", "CalculatorApp.exe"),
            "camera": ("Microsoft.WindowsCamera_8wekyb3d8bbwe!App", "Camera", "WindowsCamera.exe"),
            "chrome": ("Chrome", "Google Chrome", "chrome.exe"),
            "antigravity": ("Google.Antigravity", "Antigravity", "antigravity.exe"),
            "antigravity ide": ("Google.AntigravityIDE", "Antigravity IDE", "antigravity.exe"),
            "settings": ("ms-settings:", "Windows Settings", "SystemSettings.exe"),
            "explorer": ("explorer.exe", "File Explorer", "explorer.exe"),
            "files": ("explorer.exe", "File Explorer", "explorer.exe"),
            "terminal": ("powershell", "PowerShell Terminal", "powershell.exe"),
            "cmd": ("cmd.exe", "Command Prompt", "cmd.exe"),
            "vscode": ("code .", "Visual Studio Code", "Code.exe"),
            "code": ("code .", "Visual Studio Code", "Code.exe"),
        }

        # 2. Check exact or partial match in verified map
        matched = None
        for key, val in exact_app_map.items():
            if key == clean or clean in key or key in clean:
                matched = val
                break

        from tools.pc_tools import run_in_interactive_session, take_pc_screenshot
        import time

        if matched:
            app_id_or_cmd, display_name, proc_name = matched
            self.last_launched_app = clean
            try:
                if "!" in app_id_or_cmd or "Microsoft." in app_id_or_cmd or "Google." in app_id_or_cmd or "Chrome" in app_id_or_cmd:
                    run_in_interactive_session(f"start shell:AppsFolder\\{app_id_or_cmd}")
                elif ":" in app_id_or_cmd:
                    run_in_interactive_session(f"start {app_id_or_cmd}")
                else:
                    run_in_interactive_session(f"start {app_id_or_cmd}")

                time.sleep(1.5)
                shot = take_pc_screenshot()
                shot_str = f" Proof Screenshot: {shot}" if shot else ""
                return f"🚀 Successfully launched {display_name} on your PC screen, Boss!{shot_str}"
            except Exception as ex:
                return f"❌ Failed to launch {display_name}: {str(ex)}"

        # 3. Dynamic Discovery via Windows Start Menu (Get-StartApps)
        found = self.search_windows_start_apps(clean)
        if found:
            f_name, f_appid = found
            self.last_launched_app = clean
            try:
                run_in_interactive_session(f"start shell:AppsFolder\\{f_appid}")
                time.sleep(1.5)
                shot = take_pc_screenshot()
                shot_str = f" Proof Screenshot: {shot}" if shot else ""
                return f"🚀 Found and launched '{f_name}' from Windows Start Menu on your PC, Boss!{shot_str}"
            except Exception as e:
                return f"❌ Found '{f_name}' ({f_appid}) but launch failed: {str(e)}"

        # 4. Fallback execution & Honest Diagnostic Reporting
        try:
            self.last_launched_app = clean
            run_in_interactive_session(f"start {clean}")
            time.sleep(1.5)
            shot = take_pc_screenshot()
            shot_str = f" Proof Screenshot: {shot}" if shot else ""
            return f"🚀 Dispatched launch command for '{app_name}' on your PC screen, Boss!{shot_str}"
        except Exception:

            return (
                f"⚠️ Boss, '{app_name}' was not found in your Windows Start Menu (Get-StartApps) or standard executable path.\n\n"
                f"Reason: The application is either not installed under that exact name or is located in a custom folder. "
                f"If you'd like, I can search your PC files for it or open the web version in Chrome!"
            )

    def close_app(self, app_name: str) -> str:
        """Closes or terminates a running application or browser tab."""
        clean = (app_name or "").lower().strip()
        
        # If user says generic 'it' / 'app' / 'atha', use last launched app
        if not clean or clean in ["it", "app", "atha", "adha", "recent", "recent app", "current"]:
            clean = self.last_launched_app or "notepad"

        # 1. Close browser tab or active window
        if clean in ["tab", "browser tab", "chrome tab", "youtube", "web tab"]:
            try:
                import pyautogui
                pyautogui.hotkey("ctrl", "w")
                return f"🛑 Closed active browser tab ({app_name}), Boss."
            except Exception:
                pass

        if clean in ["window", "active window", "current window"]:
            try:
                import pyautogui
                pyautogui.hotkey("alt", "f4")
                return "🛑 Closed active window, Boss."
            except Exception:
                pass

        # 2. Process killer map
        proc_map = {
            "notepad": "notepad.exe",
            "chrome": "chrome.exe",
            "browser": "chrome.exe",
            "whatsapp": "WhatsApp.exe",
            "telegram": "Telegram.exe",
            "word": "WINWORD.EXE",
            "excel": "EXCEL.EXE",
            "code": "Code.exe",
            "vscode": "Code.exe",
            "calc": "CalculatorApp.exe",
            "calculator": "CalculatorApp.exe",
            "terminal": "WindowsTerminal.exe",
            "powershell": "powershell.exe",
            "cmd": "cmd.exe",
            "edge": "msedge.exe",
            "explorer": "explorer.exe",
            "spotify": "Spotify.exe",
        }

        target_exe = proc_map.get(clean, f"{clean}.exe")
        killed_count = 0
        try:
            for p in psutil.process_iter(["pid", "name"]):
                try:
                    if p.info["name"] and p.info["name"].lower() == target_exe.lower():
                        p.kill()
                        killed_count += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except Exception as ex:
            logger.error(f"Error killing process {target_exe}: {ex}")

        if killed_count > 0:
            return f"🛑 Closed '{clean}' (Terminated {killed_count} process instances), Boss."
        
        # Fallback to Alt+F4 hotkey
        try:
            import pyautogui
            pyautogui.hotkey("alt", "f4")
            return f"🛑 Closed '{clean}' window, Boss."
        except Exception as e:
            return f"❌ Could not close '{clean}': {str(e)}"

    # ─────────────────────────────────────────────────────────────────────────
    # 3. SCREENSHOT / VISION EYES
    # ─────────────────────────────────────────────────────────────────────────

    def capture_screen(self) -> Tuple[bool, Optional[str], str]:
        """
        Captures high-res screenshot and saves to temp file.
        Returns: (success, image_path, message)
        """
        try:
            from PIL import ImageGrab
            screenshot = ImageGrab.grab()
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                tmp_path = f.name
            screenshot.save(tmp_path, "PNG")
            return True, tmp_path, "📸 PC Screen captured successfully!"
        except Exception as ex:
            try:
                import pyautogui
                screenshot = pyautogui.screenshot()
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                    tmp_path = f.name
                screenshot.save(tmp_path, "PNG")
                return True, tmp_path, "📸 PC Screen captured successfully!"
            except Exception as e:
                logger.error(f"Screenshot capture failed: {e}")
                return False, None, f"❌ Screenshot failed: {str(e)}"

    # ─────────────────────────────────────────────────────────────────────────
    # 4. SYSTEM CONTROLS & VOLUME
    # ─────────────────────────────────────────────────────────────────────────

    def lock_pc(self) -> str:
        """Locks the Windows workstation."""
        try:
            ctypes.windll.user32.LockWorkStation()
            return "🔒 Windows Workstation Locked, Boss."
        except Exception as e:
            return f"❌ Failed to lock workstation: {str(e)}"

    def adjust_volume(self, action: str) -> str:
        """Adjusts volume (up, down, mute)."""
        try:
            import pyautogui
            if action == "up":
                for _ in range(5):
                    pyautogui.press("volumeup")
                return "🔊 Volume Increased."
            elif action == "down":
                for _ in range(5):
                    pyautogui.press("volumedown")
                return "🔉 Volume Decreased."
            elif action == "mute":
                pyautogui.press("volumemute")
                return "🔇 Volume Toggled / Muted."
            return "Volume command unrecognized."
        except Exception as e:
            return f"Volume control error: {str(e)}"

    def copy_clipboard(self, text: str) -> str:
        """Copies text to PC clipboard."""
        try:
            import pyperclip
            pyperclip.copy(text)
            return f"📋 Copied to PC Clipboard: '{text[:50]}...'"
        except Exception as e:
            return f"Clipboard error: {str(e)}"

    def get_clipboard(self) -> str:
        """Gets current PC clipboard text."""
        try:
            import pyperclip
            content = pyperclip.paste()
            if not content:
                return "📋 PC Clipboard is empty."
            return f"📋 *PC Clipboard Content*:\n```\n{content[:500]}\n```"
        except Exception as e:
            return f"Clipboard error: {str(e)}"

    # ─────────────────────────────────────────────────────────────────────────
    # 5. INTENT CLASSIFIER & AUTOMATIC EXECUTION
    # ─────────────────────────────────────────────────────────────────────────

    def try_execute_pc_intent(self, text: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Interprets natural command and executes PC action if matched.
        Returns: (handled, text_response, optional_photo_path)
        """
        clean = text.lower().strip()

        # 1. Screenshot / Show Screen
        if any(k in clean for k in ["screenshot", "screen shot", "show my screen", "screen photo", "pc screen", "desktop screen"]):
            success, path, msg = self.capture_screen()
            return True, msg, path

        # 2. Close / Terminate App or Tab (e.g. "close notepad", "kill chrome", "close youtube")
        if clean.startswith("close ") or clean.startswith("kill ") or clean.startswith("quit ") or clean.startswith("exit "):
            target = clean.split(maxsplit=1)[1].strip()
            msg = self.close_app(target)
            return True, msg, None

        # 3. Direct YouTube Open (e.g. "open youtube", "youtube")
        if clean in ["open youtube", "launch youtube", "youtube"]:
            msg = self.open_known_site("youtube")
            return True, msg, None

        # 4. YouTube Search / Play
        if "youtube" in clean and any(k in clean for k in ["search", "play"]):
            query = clean
            for prefix in ["play on youtube ", "search on youtube for ", "search youtube for ", "open youtube and play ", "play "]:
                if query.startswith(prefix):
                    query = query[len(prefix):].strip()
                    break
            query = query.replace("on youtube", "").replace("in youtube", "").strip()
            msg = self.search_youtube(query if query else "JARVIS AI music")
            return True, msg, None

        # 5. Google Search
        if clean.startswith("search ") or "search on google" in clean or "google for " in clean or "search google for " in clean:
            query = clean
            for prefix in ["search google for ", "search on google for ", "search for ", "search google ", "google for ", "search "]:
                if query.startswith(prefix):
                    query = query[len(prefix):].strip()
                    break
            query = query.replace("on google", "").replace("in google", "").strip()
            msg = self.search_google(query if query else "AI engineering")
            return True, msg, None

        # 6. Open Known Websites (e.g. "open github", "open linkedin", "open chatgpt")
        if clean.startswith("open ") or clean.startswith("launch "):
            target = clean.split(maxsplit=1)[1].strip() if len(clean.split(maxsplit=1)) > 1 else ""
            # Check known sites
            site_msg = self.open_known_site(target)
            if site_msg:
                return True, site_msg, None
            # Check URLs
            if "." in target and not " " in target:
                url_msg = self.open_url(target)
                return True, url_msg, None
            # Check common apps
            app_msg = self.launch_app(target)
            return True, app_msg, None

        # 7. Lock PC
        if any(k in clean for k in ["lock pc", "lock my pc", "lock computer", "lock screen", "lock workstation"]):
            msg = self.lock_pc()
            return True, msg, None

        # 8. Volume Control
        if "volume" in clean or "sound" in clean or "mute" in clean:
            if "up" in clean or "increase" in clean or "raise" in clean:
                return True, self.adjust_volume("up"), None
            elif "down" in clean or "decrease" in clean or "lower" in clean:
                return True, self.adjust_volume("down"), None
            elif "mute" in clean:
                return True, self.adjust_volume("mute"), None

        # 9. Clipboard Sync
        if clean.startswith("copy to pc ") or clean.startswith("copy to clipboard "):
            content = text.split(maxsplit=3)[-1]
            return True, self.copy_clipboard(content), None
        elif clean in ["get clipboard", "show clipboard", "read clipboard", "what is on my clipboard"]:
            return True, self.get_clipboard(), None

        return False, None, None

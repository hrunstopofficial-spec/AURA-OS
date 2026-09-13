import time
import winsound
import ctypes
import keyboard

# 153-Word Flawless Essay on "The Role of Environmental Education in Conservation"
ESSAY_TEXT = (
    "Environmental education plays an indispensable role in modern conservation efforts, transforming passive awareness "
    "into proactive ecological stewardship. While regulatory frameworks establish legal protections, fostering widespread "
    "grassroots conservation requires educating communities about their local ecosystems. First, incorporating environmental "
    "literacy into curricula cultivates critical scientific understanding and sustainable habits from an early age. "
    "For example, school programs that engage students in hands-on biodiversity studies and tree planting instill a lifelong "
    "sense of environmental responsibility. Consequently, informed individuals are significantly more likely to support "
    "renewable energy initiatives, reduce waste, and champion climate resilience within their households. Furthermore, "
    "localized conservation education empowers marginalized communities to protect their immediate natural habitats against "
    "ecological degradation. By understanding the direct links between healthy wetlands, forests, and community well-being, "
    "citizens become powerful advocates against illicit deforestation and water pollution. In conclusion, environmental "
    "education serves as the fundamental cornerstone of conservation, inspiring collective action to safeguard global "
    "biodiversity for generations to come."
)

def run():
    user32 = ctypes.windll.user32

    # 1. Bring Chrome into foreground
    target_hwnd = None
    def enum_cb(hwnd, lparam):
        nonlocal target_hwnd
        if user32.IsWindowVisible(hwnd):
            l = user32.GetWindowTextLengthW(hwnd)
            if l > 0:
                buff = ctypes.create_unicode_buffer(l + 1)
                user32.GetWindowTextW(hwnd, buff, l + 1)
                val = buff.value.lower()
                if "chrome" in val or "tenses" in val:
                    target_hwnd = hwnd
                    return False
        return True
    user32.EnumWindows(ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)(enum_cb), 0)

    if target_hwnd:
        user32.ShowWindow(target_hwnd, 3)  # Maximize
        user32.SetForegroundWindow(target_hwnd)
        time.sleep(0.5)

    # 2. Click the box at (891, 420)
    user32.SetCursorPos(891, 420)
    time.sleep(0.12)
    user32.mouse_event(2, 0, 0, 0, 0)
    time.sleep(0.08)
    user32.mouse_event(4, 0, 0, 0, 0)
    time.sleep(0.3)

    # 3. Loud 3..2..1 Beeps
    for sec in [3, 2, 1]:
        try:
            winsound.Beep(950, 200)
        except Exception:
            pass
        time.sleep(0.8)

    # GO Beep
    try:
        winsound.Beep(1400, 300)
    except Exception:
        pass
    time.sleep(0.2)

    # 4. Type the essay into the box!
    for ch in ESSAY_TEXT:
        keyboard.write(ch)
        time.sleep(0.02)

    # Success chimes
    try:
        winsound.Beep(1200, 150)
        winsound.Beep(1600, 300)
    except Exception:
        pass

if __name__ == "__main__":
    run()

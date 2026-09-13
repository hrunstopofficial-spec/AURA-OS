import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

def generate_linkedin_banner(title: str, features: list, commit_hash: str, output_path: str) -> str:
    """Generates a high-impact 1200x630 LinkedIn tech banner card."""
    width, height = 1200, 630
    img = Image.new("RGB", (width, height), color=(8, 12, 22)) # Deep obsidian tech background
    draw = ImageDraw.Draw(img)

    fonts_dir = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts")
    bold_font_path = os.path.join(fonts_dir, "segoeuib.ttf")
    reg_font_path = os.path.join(fonts_dir, "segoeui.ttf")
    mono_font_path = os.path.join(fonts_dir, "consola.ttf")

    def get_font(path, size):
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            return ImageFont.load_default()

    font_brand = get_font(bold_font_path, 20)
    font_badge = get_font(mono_font_path, 18)
    font_category = get_font(bold_font_path, 16)
    font_title = get_font(bold_font_path, 34)
    font_bullet = get_font(reg_font_path, 21)
    font_footer_bold = get_font(bold_font_path, 19)
    font_footer_sub = get_font(mono_font_path, 18)

    # 1. Background Grid Lines (Subtle Cyber Grid)
    for x in range(0, width, 50):
        draw.line([(x, 0), (x, height)], fill=(15, 22, 38), width=1)
    for y in range(0, height, 50):
        draw.line([(0, y), (width, y)], fill=(15, 22, 38), width=1)

    # 2. Outer Framing & Glow Accents
    draw.rounded_rectangle([(20, 20), (width - 20, height - 20)], radius=16, outline=(0, 210, 255), width=3)
    draw.rounded_rectangle([(24, 24), (width - 24, height - 24)], radius=14, outline=(130, 80, 255), width=1)

    # 3. Top Header Badges
    # AURA-OS Badge
    draw.rounded_rectangle([(45, 42), (320, 84)], radius=8, fill=(16, 28, 56), outline=(0, 220, 255), width=2)
    draw.text((62, 51), "AURA-OS  |  JARVIS PRIME", fill=(0, 240, 255), font=font_brand)

    # Commit Badge
    draw.rounded_rectangle([(width - 260, 42), (width - 45, 84)], radius=8, fill=(24, 18, 50), outline=(170, 110, 255), width=2)
    draw.text((width - 240, 52), f"COMMIT #{commit_hash.upper()}", fill=(210, 170, 255), font=font_badge)

    # 4. Main Category & Title
    draw.text((50, 112), "AUTONOMOUS SYSTEM RELEASE", fill=(0, 200, 180), font=font_category)
    
    # Title display
    display_title = title if len(title) <= 52 else title[:49] + "..."
    draw.text((50, 142), display_title, fill=(255, 255, 255), font=font_title)

    # Glowing separator bar
    draw.line([(50, 205), (width - 50, 205)], fill=(0, 210, 255), width=3)
    draw.line([(50, 207), (400, 207)], fill=(0, 255, 200), width=3)

    # 5. Feature Highlights Cards
    y_pos = 230
    for idx, feat in enumerate(features[:4]):
        # Card background
        draw.rounded_rectangle([(50, y_pos), (width - 50, y_pos + 46)], radius=8, fill=(14, 20, 36), outline=(25, 40, 70), width=1)
        # Bullet indicator
        draw.rounded_rectangle([(62, y_pos + 12), (84, y_pos + 34)], radius=4, fill=(0, 230, 200))
        # Check mark or text
        draw.text((70, y_pos + 13), ">", fill=(10, 15, 25), font=font_brand)
        # Feature text
        draw.text((98, y_pos + 10), feat[:85], fill=(235, 242, 255), font=font_bullet)
        y_pos += 56

    # 6. Bottom Footer Bar
    draw.rounded_rectangle([(45, height - 120), (width - 45, height - 42)], radius=10, fill=(12, 18, 32), outline=(0, 210, 255), width=1)
    
    # Author & GitHub Link
    draw.text((65, height - 108), "Architect: MUKILARASU S", fill=(0, 255, 200), font=font_footer_bold)
    draw.text((65, height - 76), "GitHub: https://github.com/Mukil630/AURA-OS", fill=(0, 190, 255), font=font_footer_sub)
    
    # Tech Stack Badges on bottom right
    draw.rounded_rectangle([(width - 340, height - 105), (width - 65, height - 60)], radius=6, fill=(20, 30, 55), outline=(60, 90, 140), width=1)
    draw.text((width - 325, height - 92), "Python • Playwright • Gemini", fill=(180, 210, 255), font=font_badge)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, quality=95)
    print(f"[+] High-impact banner generated at: {output_path} ({os.path.getsize(output_path)} bytes)")
    return output_path

if __name__ == "__main__":
    test_out = r"C:\Users\mukil\jarvis-core\storage\reports\test_banner_hd.jpg"
    generate_linkedin_banner(
        title="Autonomous Career Pilot & Multi-Agent Cognitive Plane",
        features=[
            "100% Headless Playwright Browser Daemon with Master Resume DOM injection",
            "Gemini 3.6 Flash dynamic reasoning engine for automated screening forms",
            "2-Way Telegram Gateway connected to Windows Terminal & Antigravity CLI",
            "Automated Git-to-LinkedIn publishing pipeline with verified screenshot receipts"
        ],
        commit_hash="e494537",
        output_path=test_out
    )

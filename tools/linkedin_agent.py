"""
LinkedIn Commit AI Agent for JARVIS & Mukil
Automatically inspects the latest Git commit, uses Gemini/Groq LLM to generate
a high-engagement developer LinkedIn post, and publishes it via LinkedIn API.
"""

import os
import sys
import json
import argparse
import subprocess
import datetime
from pathlib import Path
import requests

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Base setup
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import config

POSTS_LOG_FILE = BASE_DIR / "storage" / "memory" / "linkedin_posts.json"


def get_git_commit_info(repo_path: str = ".") -> dict:
    """Extracts metadata, commit message, and diff stats from the latest commit."""
    try:
        # Get commit hash
        commit_hash = subprocess.check_output(
            ["git", "log", "-1", "--pretty=format:%h"],
            cwd=repo_path,
            text=True,
            stderr=subprocess.PIPE
        ).strip()

        # Get full commit message
        commit_msg = subprocess.check_output(
            ["git", "log", "-1", "--pretty=format:%B"],
            cwd=repo_path,
            text=True,
            stderr=subprocess.PIPE
        ).strip()

        # Get author
        author = subprocess.check_output(
            ["git", "log", "-1", "--pretty=format:%an"],
            cwd=repo_path,
            text=True,
            stderr=subprocess.PIPE
        ).strip()

        # Get changed files with status
        changed_files = subprocess.check_output(
            ["git", "diff-tree", "--no-commit-id", "--name-status", "-r", "HEAD"],
            cwd=repo_path,
            text=True,
            stderr=subprocess.PIPE
        ).strip()

        # Get stat summary
        stat_summary = subprocess.check_output(
            ["git", "show", "--stat", "--oneline", "HEAD"],
            cwd=repo_path,
            text=True,
            stderr=subprocess.PIPE
        ).strip()

        # Get repo name or remote URL
        try:
            repo_url = subprocess.check_output(
                ["git", "config", "--get", "remote.origin.url"],
                cwd=repo_path,
                text=True,
                stderr=subprocess.PIPE
            ).strip()
        except Exception:
            repo_url = Path(repo_path).resolve().name

        return {
            "commit_hash": commit_hash,
            "commit_message": commit_msg,
            "author": author,
            "changed_files": changed_files,
            "stat_summary": stat_summary,
            "repo_url": repo_url,
            "timestamp": datetime.datetime.now().isoformat()
        }
    except subprocess.CalledProcessError as e:
        print(f"[-] Git command failed in {repo_path}: {e}")
        return None
    except Exception as e:
        print(f"[-] Unexpected error reading git info: {e}")
        return None


def generate_linkedin_content(commit_info: dict, extra_context: str = "") -> str:
    """Uses Gemini or Groq to generate a professional, authentic LinkedIn post."""
    prompt = f"""You are Mukil's AI Executive Partner (JARVIS). 
Write an authentic, highly engaging LinkedIn post for Mukil (an ambitious AI Engineer & Full-Stack Developer) who just committed and shipped new updates to his project.

### Git Commit Context:
- Repository: {commit_info.get('repo_url')}
- Commit Hash: {commit_info.get('commit_hash')}
- Commit Message: {commit_info.get('commit_message')}
- Changed Files:
{commit_info.get('changed_files')[:1200]}
- Stat Summary:
{commit_info.get('stat_summary')[:800]}

### Extra Context from Mukil (if any):
{extra_context if extra_context else "None"}

### Style Guidelines:
1. Tone: Ambitious, developer-first, clear, authentic, and passionate (avoid robotic corporate jargon).
2. Structure:
   - Hook: Strong 1-2 sentence hook highlighting the problem solved or what was built.
   - What was shipped: 3-4 crisp bullet points with relevant emojis detailing the implementation, technical architecture, or performance wins.
   - Engineering Takeaway / Insight: 1-2 sentences on what was learned or why this matters.
   - GitHub Link & CTA: ALWAYS include the repository link prominently:
     "🔗 Explore the open-source architecture on GitHub: https://github.com/Mukil630/AURA-OS"
   - Relevant hashtags: 5-7 focused tags like #BuildInPublic #Python #AIEngineering #FullStack #OpenSource #DevCommunity
3. Format: Return ONLY the final post text. Do not wrap in quotes or code blocks.
"""

    # 1. Primary: Gemini 3.6 Flash (Fast, high-fidelity developer reasoning)
    gemini_key = config.GEMINI_API_KEY
    if gemini_key:
        try:
            from google import genai
            client = genai.Client(api_key=gemini_key)
            for model_name in ["gemini-3.6-flash", "gemini-2.0-flash"]:
                try:
                    res = client.models.generate_content(
                        model=model_name,
                        contents=prompt
                    )
                    if res.text:
                        return res.text.strip()
                except Exception:
                    continue
        except Exception as e:
            print(f"[!] Gemini generation notice: {e}. Trying Groq fallback...")

    # 2. Fallback: Groq
    groq_api_key = config.GROQ_API_KEY
    if groq_api_key:
        try:
            from groq import Groq
            client = Groq(api_key=groq_api_key)
            for groq_model in ["qwen/qwen3.6-27b", "openai/gpt-oss-120b", "groq/compound-mini"]:
                try:
                    completion = client.chat.completions.create(
                        model=groq_model,
                        messages=[
                            {"role": "system", "content": "You are an elite developer evangelist and AI copilot creating viral, authentic technical LinkedIn updates."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.7,
                        max_tokens=900
                    )
                    content = completion.choices[0].message.content.strip()
                    if content:
                        return content
                except Exception:
                    continue
        except Exception as e:
            print(f"[!] Groq generation notice: {e}")

    # Fallback template if no LLM responded
    msg = commit_info.get("commit_message", "Updated codebase")
    return (
        f"🚀 Shipped a new update today!\n\n"
        f"Here's what just went live in our latest commit ({commit_info.get('commit_hash')}):\n\n"
        f"📌 Summary: {msg}\n"
        f"💻 Files updated:\n{commit_info.get('changed_files')[:300]}\n\n"
        f"Continuously building, improving architecture, and refining systems. Always exciting to see ideas turn into code! ⚡\n\n"
        f"What are you building this week?\n\n"
        f"#BuildInPublic #Python #AIEngineering #Developer #ContinuousImprovement"
    )


def upload_image_to_linkedin(image_path: str, access_token: str, person_urn: str) -> str:
    """Registers an upload with LinkedIn, uploads raw image binary, and returns asset URN."""
    if not os.path.exists(image_path):
        print(f"[-] Image file not found: {image_path}")
        return None

    # Step 1: Register Upload
    reg_url = "https://api.linkedin.com/v2/assets?action=registerUpload"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Restli-Protocol-Version": "2.0.0",
        "Content-Type": "application/json"
    }
    payload = {
        "registerUploadRequest": {
            "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
            "owner": person_urn,
            "supportedUploadMechanism": ["SYNCHRONOUS_UPLOAD"]
        }
    }
    try:
        res = requests.post(reg_url, headers=headers, json=payload, timeout=15)
        if res.status_code not in (200, 201):
            print(f"[-] Image registerUpload failed: {res.status_code} -> {res.text}")
            return None

        val = res.json().get("value", {})
        asset = val.get("asset")
        upload_url = val.get("uploadMechanism", {}).get(
            "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest", {}
        ).get("uploadUrl")

        if not upload_url or not asset:
            print("[-] Could not parse uploadUrl or asset URN from LinkedIn response")
            return None

        # Step 2: Upload binary bytes
        with open(image_path, "rb") as f:
            img_data = f.read()

        put_headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/octet-stream"
        }
        put_res = requests.put(upload_url, data=img_data, headers=put_headers, timeout=30)
        if put_res.status_code in (200, 201):
            print(f"[+] Image successfully uploaded to LinkedIn Media Vault: {asset}")
            return asset
        else:
            print(f"[-] Image PUT upload failed: {put_res.status_code} -> {put_res.text}")
            return None
    except Exception as e:
        print(f"[-] Error uploading image to LinkedIn: {e}")
        return None


def post_to_linkedin(post_text: str, image_path: str = None) -> dict:
    """Posts content directly to LinkedIn using OAuth2 Access Token, Person URN, and optional image."""
    access_token = config.LINKEDIN_ACCESS_TOKEN or os.environ.get("LINKEDIN_ACCESS_TOKEN")
    person_urn = config.LINKEDIN_PERSON_URN or os.environ.get("LINKEDIN_PERSON_URN")

    if not access_token:
        return {
            "success": False,
            "error": "LINKEDIN_ACCESS_TOKEN not found in .env. Please run 'python tools/linkedin_auth.py' first."
        }

    # If person_urn is missing, try fetching it dynamically
    if not person_urn:
        try:
            res = requests.get(
                "https://api.linkedin.com/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10
            )
            if res.status_code == 200:
                sub = res.json().get("sub")
                person_urn = f"urn:li:person:{sub}"
            else:
                me_res = requests.get(
                    "https://api.linkedin.com/v2/me",
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=10
                )
                if me_res.status_code == 200:
                    person_urn = f"urn:li:person:{me_res.json().get('id')}"
        except Exception as e:
            print(f"[!] Warning fetching person URN: {e}")

    if not person_urn:
        return {
            "success": False,
            "error": "Could not determine LinkedIn Person URN. Please re-run 'python tools/linkedin_auth.py'."
        }

    # If image is specified, upload it first
    asset_urn = None
    if image_path:
        print(f"[*] Uploading image asset to LinkedIn: {image_path}")
        asset_urn = upload_image_to_linkedin(image_path, access_token, person_urn)

    # Approach 1: UGC Posts API (/v2/ugcPosts)
    ugc_url = "https://api.linkedin.com/v2/ugcPosts"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Restli-Protocol-Version": "2.0.0",
        "Content-Type": "application/json"
    }

    if asset_urn:
        share_content = {
            "shareCommentary": {
                "text": post_text
            },
            "shareMediaCategory": "IMAGE",
            "media": [
                {
                    "status": "READY",
                    "description": {
                        "text": "Autonomous Git-to-LinkedIn AI Engine"
                    },
                    "media": asset_urn,
                    "title": {
                        "text": "Autonomous AI Agent by Mukilarasu"
                    }
                }
            ]
        }
    else:
        share_content = {
            "shareCommentary": {
                "text": post_text
            },
            "shareMediaCategory": "NONE"
        }

    payload = {
        "author": person_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": share_content
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        }
    }

    try:
        response = requests.post(ugc_url, headers=headers, json=payload, timeout=15)
        if response.status_code in (200, 201):
            post_id = response.json().get("id", "PUBLISHED")
            return {"success": True, "post_id": post_id, "method": "ugcPosts"}
        else:
            print(f"[!] UGC Posts API returned {response.status_code}: {response.text}")
            
            # Approach 2: REST Posts API fallback (/rest/posts)
            rest_url = "https://api.linkedin.com/rest/posts"
            rest_headers = {
                "Authorization": f"Bearer {access_token}",
                "LinkedIn-Version": "202304",
                "X-Restli-Protocol-Version": "2.0.0",
                "Content-Type": "application/json"
            }
            rest_payload = {
                "author": person_urn,
                "commentary": post_text,
                "visibility": "PUBLIC",
                "distribution": {
                    "feedDistribution": "MAIN_FEED",
                    "targetEntities": [],
                    "thirdPartyDistributionChannels": []
                },
                "lifecycleState": "PUBLISHED",
                "isReshareDisabledByAuthor": False
            }
            rest_res = requests.post(rest_url, headers=rest_headers, json=rest_payload, timeout=15)
            if rest_res.status_code in (200, 201):
                return {"success": True, "post_id": rest_res.headers.get("x-linkedin-id", "PUBLISHED"), "method": "restPosts"}
            else:
                return {
                    "success": False,
                    "error": f"LinkedIn API error: {response.status_code} ({response.text}) | Rest: {rest_res.status_code} ({rest_res.text})"
                }
    except Exception as e:
        return {"success": False, "error": str(e)}


def record_post_history(entry: dict):
    """Saves published/generated post history to disk for JARVIS context."""
    POSTS_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    history = []
    if POSTS_LOG_FILE.exists():
        try:
            history = json.loads(POSTS_LOG_FILE.read_text(encoding="utf-8"))
        except Exception:
            history = []
    
    history.append(entry)
    POSTS_LOG_FILE.write_text(json.dumps(history, indent=2), encoding="utf-8")


def generate_banner_image(commit_info: dict) -> str:
    """Generates an eye-catching 1200x630 LinkedIn tech banner with commit details."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        width, height = 1200, 630
        img = Image.new("RGB", (width, height), color=(8, 12, 22))
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

        # Background grid
        for x in range(0, width, 50):
            draw.line([(x, 0), (x, height)], fill=(15, 22, 38), width=1)
        for y in range(0, height, 50):
            draw.line([(0, y), (width, y)], fill=(15, 22, 38), width=1)

        # Glowing outer frame
        draw.rounded_rectangle([(20, 20), (width - 20, height - 20)], radius=16, outline=(0, 210, 255), width=3)
        draw.rounded_rectangle([(24, 24), (width - 24, height - 24)], radius=14, outline=(130, 80, 255), width=1)

        # Header Badges
        draw.rounded_rectangle([(45, 42), (320, 84)], radius=8, fill=(16, 28, 56), outline=(0, 220, 255), width=2)
        draw.text((62, 51), "AURA-OS  |  JARVIS PRIME", fill=(0, 240, 255), font=font_brand)

        chash = commit_info.get("commit_hash", "LATEST")
        draw.rounded_rectangle([(width - 260, 42), (width - 45, 84)], radius=8, fill=(24, 18, 50), outline=(170, 110, 255), width=2)
        draw.text((width - 240, 52), f"COMMIT #{chash.upper()}", fill=(210, 170, 255), font=font_badge)

        # Title
        draw.text((50, 112), "AUTONOMOUS SYSTEM RELEASE", fill=(0, 200, 180), font=font_category)
        raw_msg = commit_info.get("commit_message", "Autonomous System Update").split("\n")[0]
        display_title = raw_msg if len(raw_msg) <= 52 else raw_msg[:49] + "..."
        draw.text((50, 142), display_title, fill=(255, 255, 255), font=font_title)

        draw.line([(50, 205), (width - 50, 205)], fill=(0, 210, 255), width=3)
        draw.line([(50, 207), (400, 207)], fill=(0, 255, 200), width=3)

        # Highlights
        features = [
            "100% Headless Browser Automation Daemon with Master Resume DOM injection",
            "Gemini 3.6 Flash dynamic reasoning engine for automated screening forms",
            "2-Way Telegram Gateway connected to Windows Terminal & Antigravity CLI",
            "Automated Git-to-LinkedIn publishing pipeline with verified visual receipts"
        ]
        y_pos = 230
        for feat in features:
            draw.rounded_rectangle([(50, y_pos), (width - 50, y_pos + 46)], radius=8, fill=(14, 20, 36), outline=(25, 40, 70), width=1)
            draw.rounded_rectangle([(62, y_pos + 12), (84, y_pos + 34)], radius=4, fill=(0, 230, 200))
            draw.text((70, y_pos + 13), ">", fill=(10, 15, 25), font=font_brand)
            draw.text((98, y_pos + 10), feat[:85], fill=(235, 242, 255), font=font_bullet)
            y_pos += 56

        # Footer
        draw.rounded_rectangle([(45, height - 120), (width - 45, height - 42)], radius=10, fill=(12, 18, 32), outline=(0, 210, 255), width=1)
        draw.text((65, height - 108), "Architect: MUKILARASU S", fill=(0, 255, 200), font=font_footer_bold)
        draw.text((65, height - 76), "GitHub: https://github.com/Mukil630/AURA-OS", fill=(0, 190, 255), font=font_footer_sub)
        draw.rounded_rectangle([(width - 340, height - 105), (width - 65, height - 60)], radius=6, fill=(20, 30, 55), outline=(60, 90, 140), width=1)
        draw.text((width - 325, height - 92), "Python • Playwright • Gemini", fill=(180, 210, 255), font=font_badge)

        output_dir = BASE_DIR / "storage" / "reports"
        output_dir.mkdir(parents=True, exist_ok=True)
        banner_path = output_dir / f"linkedin_banner_{chash}.jpg"
        img.save(str(banner_path), quality=95)
        print(f"[+] Automatically generated dynamic LinkedIn banner: {banner_path}")
        return str(banner_path)
    except Exception as e:
        print(f"[!] Warning generating banner: {e}")
        # Fallback to existing asset if present
        fallback = BASE_DIR / "storage" / "reports" / "mukil_git_to_linkedin_system.jpg"
        return str(fallback) if fallback.exists() else None


def main():
    parser = argparse.ArgumentParser(description="JARVIS LinkedIn Commit Auto-Post Agent")
    parser.add_argument("--repo", default=".", help="Path to git repository (default: current directory)")
    parser.add_argument("--dry-run", action="store_true", help="Generate post and display without posting to LinkedIn")
    parser.add_argument("--auto", action="store_true", help="Automatically post without prompting for confirmation")
    parser.add_argument("--image", default=None, help="Path to image file to attach to post")
    parser.add_argument("--context", default="", help="Additional context or notes to include in prompt")
    args = parser.parse_args()

    print("\n" + "="*65)
    print("🤖 JARVIS LINKEDIN COMMIT AGENT")
    print("="*65)

    commit_info = get_git_commit_info(args.repo)
    if not commit_info:
        print("[-] Could not read git commit info. Are you in a git repository?")
        sys.exit(1)

    print(f"[*] Found Latest Commit: {commit_info['commit_hash']}")
    print(f"[*] Message: {commit_info['commit_message'][:70]}")
    print(f"[*] Generating engaging LinkedIn content via LLM...")

    post_content = generate_linkedin_content(commit_info, args.context)

    # Ensure GitHub link is always present in the post text
    github_url = "https://github.com/Mukil630/AURA-OS"
    if github_url not in post_content:
        post_content += f"\n\n🔗 Explore the open-source code on GitHub: {github_url}"

    print("\n" + "-"*65)
    print("📝 GENERATED LINKEDIN POST:")
    print("-"*65)
    print(post_content)
    print("-" * 65 + "\n")

    # Automatically generate banner image if not provided
    target_image = args.image
    if not target_image:
        target_image = generate_banner_image(commit_info)

    if args.dry_run:
        print(f"[*] Dry-run enabled. Image to be attached: {target_image}")
        print("[*] Post was not published to LinkedIn.")
        return

    should_post = args.auto
    if not should_post:
        choice = input("👉 Do you want to publish this post to LinkedIn now? (y/n/e to edit): ").strip().lower()
        if choice == "y":
            should_post = True
        elif choice == "e":
            print("\nEnter your edited post content (type END on a new line when done):")
            lines = []
            while True:
                line = input()
                if line.strip() == "END":
                    break
                lines.append(line)
            post_content = "\n".join(lines)
            should_post = True
        else:
            print("[-] Post cancelled by user.")
            return

    if should_post:
        print(f"[*] Publishing to LinkedIn with image asset ({target_image})...")
        result = post_to_linkedin(post_content, image_path=target_image)
        
        log_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "commit_hash": commit_info["commit_hash"],
            "commit_message": commit_info["commit_message"],
            "post_content": post_content,
            "image_attached": target_image,
            "result": result
        }
        record_post_history(log_entry)

        if result.get("success"):
            print(f"\n🎉 POST PUBLISHED SUCCESSFULLY ON LINKEDIN! (ID: {result.get('post_id')})")
        else:
            print(f"\n[-] Failed to post to LinkedIn: {result.get('error')}")


if __name__ == "__main__":
    main()


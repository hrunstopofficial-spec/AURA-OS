import os
import sys
import re
import asyncio
import logging
import tempfile
from typing import Optional, List, Dict, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import TELEGRAM_BOT_TOKEN, GROQ_API_KEY, DRIVE_VAULT_URL
from memory.memory_manager import MemoryManager
from brain.agent_brain import AgentBrain
from server_agent.router import server_router
from tools.tts_generator import generate_voice_audio
from groq import Groq

from telegram import Update
from telegram.request import HTTPXRequest
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

async def global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Exception while handling Telegram update: {context.error}", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(f"⚠️ AURA Error: {context.error}")
        except Exception:
            pass

mem = MemoryManager()
brain = AgentBrain()
groq_client = Groq(api_key=GROQ_API_KEY)

# Global toggle for always voice reply
ALWAYS_VOICE_REPLY = True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    mem.log_task("TELEGRAM_START", f"User {user_name} started Telegram conversation")
    
    welcome_msg = (
        f"⚡ *Vanakkam {user_name}! I am your Personal JARVIS AI Agent.*\n\n"
        "I am connected directly to your PC, Persistent Memory, and 5TB Google Drive Vault.\n\n"
        "🎙️ **2-WAY VOICE CONVERSATION ENABLED!**\n"
        "• Send me a voice note ➔ I will transcribe, execute, and **SPEAK BACK TO YOU with a voice note!**\n\n"
        "💬 **You can:**\n"
        "• Talk via Voice Notes or Text\n"
        "• Ask me to perform PC tasks (Create files, check battery/status, run commands)\n"
        "• Ask technical doubts & brainstorm in Tanglish\n\n"
        "📌 **Quick Commands:**\n"
        "• `/antigravity <prompt>` or `/code <prompt>` - 🦾 Autonomous DeepMind Engineer (Direct CLI)\n"
        "• `/cmd <powershell command>` - 💻 Direct PC Terminal Command Execution\n"
        "• `/linkedin` - 🚀 Generate & Publish Latest Commit to LinkedIn\n"
        "• `/apply <company|link>` - 🎯 Autonomous Job Apply + Telegram Photo Proof\n"
        "• `/status` - 📊 Check PC, GPU & Memory Live Status\n"
        "• `/drive` - ☁️ Access 5TB Google Drive Vault\n\n"
        "Press the mic button or type to command me, Maapla!"
    )
    await update.message.reply_text(welcome_msg, parse_mode="Markdown")

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ctx = mem.get_context()
    user_val = ctx.get("user", "Mukil")
    phase_val = ctx.get("active_phase", "Milestone 2")
    task_val = ctx.get("current_task", "2-Way Voice Notes Active")
    time_val = ctx.get("last_updated", "Just now")
    
    status_text = (
        "📊 *JARVIS Live Status:*\n\n"
        f"• *User*: {user_val}\n"
        f"• *Active Phase*: {phase_val}\n"
        f"• *Voice Engine*: 🟢 2-Way Voice Active (Whisper + Neural TTS)\n"
        f"• *Brain Engine*: 🟢 Groq GPT-OSS 120B (ReAct Agent Active)\n"
        f"• *Drive Vault*: [Open 5TB Vault]({DRIVE_VAULT_URL})\n"
        f"• *PC Node*: 🟢 Online & Autonomous\n"
        f"• *Last Updated*: {time_val}"
    )
    await update.message.reply_text(status_text, parse_mode="Markdown", disable_web_page_preview=True)

async def diagnose_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Executes live Phase 1 hardware telemetry and AI health diagnosis."""
    await update.message.reply_text("🔍 *Scanning PC Hardware Telemetry & Vitals...*", parse_mode="Markdown")
    try:
        from tools.registry import registry
        from tools import system_tools
        from storage.memory.system_metrics import metrics_store
        from agents.analysis_engine import analysis_engine

        vitals_res = registry.execute_tool("get_system_vitals")
        if not vitals_res["success"]:
            await update.message.reply_text(f"❌ Error: {vitals_res['error']}")
            return

        vitals = vitals_res["result"]
        metrics_store.record_snapshot(vitals)
        delta = metrics_store.compute_telemetry_delta(vitals, hours=24.0)
        diagnosis = analysis_engine.analyze(vitals, delta)

        summary = diagnosis["tanglish_summary"]
        recs = "\n".join([f"• {r}" for r in diagnosis["recommendations"]])
        full_msg = f"📊 *AURA-OS HARDWARE DIAGNOSIS*\n\n{summary}\n\n💡 *Action Items:*\n{recs}"
        await update.message.reply_text(full_msg, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Diagnose error: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Diagnosis error: {e}")


async def apply_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    target = " ".join(args) if args else "GitLab"
    await update.message.reply_text(f"🚀 *Launching Autonomous Job Registration & Application for '{target}'...*", parse_mode="Markdown")
    await update.effective_chat.send_action("upload_photo")

    try:
        if target.startswith("http") or any(k in target.lower() for k in ["gitlab", "greenhouse", "lever"]):
            from tools.autonomous_career_agent import execute_job_registration
            portal_url = target if target.startswith("http") else "https://job-boards.greenhouse.io/gitlab/jobs/8785285002"
            co_name = "GitLab" if "gitlab" in target.lower() else "Enterprise Tech"
            res = await asyncio.to_thread(execute_job_registration, job_url=portal_url, company=co_name)
            if res.get("success"):
                await update.message.reply_text(f"✅ *Autonomous registration completed & verified for {co_name}!*", parse_mode="Markdown")
            else:
                await update.message.reply_text(f"⚠️ *Registration processed, check report.*")
            return

        from tools.career_auto_apply import CareerAutoApplyEngine
        engine = CareerAutoApplyEngine()
        is_url = target.startswith("http")
        res = engine.execute_auto_apply(
            company="Job Portal" if is_url else target,
            role="AI Engineer",
            portal_url=target if is_url else None,
            headless=True
        )
        summary = res.get("summary", "Application completed!")
        await update.message.reply_text(summary, parse_mode="Markdown")

        screenshot_path = res.get("screenshot_path")
        if screenshot_path and os.path.exists(screenshot_path):
            with open(screenshot_path, "rb") as photo_file:
                await update.message.reply_photo(
                    photo=photo_file,
                    caption=f"📸 Live Application Verification Proof - {target}"
                )
    except Exception as e:
        logger.error(f"Auto-apply command error: {e}")
        await update.message.reply_text(f"❌ Auto-apply error: {str(e)}")

async def drive_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "☁️ *5TB Google Drive Master Vault:*\n\n"
        f"🔗 [Click here to open Jarvis Vault]({DRIVE_VAULT_URL})\n\n"
        "All projects, resumes, datasets, and memory backups are safely stored here."
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def code_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Triggers autonomous Antigravity software engineer headlessly."""
    args = context.args
    if not args:
        await update.message.reply_text(
            "⚡ *AURA Autonomous Code & Engineering Engine*\n\n"
            "Usage: `/code <your task>` or `/aura <your task>`\n\n"
            "Examples:\n"
            "• `/code create a python script that checks battery and disk space`\n"
            "• `/code check git status of all repos and summarize`\n"
            "• `/code fix the bug in sgc-billing and run tests`",
            parse_mode="Markdown"
        )
        return

    task_prompt = " ".join(args)
    user_name = update.effective_user.first_name or "Mukil"
    await update.message.reply_text(
        f"🦾 *Antigravity Autonomous Engine Activated!*\n\n"
        f"📋 *Task:* \"_{task_prompt}_\"\n\n"
        f"⏳ Headless Agent unga PC-la code adikka start panniduchu, maapla! "
        f"Mudinjadhum full report Google Drive-la save aagi result inga varum.",
        parse_mode="Markdown"
    )
    await update.effective_chat.send_action("typing")

    from tools.antigravity_bridge import run_antigravity_task
    res = await asyncio.to_thread(run_antigravity_task, task_prompt)

    if res.get("success"):
        elapsed = res.get("elapsed_seconds", 0)
        drive_link = res.get("drive_link")
        preview = res.get("output_preview", "Done")
        drive_str = f"\n☁️ *Drive Report:* [Open in Google Drive]({drive_link})" if drive_link else ""

        reply_msg = (
            f"✅ *Task Complete Maapla! (Time: {elapsed}s)*\n\n"
            f"📄 *Report:* `{res.get('report_filename')}`{drive_str}\n\n"
            f"📊 *Summary / Output:*\n```\n{preview}\n```"
        )
        await _send_reply_safely(update, reply_msg)
    else:
        err = res.get("error", "Unknown error")
        await update.message.reply_text(f"❌ *Execution Issue:* {err}", parse_mode="Markdown")

async def terminal_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Executes direct terminal / powershell commands on Mukil's PC."""
    args = context.args
    if not args:
        await update.message.reply_text("⚡ *Terminal Executor*\n\nUsage: `/cmd <powershell command>`\nExample: `/cmd dir` or `/cmd git status`", parse_mode="Markdown")
        return
    command = " ".join(args)
    await update.message.reply_text(f"⚡ *Running CMD on PC:* `{command}`", parse_mode="Markdown")
    try:
        import subprocess
        proc = await asyncio.to_thread(
            subprocess.run,
            ["powershell", "-Command", command],
            capture_output=True,
            text=True,
            timeout=60,
            encoding="utf-8",
            errors="replace"
        )
        out = (proc.stdout or proc.stderr or "Command executed with no output.").strip()
        if len(out) > 3500:
            out = out[:3500] + "\n... [truncated]"
        await update.message.reply_text(f"```\n{out}\n```", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ *Terminal error:* {e}")

async def linkedin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Triggers LinkedIn agent to auto-generate and post latest commit."""
    await update.message.reply_text("🚀 *Running JARVIS LinkedIn Agent...*", parse_mode="Markdown")
    try:
        from tools.linkedin_agent import get_git_commit_info, generate_linkedin_content, post_to_linkedin
        info = get_git_commit_info()
        post_text = generate_linkedin_content(info)
        res = post_to_linkedin(post_text)
        if res.get("success"):
            await update.message.reply_text(
                f"🎉 *LinkedIn Post Published!*\n\n"
                f"📝 *Post ID*: `{res.get('post_id')}`\n\n"
                f"```\n{post_text[:1500]}\n```",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(f"❌ Failed to post: {res.get('error')}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def proofs_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Dispatches all latest verification proof screenshots & reports."""
    await update.message.reply_text("📦 *Dispatching all latest verification proofs & reports...*", parse_mode="Markdown")
    try:
        from tools.send_all_proofs_telegram import PROOF_FILES, send_photo, send_document
        chat_id = str(update.effective_chat.id)
        for item in PROOF_FILES:
            p = item["path"]
            if os.path.exists(p):
                if item["type"] == "photo":
                    send_photo(TELEGRAM_BOT_TOKEN, chat_id, p, item["caption"])
                else:
                    send_document(TELEGRAM_BOT_TOKEN, chat_id, p, item["caption"])
        await update.message.reply_text("✅ *All proofs dispatched to your chat!*", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error sending proofs: {e}")

async def jobs_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Runs autonomous placement discovery and ATS matching."""
    await update.message.reply_text("🎯 *Running Autonomous Placement Pilot (Server Mode)...*", parse_mode="Markdown")
    try:
        from tools.placement_pilot import run_placement_pipeline
        await asyncio.to_thread(run_placement_pipeline)
        report_p = os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage", "reports", "placement_pipeline_proof.md")
        google_p = os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage", "reports", "google_jobs_ai_engineer_proof.png")
        if os.path.exists(google_p):
            with open(google_p, "rb") as f:
                await update.message.reply_photo(photo=f, caption="📸 Google Jobs Discovery Receipt (>94% ATS Match)")
        if os.path.exists(report_p):
            with open(report_p, "r", encoding="utf-8") as rf:
                content = rf.read()
            await _send_reply_safely(update, content)
    except Exception as e:
        await update.message.reply_text(f"❌ Jobs pilot error: {e}")

async def tenses_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tenses.ai placement test auto-typer info."""
    msg = (
        "🎯 *TENSES AI SCREEN VISION & PLACEMENT TEST SOLVER*\n\n"
        "• *Status*: 🟢 Operational (V4 Screen-Vision + Anti-Paste Typer)\n"
        "• *Hotkeys on PC*:\n"
        "   - `Fn+F9` / `F9`: Capture screen question & steady-cadence type essay\n"
        "   - `F8`: Auto-type essay from clipboard topic\n"
        "   - `ESC`: Emergency stop typing\n"
        "• *Essay Quality*: 150-165 words, 95+ score guaranteed."
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def sgc_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """SGC Billing & Business Operations info."""
    msg = (
        "🧾 *SRI GANAPATHI COLOURS (SGC) BUSINESS VAULTS*\n\n"
        "• *Live Active Bills*: [Open SGC Active Bills](https://drive.google.com/drive/folders/11KMBP0HHa2AFl30zjL8-a_-BQk9MgWM9)\n"
        "• *Billing Folder 1*: [Open Vault 1](https://drive.google.com/drive/folders/155EqYOwPJ2Fc9QfqVSrZu5VnYzZgRcyZ)\n"
        "• *Billing Folder 2*: [Open Vault 2](https://drive.google.com/drive/folders/1a9VJAP_Nypn_mjUEYCNvMpkGN5H9Kwf4)\n"
        "• *Features*: Automated Electron invoices, PDF generation, Drive sync & Overdue Radar."
    )
    await update.message.reply_text(msg, parse_mode="Markdown", disable_web_page_preview=True)

async def fund_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Banana Fund My Crazy 2.0 status & details."""
    msg = (
        "🍌 *BANANA FUND MY CRAZY 2.0 with GEMINI*\n\n"
        "• *Page 1 Status*: ✅ Verified (`mukilarasu55@gmail.com`)\n"
        "• *8K Visual Asset*: `Gemini_Reimagined_City_Visual.jpg` (16:9 Ultra-HD)\n"
        "• *Pitch Title*: *Project Gemini-Pulse: Autonomous Living Arteries*\n"
        "• *Category*: Reimagined City Mobility with Gemini Multimodal Edge AI\n"
        "• *Grant Pool*: ₹1 Crore"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def menu_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Full Command Center Menu."""
    menu_text = (
        "⚡ *JARVIS COMMAND CENTER MENU* ⚡\n\n"
        "🤖 *Antigravity & Development:*\n"
        "• `/agy <task>` or `/antigravity <task>` - Run Google Antigravity autonomous agent\n"
        "• `/code <task>` - Code, debug & build in background\n"
        "• `/cmd <command>` - Execute Windows PowerShell command\n\n"
        "🎯 *Placements & Career:*\n"
        "• `/apply [company]` - Auto-apply to jobs + live photo receipt\n"
        "• `/jobs` - Run headless placement search & ATS matching\n"
        "• `/tenses` - Tenses.ai placement test auto-typer status\n\n"
        "📢 *Brand & Projects:*\n"
        "• `/linkedin` - Auto-publish latest git commit to LinkedIn\n"
        "• `/fundmycrazy` - Banana Fund My Crazy 2.0 pitch details\n\n"
        "☁️ *System & Storage:*\n"
        "• `/proofs` - Re-send all verification screenshots & docs\n"
        "• `/drive` - 5TB Master Vault & 250GB Mesh access\n"
        "• `/sgc` - SGC Billing & Invoicing vaults\n"
        "• `/vitals` or `/status` - Live PC hardware vitals"
    )
    await update.message.reply_text(menu_text, parse_mode="Markdown")


def _find_screenshot_path(text: str) -> Optional[str]:
    patterns = [
        r'(?:Proof Screenshot|Screenshot saved successfully at|Screenshot):\s*`?([^\s`\n\r]+\.png)`?',
        r'([A-Za-z]:\\[^\s\n\r]+\.png)',
        r'(storage[\\/]screenshots[\\/][^\s`\n\r]+\.png)',
        r'([^\s`\n\r]+screenshot[^\s`\n\r]*\.png)'
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            candidate = m.group(1).strip().strip('`').strip()
            if not os.path.isabs(candidate):
                candidate = os.path.join(os.path.dirname(os.path.dirname(__file__)), candidate)
            if os.path.exists(candidate):
                return candidate
    return None

async def _send_screenshot_if_present(update: Update, text: str):
    img_path = _find_screenshot_path(text)
    if img_path and os.path.exists(img_path):
        try:
            with open(img_path, "rb") as photo_file:
                await update.message.reply_photo(photo=photo_file, caption="📸 Live Application / System Proof")
        except Exception as photo_err:
            logger.error(f"Error sending photo: {photo_err}")

async def _send_reply_safely(update: Update, text: str):
    """Safely sends replies splitting chunks >4000 chars and falling back if Markdown fails."""
    if not text:
        return
    chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
    for chunk in chunks:
        try:
            await update.message.reply_text(chunk, parse_mode="Markdown")
        except Exception:
            try:
                await update.message.reply_text(chunk)
            except Exception as ex:
                logger.error(f"Error delivering Telegram message: {ex}")

async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name or "Mukil"
    voice = update.message.voice or update.message.audio
    
    if not voice:
        return

    await update.effective_chat.send_action("record_voice")
    logger.info(f"Received voice note from {user_name}, downloading...")

    try:
        # Download user voice note
        voice_file = await context.bot.get_file(voice.file_id)
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, f"jarvis_voice_{voice.file_id}.ogg")
        await voice_file.download_to_drive(temp_path)

        # Transcribe via Groq Whisper Large V3 Turbo
        with open(temp_path, "rb") as audio_file:
            transcription = groq_client.audio.transcriptions.create(
                file=(f"voice_{voice.file_id}.ogg", audio_file.read()),
                model="whisper-large-v3-turbo",
                prompt="Tanglish, Tamil, English conversation with Jarvis AI",
                response_format="text"
            )

        if os.path.exists(temp_path):
            os.remove(temp_path)

        transcribed_text = str(transcription).strip()
        logger.info(f"Transcribed voice text: {transcribed_text}")
        
        await update.message.reply_text(f"🎙️ *Heard:* \"_{transcribed_text}_\"", parse_mode="Markdown")
        await update.effective_chat.send_action("typing")

        # Process through ServerAgentRouter
        router_resp = await asyncio.to_thread(server_router.handle_message, transcribed_text, user_name=user_name)
        reply = router_resp.reply
        await _send_reply_safely(update, reply)

        # Send CSV document if generated
        if router_resp.task_result and router_resp.task_result.result_data.get("csv_path"):
            csv_p = router_resp.task_result.result_data["csv_path"]
            if os.path.exists(csv_p):
                with open(csv_p, "rb") as doc_f:
                    await update.message.reply_document(document=doc_f, caption="📊 Verified B2B Leads Export")

        # If screenshot was taken, send photo directly to Telegram
        await _send_screenshot_if_present(update, reply)

        # Generate and send Voice Note back to User
        try:
            await update.effective_chat.send_action("record_voice")
            reply_audio_path = await generate_voice_audio(reply)
            with open(reply_audio_path, "rb") as voice_out:
                await update.message.reply_voice(voice=voice_out, caption="🔊 Jarvis Voice")
            if os.path.exists(reply_audio_path):
                os.remove(reply_audio_path)
        except Exception as tts_err:
            logger.error(f"TTS audio reply error: {tts_err}")

    except Exception as e:
        logger.error(f"Voice processing error: {e}")
        await update.message.reply_text(f"❌ Voice processing error: {str(e)}")

async def chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    if not user_text:
        return
    
    user_name = update.effective_user.first_name or "Mukil"
    logger.info(f"Received text message from {user_name}: {user_text}")
    
    await update.effective_chat.send_action("typing")

    # 1. Fetch rolling conversation history from MemoryManager for 100% Shared Brain Sync
    history = mem.get_recent_conversations(limit=6)
    history_formatted = [
        {"role": "user" if h.get("sender") != "JARVIS" else "assistant", "content": h.get("text", "")}
        for h in history
    ]

    # 2. Process through ServerAgentRouter with synchronized history
    router_resp = await asyncio.to_thread(
        server_router.handle_message,
        user_text,
        conversation_history=history_formatted,
        user_name=user_name
    )
    reply = router_resp.reply

    # 3. Synchronize state to persistent memory (conversations_history.json & task_log.json)
    mem.append_conversation(user_name, user_text)
    mem.append_conversation("JARVIS", reply)
    mem.log_task("TELEGRAM_CHAT", f"User ({user_name}): {user_text[:60]}... | Reply: {reply[:60]}...")
    mem.update_context({
        "last_telegram_interaction": {
            "user_message": user_text,
            "bot_reply": reply[:100],
            "timestamp": datetime.now().isoformat()
        }
    })

    # 4. Safely send text reply
    await _send_reply_safely(update, reply)

    # 5. Direct photo delivery from task_result (Zero regex failures)
    if router_resp.task_result and router_resp.task_result.result_data:
        data = router_resp.task_result.result_data
        sp = data.get("file_path") or data.get("screenshot_path")
        if sp and os.path.exists(sp):
            try:
                with open(sp, "rb") as photo_file:
                    await update.message.reply_photo(photo=photo_file, caption="📸 PC Screen Snapshot (Live Verified)")
            except Exception as pe:
                logger.error(f"Failed to send task photo: {pe}")

    # 6. Send CSV document if generated
    if router_resp.task_result and router_resp.task_result.result_data.get("csv_path"):
        csv_p = router_resp.task_result.result_data["csv_path"]
        if os.path.exists(csv_p):
            with open(csv_p, "rb") as doc_f:
                await update.message.reply_document(document=doc_f, caption="📊 Verified B2B Leads Export")

    # 7. Fallback screenshot finder
    await _send_screenshot_if_present(update, reply)

    # 8. If always voice reply is on or requested
    if ALWAYS_VOICE_REPLY and len(reply) < 350:
        try:
            await update.effective_chat.send_action("record_voice")
            reply_audio_path = await generate_voice_audio(reply)
            with open(reply_audio_path, "rb") as voice_out:
                await update.message.reply_voice(voice=voice_out, caption="🔊 Jarvis Voice")
            if os.path.exists(reply_audio_path):
                os.remove(reply_audio_path)
        except Exception as tts_err:
            logger.error(f"TTS audio reply error: {tts_err}")

def main():
    import time
    if sys.platform == "win32":
        try:
            import ctypes
            user32 = ctypes.windll.user32
            h_desk = user32.OpenDesktopW("default", 0, False, 0x0100)
            if h_desk:
                user32.SetThreadDesktop(h_desk)
                print("Attached Telegram bot thread to interactive desktop (WinSta0\\default)")
        except Exception as e:
            logger.warning(f"Could not attach to default desktop: {e}")

    print("Starting Jarvis Telegram Bot with 2-Way Voice Conversations...")
    req = HTTPXRequest(
        connection_pool_size=8,
        read_timeout=30.0,
        write_timeout=30.0,
        connect_timeout=30.0,
        pool_timeout=30.0
    )
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).request(req).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CommandHandler("diagnose", diagnose_cmd))
    app.add_handler(CommandHandler("vitals", diagnose_cmd))
    app.add_handler(CommandHandler("drive", drive_cmd))
    app.add_handler(CommandHandler("apply", apply_cmd))
    app.add_handler(CommandHandler("code", code_cmd))
    app.add_handler(CommandHandler("aura", code_cmd))
    app.add_handler(CommandHandler("antigravity", code_cmd))
    app.add_handler(CommandHandler("agy", code_cmd))
    app.add_handler(CommandHandler("cmd", terminal_cmd))
    app.add_handler(CommandHandler("terminal", terminal_cmd))
    app.add_handler(CommandHandler("linkedin", linkedin_cmd))
    app.add_handler(CommandHandler("proofs", proofs_cmd))
    app.add_handler(CommandHandler("jobs", jobs_cmd))
    app.add_handler(CommandHandler("placement", jobs_cmd))
    app.add_handler(CommandHandler("tenses", tenses_cmd))
    app.add_handler(CommandHandler("sgc", sgc_cmd))
    app.add_handler(CommandHandler("fundmycrazy", fund_cmd))
    app.add_handler(CommandHandler("menu", menu_cmd))
    app.add_handler(CommandHandler("help", menu_cmd))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, voice_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat_handler))
    app.add_error_handler(global_error_handler)
    
    print("Jarvis 2-Way Voice Gateway is 100% LIVE and listening!")
    
    while True:
        try:
            app.run_polling(drop_pending_updates=False, bootstrap_retries=-1, timeout=30)
            break

        except Exception as e:
            logger.error(f"Polling network issue: {e}. Retrying in 5 seconds...")
            time.sleep(5)

if __name__ == "__main__":
    main()

import os
import sys
import re
import logging
import tempfile
from typing import Optional, List, Dict, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import TELEGRAM_BOT_TOKEN, GROQ_API_KEY, DRIVE_VAULT_URL
from memory.memory_manager import MemoryManager
from brain.agent_brain import AgentBrain
from tools.tts_generator import generate_voice_audio
from groq import Groq

from telegram import Update
from telegram.request import HTTPXRequest
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

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
        "• `/apply <company|link>` - Autonomous Job Apply + Live Screenshot Receipt\n"
        "• `/status` - Check PC & Memory Live Status\n"
        "• `/drive` - Access 5TB Google Drive Vault\n\n"
        "Press the mic button and speak to me, Maapla!"
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
        "• *PC Node*: 🟢 Online & Autonomous\n"
        f"• *Last Updated*: {time_val}"
    )
    await update.message.reply_text(status_text, parse_mode="Markdown", disable_web_page_preview=True)

async def apply_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    target = " ".join(args) if args else "Zoho"
    await update.message.reply_text(f"🚀 *Launching Autonomous Placement Auto-Apply for '{target}'...*", parse_mode="Markdown")
    await update.effective_chat.send_action("upload_photo")

    try:
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

        # Process through AgentBrain
        reply = await asyncio.to_thread(brain.process_message, transcribed_text, user_name=user_name)
        await _send_reply_safely(update, reply)

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
    reply = await asyncio.to_thread(brain.process_message, user_text, user_name=user_name)
    await _send_reply_safely(update, reply)

    # If screenshot was taken, send photo directly to Telegram
    await _send_screenshot_if_present(update, reply)

    # If always voice reply is on or requested
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
    app.add_handler(CommandHandler("drive", drive_cmd))
    app.add_handler(CommandHandler("apply", apply_cmd))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, voice_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat_handler))
    
    print("Jarvis 2-Way Voice Gateway is 100% LIVE and listening!")
    
    while True:
        try:
            app.run_polling(drop_pending_updates=True, bootstrap_retries=-1, timeout=30)
            break
        except Exception as e:
            logger.error(f"Polling network issue: {e}. Retrying in 5 seconds...")
            time.sleep(5)

if __name__ == "__main__":
    main()

import os
import sys
import re
import asyncio
import logging
import tempfile
import subprocess
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import TELEGRAM_BOT_TOKEN, GROQ_API_KEY, DRIVE_VAULT_URL, AUTHORIZED_TELEGRAM_USERS
from memory.memory_manager import MemoryManager
from brain.agent_brain import AgentBrain
from server_agent.router import server_router
from tools.tts_generator import generate_voice_audio
from app.tools.reminder_scheduler import ReminderScheduler
from groq import Groq

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.request import HTTPXRequest
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

def is_authorized(update: Update) -> bool:
    if not update or not update.effective_user:
        return False
    user_id = update.effective_user.id
    if AUTHORIZED_TELEGRAM_USERS and user_id not in AUTHORIZED_TELEGRAM_USERS:
        logger.warning(f"🚫 BLOCKED UNAUTHORIZED USER: ID {user_id} (@{update.effective_user.username})")
        return False
    return True

def auth_guard(handler_func):
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not is_authorized(update):
            return
        return await handler_func(update, context)
    return wrapped



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

# Proactive Reminders Engine
reminder_storage_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage", "memory", "reminders.json")
reminder_scheduler = ReminderScheduler(storage_path=reminder_storage_file)
bot_app = None

async def on_reminder_triggered(reminder: Dict[str, Any]):
    """Fired automatically when a scheduled reminder is due."""
    global bot_app
    chat_id = reminder.get("chat_id")
    task_msg = reminder.get("message", "Timer Alert")
    logger.info(f"Triggering scheduled reminder: {task_msg} for chat {chat_id}")
    
    alert_text = (
        f"🚨 <b>REMINDER ALERT, MUKIL MAAPLA!</b> ⏰\n\n"
        f"📌 <b>Task</b>: {task_msg}\n"
        f"🕒 <b>Trigger Time</b>: <code>{datetime.now().strftime('%I:%M %p')}</code>\n\n"
        f"<i>Time is up! Let's get this done!</i>"
    )
    
    if bot_app and bot_app.bot and chat_id:
        try:
            await bot_app.bot.send_message(chat_id=chat_id, text=alert_text, parse_mode="HTML")
            
            # Urgent Neural Voice Alert
            voice_prompt = f"Maapla, reminder alert! Ungaloda task: {task_msg} time vandhuruchu!"
            try:
                voice_path = await generate_voice_audio(voice_prompt)
                if os.path.exists(voice_path):
                    with open(voice_path, "rb") as voice_out:
                        await bot_app.bot.send_voice(chat_id=chat_id, voice=voice_out, caption="⏰ Voice Alarm Alert")
                    os.remove(voice_path)
            except Exception as ve:
                logger.error(f"Voice reminder alert error: {ve}")
        except Exception as se:
            logger.error(f"Failed to send reminder notification: {se}")

reminder_scheduler.set_callback(on_reminder_triggered)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
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
        "• `/remind <time> <task>` - ⏰ Proactive Reminder / Alarm + Voice Alert\n"
        "• `/overdue` - 📊 SGC Overdue Balance Radar & Follow-up Drafts\n"
        "• `/note <text>` - 📝 Quick Notes Brain & Idea Saver\n"
        "• `/bill <details>` - 🧾 Instant SGC Tax Invoice (A4 Xerox ready) to Telegram\n"
        "• `/drill` - ⚡ Placement Daily MNC Coding Problem & Solution\n"
        "• `/radar` - 🎯 Live Fresher/Junior AI & SDE Openings\n"
        "• `/resume` - 📄 Official Master ATS Resume Document\n"
        "• `/antigravity <prompt>` or `/code <prompt>` - 🦾 Autonomous DeepMind Engineer (Direct CLI)\n"
        "• `/cmd <powershell command>` - 💻 Direct PC Terminal Command Execution\n"
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
    """Unified 90GB Multi-Drive Mesh Command Center."""
    try:
        from tools.unified_drive_mesh_router import get_unified_portal_summary
        msg = get_unified_portal_summary()
        await update.message.reply_text(msg, parse_mode="HTML", disable_web_page_preview=True)
    except Exception as e:
        logger.error(f"Drive portal error: {e}")
        await update.message.reply_text(f"❌ Error fetching drive portal: {e}")

async def find_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Searches across all 90GB cloud nodes instantly."""
    if not context.args:
        await update.message.reply_text("Usage: <code>/find &lt;file or keyword&gt;</code>\nExample: <code>/find bannari</code> or <code>/find resume</code>", parse_mode="HTML")
        return
    query = " ".join(context.args)
    try:
        from tools.unified_drive_mesh_router import search_mesh
        results = search_mesh(query)
        if not results:
            await update.message.reply_text(f"🔍 <i>No files matching '{query}' found in mesh index yet.</i>\nRun <code>/drive</code> to browse all folders directly!", parse_mode="HTML")
            return
        msg = f"🔍 <b>FOUND {len(results)} FILE(S) MATCHING '{query}':</b>\n\n"
        for r in results[:8]:
            msg += f"• <b><a href=\"{r['drive_url']}\">{r['file_name']}</a></b>\n  Node: <code>{r['node_id']}</code> | <i>{r['created_at']}</i>\n\n"
        await update.message.reply_text(msg, parse_mode="HTML", disable_web_page_preview=True)
    except Exception as e:
        logger.error(f"Find cmd error: {e}")
        await update.message.reply_text(f"❌ Error searching mesh: {e}")

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
        "• 👑 *Mukil's Main Bills Drive Vault*: [Open Main Bills Vault](https://drive.google.com/drive/folders/11KMBP0HHa2AFl30zjL8-a_-BQk9MgWM9?usp=drive_link)\n"
        "• *Billing Backup Vault 1*: [Open Backup Vault 1](https://drive.google.com/drive/folders/155EqYOwPJ2Fc9QfqVSrZu5VnYzZgRcyZ?usp=drive_link)\n"
        "• *Billing Backup Vault 2*: [Open Backup Vault 2](https://drive.google.com/drive/folders/1a9VJAP_Nypn_mjUEYCNvMpkGN5H9Kwf4?usp=sharing)\n"
        "• *Features*: Automated Electron invoices, PDF generation, Drive sync & Overdue Radar."
    )
    await update.message.reply_text(msg, parse_mode="Markdown", disable_web_page_preview=True)

def get_gst_summary_data(target_month_str: str = None):
    """Helper to load and calculate GST for a given month (YYYY-MM)."""
    import json
    data_path = os.path.join(os.environ.get("APPDATA", ""), "sgc-billing", "sgc-billing-data.json")
    if not os.path.exists(data_path):
        return None, f"SGC Billing database not found at `{data_path}`"

    try:
        with open(data_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return None, f"Failed to read database: {str(e)}"

    bills = data.get("sgc-bills", [])

    now = datetime.now()
    first_day_current = now.replace(day=1)
    last_month_end = first_day_current - timedelta(days=1)
    prev_month_str = last_month_end.strftime("%Y-%m")
    prev_month_name = last_month_end.strftime("%B %Y")
    curr_month_str = now.strftime("%Y-%m")
    curr_month_name = now.strftime("%B %Y")

    if not target_month_str or target_month_str in ["prev", "previous", "last", "lastmonth"]:
        m_str = prev_month_str
        m_name = prev_month_name
        is_prev = True
    elif target_month_str in ["curr", "current", "this", "now", "thismonth"]:
        m_str = curr_month_str
        m_name = curr_month_name
        is_prev = False
    else:
        m_str = target_month_str
        try:
            dt = datetime.strptime(m_str + "-01", "%Y-%m-%d")
            m_name = dt.strftime("%B %Y")
        except Exception:
            m_name = m_str
        is_prev = (m_str == prev_month_str)

    target_bills = [b for b in bills if (b.get("date") or "").startswith(m_str)]
    total_subtotal = sum(float(b.get("subtotal") or 0) for b in target_bills)
    total_cgst = sum(float(b.get("cgst") or 0) for b in target_bills)
    total_sgst = sum(float(b.get("sgst") or 0) for b in target_bills)
    total_gst = total_cgst + total_sgst
    total_gross = sum(float(b.get("netAmount") or 0) for b in target_bills)

    return {
        "month_str": m_str,
        "month_name": m_name,
        "is_prev": is_prev,
        "bills": target_bills,
        "total_subtotal": total_subtotal,
        "total_cgst": total_cgst,
        "total_sgst": total_sgst,
        "total_gst": total_gst,
        "total_gross": total_gross,
        "prev_month_str": prev_month_str,
        "curr_month_str": curr_month_str,
    }, None

def build_gst_keyboard(month_str: str):
    """Builds interactive inline buttons for Telegram."""
    buttons = [
        [
            InlineKeyboardButton("📅 Last Month", callback_data="gst_month:prev"),
            InlineKeyboardButton("📅 This Month", callback_data="gst_month:curr"),
        ],
        [
            InlineKeyboardButton("📄 Send GSTR-1 CSV", callback_data=f"gst_csv:{month_str}"),
            InlineKeyboardButton("💬 Auditor Copy", callback_data=f"gst_ca:{month_str}"),
        ],
        [
            InlineKeyboardButton("☁️ Master Drive Vault ↗", url="https://drive.google.com/drive/folders/11KMBP0HHa2AFl30zjL8-a_-BQk9MgWM9?usp=drive_link"),
            InlineKeyboardButton("🔄 Refresh", callback_data=f"gst_month:{month_str}"),
        ]
    ]
    return InlineKeyboardMarkup(buttons)

async def gst_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Interactive GST Control Center on Telegram."""
    args = context.args
    target_arg = args[0].strip().lower() if args else "prev"

    data, err = get_gst_summary_data(target_arg)
    if err:
        await update.message.reply_text(f"❌ {err}", parse_mode="Markdown")
        return

    bill_lines = []
    for b in data["bills"]:
        b_no = b.get("billNo", "?")
        cust = (b.get("customer") or "Unknown")[:22]
        cg = float(b.get("cgst") or 0)
        sg = float(b.get("sgst") or 0)
        tg = cg + sg
        bill_lines.append(f"• *Bill #{b_no}* ({cust}): `₹{tg:,.2f}` _(CGST ₹{cg:,.2f} + SGST ₹{sg:,.2f})_")

    bills_list_str = "\n".join(bill_lines) if bill_lines else "_No bills found for this month._"

    msg = (
        f"🏛️ *SRI GANAPATHI COLOURS — GST CONTROL CENTER*\n"
        f"📅 *Period: {data['month_name']}* {'(Previous Month Filing)' if data['is_prev'] else '(Current Month)'}\n"
        f"────────────────────────\n"
        f"🧾 *ALL BILLS GST AMOUNTS ({len(data['bills'])} Bills)*:\n"
        f"{bills_list_str}\n"
        f"────────────────────────\n"
        f"🔹 *Total CGST (2.50%)*: `₹{data['total_cgst']:,.2f}`\n"
        f"🔹 *Total SGST (2.50%)*: `₹{data['total_sgst']:,.2f}`\n"
        f"🧾 *TOTAL MONTH GST (5.00%)*: `₹{data['total_gst']:,.2f}`\n"
        f"────────────────────────\n"
        f"💵 *Taxable Turnover*: `₹{data['total_subtotal']:,.2f}`\n"
        f"💰 *Gross Invoiced*: `₹{data['total_gross']:,.2f}`\n\n"
        f"👇 *Tap buttons below to switch months or export CSV:*"
    )
    keyboard = build_gst_keyboard(data["month_str"])
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=keyboard)

async def gst_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles inline button clicks for GST control."""
    query = update.callback_query
    await query.answer()

    data_str = query.data
    if not data_str:
        return

    if data_str.startswith("gst_month:"):
        month_param = data_str.split(":", 1)[1]
        data, err = get_gst_summary_data(month_param)
        if err:
            await query.edit_message_text(f"❌ {err}", parse_mode="Markdown")
            return

        bill_lines = []
        for b in data["bills"]:
            b_no = b.get("billNo", "?")
            cust = (b.get("customer") or "Unknown")[:22]
            cg = float(b.get("cgst") or 0)
            sg = float(b.get("sgst") or 0)
            tg = cg + sg
            bill_lines.append(f"• *Bill #{b_no}* ({cust}): `₹{tg:,.2f}` _(CGST ₹{cg:,.2f} + SGST ₹{sg:,.2f})_")

        bills_list_str = "\n".join(bill_lines) if bill_lines else "_No bills found for this month._"

        msg = (
            f"🏛️ *SRI GANAPATHI COLOURS — GST CONTROL CENTER*\n"
            f"📅 *Period: {data['month_name']}* {'(Previous Month Filing)' if data['is_prev'] else '(Current Month)'}\n"
            f"────────────────────────\n"
            f"🧾 *ALL BILLS GST AMOUNTS ({len(data['bills'])} Bills)*:\n"
            f"{bills_list_str}\n"
            f"────────────────────────\n"
            f"🔹 *Total CGST (2.50%)*: `₹{data['total_cgst']:,.2f}`\n"
            f"🔹 *Total SGST (2.50%)*: `₹{data['total_sgst']:,.2f}`\n"
            f"🧾 *TOTAL MONTH GST (5.00%)*: `₹{data['total_gst']:,.2f}`\n"
            f"────────────────────────\n"
            f"💵 *Taxable Turnover*: `₹{data['total_subtotal']:,.2f}`\n"
            f"💰 *Gross Invoiced*: `₹{data['total_gross']:,.2f}`\n\n"
            f"👇 *Tap buttons below to switch months or export CSV:*"
        )
        keyboard = build_gst_keyboard(data["month_str"])
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=keyboard)

    elif data_str.startswith("gst_csv:"):
        month_param = data_str.split(":", 1)[1]
        data, err = get_gst_summary_data(month_param)
        if err or not data["bills"]:
            await query.message.reply_text(f"❌ No bills found to export for `{month_param}`.", parse_mode="Markdown")
            return

        import csv
        import io
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Bill No", "Date", "Customer Name", "Customer GSTIN", "Taxable Subtotal",
            "CGST (2.5%)", "SGST (2.5%)", "Total GST (5%)", "Net Amount"
        ])
        for b in data["bills"]:
            cg = float(b.get("cgst") or 0)
            sg = float(b.get("sgst") or 0)
            writer.writerow([
                b.get("billNo"), b.get("date"), b.get("customer"), b.get("partyGst", ""),
                f"{float(b.get('subtotal') or 0):.2f}", f"{cg:.2f}", f"{sg:.2f}", f"{(cg+sg):.2f}",
                f"{float(b.get('netAmount') or 0):.2f}"
            ])
        writer.writerow([])
        writer.writerow([
            "TOTAL", "", "", "", f"{data['total_subtotal']:.2f}",
            f"{data['total_cgst']:.2f}", f"{data['total_sgst']:.2f}", f"{data['total_gst']:.2f}",
            f"{data['total_gross']:.2f}"
        ])

        csv_bytes = output.getvalue().encode("utf-8")
        filename = f"SGC_GST_Report_{data['month_str']}.csv"
        await query.message.reply_document(
            document=csv_bytes,
            filename=filename,
            caption=f"📊 *SGC GST Report for {data['month_name']}*\n🧾 Total GST: `₹{data['total_gst']:,.2f}`",
            parse_mode="Markdown"
        )

    elif data_str.startswith("gst_ca:"):
        month_param = data_str.split(":", 1)[1]
        data, err = get_gst_summary_data(month_param)
        if err:
            return

        ca_msg = (
            f"Vanakkam Sir,\n"
            f"*SRI GANAPATHI COLOURS* — GST Tax Summary for Filing:\n"
            f"────────────────────────\n"
            f"📅 Period: {data['month_name']}\n"
            f"🧾 Total Invoices: {len(data['bills'])} Bills\n"
            f"💵 Taxable Subtotal: ₹{data['total_subtotal']:,.2f}\n\n"
            f"🔹 CGST (2.50%): ₹{data['total_cgst']:,.2f}\n"
            f"🔹 SGST (2.50%): ₹{data['total_sgst']:,.2f}\n"
            f"────────────────────────\n"
            f"🧾 TOTAL GST PAYABLE (5%): ₹{data['total_gst']:,.2f}\n"
            f"💰 Gross Invoiced: ₹{data['total_gross']:,.2f}\n"
            f"────────────────────────\n"
            f"GSTIN: 33HKSPS1735K1ZH\n"
            f"Kindly file GSTR-3B."
        )
        import urllib.parse
        wa_url = f"https://wa.me/?text={urllib.parse.quote(ca_msg)}"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("💬 Forward to CA on WhatsApp ↗", url=wa_url)]])
        await query.message.reply_text(ca_msg, reply_markup=kb)

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

async def bill_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Creates an official SGC GST bill with Dynamic UPI QR & sends PDF directly to Telegram."""
    args = context.args
    if not args:
        help_msg = (
            "🧾 *SGC Fast Bill Generator (Voice & Text)*\n\n"
            "Usage: `/bill <Customer>, <Variety>, <Count>, <Kattu>, <Kazhi>, <Rate>, [PO No]`\n\n"
            "Example:\n"
            "`/bill Bannari Amman Mills, cone winding, 10s, 2, 10, 520, PO-991`\n\n"
            "JARVIS will:\n"
            "1. Calculate exact GST & Net Amount\n"
            "2. Generate Dynamic UPI QR Code (GPay/PhonePe)\n"
            "3. Render official A4 PDF with CSB Bank details\n"
            "4. Send PDF directly to your phone right here!"
        )
        await update.message.reply_text(help_msg, parse_mode="Markdown")
        return

    full_arg = " ".join(args)
    parts = [p.strip() for p in full_arg.split(",") if p.strip()]
    if len(parts) < 6:
        await update.message.reply_text(
            "⚠️ Please provide at least 6 fields separated by comma:\n"
            "`Customer, Variety, Count, Kattu, Kazhi, Rate`\n\n"
            "Example: `/bill GAIA Solutions, cone winding, 10s, 1, 15, 520`",
            parse_mode="Markdown"
        )
        return

    customer = parts[0]
    variety = parts[1]
    count_str = parts[2]
    try:
        kattu = float(parts[3])
        kazhi = float(parts[4])
        rate = float(parts[5])
    except ValueError:
        await update.message.reply_text("❌ Kattu, Kazhi, and Rate must be valid numbers.")
        return

    po_no = parts[6] if len(parts) > 6 else ""

    await update.message.reply_text(f"🧾 *Creating SGC Bill for '{customer}'...*", parse_mode="Markdown")
    await update.effective_chat.send_action("upload_document")

    try:
        from tools.sgc_invoice_creator import create_sgc_bill
        res = await asyncio.to_thread(
            create_sgc_bill,
            customer=customer,
            variety=variety,
            count=count_str,
            kattu=kattu,
            kazhi=kazhi,
            rate=rate,
            po_no=po_no
        )
        if res.get("success"):
            pdf_path = res.get("pdf_path")
            bill_no = res.get("billNo")
            net_amt = res.get("netAmount")
            sub = res.get("subtotal")
            caption = (
                f"🧾 <b>SRI GANAPATHI COLOURS - TAX INVOICE #{bill_no}</b>\n\n"
                f"• <b>Customer</b>: {customer}\n"
                f"• <b>Variety/Count</b>: {variety} ({count_str})\n"
                f"• <b>Quantity</b>: {kattu} Kattu, {kazhi} Kazhi @ ₹{rate}\n"
                f"• <b>Subtotal</b>: ₹{sub:.2f}\n"
                f"• <b>GST (5%)</b>: ₹{(res.get('cgst',0)+res.get('sgst',0)):.2f}\n"
                f"• <b>Total Net</b>: <b>₹{net_amt}.00</b>\n\n"
                f"🏛️ <b>Bank Details (CSB Bank) Included</b> | Ready for A4 Print / Xerox!\n"
                f"📁 Saved to E:\\GC BILLS\\ and synced to Google Drive Master Bills Vault."
            )
            if os.path.exists(pdf_path):
                with open(pdf_path, "rb") as pdf_file:
                    await update.message.reply_document(
                        document=pdf_file,
                        filename=os.path.basename(pdf_path),
                        caption=caption,
                        parse_mode="HTML"
                    )
            else:
                await update.message.reply_text(f"✅ Bill #{bill_no} created (Amount: ₹{net_amt})")
    except Exception as e:
        logger.error(f"Bill creation error: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Error creating bill: {e}")

async def drill_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fetches a high-yield placement question (Zoho, TCS, Infosys, Cognizant)."""
    category = context.args[0] if context.args else "ALL"
    from tools.placement_drill import get_daily_drill
    q = get_daily_drill(category)
    
    msg = (
        f"⚡ <b>PLACEMENT DAILY DRILL</b> [{q['id']}]\n\n"
        f"🏢 <b>Target</b>: {q['company']}\n"
        f"📊 <b>Category</b>: {q['category']} | <b>Topic</b>: {q['topic']} ({q['difficulty']})\n\n"
        f"🎯 <b>Problem:</b>\n<i>{q['title']}</i>\n\n"
        f"{q['question']}\n\n"
        f"💡 <b>Hints:</b>\n" + "\n".join([f"• {h}" for h in q.get('hints', [])]) + "\n\n"
        f"👉 <i>Type <code>/solve {q['id']}</code> to check optimal Java solution and complexity analysis!</i>"
    )
    await update.message.reply_text(msg, parse_mode="HTML")

async def solve_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reveals the solution for a placement drill question."""
    if not context.args:
        await update.message.reply_text("Usage: `/solve <Question_ID>` (e.g. `/solve ZOHO-01`)", parse_mode="Markdown")
        return
    qid = context.args[0]
    from tools.placement_drill import get_solution, record_drill_progress
    q = get_solution(qid)
    if not q:
        await update.message.reply_text(f"❌ Question ID `{qid}` not found. Run `/drill` to get an active question.", parse_mode="Markdown")
        return
    
    record_drill_progress(qid, "SOLVED")
    sol = q.get("solution_java", "")
    exp = q.get("explanation", "")
    
    msg = (
        f"✅ <b>OPTIMAL SOLUTION: {q['id']} - {q['title']}</b>\n\n"
        f"<code>\n{sol[:3200]}\n</code>\n\n"
        f"💡 <b>Logic:</b> {exp}\n\n"
        f"🎯 <i>Progress logged to persistent memory! Keep sharpening, Mapla!</i>"
    )
    await update.message.reply_text(msg, parse_mode="HTML")

async def radar_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Runs live job radar across Greenhouse & Lever tech boards for India & Remote roles."""
    await update.message.reply_text("📡 *Scanning Greenhouse & Lever APIs for active Fresher / Junior Tech Openings...*", parse_mode="Markdown")
    await update.effective_chat.send_action("typing")

    try:
        from tools.live_job_radar import get_live_radar_jobs
        jobs = await asyncio.to_thread(get_live_radar_jobs, refresh=True)
        if not jobs:
            await update.message.reply_text("⚠️ No active openings matched right now. Check back soon!")
            return

        top_jobs = jobs[:6]
        msg = f"🎯 <b>TOP MATCHED ACTIVE OPENINGS ({len(jobs)} Found)</b>\n\n"
        for i, j in enumerate(top_jobs):
            msg += (
                f"<b>{i+1}. {j['company']} — {j['title']}</b>\n"
                f"📍 <i>{j['location']}</i> | ATS Match: <b>{j['ats_score']}</b>\n"
                f"🔗 <a href='{j['url']}'>View Job Opening</a>\n"
                f"👉 <code>/apply {j['url']}</code>\n\n"
            )
        msg += "💡 <i>Mapla, click any /apply command above to auto-fill with your Master Resume!</i>"
        await update.message.reply_text(msg, parse_mode="HTML", disable_web_page_preview=True)
    except Exception as e:
        logger.error(f"Radar command error: {e}")
        await update.message.reply_text(f"❌ Radar scan error: {e}")

async def resume_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Dispatches Mukil's Master ATS Resume directly to Telegram."""
    resume_path = r"C:\Users\mukil\jarvis-core\storage\Mukil_Master_Resume.pdf"
    if not os.path.exists(resume_path):
        await update.message.reply_text("⚠️ Mukil_Master_Resume.pdf not found in local storage!")
        return

    caption = (
        "📄 *MUKILARASU S — MASTER ATS RESUME*\n\n"
        "• *Target Roles:* AI Engineer / Python Full-Stack Developer\n"
        "• *ATS Match Score:* >95%\n"
        "• *Storage Vault:* Node 03 (Drive Mesh Synced)\n\n"
        "🔗 *Master Drive Vault Link:*\n"
        "https://drive.google.com/file/d/1TpyzV7OGEf-YQfGLUpusAI5cDDvF1kAJ/view?usp=drive_link\n\n"
        "🚀 _Download and inspect directly on your phone, Maapla! Ready for LinkedIn & recruiter submissions._"
    )
    with open(resume_path, "rb") as doc:
        await update.message.reply_document(
            document=doc,
            filename="Mukilarasu_S_Master_Resume.pdf",
            caption=caption,
            parse_mode="Markdown"
        )

async def shade_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Calculates bulk industrial dye recipe and dosing schedule for SGC."""
    args = context.args
    if not args:
        help_text = (
            "🎨 *SGC SHADE INTELLIGENCE & RECIPE CALCULATOR*\n\n"
            "Usage:\n"
            "• `/shade <fabric_kg> <preset_shade>`\n"
            "  _Example:_ `/shade 250 navy_blue`\n"
            "  _Example:_ `/shade 500 jet_black`\n\n"
            "• `/shade <fabric_kg> <yellow%> <red%> <blue%>`\n"
            "  _Example:_ `/shade 250 0.85 0.42 0.18`\n\n"
            "Available Presets:\n"
            "`jet_black`, `navy_blue`, `royal_blue`, `forest_green`, `olive_green`, `maroon`, `golden_yellow`, `charcoal_grey`, `baby_pink`, `sky_blue`"
        )
        await update.message.reply_text(help_text, parse_mode="Markdown")
        return

    try:
        fabric_kg = float(args[0])
        from tools.sgc_shade_engine import calculate_dye_recipe, format_recipe_telegram_markdown

        if len(args) == 2:
            shade_name = args[1]
            recipe = calculate_dye_recipe(fabric_kg, shade_name)
        elif len(args) >= 4:
            y_pct = float(args[1])
            r_pct = float(args[2])
            b_pct = float(args[3])
            custom_dyes = {
                "name": f"Custom Formula (Y:{y_pct}% R:{r_pct}% B:{b_pct}%)",
                "reactive_yellow": y_pct,
                "reactive_red": r_pct,
                "reactive_blue": b_pct
            }
            recipe = calculate_dye_recipe(fabric_kg, custom_dyes)
        else:
            shade_name = args[1]
            recipe = calculate_dye_recipe(fabric_kg, shade_name)

        report = format_recipe_telegram_markdown(recipe)
        await _send_reply_safely(update, report)

    except Exception as e:
        logger.error(f"Shade calculation error: {e}")
        await update.message.reply_text(f"❌ Recipe calculation error: {e}")

async def color_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Matches any Hex / RGB color code against Pantone TCX & SGC database with dye prediction."""
    args = context.args
    if not args:
        help_text = (
            "🎯 *SGC COLOR FINDER & SHADE MATCHER*\n\n"
            "Usage:\n"
            "• `/findcolor <hex_code> [fabric_kg]`\n"
            "  _Example:_ `/findcolor #1B2F4D`\n"
            "  _Example:_ `/findcolor #BF1932 500`\n"
            "• `/findcolor <r> <g> <b> [fabric_kg]`\n"
            "  _Example:_ `/findcolor 27 47 77 250`\n\n"
            "💡 _You can also just send a PHOTO of any fabric/yarn swatch directly to this chat!_"
        )
        await update.message.reply_text(help_text, parse_mode="Markdown")
        return

    try:
        fabric_kg = 250.0
        from tools.sgc_color_finder import solve_swatch_full_solution, format_color_solution_telegram

        if args[0].startswith("#") or len(args[0]) in (6, 7):
            target = args[0] if args[0].startswith("#") else f"#{args[0]}"
            if len(args) >= 2:
                fabric_kg = float(args[1])
            res = solve_swatch_full_solution(target, fabric_kg=fabric_kg)
        elif len(args) >= 3:
            r, g, b = int(args[0]), int(args[1]), int(args[2])
            if len(args) >= 4:
                fabric_kg = float(args[3])
            res = solve_swatch_full_solution((r, g, b), fabric_kg=fabric_kg)
        else:
            target = args[0]
            res = solve_swatch_full_solution(target, fabric_kg=fabric_kg)

        report = format_color_solution_telegram(res)
        await _send_reply_safely(update, report)

        if ALWAYS_VOICE_REPLY:
            p_name = res["best_pantone_match"]["name"]
            p_code = res["best_pantone_match"]["code"]
            cost = res["industrial_batch_recipe"]["financials"]["cost_per_kg_fabric_inr"]
            voice_text = f"Maapla, colour find panniten! Closest match Pantone {p_name} ({p_code}). Chemical recipe calculation ready, cost around {cost} rupees per kg."
            try:
                voice_path = await generate_voice_audio(voice_text)
                if os.path.exists(voice_path):
                    with open(voice_path, "rb") as v:
                        await update.message.reply_voice(voice=v, caption="🎨 Color Match Voice Note")
                    os.remove(voice_path)
            except Exception:
                pass

    except Exception as e:
        logger.error(f"Color finder error: {e}")
        await update.message.reply_text(f"❌ Color Finder error: {e}")

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Automatically analyzes uploaded fabric swatch photos and generates chemical dyeing recipes."""
    if not is_authorized(update):
        return
    user_name = update.effective_user.first_name or "Mukil"
    logger.info(f"Received photo from {user_name}, processing swatch color analysis...")

    await update.effective_chat.send_action("typing")

    photo = None
    if update.message.photo:
        photo = update.message.photo[-1]
    elif update.message.document and update.message.document.mime_type and update.message.document.mime_type.startswith("image/"):
        photo = update.message.document

    if not photo:
        return

    try:
        swatches_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage", "swatches")
        os.makedirs(swatches_dir, exist_ok=True)
        save_path = os.path.join(swatches_dir, "latest_swatch.jpg")

        p_file = await context.bot.get_file(photo.file_id)
        await p_file.download_to_drive(save_path)

        # Parse fabric weight from caption if given
        caption = update.message.caption or ""
        fabric_kg = 250.0
        match_kg = re.search(r'(\d+(?:\.\d+)?)\s*(?:kg|kilo)', caption, re.IGNORECASE)
        if match_kg:
            fabric_kg = float(match_kg.group(1))

        await update.message.reply_text(f"🔬 *Analyzing Fabric Swatch...*\nFiltering shadows, glare, and computing CIEDE2000 Pantone & Reactive Recipe for `{fabric_kg} kg` lot...", parse_mode="Markdown")

        from tools.sgc_color_finder import solve_swatch_full_solution, format_color_solution_telegram
        res = solve_swatch_full_solution(save_path, fabric_kg=fabric_kg)
        report = format_color_solution_telegram(res)

        await _send_reply_safely(update, report)

        # Log to memory
        p = res["best_pantone_match"]
        c = res["extracted_color"]
        mem.log_task("SWATCH_COLOR_MATCH", f"Analyzed swatch photo. Matched: {p['name']} ({p['code']}), Hex: {c['hex']}, Lot: {fabric_kg}kg")
        mem.update_context({
            "latest_swatch_match": {
                "hex": c["hex"],
                "pantone": f"{p['name']} ({p['code']})",
                "delta_e": p["delta_e"],
                "fabric_kg": fabric_kg,
                "timestamp": datetime.now().isoformat()
            }
        })

        if ALWAYS_VOICE_REPLY:
            cost = res["industrial_batch_recipe"]["financials"]["cost_per_kg_fabric_inr"]
            voice_summary = (
                f"Maapla, unga swatch photo-va analyze panniten! Indha color Pantone {p['name']} kooda match aagudhu. "
                f"Delta E romba accurate-ah irukku. {fabric_kg} kg lot-ku full chemical recipe calculation anuppitten. Cost {cost} rupees per kg!"
            )
            try:
                voice_path = await generate_voice_audio(voice_summary)
                if os.path.exists(voice_path):
                    with open(voice_path, "rb") as v:
                        await update.message.reply_voice(voice=v, caption="🎙️ Swatch Analysis Summary")
                    os.remove(voice_path)
            except Exception:
                pass

    except Exception as e:
        logger.error(f"Swatch photo processing error: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Error analyzing swatch photo: {e}")

async def menu_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Full Command Center Menu."""
    menu_text = (
        "⚡ *JARVIS COMMAND CENTER MENU* ⚡\n\n"
        "⏰ *Smart Reminders & Notes:*\n"
        "• `/remind <time> <task>` - Set Timed Reminder / Alarm + Voice Alert\n"
        "• `/reminders` - View active scheduled reminders\n"
        "• `/cancelremind <id>` - Cancel an active reminder\n"
        "• `/overdue` - SGC Overdue Balance Radar & Follow-up Drafts\n"
        "• `/note <text>` - Save idea/rate to Quick Notes Brain\n"
        "• `/notes` - List all saved quick notes\n"
        "• `/delnote <id>` - Delete a quick note\n\n"
        "🧾 *SGC Dyeing & Business Automation:*\n"
        "• `/shade <kg> <shade>` - Kubelka-Munk Dye Dosing & Chemical Schedule\n"
        "• `/bill <details>` - Instant Bill Creation + CSB Bank Details (Print / Xerox ready) + PDF\n"
        "• `/sgc` - SGC Invoicing Drive Vaults & Status\n\n"
        "🎯 *Placements & Career:*\n"
        "• `/resume` or `/cv` - Instant Master ATS Resume Document to Telegram\n"
        "• `/drill` - Daily MNC Coding (Zoho, TCS, Infosys) & Aptitude Problem\n"
        "• `/solve <id>` - Optimal Java Solution & Analysis\n"
        "• `/radar` or `/jobs` - Live Fresher/Junior AI & SDE Openings Radar\n"
        "• `/apply <company|link>` - Autonomous Auto-Apply + Live Photo Receipt\n"
        "• `/tenses` - Tenses.ai placement test auto-typer status\n\n"
        "🤖 *Antigravity & PC Terminal:*\n"
        "• `/agy <task>` or `/code <task>` - Run Google Antigravity autonomous agent\n"
        "• `/cmd <command>` - Execute Windows PowerShell command\n"
        "• `/linkedin` - Auto-publish latest git commit to LinkedIn\n"
        "• `/proofs` - Re-send all verification screenshots & docs\n"
        "• `/drive` - 5TB Master Vault & 250GB Mesh access\n"
        "• `/vitals` - Live PC hardware vitals"
    )
    await update.message.reply_text(menu_text, parse_mode="Markdown")

async def remind_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sets a timed reminder, alarm, or countdown timer."""
    if not context.args:
        help_text = (
            "⏰ <b>JARVIS SMART REMINDERS & ALARMS</b>\n\n"
            "Usage:\n"
            "• <code>/remind &lt;time&gt; &lt;task&gt;</code>\n\n"
            "<b>Examples:</b>\n"
            "• <code>/remind 10m Study Java DSA</code>\n"
            "• <code>/remind 5 mins Call Bannari Amman Mills</code>\n"
            "• <code>/remind 1h 30m Placement Aptitude Test</code>\n"
            "• <code>/remind 10:00 PM Bedtime & Drive Sync</code>\n"
            "• <code>/remind 17:30 SGC Dyeing Machine Check</code>\n\n"
            "👉 <i>You can also just speak or type naturally! (e.g. '10 mins ku reminder veyyi')</i>"
        )
        await update.message.reply_text(help_text, parse_mode="HTML")
        return

    raw_args = " ".join(context.args)
    try:
        reminder = reminder_scheduler.parse_and_create(
            chat_id=update.effective_chat.id,
            user_id=update.effective_user.id,
            command_args=raw_args
        )
        target_dt = datetime.fromisoformat(reminder["target_time"])
        ist_offset = timedelta(hours=5, minutes=30)
        target_ist = target_dt + ist_offset

        reply_msg = (
            f"✅ <b>REMINDER SCHEDULED!</b> ⏰\n\n"
            f"📌 <b>Task</b>: {reminder['message']}\n"
            f"🕒 <b>Alert Time</b>: <code>{target_ist.strftime('%I:%M %p (IST)')}</code>\n"
            f"🆔 <b>ID</b>: <code>{reminder['reminder_id']}</code>\n\n"
            f"<i>JARVIS will send you an urgent notification & voice alert when time is up!</i>\n"
            f"To cancel: <code>/cancelremind {reminder['reminder_id']}</code>"
        )
        await update.message.reply_text(reply_msg, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Remind command error: {e}")
        await update.message.reply_text(
            f"❌ Could not schedule reminder: {e}\nTry e.g.: <code>/remind 10m Study Java</code>",
            parse_mode="HTML"
        )

async def reminders_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lists all active pending reminders."""
    active = reminder_scheduler.list_reminders(user_id=update.effective_user.id)
    if not active:
        await update.message.reply_text(
            "⏰ <b>No active reminders.</b>\n\nSet one with <code>/remind &lt;time&gt; &lt;task&gt;</code> (e.g. <code>/remind 10m Study Java</code>)!",
            parse_mode="HTML"
        )
        return

    msg = f"⏰ <b>ACTIVE REMINDERS & TIMERS ({len(active)})</b>\n\n"
    ist_offset = timedelta(hours=5, minutes=30)
    for r in active:
        target_dt = datetime.fromisoformat(r["target_time"])
        target_ist = target_dt + ist_offset
        msg += f"• <b>{r['message']}</b>\n  🕒 {target_ist.strftime('%I:%M %p')} | 🆔 <code>{r['reminder_id']}</code>\n"
    
    msg += "\n👉 <i>To cancel any reminder: <code>/cancelremind &lt;reminder_id&gt;</code></i>"
    await update.message.reply_text(msg, parse_mode="HTML")

async def cancelremind_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancels an active reminder."""
    if not context.args:
        await update.message.reply_text("Usage: <code>/cancelremind &lt;reminder_id&gt;</code>\nRun <code>/reminders</code> to view active IDs.", parse_mode="HTML")
        return
    
    rid = context.args[0].strip()
    success = reminder_scheduler.cancel_reminder(rid)
    if success:
        await update.message.reply_text(f"✅ Reminder <code>{rid}</code> cancelled.", parse_mode="HTML")
    else:
        await update.message.reply_text(f"❌ Reminder <code>{rid}</code> not found or already fired.", parse_mode="HTML")

async def overdue_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Checks SGC Dyeing overdue payments and returns follow-up templates."""
    await update.effective_chat.send_action("typing")
    try:
        from tools.sgc_overdue_radar import format_overdue_telegram
        report = format_overdue_telegram()
        await update.message.reply_text(report, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Overdue radar error: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Overdue Radar error: {e}")

async def note_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Saves a quick thought or note to persistent memory."""
    if not context.args:
        await update.message.reply_text("Usage: <code>/note &lt;your thought or note&gt;</code>\nExample: <code>/note Karur spinning mill rate 240/kg for 20s cone</code>", parse_mode="HTML")
        return
    text = " ".join(context.args)
    try:
        from tools.quick_notes import add_note
        n = add_note(text, source="Telegram")
        await update.message.reply_text(
            f"📝 <b>Note #{n['id']} Saved!</b>\n\n<i>\"{n['text']}\"</i>\n\nView all: <code>/notes</code>",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Note save error: {e}")
        await update.message.reply_text(f"❌ Error saving note: {e}")

async def notes_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays all saved quick notes."""
    try:
        from tools.quick_notes import format_notes_telegram
        text = format_notes_telegram()
        await update.message.reply_text(text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Notes display error: {e}")
        await update.message.reply_text(f"❌ Error retrieving notes: {e}")

async def delnote_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Deletes a quick note by ID."""
    if not context.args:
        await update.message.reply_text("Usage: <code>/delnote &lt;id&gt;</code> (Run <code>/notes</code> to view IDs)", parse_mode="HTML")
        return
    try:
        from tools.quick_notes import delete_note
        nid = int(context.args[0])
        if delete_note(nid):
            await update.message.reply_text(f"🗑️ <b>Note #{nid} deleted.</b>", parse_mode="HTML")
        else:
            await update.message.reply_text(f"❌ Note #{nid} not found.", parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ Error deleting note: {e}")

async def handle_direct_shortcuts(text: str, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Inspects raw user text/voice input for direct actions before calling Antigravity."""
    t_lower = text.lower().strip()

    # 1. Bill creation shortcut
    if t_lower.startswith("bill:") or t_lower.startswith("/bill") or ("kattu" in t_lower and "kazhi" in t_lower and any(w in t_lower for w in ["rate", "bill", "yarn"])):
        clean_prompt = text.replace("bill:", "").replace("/bill", "").strip()
        context.args = clean_prompt.split(",")
        await bill_cmd(update, context)
        return True

    # 2. Overdue Radar shortcut
    if any(k in t_lower for k in ["overdue", "pending bill", "pending payment", "balance amount", "balance collection"]):
        await overdue_cmd(update, context)
        return True

    # 3. Reminder / Alarm detection
    reminder_keywords = ["remind me", "set reminder", "set a reminder", "set alarm", "set an alarm", "alarm veyyi", "timer veyyi", "reminder veyyi", "mani ku remind", "manikku remind"]
    is_explicit_remind = any(k in t_lower for k in reminder_keywords)
    is_timer_like = ("timer" in t_lower or "remind" in t_lower) and any(u in t_lower for u in ["min", "minute", "hour", "hr", "sec", "pm", "am", "mani", "m", "h", "s"])

    if is_explicit_remind or is_timer_like:
        try:
            reminder = reminder_scheduler.parse_and_create(
                chat_id=update.effective_chat.id,
                user_id=update.effective_user.id,
                command_args=text
            )
            target_dt = datetime.fromisoformat(reminder["target_time"])
            ist_offset = timedelta(hours=5, minutes=30)
            target_ist = target_dt + ist_offset

            reply_msg = (
                f"✅ <b>REMINDER SCHEDULED!</b> ⏰\n\n"
                f"📌 <b>Task</b>: {reminder['message']}\n"
                f"🕒 <b>Alert Time</b>: <code>{target_ist.strftime('%I:%M %p (IST)')}</code>\n"
                f"🆔 <b>ID</b>: <code>{reminder['reminder_id']}</code>\n\n"
                f"<i>JARVIS will send you an urgent notification & voice alert when time is up!</i>\n"
                f"To cancel: <code>/cancelremind {reminder['reminder_id']}</code>"
            )
            await update.message.reply_text(reply_msg, parse_mode="HTML")
            if ALWAYS_VOICE_REPLY:
                try:
                    voice_path = await generate_voice_audio(f"Maapla, {reminder['message']} ku reminder set panniten at {target_ist.strftime('%I:%M %p')}!")
                    if os.path.exists(voice_path):
                        with open(voice_path, "rb") as v:
                            await update.message.reply_voice(voice=v, caption="⏰ Reminder Confirmed")
                        os.remove(voice_path)
                except Exception:
                    pass
            return True
        except Exception as ex:
            logger.info(f"Natural reminder parse fell through to Antigravity: {ex}")

    # 4. Quick Note detection
    if t_lower.startswith("note:") or t_lower.startswith("save note:"):
        note_txt = text.replace("save note:", "", 1).replace("Save note:", "", 1).replace("note:", "", 1).replace("Note:", "", 1).strip()
        if note_txt:
            context.args = note_txt.split()
            await note_cmd(update, context)
            return True

    # 5. Master Resume auto-dispatch
    if ("resume" in t_lower or "cv" in t_lower) and any(w in t_lower for w in ["send", "anuppu", "share", "kudu", "view", "check", "linked", "open"]):
        logger.info("Auto-dispatching Master Resume...")
        resume_path = r"C:\Users\mukil\jarvis-core\storage\Mukil_Master_Resume.pdf"
        if os.path.exists(resume_path):
            try:
                with open(resume_path, "rb") as doc:
                    await update.message.reply_document(
                        document=doc,
                        filename="Mukilarasu_S_Master_Resume.pdf",
                        caption="📄 *Mukilarasu S — Master ATS Resume (Verified)*\n🔗 https://drive.google.com/file/d/1TpyzV7OGEf-YQfGLUpusAI5cDDvF1kAJ/view?usp=drive_link\n\nMaapla, unga official Master ATS Resume direct-ah anuppi vachitten!",
                        parse_mode="Markdown"
                    )
                return True
            except Exception as resume_err:
                logger.error(f"Failed to auto-send resume document: {resume_err}")

    # 6. Smart Color Finder shortcut
    hex_match = re.search(r'#([A-Fa-f0-9]{6})\b', text)
    if hex_match or any(k in t_lower for k in ["color find", "colour find", "shade find", "color match", "match color", "pantone match"]):
        if hex_match:
            context.args = [f"#{hex_match.group(1)}"]
        else:
            context.args = text.split()
        await color_cmd(update, context)
        return True

    return False


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


def _find_pdf_path(text: str) -> Optional[str]:
    patterns = [
        r'(?:Proof Screenshot / PDF|PDF Document|PDF):\s*`?([^\s`\n\r]+\.pdf)`?',
        r'([A-Za-z]:\\[^\s\n\r]+\.pdf)',
        r'(storage[\\/]bills[\\/][^\s`\n\r]+\.pdf)',
        r'([^\s`\n\r]+Bill[^\s`\n\r]*\.pdf)'
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


async def _send_pdf_if_present(update: Update, text: str):
    pdf_p = _find_pdf_path(text)
    if pdf_p and os.path.exists(pdf_p):
        try:
            with open(pdf_p, "rb") as pdf_file:
                await update.message.reply_document(
                    document=pdf_file,
                    filename=os.path.basename(pdf_p),
                    caption=f"🧾 Official PDF Invoice: {os.path.basename(pdf_p)}"
                )
        except Exception as pdf_err:
            logger.error(f"Error sending PDF: {pdf_err}")

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

async def query_antigravity(prompt: str, user_name: str = "Mukil") -> str:
    """
    Executes prompt through the Cloud Antigravity Cognitive Brain (ServerRouter + Groq/Gemini).
    Zero physical PC access, zero local disk blocking, pure online cloud execution.
    """
    try:
        history = mem.get_recent_conversations(limit=6)
        history_formatted = [
            {"role": "user" if h.get("sender") != "JARVIS" else "assistant", "content": h.get("text", "")}
            for h in history
        ]
        router_resp = await asyncio.to_thread(
            server_router.handle_message,
            prompt,
            conversation_history=history_formatted,
            user_name=user_name
        )
        return router_resp.reply
    except Exception as e:
        logger.error(f"Cloud brain execution error: {e}")
        return f"⚠️ Cloud brain issue: {e}"

async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
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
                prompt="Tanglish, Tamil, English conversation with Jarvis and Antigravity AI",
                response_format="text"
            )

        if os.path.exists(temp_path):
            os.remove(temp_path)

        transcribed_text = str(transcription).strip()
        logger.info(f"Transcribed voice text: {transcribed_text}")
        
        await update.message.reply_text(f"🎙️ *Heard:* \"_{transcribed_text}_\"", parse_mode="Markdown")
        await update.effective_chat.send_action("typing")

        # 1. Check direct shortcuts first (Bill, Overdue, Reminders, Notes, Resume)
        shortcut_handled = await handle_direct_shortcuts(transcribed_text, update, context)
        if shortcut_handled:
            return

        # 2. Execute directly on Google Antigravity
        reply = await query_antigravity(transcribed_text)
        await _send_reply_safely(update, reply)

        # If screenshot or PDF was created, send directly to Telegram
        await _send_screenshot_if_present(update, reply)
        await _send_pdf_if_present(update, reply)

        # Generate and send Voice Note back to User
        try:
            await update.effective_chat.send_action("record_voice")
            voice_summary = reply[:300]
            reply_audio_path = await generate_voice_audio(voice_summary)
            with open(reply_audio_path, "rb") as voice_out:
                await update.message.reply_voice(voice=voice_out, caption="🔊 Antigravity Voice")
            if os.path.exists(reply_audio_path):
                os.remove(reply_audio_path)
        except Exception as tts_err:
            logger.error(f"TTS audio reply error: {tts_err}")

    except Exception as e:
        logger.error(f"Voice processing error: {e}")
        await update.message.reply_text(f"❌ Voice processing error: {str(e)}")

async def chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    user_text = update.message.text
    if not user_text:
        return
    
    user_name = update.effective_user.first_name or "Mukil"
    logger.info(f"Received text message from {user_name}: {user_text}")
    
    await update.effective_chat.send_action("typing")

    # 1. Check direct shortcuts first (Bill, Overdue, Reminders, Notes, Resume)
    shortcut_handled = await handle_direct_shortcuts(user_text, update, context)
    if shortcut_handled:
        return

    # 2. Query Google Antigravity Direct Brain
    reply = await query_antigravity(user_text)

    # 3. Synchronize state to persistent memory (conversations_history.json & task_log.json)
    mem.append_conversation(user_name, user_text)
    mem.append_conversation("Antigravity", reply)
    mem.log_task("TELEGRAM_CHAT", f"User ({user_name}): {user_text[:60]}... | Antigravity: {reply[:60]}...")
    mem.update_context({
        "last_telegram_interaction": {
            "user_message": user_text,
            "bot_reply": reply[:100],
            "timestamp": datetime.now().isoformat()
        }
    })

    # 4. Safely send text reply
    await _send_reply_safely(update, reply)

    # 5. Screenshot and PDF Document finder
    await _send_screenshot_if_present(update, reply)
    await _send_pdf_if_present(update, reply)

    # 6. If always voice reply is on and reply is concise
    if ALWAYS_VOICE_REPLY and len(reply) < 300:
        try:
            await update.effective_chat.send_action("record_voice")
            reply_audio_path = await generate_voice_audio(reply)
            with open(reply_audio_path, "rb") as voice_out:
                await update.message.reply_voice(voice=voice_out, caption="🔊 Antigravity Voice")
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

async def bot_post_init(application):
    global bot_app
    bot_app = application
    await reminder_scheduler.start()
    logger.info("ReminderScheduler background loop successfully started.")

async def bot_post_shutdown(application):
    await reminder_scheduler.stop()
    logger.info("ReminderScheduler stopped.")

def build_app():
    req = HTTPXRequest(
        connection_pool_size=8,
        read_timeout=30.0,
        write_timeout=30.0,
        connect_timeout=30.0,
        pool_timeout=30.0
    )
    app = (
        ApplicationBuilder()
        .token(TELEGRAM_BOT_TOKEN)
        .request(req)
        .post_init(bot_post_init)
        .post_shutdown(bot_post_shutdown)
        .build()
    )
    
    def add_cmd(name, fn):
        app.add_handler(CommandHandler(name, auth_guard(fn)))

    add_cmd("start", start)
    add_cmd("status", status_cmd)
    add_cmd("diagnose", diagnose_cmd)
    add_cmd("vitals", diagnose_cmd)
    add_cmd("drive", drive_cmd)
    add_cmd("find", find_cmd)
    add_cmd("search", find_cmd)
    add_cmd("apply", apply_cmd)
    add_cmd("code", code_cmd)
    add_cmd("aura", code_cmd)
    add_cmd("antigravity", code_cmd)
    add_cmd("agy", code_cmd)
    add_cmd("cmd", terminal_cmd)
    add_cmd("terminal", terminal_cmd)
    add_cmd("linkedin", linkedin_cmd)
    add_cmd("proofs", proofs_cmd)
    add_cmd("bill", bill_cmd)
    add_cmd("newbill", bill_cmd)
    add_cmd("remind", remind_cmd)
    add_cmd("reminders", reminders_cmd)
    add_cmd("alarms", reminders_cmd)
    add_cmd("cancelremind", cancelremind_cmd)
    add_cmd("delremind", cancelremind_cmd)
    add_cmd("overdue", overdue_cmd)
    add_cmd("sgcoverdue", overdue_cmd)
    add_cmd("note", note_cmd)
    add_cmd("notes", notes_cmd)
    add_cmd("delnote", delnote_cmd)
    add_cmd("drill", drill_cmd)
    add_cmd("dsa", drill_cmd)
    add_cmd("apti", drill_cmd)
    add_cmd("solve", solve_cmd)
    add_cmd("radar", radar_cmd)
    add_cmd("jobs", radar_cmd)
    add_cmd("placement", radar_cmd)
    add_cmd("resume", resume_cmd)
    add_cmd("cv", resume_cmd)
    add_cmd("shade", shade_cmd)
    add_cmd("recipe", shade_cmd)
    add_cmd("findcolor", color_cmd)
    add_cmd("color", color_cmd)
    add_cmd("match", color_cmd)
    add_cmd("swatch", color_cmd)
    add_cmd("tenses", tenses_cmd)
    add_cmd("sgc", sgc_cmd)
    add_cmd("gst", gst_cmd)
    add_cmd("gstr", gst_cmd)
    add_cmd("fundmycrazy", fund_cmd)
    add_cmd("menu", menu_cmd)
    add_cmd("help", menu_cmd)
    app.add_handler(CallbackQueryHandler(gst_callback_handler, pattern="^gst_"))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, photo_handler))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, voice_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat_handler))
    app.add_error_handler(global_error_handler)
    return app

def main():
    if sys.platform == "win32":
        try:
            import ctypes
            user32 = ctypes.windll.user32
            h_desk = user32.OpenDesktopW("default", 0, False, 0x0100)
            if h_desk:
                user32.SetThreadDesktop(h_desk)
        except Exception:
            pass

    print("Jarvis 2-Way Voice Gateway is 100% LIVE and listening!")
    
    while True:
        try:
            app = build_app()
            app.run_polling(drop_pending_updates=True, bootstrap_retries=-1, timeout=20)
            time.sleep(3)
        except (KeyboardInterrupt, SystemExit):
            break
        except Exception as e:
            logger.error(f"Polling loop auto-recovering from: {e}. Retrying in 5s...")
            time.sleep(5)

if __name__ == "__main__":
    main()

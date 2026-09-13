import json
import os
import sys
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

SGC_DATA_PATH = Path(os.environ.get("APPDATA", "")) / "sgc-billing" / "sgc-billing-data.json"

def get_overdue_report() -> dict:
    """Analyzes pending bills in SGC Billing and returns overdue analysis & follow-up messages."""
    if not SGC_DATA_PATH.exists():
        return {"error": "SGC Billing database not found."}

    try:
        with open(SGC_DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return {"error": f"Failed to read database: {e}"}

    bills = data.get("sgc-bills", [])
    now = datetime.now()

    pending_bills = []
    total_pending = 0.0

    for b in bills:
        if b.get("status", "").lower() == "pending":
            net = float(b.get("netAmount", 0))
            total_pending += net
            date_str = b.get("date", "")
            days_ago = 0
            try:
                b_date = datetime.strptime(date_str, "%Y-%m-%d")
                days_ago = (now - b_date).days
            except Exception:
                pass

            if days_ago > 30:
                tier = "CRITICAL_30_DAYS"
                badge = "🔴"
            elif days_ago > 14:
                tier = "WARNING_15_DAYS"
                badge = "🟡"
            else:
                tier = "RECENT"
                badge = "🟢"

            # Pre-formatted professional follow-up message in Tamil & English
            customer = b.get("customer", "Client")
            bill_no = b.get("billNo")
            draft_msg = (
                f"Vanakkam sir, Sri Ganapathi Colours la irundhu. "
                f"Namma Invoice #{bill_no} (Dated: {date_str}) total amount Rs.{net:,.0f} pending-la irukku. "
                f"Please update payment status when convenient. Bank: CSB Bank, A/C: 003204157368195001, IFSC: CSBK0000032. Nandri!"
            )

            pending_bills.append({
                "bill_no": bill_no,
                "customer": customer,
                "date": date_str,
                "days_overdue": days_ago,
                "net_amount": net,
                "tier": tier,
                "badge": badge,
                "draft_followup": draft_msg
            })

    pending_bills.sort(key=lambda x: x["days_overdue"], reverse=True)

    return {
        "total_pending_amount": total_pending,
        "total_pending_count": len(pending_bills),
        "bills": pending_bills,
        "as_of": now.strftime("%Y-%m-%d %I:%M %p")
    }

def format_overdue_telegram() -> str:
    rep = get_overdue_report()
    if rep.get("error"):
        return f"⚠️ {rep['error']}"

    total = rep["total_pending_amount"]
    count = rep["total_pending_count"]
    bills = rep["bills"]

    if count == 0:
        return "🎉 *All SGC bills are 100% cleared! Zero pending payments.*"

    text = (
        f"📊 <b>SGC PAYMENT OVERDUE & COLLECTION RADAR</b>\n\n"
        f"• <b>Total Outstanding</b>: <b>₹{total:,.2f}</b> across <b>{count} Bills</b>\n"
        f"• <b>As of</b>: <code>{rep['as_of']}</code>\n\n"
        f"<b>Pending Bills Breakdown:</b>\n"
    )

    for b in bills:
        text += (
            f"{b['badge']} <b>Bill #{b['bill_no']}</b>: <b>{b['customer']}</b>\n"
            f"   💰 Amount: <b>₹{b['net_amount']:,.0f}</b> | ⏳ Age: <b>{b['days_overdue']} days ago</b> ({b['date']})\n"
        )

    text += (
        "\n💡 <b>Follow-up Action:</b>\n"
        "Copy draft payment reminder for any client to send on WhatsApp with CSB Bank details!"
    )
    return text

if __name__ == "__main__":
    print(format_overdue_telegram())

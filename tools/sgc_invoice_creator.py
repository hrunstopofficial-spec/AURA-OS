import base64
import io
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
try:
    import qrcode
except ImportError:
    qrcode = None

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_BILLS_DIR = BASE_DIR / "storage" / "bills"
STORAGE_BILLS_DIR.mkdir(parents=True, exist_ok=True)

SGC_DATA_PATH = Path(os.environ.get("APPDATA", "")) / "sgc-billing" / "sgc-billing-data.json"
LOCAL_EXPORT_DIR = Path("E:/GC BILLS")
if not LOCAL_EXPORT_DIR.exists():
    try:
        LOCAL_EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:
        LOCAL_EXPORT_DIR = STORAGE_BILLS_DIR

COMPANY_PROFILE = {
    "name": "SRI GANAPATHI COLOURS",
    "address": "# 14/1, P.Vellalapatti, Puliyur (P.o), Karur - 639114.",
    "contact": "Tamilnadu. Cell : 9655527062",
    "gstin": "33HKSPS1735K1ZH",
    "hsn": "9988",
    "bankName": "CSB BANK",
    "accountNo": "003204157368195001",
    "ifsc": "CSBK0000032",
    "upiVpa": "003204157368195001@csb",
    "title": "TAX INVOICE - DYEING COOLIE CHARGES",
    "jurisdiction": "KARUR"
}

DEFAULT_COUNT_MAP = [
    {"count": "2/40s", "kazhi": 17},
    {"count": "2/30s", "kazhi": 15},
    {"count": "10s", "kazhi": 20},
    {"count": "20s", "kazhi": 20},
    {"count": "2/20s", "kazhi": 17},
    {"count": "16s", "kazhi": 20},
    {"count": "2s", "kazhi": 20},
    {"count": "2/4s", "kazhi": 10},
    {"count": "2/6s", "kazhi": 12},
    {"count": "2/10s", "kazhi": 10}
]

def num_to_words(n):
    a = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine', 'Ten',
         'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen', 'Seventeen', 'Eighteen', 'Nineteen']
    b = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety']
    n = int(round(n))
    if n == 0: return 'Zero'
    if n < 20: return a[n]
    if n < 100: return b[n // 10] + ((' ' + a[n % 10]) if n % 10 else '')
    if n < 1000: return a[n // 100] + ' Hundred' + ((' ' + num_to_words(n % 100)) if n % 100 else '')
    if n < 100000: return num_to_words(n // 1000) + ' Thousand' + ((' ' + num_to_words(n % 1000)) if n % 1000 else '')
    if n < 10000000: return num_to_words(n // 100000) + ' Lakh' + ((' ' + num_to_words(n % 100000)) if n % 100000 else '')
    return num_to_words(n // 10000000) + ' Crore' + ((' ' + num_to_words(n % 10000000)) if n % 10000000 else '')

def calc_amount(kattu, kazhi, rate, count_str, count_map=None):
    k = float(kattu or 0)
    kz = float(kazhi or 0)
    r = float(rate or 0)
    if r == 0 or (k == 0 and kz == 0):
        return 0.0
    if k == 0:
        return kz * r
    if kz == 0:
        return k * r
    
    count_key = str(count_str or "").strip().lower()
    c_map = count_map or DEFAULT_COUNT_MAP
    mapping = next((m for m in c_map if m["count"].lower() == count_key), None)
    
    if not mapping or not mapping.get("kazhi"):
        return (k * r) + (kz * r)
    kazhi_per_kattu = float(mapping["kazhi"])
    return (k * r) + (kz * (r / kazhi_per_kattu))

def generate_upi_qr_base64(bill_no, customer, net_amount):
    """Generates an NPCI compliant Dynamic UPI QR code as base64 PNG."""
    pa = COMPANY_PROFILE["upiVpa"]
    pn = "SRI GANAPATHI COLOURS"
    safe_cust = re.sub(r'[^a-zA-Z0-9 ]', '', customer)[:20].strip()
    tn = f"Bill {bill_no} {safe_cust}"
    upi_url = f"upi://pay?pa={pa}&pn={pn}&am={net_amount:.2f}&cu=INR&tn={tn}"
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=4,
        border=2,
    )
    qr.add_data(upi_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    b64_qr = base64.b64encode(buf.getvalue()).decode("utf-8")
    return upi_url, b64_qr

def generate_html_invoice(bill, b64_qr=None):
    """Generates print-ready HTML matching Sri Ganapathi Colours official bill format."""
    c = COMPANY_PROFILE
    items = bill.get("items", [])
    sub = float(bill.get("subtotal", 0))
    cgst = float(bill.get("cgst", 0))
    sgst = float(bill.get("sgst", 0))
    net = int(bill.get("netAmount", 0))
    words = num_to_words(net) + " Rupees Only"
    
    rows_html = ""
    for i, it in enumerate(items):
        rows_html += f"""
        <tr style="background:{'#ffffff' if i%2==0 else '#f8faff'}">
            <td style="border:1px solid #9bb;padding:6px 3px;text-align:center;font-size:12px;">{i+1}</td>
            <td style="border:1px solid #9bb;padding:6px 4px;text-align:center;font-size:12px;">{it.get('delNo','')}</td>
            <td style="border:1px solid #9bb;padding:6px 4px;text-align:center;font-size:12px;">{it.get('poNo','')}</td>
            <td style="border:1px solid #9bb;padding:6px 6px;text-align:left;font-size:12px;font-weight:600;">{it.get('variety','')}</td>
            <td style="border:1px solid #9bb;padding:6px 4px;text-align:center;font-size:12px;">{it.get('count','')}</td>
            <td style="border:1px solid #9bb;padding:6px 4px;text-align:center;font-size:12px;">{it.get('kattu','')}</td>
            <td style="border:1px solid #9bb;padding:6px 4px;text-align:center;font-size:12px;">{it.get('kazhi','')}</td>
            <td style="border:1px solid #9bb;padding:6px 4px;text-align:center;font-size:12px;">{float(it.get('rate',0)):.2f}</td>
            <td style="border:1px solid #9bb;padding:6px 6px;text-align:right;font-size:12px;font-weight:700;">{float(it.get('amount',0)):.2f}</td>
        </tr>
        """
    
    # Fill remaining empty rows for standard A4 invoice format
    empty_count = max(0, 10 - len(items))
    for _ in range(empty_count):
        rows_html += '<tr>' + '<td style="border:1px solid #9bb;height:22px">&nbsp;</td>'*9 + '</tr>'

    html = f"""<!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8">
    <title>Invoice #{bill['billNo']}</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: 20px; color: #111; background: #fff; }}
        .box {{ border: 2px solid #003366; padding: 12px; border-radius: 4px; }}
        .header {{ text-align: center; border-bottom: 2px solid #003366; padding-bottom: 8px; margin-bottom: 10px; }}
        .header h1 {{ margin: 0; font-size: 26px; color: #003366; letter-spacing: 1px; font-weight: 800; }}
        .header p {{ margin: 2px 0; font-size: 11px; color: #444; }}
        .info-grid {{ display: flex; justify-content: space-between; margin-bottom: 10px; font-size: 12px; }}
        .bill-table {{ width: 100%; border-collapse: collapse; margin-top: 5px; }}
        .bill-table th {{ background: #003366; color: #fff; border: 1px solid #003366; padding: 6px; font-size: 11px; text-transform: uppercase; }}
        .totals-table {{ width: 100%; margin-top: 10px; font-size: 12px; }}
        .bank-box {{ border: 1px solid #003366; padding: 8px; border-radius: 4px; background: #f4f8ff; font-size: 11px; }}
        .qr-box {{ text-align: center; border: 1px solid #003366; padding: 6px; border-radius: 4px; background: #fff; }}
    </style>
    </head>
    <body>
    <div class="box">
        <div class="header">
            <div style="font-size: 10px; font-weight: bold; color: #888; text-transform: uppercase; letter-spacing: 2px;">GST TAX INVOICE</div>
            <h1>{c['name']}</h1>
            <p>{c['address']}</p>
            <p>{c['contact']} | <b>GSTIN: {c['gstin']}</b> | HSN/SAC: {c['hsn']}</p>
        </div>

        <table style="width: 100%; font-size: 12px; margin-bottom: 8px;">
            <tr>
                <td style="width: 60%; vertical-align: top;">
                    <b>TO / CUSTOMER:</b><br>
                    <span style="font-size: 15px; font-weight: 700; color: #003366;">{bill.get('customer','')}</span><br>
                    GSTIN: <b>{bill.get('partyGst') or 'URP / Not Provided'}</b>
                </td>
                <td style="width: 40%; vertical-align: top; text-align: right;">
                    <b>INVOICE NO:</b> <span style="font-size: 16px; font-weight: 800; color: #d32f2f;">#{bill['billNo']}</span><br>
                    <b>DATE:</b> {bill.get('date', datetime.now().strftime('%Y-%m-%d'))}<br>
                    <b>PLACE:</b> {c['jurisdiction']}
                </td>
            </tr>
        </table>

        <table class="bill-table">
            <thead>
                <tr>
                    <th style="width: 5%;">S.No</th>
                    <th style="width: 10%;">Del.No</th>
                    <th style="width: 10%;">PO.No</th>
                    <th style="width: 25%;">Variety / Item</th>
                    <th style="width: 10%;">Count</th>
                    <th style="width: 8%;">Kattu</th>
                    <th style="width: 8%;">Kazhi</th>
                    <th style="width: 10%;">Rate</th>
                    <th style="width: 14%;">Amount (₹)</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>

        <table style="width: 100%; margin-top: 10px;">
            <tr>
                <td style="width: 60%; vertical-align: top;">
                    <div style="font-size: 11px; margin-bottom: 6px;">
                        <b>Amount in Words:</b><br>
                        <i style="color: #003366; font-weight: 600;">{words}</i>
                    </div>

                    <div class="bank-box" style="margin-top: 8px; padding: 10px; border: 1px solid #003366; border-radius: 4px; background: #f8faff;">
                        <b style="color: #003366; font-size: 11px;">🏦 BANK DETAILS FOR PAYMENT:</b><br>
                        Bank Name: <b>{c['bankName']}</b> &nbsp;|&nbsp; Branch: <b>Karur</b><br>
                        Current A/c No: <b style="font-size: 13px; color: #003366;">{c['accountNo']}</b><br>
                        IFSC Code: <b>{c['ifsc']}</b>
                    </div>
                </td>

                <td style="width: 40%; vertical-align: top;">
                    <table style="width: 100%; font-size: 12px; border-collapse: collapse; text-align: right;">
                        <tr>
                            <td style="padding: 4px;"><b>Subtotal (Taxable):</b></td>
                            <td style="padding: 4px; font-weight: 600;">₹{sub:.2f}</td>
                        </tr>
                        <tr>
                            <td style="padding: 4px;">CGST @ 2.5%:</td>
                            <td style="padding: 4px;">₹{cgst:.2f}</td>
                        </tr>
                        <tr>
                            <td style="padding: 4px;">SGST @ 2.5%:</td>
                            <td style="padding: 4px;">₹{sgst:.2f}</td>
                        </tr>
                        <tr style="border-top: 2px solid #003366; border-bottom: 2px solid #003366; background: #f0f5ff;">
                            <td style="padding: 6px; font-size: 14px; font-weight: 800; color: #003366;">NET AMOUNT:</td>
                            <td style="padding: 6px; font-size: 16px; font-weight: 800; color: #d32f2f;">₹{net}.00</td>
                        </tr>
                    </table>

                    <div style="text-align: center; margin-top: 35px; font-size: 11px;">
                        For <b>SRI GANAPATHI COLOURS</b><br><br><br>
                        <b>Authorised Signatory</b>
                    </div>
                </td>
            </tr>
        </table>
    </div>
    </body>
    </html>
    """
    return html

def create_sgc_bill(customer, variety, count, kattu, kazhi, rate, po_no="", del_no="", party_gst=""):
    """
    Main entry point: Creates bill in sgc-billing data store, renders PDF with UPI QR code,
    and returns full bill payload and file path.
    """
    # 1. Read SGC Billing DB
    data = {}
    if SGC_DATA_PATH.exists():
        try:
            with open(SGC_DATA_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"[!] Error loading SGC DB: {e}")

    bills = data.get("sgc-bills", [])
    count_map = data.get("sgc-countmap", DEFAULT_COUNT_MAP)

    # 2. Determine Next Bill Number
    existing_nos = [b.get("billNo", 0) for b in bills if isinstance(b.get("billNo"), int)]
    next_bill_no = (max(existing_nos) + 1) if existing_nos else 1

    # 3. Calculate Item Amount
    item_amt = calc_amount(kattu, kazhi, rate, count, count_map)
    subtotal = item_amt
    cgst = subtotal * 0.025
    sgst = subtotal * 0.025
    net_amt = int(round(subtotal + cgst + sgst))

    today_str = datetime.now().strftime("%Y-%m-%d")
    item_entry = {
        "id": f"item_{int(time.time())}",
        "delNo": str(del_no or next_bill_no),
        "poNo": str(po_no or ""),
        "variety": str(variety),
        "count": str(count),
        "kattu": str(kattu),
        "kazhi": str(kazhi),
        "rate": str(rate),
        "amount": f"{item_amt:.2f}"
    }

    bill_record = {
        "billNo": next_bill_no,
        "date": today_str,
        "customer": customer.strip(),
        "partyGst": party_gst.strip(),
        "items": [item_entry],
        "status": "pending",
        "subtotal": subtotal,
        "cgst": cgst,
        "sgst": sgst,
        "netAmount": net_amt,
        "id": f"bill_{next_bill_no}_{int(time.time())}"
    }

    # 4. Render Clean Print-Ready HTML (No QR code, clean A4 xerox ready)
    html_content = generate_html_invoice(bill_record)

    # 6. Render PDF with Playwright
    safe_name = re.sub(r'[^a-zA-Z0-9 ]', '_', customer)[:30].strip()
    pdf_filename = f"Bill_{str(next_bill_no).zfill(4)}_{safe_name}.pdf"
    
    primary_pdf_path = LOCAL_EXPORT_DIR / pdf_filename
    vault_pdf_path = STORAGE_BILLS_DIR / pdf_filename

    print(f"[*] Rendering Invoice #{next_bill_no} via Playwright Chromium...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(html_content, wait_until="networkidle")
        page.pdf(
            path=str(primary_pdf_path),
            format="A4",
            print_background=True,
            margin={"top": "8mm", "bottom": "8mm", "left": "8mm", "right": "8mm"}
        )
        browser.close()

    # Save duplicate in storage/bills
    if primary_pdf_path.exists() and primary_pdf_path != vault_pdf_path:
        try:
            with open(primary_pdf_path, "rb") as sf, open(vault_pdf_path, "wb") as df:
                df.write(sf.read())
        except Exception:
            pass

    # 7. Update SGC DB
    bill_record["localPath"] = str(primary_pdf_path)
    bills.append(bill_record)
    data["sgc-bills"] = bills

    try:
        with open(SGC_DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"[+] SGC DB updated with Bill #{next_bill_no}")
    except Exception as e:
        print(f"[!] Warning: Could not write SGC DB: {e}")

    return {
        "success": True,
        "billNo": next_bill_no,
        "customer": customer,
        "netAmount": net_amt,
        "subtotal": subtotal,
        "cgst": cgst,
        "sgst": sgst,
        "pdf_path": str(primary_pdf_path),
        "vault_pdf_path": str(vault_pdf_path),
        "items": [item_entry]
    }

if __name__ == "__main__":
    # Test creation
    res = create_sgc_bill(
        customer="Bannari Amman Spinning Mills",
        variety="cone winding",
        count="10s",
        kattu=2,
        kazhi=10,
        rate=520,
        po_no="PO-991"
    )
    print("Bill Created Successfully:")
    print(json.dumps(res, indent=2))

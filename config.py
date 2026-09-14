import os
from dotenv import load_dotenv

load_dotenv()

import base64

def _d(s: str) -> str:
    try:
        return base64.b64decode(s).decode('utf-8')
    except Exception:
        return ""

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN') or _d('ODczODcwMDIwNDpBQUdmT2x1YU9XVVVwNUhnWlROMlpYaXd4YlpybERFaXR1aw==')
GROQ_API_KEY = os.getenv('GROQ_API_KEY') or _d('Z3NrX3Y4RFcySElBYzV4cnJSQmppam5OV0dkeWJvRllETHB2MXVESWFBYWhCZmpLRGZpSU9oR28=')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY') or _d('QVEuQWI4Uk42SWVHYkhIY3NNc1V6QkhMenVOZjJrTnM3VDRJQkszODA3SFA5ZE9yUEh1T1E=')
JARVIS_VOICE_SECRET_TOKEN = os.getenv('JARVIS_VOICE_SECRET_TOKEN', 'mukil-jarvis-vault-key-9080030538')
AURA_BRIDGE_HMAC_SECRET = os.getenv('AURA_BRIDGE_HMAC_SECRET', JARVIS_VOICE_SECRET_TOKEN)
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', '')

# Propagate fallback keys to os.environ so all container processes resolve them
if not os.environ.get('TELEGRAM_BOT_TOKEN'):
    os.environ['TELEGRAM_BOT_TOKEN'] = TELEGRAM_BOT_TOKEN
if not os.environ.get('GROQ_API_KEY'):
    os.environ['GROQ_API_KEY'] = GROQ_API_KEY
if not os.environ.get('GEMINI_API_KEY'):
    os.environ['GEMINI_API_KEY'] = GEMINI_API_KEY

DRIVE_VAULT_URL = os.getenv('DRIVE_VAULT_URL', 'https://drive.google.com/drive/folders/1nGZG5-eIcxmkgQxBtZ7tjGTUoWWNY4m1?usp=sharing')
DRIVE_FOLDER_ID = os.getenv('DRIVE_FOLDER_ID', '1nGZG5-eIcxmkgQxBtZ7tjGTUoWWNY4m1')

# SGC Billing & Invoicing Dual Drive Folders
DRIVE_BILLING_FOLDER_1_URL = 'https://drive.google.com/drive/folders/155EqYOwPJ2Fc9QfqVSrZu5VnYzZgRcyZ?usp=drive_link'
DRIVE_BILLING_FOLDER_1_ID = os.getenv('DRIVE_BILLING_FOLDER_1_ID', '155EqYOwPJ2Fc9QfqVSrZu5VnYzZgRcyZ')

DRIVE_BILLING_FOLDER_2_URL = 'https://drive.google.com/drive/folders/1a9VJAP_Nypn_mjUEYCNvMpkGN5H9Kwf4?usp=sharing'
DRIVE_BILLING_FOLDER_2_ID = os.getenv('DRIVE_BILLING_FOLDER_2_ID', '1a9VJAP_Nypn_mjUEYCNvMpkGN5H9Kwf4')

DRIVE_BILLING_FOLDERS = [
    DRIVE_BILLING_FOLDER_1_ID,
    DRIVE_BILLING_FOLDER_2_ID
]

# LinkedIn Automation Config
LINKEDIN_CLIENT_ID = os.getenv('LINKEDIN_CLIENT_ID', '862b1jt5gae1oe')
LINKEDIN_CLIENT_SECRET = os.getenv('LINKEDIN_CLIENT_SECRET', '')
LINKEDIN_REDIRECT_URI = os.getenv('LINKEDIN_REDIRECT_URI', 'http://localhost:8000/callback')
LINKEDIN_ACCESS_TOKEN = os.getenv('LINKEDIN_ACCESS_TOKEN', '')
LINKEDIN_PERSON_URN = os.getenv('LINKEDIN_PERSON_URN', '')
# Storage Paths
LOCAL_SECONDARY_STORAGE = os.getenv('AURA_STORAGE_DIR', r'E:\AURA_STORAGE')
AUTO_SYNC_TO_DRIVE = True

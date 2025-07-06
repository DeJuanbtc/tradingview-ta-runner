import os
import ccxt
import requests
import pandas as pd
import pandas_ta as ta
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import base64
from email.mime.text import MIMEText
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
import json

# ================= GOOGLE DRIVE SETUP ==================
DRIVE_FOLDER_ID = "1kabJkt9I5uUitepAorXkvJvrwU5ZBVAF"
SERVICE_ACCOUNT_FILE = "/etc/secrets/ta_runner.json"
SCOPES = ['https://www.googleapis.com/auth/drive']

credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)
drive_service = build('drive', 'v3', credentials=credentials)

# ================== EMAIL SETUP (for alerts) ===================
SENDER = 'dejuan@dlabcapital.com'
RECIPIENT = 'dejuanbrunson@proton.me'
SUBJECT = '📈 Divergence Detected in Market Chart'
BODY_TEMPLATE = """
Divergence detected on {symbol} {timeframe} chart

Summary:
{details}

Check Drive folder for updated chart and data.

- TA Pro
"""

def create_message(sender, to, subject, message_text):
    message = MIMEText(message_text)
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject
    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {'raw': encoded_message}

def get_gmail_service():
    SCOPES = ['https://www.googleapis.com/auth/gmail.send']
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            gmail_creds = json.loads(os.environ["GMAIL_OAUTH_CREDS"])
            flow = InstalledAppFlow.from_client_config(gmail_creds, SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    service = build('gmail', 'v1', credentials=creds)
    return service

def send_gmail_alert(symbol, timeframe, details):
    service = get_gmail_service()
    body = BODY_TEMPLATE.format(symbol=symbol, timeframe=timeframe, details=details)
    message = create_message(SENDER, RECIPIENT, SUBJECT, body)
    try:
        send_message = service.users().messages().send(userId='me', body=message).execute()
        print(f"[EMAIL SENT] Alert sent for {symbol} | {timeframe}")
    except Exception as e:
        print(f"[ERROR] Failed to send alert: {e}")

# (rest of script remains unchanged)

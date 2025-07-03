import base64
import json
import os
from email.mime.text import MIMEText
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
from datetime import datetime

# --- CONFIGURATION ---
OAUTH_CREDENTIALS_FILE = 'DLAB Chart Alert.json'  # Path to your JSON credentials
SENDER = 'drive-uploader@tradingviewdriveuploader.iam.gserviceaccount.com'
RECIPIENT = 'dejuanbrunson@proton.me'
SUBJECT = '📈 Divergence Detected in Market Chart'
BODY_TEMPLATE = """
Divergence detected on {symbol} {timeframe} chart

Summary:
{details}

Check Drive folder for updated chart and data.

- TA Pro
"""

# --- DIVERGENCE DETECTION ---
def detect_divergence(price_1, price_2, ind_1, ind_2):
    results = []
    # Classic Bullish: Price LL, Ind HL
    if price_2 < price_1 and ind_2 > ind_1:
        results.append("Classic Bullish Divergence")
    # Classic Bearish: Price HH, Ind LH
    if price_2 > price_1 and ind_2 < ind_1:
        results.append("Classic Bearish Divergence")
    # Hidden Bullish: Price HL, Ind LL
    if price_2 > price_1 and ind_2 < ind_1:
        results.append("Hidden Bullish Divergence")
    # Hidden Bearish: Price LH, Ind HH
    if price_2 < price_1 and ind_2 > ind_1:
        results.append("Hidden Bearish Divergence")
    return results

# --- EMAIL COMPOSER ---
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
            flow = InstalledAppFlow.from_client_secrets_file(
                OAUTH_CREDENTIALS_FILE, SCOPES)
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

# --- MAIN ALERT FUNCTION ---
def process_asset(symbol, timeframe, price_1, price_2, rsi_1, rsi_2, macd_1, macd_2, timestamp=None):
    results_rsi = detect_divergence(price_1, price_2, rsi_1, rsi_2)
    results_macd = detect_divergence(price_1, price_2, macd_1, macd_2)
    all_divs = []
    if results_rsi:
        all_divs += results_rsi
    if results_macd:
        all_divs += results_macd

    classic = [d for d in all_divs if 'Classic' in d]
    hidden = [d for d in all_divs if 'Hidden' in d]

    # Only send alert if only classic OR only hidden divergences (not both, and at least one found)
    if (classic and not hidden) or (hidden and not classic):
        if timestamp is None:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        details = ""
        if results_rsi:
            details += (f"RSI: {', '.join(results_rsi)}\n"
                        f"Price: {price_1} → {price_2}\n"
                        f"RSI: {rsi_1} → {rsi_2}\n")
        if results_macd:
            details += (f"MACD: {', '.join(results_macd)}\n"
                        f"Price: {price_1} → {price_2}\n"
                        f"MACD: {macd_1} → {macd_2}\n")
        print(f"[ALERT] {symbol} {timeframe}:\n{details}\n")
        send_gmail_alert(symbol, timeframe, details)
    else:
        print(f"[NO EMAIL] {symbol} {timeframe}: Mixed/unclear signal ({', '.join(all_divs)})")

# --- EXAMPLE USAGE ---
if __name__ == "__main__":
    symbol = 'ETHUSD'
    timeframe = '5m'
    price_1 = 2590
    price_2 = 2625
    rsi_1 = 70.1
    rsi_2 = 68.4
    macd_1 = -0.8
    macd_2 = -1.1
    timestamp = "2025-06-12 15:05"
    process_asset(symbol, timeframe, price_1, price_2, rsi_1, rsi_2, macd_1, macd_2, timestamp)

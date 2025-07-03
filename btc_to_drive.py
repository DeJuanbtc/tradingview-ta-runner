import os
import time
import schedule
import pandas as pd
from tradingview_ta import TA_Handler, Interval, Exchange

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Fetch and save TradingView analysis
def fetch_analysis():
    handler = TA_Handler(
        symbol="BTCUSDT",
        exchange="BINANCE",
        screener="crypto",
        interval=Interval.INTERVAL_1_HOUR
    )
    analysis = handler.get_analysis()
    summary = analysis.summary

    df = pd.DataFrame({
        "RECOMMENDATION": [summary["RECOMMENDATION"]],
        "BUY": [summary["BUY"]],
        "SELL": [summary["SELL"]],
        "NEUTRAL": [summary["NEUTRAL"]]
    })

    df.to_csv("BTCUSDT_TA_1h.csv", index=False)
    print("✅ Saved BTCUSDT technical analysis to BTCUSDT_TA_1h.csv")

# Upload CSV to Google Drive
def upload_to_drive():
    SCOPES = ['https://www.googleapis.com/auth/drive.file']
    credentials = Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
    service = build('drive', 'v3', credentials=credentials)

    file_metadata = {
        'name': 'BTCUSDT_TA_1h.csv',
        'mimeType': 'application/vnd.google-apps.spreadsheet'
    }
    media = MediaFileUpload('BTCUSDT_TA_1h.csv', mimetype='text/csv')
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()

    print(f"📤 File uploaded to Google Drive with ID: {file.get('id')}")

# Combine and schedule
def job():
    fetch_analysis()
    upload_to_drive()

# Schedule the job every hour
schedule.every(1).hours.do(job)

# Run initially
job()

while True:
    schedule.run_pending()
    time.sleep(1)

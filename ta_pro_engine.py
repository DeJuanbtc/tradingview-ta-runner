import datetime
import io
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import mplfinance as mpf


def google_client(creds_path: str):
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
    gc = gspread.authorize(creds)
    drive = build('drive', 'v3', credentials=creds)
    return gc, drive


def fetch_csv_from_drive(drive, file_id: str, dest: str):
    request = drive.files().get_media(fileId=file_id)
    with open(dest, "wb") as fh:
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
    return dest


def generate_chart(csv_path: str, asset: str, out_dir: str = 'charts'):
    df = pd.read_csv(csv_path, index_col=0, parse_dates=True)
    mpf.plot(
        df,
        type='candle',
        volume=True,
        style='charles',
        mav=(10, 50),
        title=f"{asset} Chart",
        savefig=f"{out_dir}/{asset}_chart.png"
    )


def detect_patterns(df: pd.DataFrame):
    patterns = []
    for i in range(1, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i-1]
        body = abs(row['Close'] - row['Open'])
        range_c = row['High'] - row['Low']
        if body < 0.1 * range_c:
            patterns.append((row.name, 'Doji'))
        if row['Close'] > row['Open'] and prev['Close'] < prev['Open'] and row['Open'] < prev['Close'] and row['Close'] > prev['Open']:
            patterns.append((row.name, 'Bullish Engulfing'))
        if row['Close'] < row['Open'] and prev['Close'] > prev['Open'] and row['Open'] > prev['Close'] and row['Close'] < prev['Open']:
            patterns.append((row.name, 'Bearish Engulfing'))
    return patterns


def log_patterns(sheet, market: str, patterns):
    now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    for ts, label in patterns:
        sheet.append_row([now, market, ts.strftime("%Y-%m-%d"), label])


def update_market_csv(drive, file_id: str, name: str, sheet=None):
    dest = f"data/{name}.csv"
    fetch_csv_from_drive(drive, file_id, dest)
    df = pd.read_csv(dest, index_col=0, parse_dates=True)
    patterns = detect_patterns(df)
    if patterns:
        print(f"{name}: detected {len(patterns)} patterns")
        if sheet is not None:
            log_patterns(sheet, name, patterns)
    generate_chart(dest, name)
    return dest


if __name__ == "__main__":
    CREDS_FILE = "ta-pro-suggestions-creds.json"
    gc, drive = google_client(CREDS_FILE)
    sheet = gc.open("TA Pro – Suggestion Chart Log").sheet1
    # Example file IDs - replace with real ones
    MARKET_IDS = {
        'TOTAL': 'TOTAL_FILE_ID',
        'TOTAL3': 'TOTAL3_FILE_ID'
    }
    for market, fid in MARKET_IDS.items():
        try:
            update_market_csv(drive, fid, market, sheet)
        except Exception as e:
            print(f"Failed to update {market}: {e}")

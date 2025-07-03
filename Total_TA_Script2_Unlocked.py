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

# ================= GOOGLE DRIVE SETUP ==================
DRIVE_FOLDER_ID = "1kabJkt9I5uUitepAorXkvJvrwU5ZBVAF"
SERVICE_ACCOUNT_FILE = "Updated_DLAB_Chart_Creds.json"
SCOPES = ['https://www.googleapis.com/auth/drive']

credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)
drive_service = build('drive', 'v3', credentials=credentials)

# ================== EMAIL SETUP (for alerts) ===================
OAUTH_CREDENTIALS_FILE = 'DLAB_Chart_Alert.json'
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

# ==================== EXCHANGES ==========================
EXCHANGE_PRIORITY = ['coinbase', 'kraken', 'bybit']
exchanges = {}
for ex_id in EXCHANGE_PRIORITY:
    try:
        ex = getattr(ccxt, ex_id)()
        exchanges[ex_id] = ex
        print(f"[INFO] Initialized exchange: {ex_id}")
    except Exception as e:
        print(f"[WARN] Failed to initialize {ex_id}: {e}")

symbols = ["BTC/USD", "ETH/USD", "ARB/USD", "LINK/USD"]
timeframes = ["1m", "5m", "15m", "1h", "4h", "1d", "1w", "1M"]
cmc_symbols = ["TOTAL", "TOTAL3", "BTC.D"]

# Normalize for Kraken/Bybit symbols
def normalize_symbol(exchange_id, symbol):
    if exchange_id in ['kraken', 'bybit']:
        return symbol.replace("USD", "USDT")
    return symbol

# Fetch OHLCV
def fetch_ohlcv(symbol, timeframe):
    for ex_id, ex in exchanges.items():
        try:
            if ex_id == 'coinbase' and timeframe not in ['1m', '5m', '15m', '1h', '1d']:
                print(f"[SKIP] Unsupported timeframe {timeframe} for coinbase")
                continue
            norm_symbol = normalize_symbol(ex_id, symbol)
            print(f"[INFO] Fetching: {norm_symbol} | {timeframe} on {ex_id}")
            ohlcv = ex.fetch_ohlcv(norm_symbol, timeframe)
            if isinstance(ohlcv[0], list):
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.ta.ema(length=20, append=True)
                df.ta.rsi(length=14, append=True)
                df.ta.macd(append=True)
                df.ta.bbands(append=True)
                df.ta.sma(length=50, append=True)
                df.ta.sma(length=200, append=True)
                df.ta.atr(length=10, append=True)  # Needed for UT Bot!
                return df
        except Exception as e:
            print(f"[WARN] {ex_id} failed {symbol} {timeframe}: {e}")
    print(f"[ERROR] All exchanges failed for {symbol} {timeframe}")
    return None

# Simulated macro fetch
def fetch_macro(symbol):
    print(f"[INFO] CMC Fetch: {symbol}")
    try:
        return pd.DataFrame({
            'timestamp': [datetime.utcnow()],
            'value': [float(pd.Timestamp.now().timestamp()) % 1000]
        })
    except Exception as e:
        print(f"[ERROR] Fetching macro {symbol}: {e}")
        return None

# Upload to Google Drive
def upload_to_drive(filepath):
    file_metadata = {
        'name': os.path.basename(filepath),
        'parents': [DRIVE_FOLDER_ID]
    }
    media = MediaFileUpload(filepath, mimetype='text/csv')
    try:
        drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        print(f"[UPLOAD] {filepath} uploaded to Drive.")
    except Exception as e:
        print(f"[ERROR] Drive upload failed for {filepath}: {e}")

# ================ DIVERGENCE DETECTION ================
def detect_divergence(price_1, price_2, ind_1, ind_2):
    results = []
    if price_2 < price_1 and ind_2 > ind_1:
        results.append("Classic Bullish Divergence")
    if price_2 > price_1 and ind_2 < ind_1:
        results.append("Classic Bearish Divergence")
    # Only include each divergence type once per check
    return results

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

# =============== UT BOT LOGIC ===============
def ut_bot_signal(df, atr_period=10, sensitivity=1):
    src = df['close']
    xATR = df[f'ATRr_{atr_period}'] if f'ATRr_{atr_period}' in df.columns else df.ta.atr(length=atr_period)
    nLoss = sensitivity * xATR

    trailing_stop = [src.iloc[0] - nLoss.iloc[0]]
    for i in range(1, len(src)):
        prev_stop = trailing_stop[-1]
        if src.iloc[i] > prev_stop and src.iloc[i-1] > prev_stop:
            trailing_stop.append(max(prev_stop, src.iloc[i] - nLoss.iloc[i]))
        elif src.iloc[i] < prev_stop and src.iloc[i-1] < prev_stop:
            trailing_stop.append(min(prev_stop, src.iloc[i] + nLoss.iloc[i]))
        elif src.iloc[i] > prev_stop:
            trailing_stop.append(src.iloc[i] - nLoss.iloc[i])
        else:
            trailing_stop.append(src.iloc[i] + nLoss.iloc[i])
    df['atr_stop'] = trailing_stop

    buy_signal = src.iloc[-2] < trailing_stop[-2] and src.iloc[-1] > trailing_stop[-1]
    sell_signal = src.iloc[-2] > trailing_stop[-2] and src.iloc[-1] < trailing_stop[-1]
    return buy_signal, sell_signal

# ========== FIBONACCI RETRACEMENT (ADD THIS FUNCTION OUTSIDE CONDITIONAL!) ===========
def get_fib_levels(df, lookback=100):
    if len(df) < lookback:
        lookback = len(df)
    window = df.iloc[-lookback:]
    high = window['high'].max()
    low = window['low'].min()
    diff = high - low
    fibs = {
        '0.0': high,
        '0.236': high - 0.236 * diff,
        '0.382': high - 0.382 * diff,
        '0.5': high - 0.5 * diff,
        '0.618': high - 0.618 * diff,
        '0.786': high - 0.786 * diff,
        '1.0': low
    }
    return fibs

# =================== FETCH & SAVE =========================
data = {}
for symbol in symbols:
    for tf in timeframes:
        df = fetch_ohlcv(symbol, tf)
        if df is not None:
            key = f"{symbol.replace('/', '')}_{tf}"
            data[key] = df

for macro in cmc_symbols:
    df = fetch_macro(macro)
    if df is not None:
        data[macro] = df

if data:
    for key, df in data.items():
        filename = f"{key}.csv"
        df.to_csv(filename, index=False)
        print(f"[INFO] Saved {filename}")
        upload_to_drive(filename)
else:
    print("⚠️ No data to save.")

# ========== MAIN ANALYSIS LOOP ==========
lookbacks = {
    '5m': 50,
    '15m': 75,
    '1h': 100,
    '4h': 150,
    '1d': 200,
    '1w': 250,
    '1M': 500
}

tracked_symbols = ["ETH/USD", "ARB/USD", "LINK/USD"]
timeframes_to_analyze = ["5m", "1h", "4h", "1d", "1w", "1M"]

for symbol in tracked_symbols:
    for tf in timeframes_to_analyze:
        key = f"{symbol.replace('/', '')}_{tf}"
        if key not in data:
            continue
        df = data[key].dropna().reset_index(drop=True)
        if len(df) < 2:
            continue

        # === FIB ADDED HERE ===
        lookback = lookbacks.get(tf, 100)
        fib_levels = get_fib_levels(df, lookback=lookback)
        print(f"[FIB LEVELS] {symbol} {tf}: {fib_levels}")

        price_1, price_2 = df['close'].iloc[-2], df['close'].iloc[-1]
        rsi_1, rsi_2     = df['RSI_14'].iloc[-2], df['RSI_14'].iloc[-1]
        macd_1, macd_2   = df['MACD_12_26_9'].iloc[-2], df['MACD_12_26_9'].iloc[-1]
        timestamp        = df['timestamp'].iloc[-1] if 'timestamp' in df.columns else None

        process_asset(symbol, tf, price_1, price_2, rsi_1, rsi_2, macd_1, macd_2, timestamp)

        if tf in ['1h', '4h']:
            buy_signal, sell_signal = ut_bot_signal(df)
            if buy_signal:
                send_gmail_alert(symbol, tf, f"UT BOT BUY on {symbol} {tf}")
                print(f"[UT BOT BUY] {symbol} {tf}")
            if sell_signal:
                send_gmail_alert(symbol, tf, f"UT BOT SELL on {symbol} {tf}")
                print(f"[UT BOT SELL] {symbol} {tf}")

# ================ TEST CONNECTION ================
def test_connection():
    if not exchanges:
        print("[TEST ERROR] No exchanges initialized.")
        return
    try:
        test_df = fetch_ohlcv("BTC/USD", "5m")
        assert test_df is not None and not test_df.empty, "Test fetch failed or returned empty data."
        print("[TEST PASS] BTC/USD 5m data fetched successfully.")
    except AssertionError as ae:
        print(f"[TEST FAIL] {ae}")
    except Exception as e:
        print(f"[TEST ERROR] Unexpected error during test: {e}")

if __name__ == "__main__":
    test_connection()

import pandas as pd
import requests
import ta
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# === Step 1: Fetch OHLCV from Binance API ===
url = 'https://api.binance.com/api/v3/klines'
params = {
    'symbol': 'BTCUSDT',
    'interval': '1h',
    'limit': 1000
}

response = requests.get(url, params=params)
data = response.json()

# === Step 2: Format into DataFrame ===
df = pd.DataFrame(data, columns=[
    'timestamp', 'open', 'high', 'low', 'close', 'volume',
    'close_time', 'quote_asset_volume', 'num_trades',
    'taker_buy_base', 'taker_buy_quote', 'ignore'
])

df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
df.set_index('timestamp', inplace=True)

numeric_cols = ['open', 'high', 'low', 'close', 'volume']
df[numeric_cols] = df[numeric_cols].astype(float)

# === Step 3: Add TA indicators ===
df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
macd = ta.trend.MACD(df['close'])
df['macd'] = macd.macd()
df['macd_signal'] = macd.macd_signal()
df['macd_diff'] = macd.macd_diff()
df['ema20'] = ta.trend.EMAIndicator(df['close'], window=20).ema_indicator()
df['ema50'] = ta.trend.EMAIndicator(df['close'], window=50).ema_indicator()
df['ema200'] = ta.trend.EMAIndicator(df['close'], window=200).ema_indicator()

# === Step 4: Buy/Sell Signal Logic ===
df['macd_crossup'] = ((df['macd'] > df['macd_signal']) & (df['macd'].shift(1) <= df['macd_signal'].shift(1))).astype(int)
df['macd_crossdown'] = ((df['macd'] < df['macd_signal']) & (df['macd'].shift(1) >= df['macd_signal'].shift(1))).astype(int)
df['rsi_buy'] = (df['rsi'] < 30).astype(int)
df['rsi_sell'] = (df['rsi'] > 70).astype(int)
df['ema_buy'] = ((df['ema20'] > df['ema50']) & (df['ema20'].shift(1) <= df['ema50'].shift(1))).astype(int)
df['ema_sell'] = ((df['ema20'] < df['ema50']) & (df['ema20'].shift(1) >= df['ema50'].shift(1))).astype(int)

# === Step 5: UT Bot Buy/Sell ===
atr = ta.volatility.AverageTrueRange(df['high'], df['low'], df['close'], window=10).average_true_range()
nLoss = 1 * atr
xATRTrailingStop = [df['close'].iloc[0] + nLoss.iloc[0]]

for i in range(1, len(df)):
    prev_stop = xATRTrailingStop[-1]
    price = df['close'].iloc[i]
    prev_price = df['close'].iloc[i - 1]

    if price > prev_stop and prev_price > prev_stop:
        xATRTrailingStop.append(max(prev_stop, price - nLoss.iloc[i]))
    elif price < prev_stop and prev_price < prev_stop:
        xATRTrailingStop.append(min(prev_stop, price + nLoss.iloc[i]))
    elif price > prev_stop:
        xATRTrailingStop.append(price - nLoss.iloc[i])
    else:
        xATRTrailingStop.append(price + nLoss.iloc[i])

df['ut_trailing_stop'] = xATRTrailingStop
df['ut_buy'] = ((df['close'].shift(1) < df['ut_trailing_stop'].shift(1)) & (df['close'] > df['ut_trailing_stop'])).astype(int)
df['ut_sell'] = ((df['close'].shift(1) > df['ut_trailing_stop'].shift(1)) & (df['close'] < df['ut_trailing_stop'])).astype(int)

# === Step 6: Combined Signal ===
def combine_signals(row):
    if row['macd_crossup'] or row['rsi_buy'] or row['ema_buy'] or row['ut_buy']:
        return 'BUY'
    elif row['macd_crossdown'] or row['rsi_sell'] or row['ema_sell'] or row['ut_sell']:
        return 'SELL'
    else:
        return 'HOLD'

df['signal'] = df.apply(combine_signals, axis=1)

# === Step 7: Save CSV ===
df.to_csv('BTCUSDT_TA_1h.csv')
print("✅ TA + UT Bot data saved to BTCUSDT_TA_1h.csv")

# === Step 8: Upload to Google Drive ===
SCOPES = ['https://www.googleapis.com/auth/drive.file']
creds = Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
service = build('drive', 'v3', credentials=creds)

file_metadata = {
    'name': 'BTCUSDT_TA_1h.csv',
    'mimeType': 'application/vnd.google-apps.spreadsheet'
}
media = MediaFileUpload('BTCUSDT_TA_1h.csv', mimetype='text/csv')

try:
    print("🚀 Uploading to Google Drive...")
    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, name'
    ).execute()

    # Share it with your account
    service.permissions().create(
        fileId=file.get('id'),
        body={'type': 'user', 'role': 'writer', 'emailAddress': 'dbrunson2011@gmail.com'},
        fields='id'
    ).execute()

    print(f"✅ Uploaded & shared: {file.get('name')} | 🔗 https://drive.google.com/file/d/{file.get('id')}/view")
except Exception as e:
    print(f"❌ Upload failed: {e}")

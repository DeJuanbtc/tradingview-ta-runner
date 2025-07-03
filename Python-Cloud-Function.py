import os
import datetime
import gspread
from google.oauth2.service_account import Credentials

# Define the scope
SCOPES = ["https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive"]

# Load credentials from JSON key file
creds = Credentials.from_service_account_file(
    "ta-pro-suggestions-creds.json",  # <-- Replace with the path to your downloaded key file
    scopes=SCOPES
)

# Connect to Google Sheets
client = gspread.authorize(creds)
sheet = client.open("TA Pro – Suggestion Chart Log").sheet1

# Prepare the data row
now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
row = [
    now,
    "ETH",  # Asset
    "Collateral Swap",
    "Neutral-Bullish",
    "Long > $2,600",
    "Wait for $2,650 4H",
    "No",
    "Yes (if $2,600 4H holds)",
    "SL < $2,550",
    "62%",
    "Based on confluence with macro + trend"
]

# Append row to the sheet
sheet.append_row(row)
print("Suggestion logged.")

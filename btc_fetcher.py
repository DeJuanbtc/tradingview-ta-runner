from tvDatafeed import TvDatafeed, Interval
import pandas as pd
import schedule
import time

# Replace with your actual TradingView login
tv = TvDatafeed(username='JuanAmaruKhan', password='Kegfad-funwy7-xoccet')

def fetch_and_export():
    data = tv.get_hist(symbol='BTCUSDT', exchange='BINANCE', interval=Interval.in_1_hour
, n_bars=100)
    data.to_csv('BTCUSDT_1h.csv')
    print("Exported latest candle data!")

# Run this every 1 hour
schedule.every(1).hour.do(fetch_and_export)

# Initial run
fetch_and_export()

while True:
    schedule.run_pending()
    time.sleep(1)

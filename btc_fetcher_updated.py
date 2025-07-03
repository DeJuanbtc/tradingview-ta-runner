from tradingview_ta import TA_Handler, Interval, Exchange
import schedule
import time
import pandas as pd

def fetch_analysis():
    handler = TA_Handler(
        symbol="BTCUSDT",
        exchange="BINANCE",
        screener="crypto",
        interval=Interval.INTERVAL_1_HOUR
    )

    analysis = handler.get_analysis()
    summary = analysis.summary
    oscillators = analysis.oscillators
    moving_averages = analysis.moving_averages

    # Save to CSV
    df = pd.DataFrame({
        "RECOMMENDATION": [summary["RECOMMENDATION"]],
        "BUY": [summary["BUY"]],
        "SELL": [summary["SELL"]],
        "NEUTRAL": [summary["NEUTRAL"]]
    })

    df.to_csv("BTCUSDT_TA_1h.csv", index=False)
    print("✅ Saved BTCUSDT technical analysis to BTCUSDT_TA_1h.csv")

# Run every hour
schedule.every(1).hours.do(fetch_analysis)

# Initial run
fetch_analysis()

# Keep running
while True:
    schedule.run_pending()
    time.sleep(1)

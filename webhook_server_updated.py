
from flask import Flask, request, jsonify
import pandas as pd
import os

from Total_TA_Script2_Unlocked import process_asset, send_gmail_alert

app = Flask(__name__)
UPLOAD_DIR = "uploaded_data"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.route('/webhook', methods=['POST'])
def webhook():
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file uploaded'}), 400

    file = request.files['file']
    path = os.path.join(UPLOAD_DIR, file.filename)
    file.save(path)

    try:
        df = pd.read_csv(path)

        # Run Technical Analysis
        ta_results = process_asset(df)  # Expected to return a summary or signal info

        # Send Email Alert with TA result
        send_gmail_alert(f"{file.filename} TA Results", str(ta_results))

        return jsonify({'status': 'ok', 'results': ta_results}), 200

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == "__main__":
    app.run(port=5000, debug=True)

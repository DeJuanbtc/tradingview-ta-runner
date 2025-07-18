from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    print(f"Received data: {data}")  # You should see this in the Flask terminal!
    return jsonify({'status': 'ok', 'received': data}), 200

if __name__ == "__main__":
    app.run(port=5000, debug=True)

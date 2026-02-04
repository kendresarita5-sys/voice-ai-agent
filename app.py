 from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ AI Voice Agent Running!"

@app.route('/call', methods=['POST'])
def handle_call():
    return jsonify([{
        "action": "talk",
        "text": "Hello! This is AI assistant. Calling you back on WhatsApp in 2 seconds.",
        "voice": "en-IN-NeerjaNeural"
    }])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

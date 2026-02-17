import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# CEO Settings - Tells AI what to do
SYSTEM_PROMPT = "You are the LabKing AI assistant. Be professional. Ask for the patient name, phone number, and test type (CBC or Sugar). Once they give all three, say 'Booking confirmed' and hang up."

@app.route('/webhook', methods=['POST'])
def handle_vapi_call():
    # 1. Get the data from the AI Call
    data = request.json
    call_status = data.get('message', {}).get('type')

    # 2. When the call ends, save to Airtable
    if call_status == 'end-of-call-report':
        # Get patient info from the AI's summary
        analysis = data.get('message', {}).get('analysis', {})
        name = analysis.get('structuredData', {}).get('name', 'New Patient')
        phone = analysis.get('structuredData', {}).get('phone', '0000000000')
        test = analysis.get('structuredData', {}).get('test', 'Blood Test')

        # 3. Push to your Airtable Dashboard
        token = os.environ.get('AIRTABLE_TOKEN')
        base_id = os.environ.get('AIRTABLE_BASE_ID')
        url = f"https://api.airtable.com{base_id}/Test%20Orders"
        
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        payload = {
            "records": [{
                "fields": {
                    "Patient Name": name,
                    "Mobile Number": phone,
                    "Status": "Pending"
                }
            }]
        }
        requests.post(url, json=payload, headers=headers)
        return jsonify({"status": "success"}), 200

    return jsonify({"status": "listening"}), 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))

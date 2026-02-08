from flask import Flask, request, jsonify
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

app = Flask(__name__)

# ==================== MEDICAL AI CORE ====================
class MedicalAI:
    def __init__(self):
        self.tests = {
            'blood': ['CBC (Complete Blood Count)', 'Sugar Fasting', 'HbA1c (Diabetes)', 'Lipid Profile', 'Thyroid TSH'],
            'urine': ['Urine Routine', 'Urine Culture', 'Pregnancy Test'],
            'imaging': ['X-Ray Chest', 'Ultrasound Abdomen', 'ECG'],
            'packages': ['Full Body Checkup - ₹2500', 'Executive Health - ₹5000', 'Basic Screening - ₹1500']
        }
        
        self.prices = {
            'CBC': 300, 'Sugar Fasting': 100, 'HbA1c': 500, 'Lipid Profile': 600,
            'Thyroid TSH': 400, 'Urine Routine': 150, 'X-Ray Chest': 300
        }
    
    def detect_intent(self, text):
        text_lower = text.lower()
        
        # Test inquiries
        if any(word in text_lower for word in ['blood', 'cbc', 'sugar', 'diabetes', 'thyroid']):
            return 'blood_test'
        elif any(word in text_lower for word in ['urine', 'pregnancy', 'culture']):
            return 'urine_test'
        elif any(word in text_lower for word in ['xray', 'x-ray', 'ultrasound', 'ecg']):
            return 'imaging'
        elif any(word in text_lower for word in ['package', 'checkup', 'full body', 'executive']):
            return 'package'
        elif any(word in text_lower for word in ['price', 'cost', 'charge', 'rate']):
            return 'price_inquiry'
        elif any(word in text_lower for word in ['book', 'appointment', 'schedule', 'आज', 'कल']):
            return 'book_appointment'
        elif any(word in text_lower for word in ['report', 'result', 'रिपोर्ट', 'परिणाम']):
            return 'report_inquiry'
        elif any(word in text_lower for word in ['time', 'hour', 'समय', 'खुला']):
            return 'timing'
        elif any(word in text_lower for word in ['location', 'address', 'जगह', 'पता']):
            return 'location'
        
        return 'greeting'
    
    def detect_language(self, text):
        # Simple language detection
        hindi_words = ['नमस्ते', 'है', 'में', 'करवाना', 'चाहिए']
        marathi_words = ['नमस्कार', 'आहे', 'मी', 'होय', 'पाहिजे']
        
        text_lower = text.lower()
        hi_count = sum(1 for word in hindi_words if word in text_lower)
        mr_count = sum(1 for word in marathi_words if word in text_lower)
        
        if hi_count > mr_count and hi_count > 0:
            return 'hi'
        elif mr_count > hi_count and mr_count > 0:
            return 'mr'
        else:
            return 'en'
    
    def get_response(self, intent, language='en'):
        responses = {
            'en': {
                'greeting': "Hello! Welcome to City Lab Services. I'm your AI assistant. How can I help you today?",
                'blood_test': "We offer comprehensive blood tests including: CBC (₹300), Sugar Fasting (₹100), HbA1c for diabetes (₹500), Lipid Profile (₹600), and Thyroid test (₹400). Which test would you like?",
                'urine_test': "We provide Urine Routine test (₹150), Urine Culture (₹500), and Pregnancy test (₹200).",
                'imaging': "Available imaging tests: X-Ray Chest (₹300), Ultrasound Abdomen (₹800), ECG (₹400).",
                'package': "Health packages: Full Body Checkup (₹2500), Executive Health (₹5000), Basic Screening (₹1500). All packages include doctor consultation.",
                'book_appointment': "I can book your appointment. Please provide your name, phone number, and preferred date.",
                'price_inquiry': "Our tests are affordably priced. CBC: ₹300, Sugar: ₹100, Urine Routine: ₹150, X-Ray: ₹300. Would you like to book any test?",
                'report_inquiry': "Reports are usually ready in 24 hours. You'll receive WhatsApp notification when ready.",
                'timing': "We're open Monday to Saturday, 7 AM to 9 PM. Sunday: 8 AM to 2 PM.",
                'location': "Our lab is at Main Road, Aurangabad. Near City Hospital. Google Maps: https://maps.app.goo.gl/xxxxx"
            },
            'hi': {
                'greeting': "नमस्ते! सिटी लैब सर्विसेज में आपका स्वागत है। मैं आपकी AI सहायक हूं। आज मैं आपकी क्या मदद कर सकती हूं?",
                'blood_test': "हम व्यापक ब्लड टेस्ट करते हैं: CBC (₹300), शुगर फास्टिंग (₹100), HbA1c डायबिटीज के लिए (₹500), लिपिड प्रोफाइल (₹600), और थायराइड टेस्ट (₹400)। आप कौन सा टेस्ट करवाना चाहते हैं?",
                'urine_test': "हम यूरिन रूटीन टेस्ट (₹150), यूरिन कल्चर (₹500), और प्रेगनेंसी टेस्ट (₹200) प्रदान करते हैं।",
                'book_appointment': "मैं आपका अपॉइंटमेंट बुक कर सकती हूं। कृपया अपना नाम, फोन नंबर और पसंदीदा तारीख बताएं।",
                'price_inquiry': "हमारे टेस्ट किफायती दामों में उपलब्ध हैं: CBC: ₹300, शुगर: ₹100, यूरिन रूटीन: ₹150, एक्स-रे: ₹300। क्या आप कोई टेस्ट बुक करना चाहेंगे?",
                'report_inquiry': "रिपोर्ट्स आमतौर पर 24 घंटे में तैयार हो जाती हैं। तैयार होने पर आपको WhatsApp नोटिफिकेशन मिलेगा।",
                'timing': "हम सोमवार से शनिवार, सुबह 7 से रात 9 बजे तक खुले रहते हैं। रविवार: सुबह 8 से दोपहर 2 बजे तक।",
                'location': "हमारी लैब मेन रोड, औरंगाबाद में है। सिटी हॉस्पिटल के पास। Google Maps: https://maps.app.goo.gl/xxxxx"
            }
        }
        
        return responses.get(language, responses['en']).get(intent, "I can help you with lab tests and appointments.")

# Initialize AI
ai = MedicalAI()

# ==================== APPOINTMENT SYSTEM ====================
class AppointmentSystem:
    def __init__(self):
        try:
            # Google Sheets setup (optional - can comment out if no credentials)
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets"]
            creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
            client = gspread.authorize(creds)
            self.sheet = client.open("City_Lab_Appointments").sheet1
            self.use_sheets = True
        except:
            self.use_sheets = False
            self.appointments = []
    
    def book(self, name, phone, test, date="tomorrow"):
        appointment = {
            'name': name,
            'phone': phone,
            'test': test,
            'date': date,
            'status': 'Booked'
        }
        
        if self.use_sheets:
            self.sheet.append_row([name, phone, test, date, 'Booked'])
        else:
            self.appointments.append(appointment)
            print(f"Appointment stored: {appointment}")
        
        return appointment

# Initialize appointment system
appointments = AppointmentSystem()

# ==================== ROUTES ====================
@app.route('/')
def home():
    return "✅ City Lab AI Voice Agent Running! Visit /test for web interface."

# Web testing interface
@app.route('/test', methods=['GET', 'POST'])
def test_ai():
    if request.method == 'POST':
        user_message = request.form.get('message', '')
        language = request.form.get('language', 'en')
        
        # Detect intent and language
        intent = ai.detect_intent(user_message)
        if user_message.strip():
            detected_lang = ai.detect_language(user_message)
            if detected_lang != 'en':
                language = detected_lang
        
        response = ai.get_response(intent, language)
        
        # If booking intent, create sample appointment
        booking_info = None
        if intent == 'book_appointment':
            booking = appointments.book(
                name="Sample Patient",
                phone="9876543210",
                test="Blood Test",
                date="tomorrow"
            )
            booking_info = f" Appointment booked: {booking['test']} for {booking['date']}"
            response += booking_info
        
        return jsonify({
            "input": user_message,
            "intent": intent,
            "language": language,
            "response": response,
            "booking": booking_info if booking_info else "Not a booking"
        })
    
    # HTML interface
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test City Lab AI</title>
        <style>
            body { font-family: Arial; padding: 20px; }
            textarea { width: 100%; padding: 10px; margin: 10px 0; }
            button { padding: 10px 20px; background: #007bff; color: white; border: none; cursor: pointer; }
            .response { background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 5px; }
        </style>
    </head>
    <body>
        <h2>🏥 Test City Lab Medical AI</h2>
        <form method="post">
            <textarea name="message" rows="3" placeholder="Type patient message... 
Examples: 
- I want blood test
- मुझे ब्लड टेस्ट करवाना है
- What is your timing?
- प्राइस क्या है?"></textarea><br>
            
            <label>Language:</label>
            <select name="language">
                <option value="en">English</option>
                <option value="hi">Hindi</option>
            </select><br><br>
            
            <button type="submit">Test AI Response</button>
        </form>
        
        <div>
            <h3>Test Phrases:</h3>
            <ul>
                <li>blood test price</li>
                <li>book appointment for tomorrow</li>
                <li>मुझे शुगर टेस्ट करवाना है</li>
                <li>where is your lab</li>
                <li>report kab tak aayegi</li>
            </ul>
        </div>
    </body>
    </html>
    '''

# Phone/webhook endpoint (for future SIM integration)
@app.route('/call', methods=['POST'])
def handle_call():
    # This is for phone system integration
    # Returns Twilio-compatible response
    
    response_text = ai.get_response('greeting', 'en')
    
    return jsonify([{
        "action": "talk",
        "text": response_text,
        "voice": "en-IN-NeerjaNeural",
        "bargeIn": True
    }])

# API endpoint for external systems
@app.route('/api/book', methods=['POST'])
def api_book():
    data = request.json
    appointment = appointments.book(
        name=data.get('name', ''),
        phone=data.get('phone', ''),
        test=data.get('test', ''),
        date=data.get('date', 'tomorrow')
    )
    return jsonify({"status": "success", "appointment": appointment})

# ==================== MAIN ====================
if __name__ == '__main__':
    print("🚀 City Lab Medical AI Starting...")
    print("🌐 Web Interface: http://localhost:5000/test")
    print("📞 Phone Endpoint: /call (POST)")
    print("📅 Appointment API: /api/book (POST)")
    app.run(host='0.0.0.0', port=5000, debug=True)

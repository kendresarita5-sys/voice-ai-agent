from flask import Flask, request, jsonify, send_file, render_template_string
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import speech_recognition as sr
from gtts import gTTS
import tempfile
import os
import io
from datetime import datetime
from twilio.twiml.voice_response import VoiceResponse, Gather

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
        elif any(word in text_lower for word in ['hi', 'hello', 'नमस्ते', 'नमस्कार', 'hey']):
            return 'greeting'
        
        return 'general'
    
    def detect_language(self, text):
        # Simple language detection
        hindi_words = ['नमस्ते', 'है', 'में', 'करवाना', 'चाहिए', 'मुझे', 'टेस्ट']
        marathi_words = ['नमस्कार', 'आहे', 'मी', 'होय', 'पाहिजे', 'मला']
        
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
                'location': "Our lab is at Main Road, Aurangabad. Near City Hospital. Google Maps: https://maps.app.goo.gl/xxxxx",
                'general': "I can help you with lab tests, appointments, reports, and general inquiries. What do you need?"
            },
            'hi': {
                'greeting': "नमस्ते! सिटी लैब सर्विसेज में आपका स्वागत है। मैं आपकी AI सहायक हूं। आज मैं आपकी क्या मदद कर सकती हूं?",
                'blood_test': "हम व्यापक ब्लड टेस्ट करते हैं: CBC (₹300), शुगर फास्टिंग (₹100), HbA1c डायबिटीज के लिए (₹500), लिपिड प्रोफाइल (₹600), और थायराइड टेस्ट (₹400)। आप कौन सा टेस्ट करवाना चाहते हैं?",
                'urine_test': "हम यूरिन रूटीन टेस्ट (₹150), यूरिन कल्चर (₹500), और प्रेगनेंसी टेस्ट (₹200) प्रदान करते हैं।",
                'book_appointment': "मैं आपका अपॉइंटमेंट बुक कर सकती हूं। कृपया अपना नाम, फोन नंबर और पसंदीदा तारीख बताएं।",
                'price_inquiry': "हमारे टेस्ट किफायती दामों में उपलब्ध हैं: CBC: ₹300, शुगर: ₹100, यूरिन रूटीन: ₹150, एक्स-रे: ₹300। क्या आप कोई टेस्ट बुक करना चाहेंगे?",
                'report_inquiry': "रिपोर्ट्स आमतौर पर 24 घंटे में तैयार हो जाती हैं। तैयार होने पर आपको WhatsApp नोटिफिकेशन मिलेगा।",
                'timing': "हम सोमवार से शनिवार, सुबह 7 से रात 9 बजे तक खुले रहते हैं। रविवार: सुबह 8 से दोपहर 2 बजे तक।",
                'location': "हमारी लैब मेन रोड, औरंगाबाद में है। सिटी हॉस्पिटल के पास। Google Maps: https://maps.app.goo.gl/xxxxx",
                'general': "मैं आपकी लैब टेस्ट, अपॉइंटमेंट, रिपोर्ट्स और सामान्य जानकारी में मदद कर सकती हूं। आपको क्या चाहिए?"
            }
        }
        
        return responses.get(language, responses['en']).get(intent, responses['en']['general'])

# Initialize AI
ai = MedicalAI()

# ==================== VOICE PROCESSOR ====================
class VoiceProcessor:
    def __init__(self):
        self.recognizer = sr.Recognizer()
    
    def speech_to_text(self, audio_data):
        """Convert audio bytes to text"""
        try:
            # Save audio to temp file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(audio_data)
                temp_file = f.name
            
            # Convert to text
            with sr.AudioFile(temp_file) as source:
                audio = self.recognizer.record(source)
                text = self.recognizer.recognize_google(audio, language="en-IN")
            
            # Cleanup
            os.unlink(temp_file)
            return text
            
        except sr.UnknownValueError:
            return "Sorry, I didn't understand that."
        except sr.RequestError:
            return "Speech service is unavailable."
        except Exception as e:
            return f"Error processing audio: {str(e)}"
    
    def text_to_speech(self, text, language='en'):
        """Convert text to audio bytes"""
        try:
            # Map language codes
            lang_map = {'en': 'en', 'hi': 'hi', 'mr': 'mr'}
            tts_lang = lang_map.get(language, 'en')
            
            # Create TTS
            tts = gTTS(text=text, lang=tts_lang, slow=False)
            
            # Save to bytes
            audio_bytes = io.BytesIO()
            tts.write_to_fp(audio_bytes)
            audio_bytes.seek(0)
            
            return audio_bytes
            
        except Exception as e:
            # Fallback to simple error message
            error_tts = gTTS(text="System error occurred", lang='en')
            error_bytes = io.BytesIO()
            error_tts.write_to_fp(error_bytes)
            error_bytes.seek(0)
            return error_bytes

# Initialize voice processor
voice = VoiceProcessor()

# ==================== APPOINTMENT SYSTEM ====================
class AppointmentSystem:
    def __init__(self):
        try:
            # Google Sheets setup
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets"]
            creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
            client = gspread.authorize(creds)
            self.sheet = client.open("City_Lab_Appointments").sheet1
            self.use_sheets = True
            print("✅ Connected to Google Sheets")
        except Exception as e:
            print(f"⚠️ Google Sheets not configured: {e}")
            self.use_sheets = False
            self.appointments = []
    
    def book(self, name, phone, test, date="tomorrow"):
        appointment = {
            'id': len(self.appointments) if not self.use_sheets else None,
            'name': name,
            'phone': phone,
            'test': test,
            'date': date,
            'status': 'Booked',
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        if self.use_sheets:
            try:
                self.sheet.append_row([name, phone, test, date, 'Booked', appointment['timestamp']])
            except Exception as e:
                print(f"Error saving to sheet: {e}")
                self.appointments.append(appointment)
        else:
            self.appointments.append(appointment)
            print(f"📅 Appointment stored: {appointment}")
        
        return appointment

# Initialize appointment system
appointments = AppointmentSystem()

# ==================== ROUTES ====================
@app.route('/')
def home():
    return jsonify({
        "status": "running",
        "service": "City Lab AI Voice Agent",
        "endpoints": {
            "/": "This info",
            "/test": "Web testing interface",
            "/voice-test": "Voice testing interface",
            "/twilio-voice": "Twilio Voice API (POST)",
            "/twilio-test": "Twilio setup test page",
            "/voice": "Voice API (POST audio file)",
            "/api/chat": "Text chat API",
            "/api/book": "Book appointment API",
            "/health": "Health check"
        }
    })

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

# ==================== TWILIO VOICE ENDPOINT ====================
@app.route('/twilio-voice', methods=['POST'])
def twilio_voice():
    """Twilio calls this endpoint when someone calls your Twilio number"""
    try:
        # Get speech input from Twilio
        speech_result = request.form.get('SpeechResult', '').strip()
        caller_number = request.form.get('Caller', 'Unknown')
        
        print(f"📞 Twilio Call from: {caller_number}")
        print(f"🎤 Patient said: '{speech_result}'")
        
        # If first call, no speech result yet
        if not speech_result:
            response_text = ai.get_response('greeting', 'en')
            print(f"🤖 AI greeting: '{response_text}'")
            
            # Create TwiML response
            resp = VoiceResponse()
            gather = Gather(
                input='speech',
                speech_timeout='auto',
                language='en-IN',
                speech_model='phone_call',
                action='/twilio-voice',
                method='POST'
            )
            gather.say(response_text, voice='Polly.Aditi')
            resp.append(gather)
            
            # If no response, say goodbye
            resp.say("We didn't hear your response. Please call back. Goodbye.", 
                    voice='Polly.Aditi')
            resp.hangup()
            
            return str(resp), 200, {'Content-Type': 'text/xml'}
        
        # Process speech input
        language = ai.detect_language(speech_result)
        intent = ai.detect_intent(speech_result)
        response_text = ai.get_response(intent, language)
        
        print(f"🎯 Intent: {intent}, Language: {language}")
        print(f"🤖 AI response: '{response_text}'")
        
        # Handle appointment booking
        if intent == 'book_appointment':
            # Simple extraction (you can enhance this)
            booking = appointments.book(
                name=f"Caller {caller_number[-4:]}",
                phone=caller_number,
                test="Phone Consultation",
                date="Today"
            )
            response_text += " Appointment booked successfully! You will get WhatsApp confirmation."
            print(f"📅 Appointment booked: {booking}")
        
        # Create response
        resp = VoiceResponse()
        
        if intent in ['book_appointment', 'price_inquiry', 'report_inquiry']:
            # For these intents, end call after response
            resp.say(response_text, voice='Polly.Aditi')
            resp.say("Thank you for calling. Goodbye!", voice='Polly.Aditi')
            resp.hangup()
        else:
            # Continue conversation
            gather = Gather(
                input='speech',
                speech_timeout='auto',
                language='en-IN',
                speech_model='phone_call',
                action='/twilio-voice',
                method='POST'
            )
            gather.say(response_text, voice='Polly.Aditi')
            resp.append(gather)
            
            # Timeout handler
            resp.say("We didn't hear your response. Goodbye!", voice='Polly.Aditi')
            resp.hangup()
        
        return str(resp), 200, {'Content-Type': 'text/xml'}
        
    except Exception as e:
        print(f"❌ Twilio error: {e}")
        # Error response
        resp = VoiceResponse()
        resp.say("Sorry, there was an error. Please call back later.", 
                voice='Polly.Aditi')
        resp.hangup()
        return str(resp), 200, {'Content-Type': 'text/xml'}

# Simple test endpoint for Twilio
@app.route('/twilio-test', methods=['GET'])
def twilio_test():
    """Test page to verify Twilio setup"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Twilio Test</title>
        <style>
            body { font-family: Arial; padding: 20px; }
            .box { background: #f0f8ff; padding: 20px; border-radius: 10px; margin: 20px 0; }
            code { background: #e0e0e0; padding: 2px 5px; border-radius: 3px; }
        </style>
    </head>
    <body>
        <h1>✅ Twilio Voice AI Setup</h1>
        
        <div class="box">
            <h2>📞 Twilio Configuration:</h2>
            <p>1. Buy Indian number in Twilio Console</p>
            <p>2. Set Voice Webhook URL to:</p>
            <code>https://YOUR-RENDER-APP.onrender.com/twilio-voice</code>
            <p>3. Set HTTP Method: <code>POST</code></p>
            <p>4. Save configuration</p>
        </div>
        
        <div class="box">
            <h2>🧪 Test Endpoints:</h2>
            <p><strong>Voice Endpoint:</strong> <code>/twilio-voice</code> (POST)</p>
            <p><strong>Test Call:</strong> Call your Twilio number</p>
            <p><strong>Health Check:</strong> <a href="/health">/health</a></p>
        </div>
        
        <div class="box">
            <h2>🔧 Quick Test:</h2>
            <p>Once deployed, call your Twilio number and say:</p>
            <ul>
                <li>"Hello, I need blood test"</li>
                <li>"Book appointment tomorrow"</li>
                <li>"What is your timing?"</li>
                <li>"मुझे टेस्ट करवाना है"</li>
            </ul>
        </div>
    </body>
    </html>
    '''

# Web testing interface
@app.route('/test', methods=['GET', 'POST'])
def test_ai():
    if request.method == 'POST':
        user_message = request.form.get('message', '').strip()
        language = request.form.get('language', 'en')
        
        if not user_message:
            return jsonify({"error": "No message provided"}), 400
        
        # Detect intent and language
        intent = ai.detect_intent(user_message)
        detected_lang = ai.detect_language(user_message)
        if detected_lang != 'en' or language != 'en':
            language = detected_lang if detected_lang != 'en' else language
        
        response = ai.get_response(intent, language)
        
        # If booking intent, create appointment
        booking_info = None
        if intent == 'book_appointment':
            booking = appointments.book(
                name="Patient from Web",
                phone="9876543210",
                test="General Consultation",
                date="ASAP"
            )
            booking_info = {
                "id": booking.get('id'),
                "test": booking['test'],
                "date": booking['date'],
                "status": booking['status']
            }
        
        return jsonify({
            "input": user_message,
            "intent": intent,
            "language": language,
            "response": response,
            "booking": booking_info if booking_info else None
        })
    
    # HTML interface
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>City Lab AI - Test Interface</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
            h1 { color: #2c3e50; }
            textarea { width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ddd; border-radius: 5px; }
            button { background: #3498db; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; }
            button:hover { background: #2980b9; }
            .response { background: #ecf0f1; padding: 15px; margin: 10px 0; border-radius: 5px; white-space: pre-wrap; }
            .container { display: flex; gap: 20px; }
            .left, .right { flex: 1; }
            .endpoint { background: #f8f9fa; padding: 10px; margin: 10px 0; border-left: 3px solid #3498db; }
        </style>
    </head>
    <body>
        <h1>🏥 City Lab Medical AI - Test Interface</h1>
        
        <div class="container">
            <div class="left">
                <h2>Test Chat</h2>
                <form method="post" id="chatForm">
                    <textarea name="message" rows="4" placeholder="Type patient message... 
Examples: 
- I want blood test
- मुझे ब्लड टेस्ट करवाना है
- What is your timing?
- प्राइस क्या है?
- Book appointment tomorrow"></textarea><br>
                    
                    <label>Language:</label>
                    <select name="language">
                        <option value="en">English</option>
                        <option value="hi">Hindi</option>
                    </select><br><br>
                    
                    <button type="submit">Get AI Response</button>
                </form>
                
                <div id="result"></div>
            </div>
            
            <div class="right">
                <h2>Endpoints</h2>
                <div class="endpoint">
                    <strong>Twilio Test:</strong> <a href="/twilio-test">/twilio-test</a>
                    <p>Setup instructions for Twilio</p>
                </div>
                
                <div class="endpoint">
                    <strong>Voice Test:</strong> <a href="/voice-test">/voice-test</a>
                    <p>Upload audio file to test voice AI</p>
                </div>
                
                <div class="endpoint">
                    <strong>Health Check:</strong> <a href="/health">/health</a>
                    <p>Check if service is running</p>
                </div>
                
                <h3>Test Phrases:</h3>
                <ul>
                    <li>blood test price</li>
                    <li>book appointment for tomorrow</li>
                    <li>मुझे शुगर टेस्ट करवाना है</li>
                    <li>where is your lab</li>
                    <li>report kab tak aayegi</li>
                </ul>
            </div>
        </div>
        
        <script>
            document.getElementById('chatForm').onsubmit = async function(e) {
                e.preventDefault();
                
                const formData = new FormData(this);
                const responseDiv = document.getElementById('result');
                responseDiv.innerHTML = "Processing...";
                
                try {
                    const response = await fetch('/test', {
                        method: 'POST',
                        body: formData
                    });
                    
                    const data = await response.json();
                    
                    let html = `<div class="response">
                        <strong>Input:</strong> ${data.input}<br>
                        <strong>Intent:</strong> ${data.intent}<br>
                        <strong>Language:</strong> ${data.language}<br>
                        <strong>Response:</strong> ${data.response}`;
                    
                    if (data.booking) {
                        html += `<br><strong>Booking:</strong> ${JSON.stringify(data.booking)}`;
                    }
                    
                    html += '</div>';
                    responseDiv.innerHTML = html;
                    
                } catch (error) {
                    responseDiv.innerHTML = `<div class="response" style="background:#ffebee;">Error: ${error}</div>`;
                }
            };
        </script>
    </body>
    </html>
    '''
    return render_template_string(html)

# Voice testing interface
@app.route('/voice-test', methods=['GET'])
def voice_test_page():
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Voice AI Test</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }
            h1 { color: #2c3e50; }
            input, button { margin: 10px 0; padding: 10px; }
            button { background: #27ae60; color: white; border: none; cursor: pointer; border-radius: 5px; }
            button:disabled { background: #95a5a6; }
            .recording { background: #e74c3c !important; }
            audio { width: 100%; margin: 10px 0; }
            .info { background: #f8f9fa; padding: 10px; border-radius: 5px; margin: 10px 0; }
        </style>
    </head>
    <body>
        <h1>🎤 Test Voice AI</h1>
        
        <div class="info">
            <p><strong>Instructions:</strong></p>
            <p>1. Record audio using your microphone</p>
            <p>2. Or upload a pre-recorded .wav file</p>
            <p>3. AI will process and respond with voice</p>
        </div>
        
        <button id="recordBtn">🎤 Start Recording</button>
        <button id="stopBtn" disabled>⏹️ Stop Recording</button>
        
        <div>
            <p>Or upload audio file:</p>
            <input type="file" id="audioUpload" accept="audio/*">
            <button onclick="uploadAudio()">📤 Upload & Process</button>
        </div>
        
        <div id="response"></div>
        
        <h3>Sample Phrases:</h3>
        <ul>
            <li>"Hello, I need blood test"</li>
            <li>"Book appointment tomorrow"</li>
            <li>"What tests do you offer?"</li>
            <li>"मुझे शुगर टेस्ट करवाना है"</li>
        </ul>
        
        <script>
            let mediaRecorder;
            let audioChunks = [];
            
            document.getElementById('recordBtn').onclick = async () => {
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                    mediaRecorder = new MediaRecorder(stream);
                    
                    mediaRecorder.ondataavailable = event => {
                        audioChunks.push(event.data);
                    };
                    
                    mediaRecorder.onstop = async () => {
                        const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                        await sendAudio(audioBlob);
                        audioChunks = [];
                    };
                    
                    mediaRecorder.start();
                    document.getElementById('recordBtn').disabled = true;
                    document.getElementById('stopBtn').disabled = false;
                    document.getElementById('recordBtn').classList.add('recording');
                    
                } catch (error) {
                    alert('Error accessing microphone: ' + error);
                }
            };
            
            document.getElementById('stopBtn').onclick = () => {
                if (mediaRecorder && mediaRecorder.state !== 'inactive') {
                    mediaRecorder.stop();
                    document.getElementById('recordBtn').disabled = false;
                    document.getElementById('stopBtn').disabled = true;
                    document.getElementById('recordBtn').classList.remove('recording');
                }
            };
            
            async function uploadAudio() {
                const fileInput = document.getElementById('audioUpload');
                if (!fileInput.files[0]) {
                    alert('Please select an audio file');
                    return;
                }
                
                await sendAudio(fileInput.files[0]);
            }
            
            async function sendAudio(audioBlob) {
                const responseDiv = document.getElementById('response');
                responseDiv.innerHTML = "Processing audio...";
                
                const formData = new FormData();
                formData.append('audio', audioBlob, 'recording.wav');
                
                try {
                    const response = await fetch('/voice', {
                        method: 'POST',
                        body: formData
                    });
                    
                    if (response.ok) {
                        const audioBlob = await response.blob();
                        const audioUrl = URL.createObjectURL(audioBlob);
                        
                        responseDiv.innerHTML = `
                            <h3>AI Response:</h3>
                            <audio controls autoplay>
                                <source src="${audioUrl}" type="audio/mpeg">
                                Your browser does not support audio playback.
                            </audio>
                            <p>✅ AI responded successfully!</p>
                        `;
                    } else {
                        const error = await response.text();
                        responseDiv.innerHTML = `<div style="color:red;">Error: ${error}</div>`;
                    }
                } catch (error) {
                    responseDiv.innerHTML = `<div style="color:red;">Network error: ${error}</div>`;
                }
            }
        </script>
    </body>
    </html>
    '''
    return render_template_string(html)

# Voice API endpoint
@app.route('/voice', methods=['POST'])
def handle_voice():
    """Handle voice input and return voice output"""
    try:
        # Check if audio file is provided
        if 'audio' not in request.files:
            return jsonify({"error": "No audio file provided"}), 400
        
        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({"error": "No selected file"}), 400
        
        # Check file type
        if not audio_file.filename.lower().endswith(('.wav', '.mp3', '.m4a', '.ogg')):
            return jsonify({"error": "Unsupported audio format. Use WAV or MP3"}), 400
        
        # Convert audio to text
        audio_data = audio_file.read()
        user_text = voice.speech_to_text(audio_data)
        
        # Log for debugging
        print(f"🎤 Voice input: '{user_text}'")
        
        # Process with AI
        language = ai.detect_language(user_text)
        intent = ai.detect_intent(user_text)
        response_text = ai.get_response(intent, language)
        
        print(f"🤖 AI response: '{response_text}' (Intent: {intent}, Lang: {language})")
        
        # If it's a booking, create appointment
        if intent == 'book_appointment':
            booking = appointments.book(
                name="Voice Call Patient",
                phone="Not provided",
                test="Voice Consultation",
                date="ASAP"
            )
            response_text += " Appointment booked successfully!"
            print(f"📅 Appointment booked: {booking}")
        
        # Convert response to speech
        audio_response = voice.text_to_speech(response_text, language)
        
        # Return audio file
        return send_file(
            audio_response,
            mimetype='audio/mpeg',
            as_attachment=False,
            download_name='ai_response.mp3'
        )
        
    except Exception as e:
        print(f"❌ Error in voice endpoint: {e}")
        return jsonify({"error": str(e)}), 500

# Text chat API endpoint
@app.route('/api/chat', methods=['POST'])
def api_chat():
    """Text-based chat endpoint"""
    try:
        data = request.json
        if not data or 'message' not in data:
            return jsonify({"error": "No message provided"}), 400
        
        user_text = data['message']
        language = data.get('language', 'en')
        
        # Detect intent and language
        intent = ai.detect_intent(user_text)
        detected_lang = ai.detect_language(user_text)
        if detected_lang != 'en':
            language = detected_lang
        
        response_text = ai.get_response(intent, language)
        
        # Book appointment if requested
        booking = None
        if intent == 'book_appointment':
            booking = appointments.book(
                name=data.get('name', 'API User'),
                phone=data.get('phone', '0000000000'),
                test=data.get('test', 'General Consultation'),
                date=data.get('date', 'ASAP')
            )
            response_text += f" Appointment booked for {booking['date']}!"
        
        return jsonify({
            "response": response_text,
            "intent": intent,
            "language": language,
            "booking": booking,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Appointment booking API
@app.route('/api/book', methods=['POST'])
def api_book():
    try:
        data = request.json
        required = ['name', 'phone', 'test']
        
        for field in required:
            if field not in data:
                return jsonify({"error": f"Missing field: {field}"}), 400
        
        appointment = appointments.book(
            name=data['name'],
            phone=data['phone'],
            test=data['test'],
            date=data.get('date', 'ASAP')
        )
        
        return jsonify({
            "status": "success",
            "appointment": appointment,
            "message": "Appointment booked successfully!"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==================== MAIN ====================
if __name__ == '__main__':
    print("=" * 60)
    print("🚀 CITY LAB AI VOICE AGENT WITH TWILIO")
    print("=" * 60)
    print(f"✅ Medical AI initialized")
    print(f"✅ Voice processor ready")
    print(f"✅ Appointment system: {'Google Sheets' if appointments.use_sheets else 'Local storage'}")
    print(f"✅ Twilio integration ready")
    print("=" * 60)
    print("🌐 WEB INTERFACES:")
    print("   • Main Test: http://localhost:5000/test")
    print("   • Twilio Setup: http://localhost:5000/twilio-test")
    print("   • Voice Test: http://localhost:5000/voice-test")
    print("")
    print("📞 TWILIO VOICE ENDPOINTS:")
    print("   • Voice API: POST http://localhost:5000/twilio-voice")
    print("   • Test Call: Buy Indian number → Set webhook → Call!")
    print("")
    print("🔧 OTHER ENDPOINTS:")
    print("   • Chat API: POST http://localhost:5000/api/chat")
    print("   • Booking API: POST http://localhost:5000/api/book")
    print("   • Health Check: http://localhost:5000/health")
    print("=" * 60)
    print("💡 TWILIO SETUP STEPS:")
    print("1. Buy Indian number on Twilio")
    print("2. Set Voice Webhook to: http://YOUR-APP/twilio-voice")
    print("3. Set HTTP Method: POST")
    print("4. Call your number to test!")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5000, debug=True)

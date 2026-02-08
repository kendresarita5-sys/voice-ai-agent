#!/usr/bin/env python3
"""
Test Voice AI Locally
Run: python test_voice.py
"""

import requests
import json

def test_web_interface():
    """Test the web interface"""
    print("Testing Web Interface...")
    
    try:
        # Test with local server
        url = "http://localhost:5000/test"
        
        # GET request
        response = requests.get(url)
        if response.status_code == 200:
            print("✅ Web interface is working!")
        else:
            print(f"❌ Web interface error: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("⚠️  Flask app not running. Start it with: python app.py")
    except Exception as e:
        print(f"❌ Error: {e}")

def test_health_endpoint():
    """Test health endpoint"""
    print("\nTesting Health Endpoint...")
    
    try:
        response = requests.get("http://localhost:5000/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check: {data.get('status')}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
    except:
        print("⚠️  Cannot connect to server")

def test_chat_api():
    """Test the chat API"""
    print("\nTesting Chat API...")
    
    test_messages = [
        "I need blood test",
        "book appointment tomorrow",
        "मुझे टेस्ट करवाना है",
        "what is your timing"
    ]
    
    for msg in test_messages:
        try:
            response = requests.post(
                "http://localhost:5000/api/chat",
                json={"message": msg},
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ '{msg[:20]}...' → {data.get('intent')}")
            else:
                print(f"❌ '{msg[:20]}...' failed: {response.status_code}")
                
        except:
            print(f"⚠️  Cannot test: '{msg[:20]}...'")

def test_endpoints():
    """List all endpoints"""
    print("\n" + "="*50)
    print("AVAILABLE ENDPOINTS:")
    print("="*50)
    
    endpoints = [
        ("GET",  "/",            "Service info"),
        ("GET",  "/test",        "Web testing interface"),
        ("GET",  "/twilio-test", "Twilio setup instructions"),
        ("GET",  "/voice-test",  "Voice testing interface"),
        ("GET",  "/health",      "Health check"),
        ("POST", "/voice",       "Voice API (upload audio)"),
        ("POST", "/twilio-voice","Twilio voice webhook"),
        ("POST", "/api/chat",    "Chat API"),
        ("POST", "/api/book",    "Booking API")
    ]
    
    for method, path, desc in endpoints:
        print(f"{method:6} {path:20} - {desc}")
    
    print("="*50)

def main():
    print("="*60)
    print("CITY LAB AI - LOCAL TEST SUITE")
    print("="*60)
    
    print("\n⚠️  MAKE SURE THE APP IS RUNNING:")
    print("   $ python app.py")
    print("\nThen run these tests in another terminal window.")
    
    test_endpoints()
    
    choice = input("\nRun tests? (y/n): ").lower()
    if choice == 'y':
        test_web_interface()
        test_health_endpoint()
        test_chat_api()
        
        print("\n" + "="*60)
        print("NEXT STEPS:")
        print("1. Open browser: http://localhost:5000/test")
        print("2. Test chat interface")
        print("3. Test voice: http://localhost:5000/voice-test")
        print("4. Deploy to Render: git push")
        print("5. Buy Twilio number and setup webhook")
        print("="*60)

if __name__ == "__main__":
    main()

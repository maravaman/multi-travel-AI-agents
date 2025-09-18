#!/usr/bin/env python3
"""
Start Test Server and Verify UI Functionality
Starts the travel assistant server and tests if UI endpoints work
"""

import subprocess
import time
import requests
import sys
import os
import threading

def test_ui_routes():
    """Test UI routes after server starts"""
    time.sleep(5)  # Wait for server to fully start
    
    print("\n🌐 Testing UI Routes:")
    
    try:
        # Test root route (should serve the travel interface)
        root_response = requests.get("http://localhost:8000/", timeout=5)
        if root_response.status_code == 200:
            print("✅ Root route (/) serving HTML successfully")
            if "travel" in root_response.text.lower():
                print("✅ Travel interface content detected")
            else:
                print("⚠️ Travel interface content not found")
        else:
            print(f"❌ Root route failed: {root_response.status_code}")
        
        # Test health endpoint
        health_response = requests.get("http://localhost:8000/health", timeout=5)
        if health_response.status_code == 200:
            print("✅ Health endpoint working")
        else:
            print(f"❌ Health endpoint failed: {health_response.status_code}")
            
        # Test travel chat endpoint
        chat_response = requests.post("http://localhost:8000/travel/chat", 
                                    json={"user_id": 999, "text": "Hello, testing UI"}, 
                                    timeout=10)
        if chat_response.status_code == 200:
            print("✅ Travel chat API working")
            data = chat_response.json()
            print(f"   - AI Used: {data.get('ai_used')}")
            print(f"   - Response: {data.get('response', '')[:100]}...")
        else:
            print(f"❌ Travel chat API failed: {chat_response.status_code}")
            
    except Exception as e:
        print(f"❌ UI route testing failed: {e}")
    
    print(f"\n🎯 Access the Travel Assistant UI at: http://localhost:8000/")
    print(f"🔧 Check browser console for any JavaScript errors")

def start_test_server():
    """Start the FastAPI server for testing"""
    
    print("🚀 Starting Travel Assistant Test Server")
    print("=" * 50)
    
    # Start testing thread
    test_thread = threading.Thread(target=test_ui_routes, daemon=True)
    test_thread.start()
    
    try:
        # Start the server
        result = subprocess.run([
            "uvicorn", "api.main:app", 
            "--host", "0.0.0.0", 
            "--port", "8000",
            "--reload"
        ], check=False)
        
        return result.returncode == 0
        
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
        return True
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        return False

if __name__ == "__main__":
    print("🎬 Travel Assistant - Server Startup & UI Test")
    
    # Add current directory to Python path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    
    success = start_test_server()
    
    if success:
        print("\n✅ Server started successfully!")
        print("🌐 UI should now be accessible at http://localhost:8000/")
    else:
        print("\n❌ Server startup failed!")
        sys.exit(1)
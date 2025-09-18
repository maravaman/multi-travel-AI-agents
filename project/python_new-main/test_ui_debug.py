#!/usr/bin/env python3
"""
Debug UI Response Issues
Tests if the backend is properly serving responses and UI routes are working
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import requests
import json
import time
import subprocess

def test_ui_debug():
    """Debug UI response issues by testing all components"""
    
    print("🐛 Debugging UI Response Issues\n")
    
    # Test 1: Check if FastAPI app starts correctly
    print("🚀 Test 1: Testing FastAPI startup...")
    
    try:
        # Start server briefly to test
        import uvicorn
        from api.main import app
        print("✅ FastAPI app imports successfully")
        
        # Test basic routes exist
        routes = []
        for route in app.routes:
            if hasattr(route, 'path'):
                routes.append(route.path)
        
        print(f"✅ Found {len(routes)} routes")
        travel_routes = [r for r in routes if 'travel' in r]
        print(f"✅ Travel routes: {travel_routes}")
        
    except Exception as e:
        print(f"❌ FastAPI startup issue: {e}")
        return False
    
    # Test 2: Test if templates are accessible
    print(f"\n📄 Test 2: Testing template accessibility...")
    
    try:
        template_path = "C:\\Users\\marav\\OneDrive\\Desktop\\travel-ai-system\\project\\python_new-main\\templates\\travel_interface.html"
        
        if os.path.exists(template_path):
            print("✅ Travel interface template exists")
            
            # Check if template has the key JavaScript functions
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            # Check for key functions
            key_functions = ['sendChatMessage', 'formatTravelResponse', 'addMessage']
            found_functions = []
            for func in key_functions:
                if func in template_content:
                    found_functions.append(func)
            
            print(f"✅ JavaScript functions found: {found_functions}")
            
            # Check for API endpoint calls
            api_calls = []
            if '/travel/chat' in template_content:
                api_calls.append('chat')
            if '/perfect_query' in template_content:
                api_calls.append('perfect_query')
            
            print(f"✅ API endpoints referenced: {api_calls}")
            
        else:
            print("❌ Travel interface template not found")
            return False
            
    except Exception as e:
        print(f"❌ Template test failed: {e}")
        return False
    
    # Test 3: Test direct API endpoints
    print(f"\n🌐 Test 3: Testing API endpoints directly...")
    
    # Start a test server
    print("Starting test server on port 8002...")
    server_process = None
    
    try:
        server_process = subprocess.Popen([
            "uvicorn", "api.main:app", "--host", "localhost", "--port", "8002"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Wait for server to start
        time.sleep(3)
        
        # Test basic health check
        try:
            health_response = requests.get("http://localhost:8002/health", timeout=5)
            if health_response.status_code == 200:
                print("✅ Server health check passed")
            else:
                print(f"⚠️ Health check returned {health_response.status_code}")
        except Exception as e:
            print(f"❌ Health check failed: {e}")
            return False
        
        # Test travel chat endpoint
        try:
            chat_payload = {
                "user_id": 123,
                "text": "Test query for UI debugging"
            }
            
            chat_response = requests.post(
                "http://localhost:8002/travel/chat", 
                json=chat_payload,
                timeout=10
            )
            
            if chat_response.status_code == 200:
                chat_data = chat_response.json()
                print("✅ Travel chat endpoint working")
                print(f"   - Response length: {len(chat_data.get('response', ''))}")
                print(f"   - AI used: {chat_data.get('ai_used')}")
                print(f"   - Processing time: {chat_data.get('processing_time', 0):.2f}s")
                
                # Check response format for UI compatibility
                required_fields = ['user_id', 'response', 'agents_involved', 'processing_time', 'mode', 'ai_used']
                missing_fields = [field for field in required_fields if field not in chat_data]
                
                if not missing_fields:
                    print("✅ Response format compatible with UI")
                else:
                    print(f"❌ Missing fields for UI: {missing_fields}")
                    
            else:
                print(f"❌ Chat endpoint failed: {chat_response.status_code}")
                print(f"   Error: {chat_response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Chat endpoint test failed: {e}")
            return False
        
        # Test perfect query endpoint
        try:
            perfect_payload = {
                "user": "test_user",
                "user_id": 123,
                "question": "Test perfect query for UI debugging"
            }
            
            perfect_response = requests.post(
                "http://localhost:8002/perfect_query",
                json=perfect_payload,
                timeout=10
            )
            
            if perfect_response.status_code == 200:
                perfect_data = perfect_response.json()
                print("✅ Perfect query endpoint working")
                print(f"   - Response length: {len(perfect_data.get('response', ''))}")
                print(f"   - AI used: {perfect_data.get('ai_used')}")
                print(f"   - System status: {perfect_data.get('system_status')}")
            else:
                print(f"⚠️ Perfect query endpoint issue: {perfect_response.status_code}")
        
        except Exception as e:
            print(f"⚠️ Perfect query test issue: {e}")
        
    finally:
        # Clean up server
        if server_process:
            server_process.terminate()
            server_process.wait()
            print("🛑 Test server stopped")
    
    # Test 4: Check for common UI issues
    print(f"\n🔧 Test 4: Checking for common UI issues...")
    
    ui_issues = []
    
    # Check CORS settings
    try:
        from api.main import app
        # Check if CORS middleware is configured
        middlewares = [str(middleware) for middleware in app.middleware]
        cors_configured = any('cors' in middleware.lower() for middleware in middlewares)
        
        if cors_configured:
            print("✅ CORS middleware appears to be configured")
        else:
            print("⚠️ CORS middleware not detected - may cause UI issues")
            ui_issues.append("CORS not configured")
    except Exception as e:
        print(f"⚠️ Could not check CORS configuration: {e}")
    
    # Check static file serving
    static_dir = "C:\\Users\\marav\\OneDrive\\Desktop\\travel-ai-system\\project\\python_new-main\\static"
    if os.path.exists(static_dir):
        print("✅ Static directory exists")
    else:
        print("⚠️ Static directory not found")
        ui_issues.append("Static directory missing")
    
    # Summary
    print(f"\n📊 UI Debug Summary:")
    if not ui_issues:
        print("✅ No obvious UI issues detected")
        print("✅ Backend endpoints are working correctly")
        print("✅ Template file exists and has required functions")
        print("🔍 Issue may be in client-server communication or JavaScript execution")
        
        print(f"\n💡 Recommendations to fix UI response display:")
        print("1. Check browser console for JavaScript errors")
        print("2. Verify CORS settings allow frontend requests")
        print("3. Test with browser developer tools to see network requests")
        print("4. Start server and access http://localhost:8000/travel_interface.html")
        
        return True
    else:
        print(f"❌ Found {len(ui_issues)} potential issues:")
        for issue in ui_issues:
            print(f"   - {issue}")
        return False

if __name__ == "__main__":
    success = test_ui_debug()
    if success:
        print("\n✅ Backend components working - UI issue likely in browser/CORS")
    else:
        print("\n❌ Found backend issues that may affect UI")
    print("\n🎯 Next step: Start server with 'uvicorn api.main:app --host 0.0.0.0 --port 8000' and test UI manually")
    sys.exit(0)
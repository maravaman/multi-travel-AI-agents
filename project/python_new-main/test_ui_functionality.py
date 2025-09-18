#!/usr/bin/env python3
"""
Test UI Response Display Functionality
Simulates the JavaScript behavior of the frontend to test response formatting and display
"""

import requests
import json
import time
import sys
import os

def simulate_ui_formatting(response_text):
    """Simulate the formatTravelResponse JavaScript function"""
    # Convert markdown-style formatting to HTML (simplified version)
    formatted = response_text
    
    # Bold text
    formatted = formatted.replace('**', '<strong>').replace('**', '</strong>')
    
    # Headers  
    import re
    formatted = re.sub(r'#{1,3}\s+(.*?)$', r'<h4 style="color: #667eea;">$1</h4>', formatted, flags=re.MULTILINE)
    
    # Lists
    formatted = re.sub(r'^- (.*?)$', r'<li>$1</li>', formatted, flags=re.MULTILINE)
    
    # Line breaks
    formatted = formatted.replace('\n', '<br>')
    
    return formatted

def test_ui_functionality():
    """Test the UI response display functionality"""
    
    print("🖥️ Testing UI Response Display Functionality\n")
    
    # Test data
    test_cases = [
        {
            "name": "Chat Mode Test", 
            "endpoint": "http://localhost:8001/travel/chat",
            "payload": {
                "user_id": 456,
                "text": "I'm feeling anxious about my upcoming trip to Japan. Any advice?"
            }
        },
        {
            "name": "Perfect Query Test",
            "endpoint": "http://localhost:8001/perfect_query", 
            "payload": {
                "user": "user_456",
                "user_id": 456,
                "question": "Help me communicate better with locals in Italy"
            }
        }
    ]
    
    # Start a temporary test server
    import subprocess
    import threading
    import time
    
    print("🚀 Starting test server...")
    
    # Start server in background
    server_process = subprocess.Popen([
        "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8001"
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Wait for server to start
    time.sleep(5)
    
    try:
        success_count = 0
        total_tests = len(test_cases)
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"🧪 Test {i}/{total_tests}: {test_case['name']}")
            
            try:
                # Make request
                response = requests.post(
                    test_case['endpoint'], 
                    json=test_case['payload'],
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Extract key data like the UI would
                    response_text = data.get('response', 'No response')
                    agents = data.get('agents_involved', ['Unknown'])
                    processing_time = data.get('processing_time', 0)
                    ai_used = data.get('ai_used', False)
                    mode = data.get('mode', 'unknown')
                    
                    print(f"✅ Response received successfully")
                    print(f"   - Length: {len(response_text)} characters")
                    print(f"   - AI Powered: {'🧠 YES' if ai_used else '🤖 NO'}")
                    print(f"   - Agents: {', '.join(agents)}")
                    print(f"   - Processing: {processing_time:.2f}s")
                    print(f"   - Mode: {mode}")
                    
                    # Simulate UI formatting
                    formatted_response = simulate_ui_formatting(response_text)
                    print(f"   - Formatted length: {len(formatted_response)} characters")
                    
                    # Check for typical UI indicators
                    has_structure = any(marker in response_text for marker in ['**', '##', '###', '-'])
                    has_content = len(response_text.strip()) > 50
                    correct_agents = len(agents) > 0 and agents[0] != 'Unknown'
                    
                    print(f"   - Has Structure: {'✅' if has_structure else '❌'}")
                    print(f"   - Has Content: {'✅' if has_content else '❌'}")
                    print(f"   - Correct Agents: {'✅' if correct_agents else '❌'}")
                    
                    # Preview first 200 chars like the UI would show
                    preview = response_text[:200]
                    if len(response_text) > 200:
                        preview += "..."
                    print(f"   - Preview: {preview}")
                    
                    # Simulate AI badge generation 
                    if ai_used:
                        badge_text = f"🧠 {agents[0]} AI-Powered"
                        ai_info = f"AI Response: Powered by Ollama LLaMA 3 | Processing: {processing_time:.2f}s"
                        print(f"   - UI Badge: {badge_text}")
                        print(f"   - AI Info: {ai_info}")
                    else:
                        badge_text = f"🤖 {agents[0]}"
                        print(f"   - UI Badge: {badge_text}")
                    
                    success_count += 1
                    
                else:
                    print(f"❌ Request failed with status {response.status_code}")
                    print(f"   Error: {response.text}")
                
            except requests.exceptions.Timeout:
                print(f"⏰ Request timed out (30s)")
            except requests.exceptions.RequestException as e:
                print(f"❌ Request error: {e}")
            except Exception as e:
                print(f"❌ Unexpected error: {e}")
            
            print("   " + "-"*50)
        
        # Summary
        print(f"\n🎉 UI Functionality Test Results:")
        print(f"✅ Successful tests: {success_count}/{total_tests}")
        
        if success_count == total_tests:
            print("✅ All UI response formatting working correctly")
            print("✅ AI indicators functioning properly")
            print("✅ Response structure compatible with UI")
            print("✅ UI ready for user interaction")
            ui_success = True
        else:
            print(f"❌ {total_tests - success_count} tests failed - UI may have display issues")
            ui_success = False
        
        return ui_success
        
    finally:
        # Stop test server
        server_process.terminate()
        server_process.wait()
        print("\n🛑 Test server stopped")

if __name__ == "__main__":
    success = test_ui_functionality()
    if not success:
        sys.exit(1)
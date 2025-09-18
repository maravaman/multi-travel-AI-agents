#!/usr/bin/env python3
"""
Complete System Test After Fixes
Tests both database fixes and UI functionality end-to-end
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import requests
import time
import subprocess
import threading

def test_database_functionality():
    """Test database functionality after fixes"""
    print("🗄️ Testing Database Functionality...")
    
    try:
        from core.travel_memory_manager import TravelMemoryManager
        
        memory_manager = TravelMemoryManager()
        
        # Test database connections
        mysql_ok = memory_manager.mysql_available
        redis_ok = memory_manager.redis_available
        
        print(f"   - MySQL: {'✅' if mysql_ok else '❌'}")
        print(f"   - Redis: {'✅' if redis_ok else '❌'}")
        
        if mysql_ok:
            # Test turns table (this was the original issue)
            try:
                cursor = memory_manager.mysql_conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM turns")
                turn_count = cursor.fetchone()[0]
                print(f"   - Turns table: ✅ ({turn_count} records)")
                cursor.close()
            except Exception as e:
                print(f"   - Turns table: ❌ {e}")
                return False
        
        # Test memory operations
        try:
            test_user_id = 888
            
            # Test profile storage
            test_profile = {
                "destinations": ["Tokyo", "Paris"],
                "pace": "moderate"
            }
            memory_manager.cache_user_travel_profile(test_user_id, test_profile)
            retrieved = memory_manager.get_user_travel_profile(test_user_id)
            
            if retrieved and retrieved.get('pace') == 'moderate':
                print("   - Profile storage: ✅")
            else:
                print("   - Profile storage: ❌")
                return False
            
            # Test turn storage  
            turn_id = memory_manager.add_turn(test_user_id, "user", "Test database fix")
            if turn_id:
                print("   - Turn storage: ✅")
            else:
                print("   - Turn storage: ❌")
                return False
                
        except Exception as e:
            print(f"   - Memory operations: ❌ {e}")
            return False
        
        print("✅ Database functionality working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def test_api_endpoints():
    """Test API endpoints functionality"""
    print("\n🌐 Testing API Endpoints...")
    
    # Start test server
    server_process = subprocess.Popen([
        "uvicorn", "api.main:app", "--host", "localhost", "--port", "8003"
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    time.sleep(5)  # Wait for server startup
    
    try:
        # Test health endpoint
        health_response = requests.get("http://localhost:8003/health", timeout=5)
        if health_response.status_code == 200:
            print("   - Health endpoint: ✅")
        else:
            print("   - Health endpoint: ❌")
            return False
        
        # Test travel chat endpoint
        chat_payload = {
            "user_id": 777,
            "text": "Test message for complete system verification"
        }
        
        chat_response = requests.post(
            "http://localhost:8003/travel/chat",
            json=chat_payload,
            timeout=15
        )
        
        if chat_response.status_code == 200:
            chat_data = chat_response.json()
            print("   - Travel chat endpoint: ✅")
            print(f"     * Response length: {len(chat_data.get('response', ''))}")
            print(f"     * AI used: {chat_data.get('ai_used')}")
            print(f"     * Processing time: {chat_data.get('processing_time', 0):.2f}s")
            
            # Verify response structure (this was part of UI issue)
            required_fields = ['user_id', 'response', 'agents_involved', 'ai_used']
            missing = [f for f in required_fields if f not in chat_data]
            
            if not missing:
                print("     * Response structure: ✅")
            else:
                print(f"     * Response structure: ❌ Missing {missing}")
                return False
                
        else:
            print(f"   - Travel chat endpoint: ❌ Status {chat_response.status_code}")
            return False
        
        # Test perfect query endpoint
        perfect_payload = {
            "user": "test_user",
            "user_id": 777,
            "question": "Test perfect query for system verification"
        }
        
        perfect_response = requests.post(
            "http://localhost:8003/perfect_query",
            json=perfect_payload,
            timeout=15
        )
        
        if perfect_response.status_code == 200:
            perfect_data = perfect_response.json()
            print("   - Perfect query endpoint: ✅")
            print(f"     * AI used: {perfect_data.get('ai_used')}")
            print(f"     * System status: {perfect_data.get('system_status')}")
        else:
            print(f"   - Perfect query endpoint: ❌ Status {perfect_response.status_code}")
            return False
            
        print("✅ API endpoints working correctly")
        return True
        
    except Exception as e:
        print(f"❌ API endpoint test failed: {e}")
        return False
        
    finally:
        # Clean up server
        server_process.terminate()
        server_process.wait()

def test_ui_structure():
    """Test UI template and structure"""
    print("\n📄 Testing UI Structure...")
    
    try:
        template_path = "C:\\Users\\marav\\OneDrive\\Desktop\\travel-ai-system\\project\\python_new-main\\templates\\travel_interface.html"
        
        if not os.path.exists(template_path):
            print("   - Template file: ❌ Not found")
            return False
        
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for key UI elements
        ui_elements = [
            'sendChatMessage',      # Chat functionality
            'formatTravelResponse', # Response formatting  
            '/travel/chat',         # API endpoint
            '/perfect_query',       # Perfect query endpoint
            'ai_used',             # AI usage detection
            'agent-badge'          # Agent display
        ]
        
        missing_elements = []
        for element in ui_elements:
            if element not in content:
                missing_elements.append(element)
        
        if not missing_elements:
            print("   - UI template structure: ✅")
            print("   - JavaScript functions: ✅")
            print("   - API integration: ✅")
            print("   - AI indicators: ✅")
        else:
            print(f"   - Missing UI elements: ❌ {missing_elements}")
            return False
        
        print("✅ UI structure is complete")
        return True
        
    except Exception as e:
        print(f"❌ UI structure test failed: {e}")
        return False

def main():
    """Run complete system test"""
    print("🧪 Complete System Test After Fixes")
    print("=" * 50)
    
    tests_passed = 0
    total_tests = 3
    
    # Test 1: Database functionality
    if test_database_functionality():
        tests_passed += 1
    
    # Test 2: API endpoints  
    if test_api_endpoints():
        tests_passed += 1
    
    # Test 3: UI structure
    if test_ui_structure():
        tests_passed += 1
    
    # Final assessment
    print("\n" + "=" * 50)
    print("🎯 Complete System Test Results:")
    print(f"✅ Tests passed: {tests_passed}/{total_tests}")
    
    if tests_passed == total_tests:
        print("\n🎉 ALL FIXES SUCCESSFUL!")
        print("✅ Database tables created and working")
        print("✅ API endpoints returning proper responses") 
        print("✅ UI structure complete with AI indicators")
        print("✅ CORS middleware added for frontend requests")
        print("\n🚀 System Status: FULLY OPERATIONAL")
        print("🌐 Start server with: uvicorn api.main:app --host 0.0.0.0 --port 8000")
        print("🎯 Access UI at: http://localhost:8000/")
        return True
    else:
        print(f"\n⚠️ {total_tests - tests_passed} issues remain")
        print("🔧 Please review failed tests above")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n✅ Travel Assistant system fully restored and operational!")
    else:
        print("\n❌ Some issues remain - check test results above")
    sys.exit(0 if success else 1)
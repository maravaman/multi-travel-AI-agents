#!/usr/bin/env python3
"""
Test API Endpoints Response Format
Tests the /travel/chat and /perfect_query endpoints to ensure proper response structure
"""

import asyncio
import json
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from api.travel_endpoints import router as travel_router
from api.main import app
from fastapi.testclient import TestClient

def test_api_endpoints():
    """Test both travel endpoints for proper response structure"""
    
    # Create test client
    client = TestClient(app)
    
    print("🔧 Testing API Endpoints Response Format\n")
    
    # Test data
    test_user_id = 123
    test_question = "I want to plan a relaxing beach vacation in Thailand"
    
    # Test 1: /travel/chat endpoint
    print("📡 Testing /travel/chat endpoint...")
    chat_response = client.post("/travel/chat", json={
        "user_id": test_user_id,
        "text": test_question
    })
    
    if chat_response.status_code == 200:
        chat_data = chat_response.json()
        print(f"✅ Chat endpoint successful (Status: {chat_response.status_code})")
        
        # Check required fields
        required_fields = ["user_id", "response", "agents_involved", "processing_time", "session_id", "mode", "ai_used"]
        missing_fields = [field for field in required_fields if field not in chat_data]
        
        if not missing_fields:
            print("✅ All required fields present in chat response")
            print(f"   - Response length: {len(chat_data.get('response', ''))} characters")
            print(f"   - AI Used: {chat_data.get('ai_used')}")
            print(f"   - Agents Involved: {chat_data.get('agents_involved')}")
            print(f"   - Processing Time: {chat_data.get('processing_time', 0):.3f}s")
            print(f"   - Mode: {chat_data.get('mode')}")
        else:
            print(f"❌ Missing required fields: {missing_fields}")
            
        # Preview response
        response_preview = chat_data.get('response', '')[:200]
        print(f"   - Response Preview: {response_preview}{'...' if len(response_preview) >= 200 else ''}")
        
    else:
        print(f"❌ Chat endpoint failed (Status: {chat_response.status_code})")
        print(f"   Error: {chat_response.text}")
    
    print("\n" + "="*60 + "\n")
    
    # Test 2: /perfect_query endpoint  
    print("🚀 Testing /perfect_query endpoint...")
    perfect_response = client.post("/perfect_query", json={
        "user": f"user_{test_user_id}",
        "user_id": test_user_id,
        "question": test_question
    })
    
    if perfect_response.status_code == 200:
        perfect_data = perfect_response.json()
        print(f"✅ Perfect query endpoint successful (Status: {perfect_response.status_code})")
        
        # Check required fields for perfect query
        required_perfect_fields = ["user_id", "response", "agents_involved", "processing_time", "mode", "ai_used"]
        missing_perfect_fields = [field for field in required_perfect_fields if field not in perfect_data]
        
        if not missing_perfect_fields:
            print("✅ All required fields present in perfect query response")
            print(f"   - Response length: {len(perfect_data.get('response', ''))} characters")
            print(f"   - AI Used: {perfect_data.get('ai_used')}")
            print(f"   - Agents Involved: {perfect_data.get('agents_involved')}")
            print(f"   - Processing Time: {perfect_data.get('processing_time', 0):.3f}s")
            print(f"   - Mode: {perfect_data.get('mode')}")
            print(f"   - System Status: {perfect_data.get('system_status')}")
        else:
            print(f"❌ Missing required fields: {missing_perfect_fields}")
            
        # Preview response
        perfect_preview = perfect_data.get('response', '')[:200] 
        print(f"   - Response Preview: {perfect_preview}{'...' if len(perfect_preview) >= 200 else ''}")
        
    else:
        print(f"❌ Perfect query endpoint failed (Status: {perfect_response.status_code})")
        print(f"   Error: {perfect_response.text}")
    
    print("\n" + "="*60 + "\n")
    
    # Summary
    chat_success = chat_response.status_code == 200 and 'ai_used' in chat_response.json()
    perfect_success = perfect_response.status_code == 200 and 'ai_used' in perfect_response.json()
    
    if chat_success and perfect_success:
        print("🎉 API Endpoints Test Results:")
        print("✅ Both endpoints returning proper response structure")
        print("✅ AI usage flags present and functional") 
        print("✅ Ready for UI integration")
        
        # Compare AI usage
        chat_ai = chat_response.json().get('ai_used', False)
        perfect_ai = perfect_response.json().get('ai_used', False)
        print(f"📊 AI Usage - Chat: {chat_ai}, Perfect: {perfect_ai}")
        
    else:
        print("❌ Some endpoints failed - UI may not display responses correctly")
        if not chat_success:
            print("   - Chat endpoint issues detected")
        if not perfect_success:
            print("   - Perfect query endpoint issues detected")

if __name__ == "__main__":
    test_api_endpoints()
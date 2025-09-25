#!/usr/bin/env python3
"""
Test API Response Format
Directly test the /travel/chat endpoint to see the exact response format
"""

import requests
import json
import sys

def test_api_response():
    """Test the actual API response format"""
    
    print("🧪 Testing /travel/chat API response format...")
    
    # Test data
    payload = {
        "user_id": 1234,
        "text": "I need help planning a trip to Paris"
    }
    
    try:
        print(f"📤 Sending request: {payload}")
        
        response = requests.post(
            "http://localhost:8000/travel/chat",
            json=payload,
            timeout=30
        )
        
        print(f"📡 Response status: {response.status_code}")
        print(f"📋 Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Response received successfully!")
            print(f"📊 Response structure:")
            for key, value in result.items():
                if isinstance(value, str) and len(value) > 100:
                    print(f"  - {key}: '{value[:100]}...' ({len(value)} chars)")
                else:
                    print(f"  - {key}: {value}")
            
            # Check if it matches the expected format for UI
            expected_fields = ['response', 'agents_involved', 'processing_time', 'user_id', 'ai_used']
            missing_fields = [field for field in expected_fields if field not in result]
            
            if missing_fields:
                print(f"⚠️ Missing expected fields: {missing_fields}")
            else:
                print(f"✅ All expected fields present for UI")
                
            # Test formatTravelResponse compatibility
            response_text = result.get('response', '')
            if response_text:
                print(f"🔄 Testing response text formatting:")
                print(f"  - Length: {len(response_text)}")
                print(f"  - Has markdown (**): {'**' in response_text}")
                print(f"  - Has lists (-): {response_text.count('- ') > 0}")
                print(f"  - First 200 chars: {response_text[:200]}")
                
        else:
            print(f"❌ Request failed: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed. Is the server running on localhost:8000?")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
        
    return True

def test_perfect_query():
    """Test the /perfect_query endpoint"""
    
    print("\n🚀 Testing /perfect_query API response format...")
    
    payload = {
        "user": "test_user",
        "user_id": 1234, 
        "question": "I need help planning a trip to Paris"
    }
    
    try:
        print(f"📤 Sending request: {payload}")
        
        response = requests.post(
            "http://localhost:8000/perfect_query",
            json=payload,
            timeout=30
        )
        
        print(f"📡 Response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Perfect query response received!")
            print(f"📊 Response structure:")
            for key, value in result.items():
                if isinstance(value, str) and len(value) > 100:
                    print(f"  - {key}: '{value[:100]}...' ({len(value)} chars)")
                else:
                    print(f"  - {key}: {value}")
        else:
            print(f"❌ Perfect query failed: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Perfect query error: {e}")

if __name__ == "__main__":
    print("🔍 API Response Format Test")
    print("=" * 50)
    
    if test_api_response():
        test_perfect_query()
    
    print("\n✅ Test completed")
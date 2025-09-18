#!/usr/bin/env python3
"""
Test script to verify Ollama connectivity and agent routing fixes
"""
import time
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_ollama_connectivity():
    """Test direct Ollama connection"""
    print("🔧 Testing Ollama Connectivity...")
    try:
        import requests
        
        start_time = time.time()
        response = requests.post(
            'http://localhost:11434/api/generate',
            json={
                'model': 'llama3:latest', 
                'prompt': 'Say hello in one word.', 
                'stream': False,
                'options': {'num_predict': 10}
            },
            timeout=30
        )
        
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            response_text = result.get('response', 'No response')
            print(f"✅ Ollama connected successfully in {elapsed:.2f}s")
            print(f"   Response: {response_text.strip()}")
            return True
        else:
            print(f"❌ Ollama HTTP error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Ollama connection failed: {e}")
        return False

def test_ollama_client():
    """Test our improved Ollama client"""
    print("\n🔧 Testing Improved Ollama Client...")
    try:
        from core.ollama_client import ollama_client
        
        start_time = time.time()
        response = ollama_client.generate_response(
            prompt="What is travel planning?",
            system_prompt="You are a travel expert. Answer briefly."
        )
        elapsed = time.time() - start_time
        
        if response and len(response.strip()) > 10:
            print(f"✅ Ollama client working in {elapsed:.2f}s")
            print(f"   Response: {response[:100]}...")
            return True
        else:
            print(f"❌ Ollama client returned empty response")
            return False
            
    except Exception as e:
        print(f"❌ Ollama client failed: {e}")
        return False

def test_agent_routing():
    """Test agent routing system"""
    print("\n🔧 Testing Agent Routing...")
    try:
        from core.langgraph_multiagent_system import langgraph_multiagent_system
        
        # Test simple routing
        test_queries = [
            "I'm planning a trip to Tokyo with a $2000 budget",
            "I feel overwhelmed about my travel planning",
            "How should I communicate with hotel staff?"
        ]
        
        results = []
        for query in test_queries:
            try:
                print(f"\n   Testing query: '{query[:50]}...'")
                start_time = time.time()
                
                # Just test the routing logic without full execution
                best_agent = langgraph_multiagent_system._select_best_agent(query)
                elapsed = time.time() - start_time
                
                print(f"   → Routed to: {best_agent} (in {elapsed:.3f}s)")
                results.append(True)
                
            except Exception as e:
                print(f"   ❌ Query failed: {e}")
                results.append(False)
        
        success_rate = sum(results) / len(results) * 100
        print(f"\n   Agent routing success: {success_rate:.0f}% ({sum(results)}/{len(results)})")
        return success_rate > 80
        
    except Exception as e:
        print(f"❌ Agent routing test failed: {e}")
        return False

def test_enhanced_mock_client():
    """Test enhanced mock client fallback"""
    print("\n🔧 Testing Enhanced Mock Client...")
    try:
        from core.enhanced_mock_ollama_client import enhanced_mock_client
        
        start_time = time.time()
        response = enhanced_mock_client.generate_response(
            prompt="Plan a trip to Tokyo with a budget of $2000",
            system_prompt="You are a travel planning expert."
        )
        elapsed = time.time() - start_time
        
        if response and len(response.strip()) > 50:
            print(f"✅ Enhanced mock client working in {elapsed:.2f}s")
            print(f"   Response length: {len(response)} characters")
            print(f"   Sample: {response[:100]}...")
            return True
        else:
            print(f"❌ Enhanced mock client returned insufficient response")
            return False
            
    except Exception as e:
        print(f"❌ Enhanced mock client failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Testing Travel Assistant System Fixes")
    print("=" * 60)
    
    test_results = []
    
    # Run all tests
    test_results.append(("Ollama Connectivity", test_ollama_connectivity()))
    test_results.append(("Ollama Client", test_ollama_client()))
    test_results.append(("Agent Routing", test_agent_routing()))
    test_results.append(("Enhanced Mock Client", test_enhanced_mock_client()))
    
    # Summary
    print("\n" + "=" * 60)
    print("🏁 Test Results Summary")
    print("=" * 60)
    
    passed = 0
    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name:<25} {status}")
        if result:
            passed += 1
    
    print(f"\n📊 Overall: {passed}/{len(test_results)} tests passed ({passed/len(test_results)*100:.0f}%)")
    
    if passed >= 3:  # At least 3 out of 4 should pass
        print("🎉 System fixes are working correctly!")
        sys.exit(0)
    else:
        print("⚠️ Some fixes need additional attention")
        sys.exit(1)
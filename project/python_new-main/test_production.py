#!/usr/bin/env python3

print("=== Testing Production Ollama Client ===")

try:
    from core.production_ollama_client import production_ollama_client
    print("✅ Production Ollama Client loaded successfully")
    
    status = production_ollama_client.get_connection_status()
    print(f"   - Status: {status['status']}")
    print(f"   - Model: {status['model']}")
    print(f"   - Available: {status['available']}")
    
    # Test real AI response generation
    print()
    print("🧠 Testing REAL AI Response Generation:")
    
    import time
    start_time = time.time()
    
    response = production_ollama_client.generate_response(
        prompt="I need help planning a 3-day trip to Korea for solo travel",
        system_prompt="You are a travel planning expert. Provide detailed, practical travel advice.",
        agent_name="TextTripAnalyzer"
    )
    
    elapsed = time.time() - start_time
    print(f"   - Response Time: {elapsed:.2f}s")
    print(f"   - Response Length: {len(response)} characters")
    print(f"   - Response Preview: {response[:150]}...")
    
    if "unable to access" in response or "experiencing technical" in response:
        print("   ⚠️ Got fallback response instead of AI")
    else:
        print("   ✅ Got REAL AI response!")
    
except Exception as e:
    print(f"❌ Production Ollama Client Error: {e}")

print()
print("🔧 Testing Enhanced LangGraph System:")

try:
    from core.fixed_langgraph_multiagent_system import fixed_langgraph_multiagent_system
    
    print(f"   - Ollama Client Type: {type(fixed_langgraph_multiagent_system.ollama_client).__name__}")
    
    # Test real AI processing
    result = fixed_langgraph_multiagent_system.process_request(
        user="test_user",
        user_id=7777,
        question="I am planning a solo trip to Seoul, Korea. Need budget advice and communication tips."
    )
    
    if result:
        print(f"   - Response Length: {len(result.get('response', ''))} chars")
        print(f"   - AI Used: {result.get('ai_used', False)}")
        print(f"   - Agents: {result.get('agents_involved', [])}")
        
        sample_response = result.get('response', '')[:200]
        if 'Seoul' in sample_response or 'Korea' in sample_response or 'budget' in sample_response.lower():
            print("   ✅ Response appears to be contextually relevant!")
            print(f"   - Sample Response: {sample_response}...")
        else:
            print("   ⚠️ Response may not be contextually relevant")
            print(f"   - Actual Response: {sample_response}...")
    
except Exception as e:
    print(f"❌ LangGraph Test Error: {e}")
    import traceback
    traceback.print_exc()
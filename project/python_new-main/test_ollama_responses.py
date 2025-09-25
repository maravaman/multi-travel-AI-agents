#!/usr/bin/env python3
"""
Test script to verify Ollama is generating real AI responses
"""

import sys
import os
import time
import logging

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

def test_ollama_direct():
    """Test direct Ollama API connection"""
    try:
        import requests
        
        # Test if Ollama is running
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get('models', [])
            print(f"✅ Ollama is running with {len(models)} models available:")
            for model in models[:3]:  # Show first 3 models
                print(f"   - {model['name']}")
        else:
            print(f"❌ Ollama returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Ollama connection failed: {e}")
        return False
    
    return True

def test_production_ollama_client():
    """Test the production Ollama client"""
    try:
        from core.production_ollama_client import production_ollama_client
        
        print("\n🧪 Testing Production Ollama Client...")
        
        # Test simple prompt
        test_prompt = "Plan a 3-day trip to Paris focusing on art and culture. Include must-see museums."
        
        print(f"Prompt: {test_prompt}")
        print("Generating response...")
        
        start_time = time.time()
        response = production_ollama_client.generate_response(
            prompt=test_prompt,
            system_prompt="You are a helpful travel assistant. Provide detailed, actionable travel advice.",
            agent_name="TextTripAnalyzer"
        )
        end_time = time.time()
        
        print(f"⏱️ Response generated in {end_time - start_time:.2f} seconds")
        print(f"📝 Response length: {len(response)} characters")
        
        # Check if it's a real AI response or fallback
        if "rich fallback" in response or "Production Ollama" in response or len(response) > 1000:
            if "🎯" in response or "🗺️" in response:
                print("⚠️ Response appears to be from fallback system (rich fallback)")
            else:
                print("✅ Response appears to be from real Ollama AI")
        else:
            print("✅ Response appears to be from real Ollama AI")
        
        print(f"\n📄 Response preview:\n{response[:300]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Production Ollama client test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_travel_endpoints():
    """Test travel endpoints to see if they use real AI"""
    try:
        from core.fixed_langgraph_multiagent_system import fixed_langgraph_multiagent_system
        
        print("\n🚀 Testing Travel Multi-Agent System...")
        
        test_query = "I'm planning a romantic getaway to Tuscany. What are the best hilltop towns to visit?"
        
        print(f"Query: {test_query}")
        print("Processing through travel agents...")
        
        start_time = time.time()
        result = fixed_langgraph_multiagent_system.process_request(
            user="test_user",
            user_id=12345,
            question=test_query
        )
        end_time = time.time()
        
        print(f"⏱️ Multi-agent response generated in {end_time - start_time:.2f} seconds")
        response_text = result.get('response', result.get('final_response', ''))
        print(f"📝 Response length: {len(response_text)} characters")
        
        # Check if AI was used
        ai_used = result.get('ai_used', False)
        agents_involved = result.get('agents_involved', [])
        
        print(f"🤖 AI Used: {ai_used}")
        print(f"👥 Agents Involved: {agents_involved}")
        
        if ai_used:
            print("✅ Real AI responses are being generated!")
        else:
            print("⚠️ System is using fallback responses")
        
        print(f"\n📄 Response preview:\n{response_text[:300]}...")
        
        return ai_used
        
    except Exception as e:
        print(f"❌ Travel endpoints test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🧪 Testing Ollama AI Response Generation")
    print("=" * 50)
    
    # Test 1: Direct Ollama connection
    print("\n1. Testing Direct Ollama Connection...")
    ollama_available = test_ollama_direct()
    
    # Test 2: Production Ollama client
    print("\n2. Testing Production Ollama Client...")
    production_works = test_production_ollama_client()
    
    # Test 3: Travel system integration
    print("\n3. Testing Travel System Integration...")
    travel_ai_works = test_travel_endpoints()
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 TEST SUMMARY:")
    print(f"   Ollama Server Available: {'✅' if ollama_available else '❌'}")
    print(f"   Production Client Works: {'✅' if production_works else '❌'}")
    print(f"   Travel AI Responses: {'✅' if travel_ai_works else '❌'}")
    
    if ollama_available and production_works and travel_ai_works:
        print("\n🎉 SUCCESS: System is generating real Ollama AI responses!")
    elif ollama_available and production_works:
        print("\n⚠️ PARTIAL: Ollama works but travel system may be using fallbacks")
    else:
        print("\n❌ ISSUES: System is not generating real AI responses")
        print("\n🔧 RECOMMENDATIONS:")
        if not ollama_available:
            print("   - Check if Ollama server is running: ollama serve")
            print("   - Verify Ollama models are installed: ollama list")
        if not production_works:
            print("   - Check timeout settings in production client")
            print("   - Verify model availability and compatibility")
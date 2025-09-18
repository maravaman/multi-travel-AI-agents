#!/usr/bin/env python3

from core.fixed_langgraph_multiagent_system import fixed_langgraph_multiagent_system

def test_system():
    print("🧪 Testing complete travel system with gemma2:2b...")
    
    # Test query
    query = "How should I ask my hotel about dietary restrictions?"
    
    try:
        result = fixed_langgraph_multiagent_system.process_request('test_user', 123, query)
        
        print(f"✅ Response: {result.get('response', '')[:200]}...")
        print(f"🤖 AI Used: {result.get('ai_used', False)}")
        print(f"🔧 Agents: {result.get('agents_involved', [])}")
        print(f"⏱️ Processing Time: {result.get('processing_time', 0):.2f}s")
        print(f"✨ Success: {result.get('success', False)}")
        
        if result.get('ai_used', False):
            print("🎉 SUCCESS: System is using real AI responses!")
        else:
            print("⚡ FALLBACK: Using intelligent responses (Ollama not available)")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_system()
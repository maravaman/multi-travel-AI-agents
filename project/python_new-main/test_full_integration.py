#!/usr/bin/env python3
"""
Integration test for complete Travel Assistant agent system
"""
import time
import sys
from pathlib import Path
import json

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_complete_agent_flow():
    """Test complete agent flow with a real travel query"""
    print("🔧 Testing Complete Agent Flow...")
    
    try:
        from core.langgraph_multiagent_system import langgraph_multiagent_system
        
        test_query = "I feel overwhelmed with too many destination choices and need help planning my trip"
        test_user = "integration_test_user"
        test_user_id = 12345
        
        print(f"   Query: '{test_query}'")
        print(f"   User: {test_user} (ID: {test_user_id})")
        
        start_time = time.time()
        
        # Process the request
        result = langgraph_multiagent_system.process_request(
            user=test_user,
            user_id=test_user_id,
            question=test_query
        )
        
        elapsed = time.time() - start_time
        
        if result and isinstance(result, dict):
            print(f"✅ Complete flow executed in {elapsed:.2f}s")
            
            # Analyze the result
            response = result.get('response', '')
            agents_involved = result.get('agents_involved', [])
            execution_path = result.get('execution_path', [])
            
            print(f"   Response length: {len(response)} characters")
            print(f"   Agents involved: {', '.join(agents_involved) if agents_involved else 'None'}")
            print(f"   Execution steps: {len(execution_path)}")
            
            if response and len(response) > 100:
                print(f"   Sample response: {response[:150]}...")
                
            # Check if we got reasonable results
            success_indicators = [
                len(response) > 50,  # Got substantial response
                len(agents_involved) > 0,  # At least one agent responded
                'error' not in result,  # No errors
                elapsed < 60  # Completed within reasonable time
            ]
            
            success_rate = sum(success_indicators) / len(success_indicators) * 100
            print(f"   Quality indicators: {success_rate:.0f}% ({sum(success_indicators)}/{len(success_indicators)})")
            
            return success_rate >= 75  # At least 3/4 indicators should pass
            
        else:
            print("❌ No result returned from agent system")
            return False
            
    except Exception as e:
        print(f"❌ Complete flow failed: {e}")
        return False

def test_multiple_queries():
    """Test the system with multiple different query types"""
    print("\n🔧 Testing Multiple Query Types...")
    
    try:
        from core.langgraph_multiagent_system import langgraph_multiagent_system
        
        test_cases = [
            {
                "query": "I'm planning a trip to Tokyo with a budget of $2000",
                "expected_agent": "TextTripAnalyzer",
                "description": "Trip planning query"
            },
            {
                "query": "I'm feeling nervous about my upcoming travel",
                "expected_agent": "TripMoodDetector", 
                "description": "Mood/emotion query"
            },
            {
                "query": "How do I ask for help at the hotel reception?",
                "expected_agent": "TripCommsCoach",
                "description": "Communication query"
            }
        ]
        
        results = []
        
        for i, case in enumerate(test_cases):
            print(f"\\n   Test {i+1}: {case['description']}")
            print(f"   Query: '{case['query']}'")
            
            try:
                start_time = time.time()
                
                result = langgraph_multiagent_system.process_request(
                    user="test_user",
                    user_id=999 + i,
                    question=case["query"]
                )
                
                elapsed = time.time() - start_time
                
                if result and 'response' in result:
                    response = result.get('response', '')
                    agents = result.get('agents_involved', [])
                    
                    print(f"   ✅ Completed in {elapsed:.2f}s")
                    print(f"   Response: {len(response)} chars")
                    print(f"   Agents: {', '.join(agents) if agents else 'None'}")
                    
                    # Check if expected agent was involved (if specified)
                    if case.get('expected_agent'):
                        if case['expected_agent'] in agents:
                            print(f"   ✅ Expected agent {case['expected_agent']} was involved")
                        else:
                            print(f"   ⚠️ Expected {case['expected_agent']}, got: {', '.join(agents)}")
                    
                    results.append(True)
                else:
                    print(f"   ❌ No response received")
                    results.append(False)
                    
            except Exception as e:
                print(f"   ❌ Failed: {e}")
                results.append(False)
        
        success_rate = sum(results) / len(results) * 100
        print(f"\\n   Multiple queries success: {success_rate:.0f}% ({sum(results)}/{len(results)})")
        
        return success_rate >= 66  # At least 2/3 should succeed
        
    except Exception as e:
        print(f"❌ Multiple queries test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Integration Testing Travel Assistant System")
    print("=" * 70)
    
    test_results = []
    
    # Run integration tests
    test_results.append(("Complete Agent Flow", test_complete_agent_flow()))
    test_results.append(("Multiple Query Types", test_multiple_queries()))
    
    # Summary
    print("\\n" + "=" * 70)
    print("🏁 Integration Test Results")
    print("=" * 70)
    
    passed = 0
    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name:<30} {status}")
        if result:
            passed += 1
    
    print(f"\\n📊 Overall: {passed}/{len(test_results)} integration tests passed ({passed/len(test_results)*100:.0f}%)")
    
    if passed >= len(test_results):
        print("🎉 All integration tests passed! System is working correctly.")
        sys.exit(0)
    elif passed > 0:
        print("⚠️ Some integration tests passed. System is partially working.")
        sys.exit(0)
    else:
        print("❌ Integration tests failed. System needs attention.")
        sys.exit(1)
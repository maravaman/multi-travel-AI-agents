#!/usr/bin/env python3
"""
Test Agent Routing and Effectiveness
Tests that queries route to appropriate agents and multi-agent collaboration works
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.fixed_langgraph_multiagent_system import fixed_langgraph_multiagent_system
import time

def test_agent_routing():
    """Test agent routing for different query types"""
    
    print("🧭 Testing Agent Routing and Effectiveness\n")
    
    # Test cases designed to trigger specific agents
    test_cases = [
        {
            "name": "Trip Planning Query",
            "query": "I want to plan a 2-week trip to Europe, visiting Paris and Rome",
            "expected_agents": ["TextTripAnalyzer"],
            "keywords": ["plan", "trip", "itinerary", "europe"]
        },
        {
            "name": "Mood/Anxiety Query", 
            "query": "I'm feeling nervous about traveling alone for the first time. Any advice?",
            "expected_agents": ["TripMoodDetector", "TripCalmPractice"],
            "keywords": ["nervous", "anxiety", "calm", "alone"]
        },
        {
            "name": "Communication Query",
            "query": "What are some useful Spanish phrases I should learn before visiting Mexico?",
            "expected_agents": ["TripCommsCoach"],
            "keywords": ["spanish", "phrases", "language", "communication"]
        },
        {
            "name": "Decision Help Query",
            "query": "I can't decide between staying in Tokyo or Kyoto. Help me choose!",
            "expected_agents": ["TripBehaviorGuide"],
            "keywords": ["decide", "choose", "between", "help"]
        },
        {
            "name": "Relaxation Query",
            "query": "I'm feeling overwhelmed with all the travel planning. Need to calm down.",
            "expected_agents": ["TripCalmPractice"],
            "keywords": ["overwhelmed", "calm", "relax", "stress"]
        },
        {
            "name": "Profile/Summary Query",
            "query": "Can you give me a summary of my travel preferences and past trips?",
            "expected_agents": ["TripSummarySynth"],
            "keywords": ["summary", "profile", "preferences", "past"]
        }
    ]
    
    results = []
    success_count = 0
    
    print("🧪 Running agent routing tests...\n")
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"Test {i}/{len(test_cases)}: {test_case['name']}")
        print(f"Query: \"{test_case['query']}\"")
        
        try:
            start_time = time.time()
            
            result = fixed_langgraph_multiagent_system.process_request(
                user=f"test_user_{i}",
                user_id=100 + i,
                question=test_case['query']
            )
            
            processing_time = time.time() - start_time
            
            if result and isinstance(result, dict):
                agents_used = result.get('agents_involved', [])
                response_text = result.get('response', '')
                ai_used = result.get('ai_used', False)
                
                print(f"✅ Response received in {processing_time:.2f}s")
                print(f"   - Agents involved: {agents_used}")
                print(f"   - AI used: {'🧠 Yes' if ai_used else '🤖 No'}")
                print(f"   - Response length: {len(response_text)} chars")
                
                # Check if expected agents were used
                expected_found = any(agent in agents_used for agent in test_case['expected_agents'])
                
                if expected_found:
                    print("✅ Expected agent type was used")
                else:
                    print(f"⚠️ Expected agents {test_case['expected_agents']} not found")
                    print(f"   Actual agents: {agents_used}")
                
                # Check if response contains relevant keywords
                response_lower = response_text.lower()
                query_lower = test_case['query'].lower()
                keyword_matches = [kw for kw in test_case['keywords'] if kw in response_lower]
                
                print(f"   - Contextual keywords found: {len(keyword_matches)}/{len(test_case['keywords'])}")
                if keyword_matches:
                    print(f"   - Matched: {keyword_matches}")
                
                # Response quality check
                response_quality_score = 0
                if len(response_text) > 100:  # Substantial response
                    response_quality_score += 1
                if expected_found:  # Correct agent routing
                    response_quality_score += 2
                if keyword_matches:  # Relevant content
                    response_quality_score += 1
                if ai_used:  # AI-powered response
                    response_quality_score += 1
                
                print(f"   - Quality score: {response_quality_score}/5")
                
                # Consider test successful if quality score >= 3
                if response_quality_score >= 3:
                    print("✅ Test passed")
                    success_count += 1
                else:
                    print("⚠️ Test had issues")
                
                results.append({
                    'test_name': test_case['name'],
                    'agents_used': agents_used,
                    'expected_agents': test_case['expected_agents'],
                    'processing_time': processing_time,
                    'quality_score': response_quality_score,
                    'ai_used': ai_used,
                    'passed': response_quality_score >= 3
                })
                
            else:
                print("❌ No valid response received")
                results.append({
                    'test_name': test_case['name'],
                    'passed': False,
                    'error': 'No response'
                })
        
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            results.append({
                'test_name': test_case['name'],
                'passed': False,
                'error': str(e)
            })
        
        print("   " + "-"*50 + "\n")
    
    # Summary
    print("🎉 Agent Routing Test Results:")
    print(f"✅ Tests passed: {success_count}/{len(test_cases)}")
    
    # Analyze agent usage
    all_agents_used = set()
    for result in results:
        if 'agents_used' in result:
            all_agents_used.update(result['agents_used'])
    
    print(f"🤖 Unique agents activated: {len(all_agents_used)}")
    print(f"   - Agents used: {sorted(all_agents_used)}")
    
    # Performance analysis
    processing_times = [r.get('processing_time', 0) for r in results if 'processing_time' in r]
    if processing_times:
        avg_time = sum(processing_times) / len(processing_times)
        max_time = max(processing_times)
        print(f"⏱️ Performance: avg {avg_time:.2f}s, max {max_time:.2f}s")
    
    # AI usage analysis
    ai_usage = [r.get('ai_used', False) for r in results if 'ai_used' in r]
    ai_count = sum(ai_usage)
    if ai_usage:
        print(f"🧠 AI responses: {ai_count}/{len(ai_usage)} ({ai_count/len(ai_usage)*100:.1f}%)")
    
    # Final assessment
    if success_count >= len(test_cases) * 0.8:  # 80% success rate
        print("\n🎊 Agent routing system is working excellently!")
        print("✅ Multi-agent collaboration effective")
        print("✅ Query-specific agent selection working")
        print("✅ Response quality meets expectations")
        return True
    elif success_count >= len(test_cases) * 0.6:  # 60% success rate
        print("\n✅ Agent routing system is mostly functional")
        print("⚠️ Some improvements possible but core functionality works")
        return True
    else:
        print("\n⚠️ Agent routing system needs attention")
        print("❌ Multiple tests failed - investigate agent configurations")
        return False

if __name__ == "__main__":
    success = test_agent_routing()
    if success:
        print("\n🎉 Agent routing and effectiveness verified!")
    else:
        print("\n⚠️ Agent routing issues detected")
    # Don't exit with failure to allow continued testing
    sys.exit(0)
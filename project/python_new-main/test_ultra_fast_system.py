#!/usr/bin/env python3
"""
Test Ultra-Fast LangGraph Multi-Agent System
Comprehensive testing for routing, performance, and agent functionality
"""

import time
import sys
from pathlib import Path

# Ensure we can import our modules
sys.path.insert(0, str(Path(__file__).parent))

def test_ultra_fast_system():
    """Test the ultra-fast LangGraph system comprehensively"""
    print("🚀 Testing Ultra-Fast LangGraph Multi-Agent System")
    print("=" * 60)
    
    try:
        # Import the ultra-fast system
        from ultra_fast_langgraph_system import ultra_fast_system
        print("✅ Ultra-Fast LangGraph system imported successfully")
    except Exception as e:
        print(f"❌ Failed to import system: {e}")
        return False
    
    # Test queries covering different agents
    test_queries = [
        {
            "query": "Plan a trip to Tokyo with $2000 budget",
            "expected_agent": "TextTripAnalyzer",
            "description": "Budget trip planning"
        },
        {
            "query": "I'm feeling excited but nervous about my first solo travel",
            "expected_agent": "TripMoodDetector", 
            "description": "Mood and emotion analysis"
        },
        {
            "query": "How do I talk to hotel staff to get room upgrades?",
            "expected_agent": "TripCommsCoach",
            "description": "Communication coaching"
        },
        {
            "query": "I'm stuck choosing between Barcelona and Amsterdam, help me decide",
            "expected_agent": "TripBehaviorGuide",
            "description": "Decision support"
        },
        {
            "query": "I'm overwhelmed with all this travel planning and feel anxious",
            "expected_agent": "TripCalmPractice",
            "description": "Stress relief and calming"
        },
        {
            "query": "Give me a summary of all travel planning steps",
            "expected_agent": "TripSummarySynth",
            "description": "Summary synthesis"
        }
    ]
    
    print(f"\n🧪 Running {len(test_queries)} ultra-fast test scenarios...")
    print("-" * 60)
    
    results = []
    total_start_time = time.time()
    
    for i, test in enumerate(test_queries, 1):
        print(f"\n⚡ Test {i}: {test['description']}")
        print(f"Query: {test['query']}")
        print(f"Expected Agent: {test['expected_agent']}")
        
        start_time = time.time()
        
        try:
            # Process with ultra-fast system
            result = ultra_fast_system.process_ultra_fast(
                user="test_user",
                user_id=123,
                question=test['query']
            )
            
            elapsed = time.time() - start_time
            
            # Extract results
            response = result.get('response', 'No response')
            agents_involved = result.get('agents_involved', [])
            processing_time = result.get('processing_time', elapsed)
            
            # Determine success
            success = len(response) > 20 and 'error' not in result
            
            # Performance rating
            if processing_time < 1.0:
                performance = "⚡ ULTRA-FAST"
            elif processing_time < 3.0:
                performance = "🔥 FAST"
            elif processing_time < 5.0:
                performance = "✅ GOOD"
            else:
                performance = "⚠️ SLOW"
            
            print(f"Status: {'✅ SUCCESS' if success else '❌ FAILED'}")
            print(f"Processing Time: {processing_time:.2f}s ({performance})")
            print(f"Agents Involved: {', '.join(agents_involved)}")
            print(f"Response Length: {len(response)} chars")
            print(f"Response Preview: {response[:100]}{'...' if len(response) > 100 else ''}")
            
            results.append({
                'test': i,
                'description': test['description'],
                'success': success,
                'processing_time': processing_time,
                'agents': agents_involved,
                'response_length': len(response),
                'performance_rating': performance
            })
            
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"❌ FAILED: {e}")
            print(f"Processing Time: {elapsed:.2f}s")
            
            results.append({
                'test': i,
                'description': test['description'],
                'success': False,
                'processing_time': elapsed,
                'error': str(e),
                'performance_rating': "❌ ERROR"
            })
    
    total_elapsed = time.time() - total_start_time
    
    # Performance summary
    print("\n" + "=" * 60)
    print("🏆 ULTRA-FAST LANGGRAPH SYSTEM TEST RESULTS")
    print("=" * 60)
    
    successful_tests = [r for r in results if r['success']]
    failed_tests = [r for r in results if not r['success']]
    
    print(f"Total Tests: {len(results)}")
    print(f"Successful: {len(successful_tests)} ✅")
    print(f"Failed: {len(failed_tests)} ❌")
    print(f"Success Rate: {len(successful_tests)/len(results)*100:.1f}%")
    print(f"Total Processing Time: {total_elapsed:.2f}s")
    
    if successful_tests:
        avg_time = sum(r['processing_time'] for r in successful_tests) / len(successful_tests)
        fastest_time = min(r['processing_time'] for r in successful_tests)
        slowest_time = max(r['processing_time'] for r in successful_tests)
        avg_response_length = sum(r['response_length'] for r in successful_tests) / len(successful_tests)
        
        print(f"\n📊 Performance Metrics:")
        print(f"Average Response Time: {avg_time:.2f}s")
        print(f"Fastest Response: {fastest_time:.2f}s")
        print(f"Slowest Response: {slowest_time:.2f}s")
        print(f"Average Response Length: {avg_response_length:.0f} characters")
        
        # Performance distribution
        ultra_fast = len([r for r in successful_tests if r['processing_time'] < 1.0])
        fast = len([r for r in successful_tests if 1.0 <= r['processing_time'] < 3.0])
        good = len([r for r in successful_tests if 3.0 <= r['processing_time'] < 5.0])
        slow = len([r for r in successful_tests if r['processing_time'] >= 5.0])
        
        print(f"\n⚡ Performance Distribution:")
        print(f"Ultra-Fast (<1s): {ultra_fast}")
        print(f"Fast (1-3s): {fast}")
        print(f"Good (3-5s): {good}")
        print(f"Slow (>5s): {slow}")
    
    if failed_tests:
        print(f"\n❌ Failed Test Details:")
        for result in failed_tests:
            print(f"Test {result['test']}: {result['description']}")
            if 'error' in result:
                print(f"  Error: {result['error']}")
    
    # Overall assessment
    print(f"\n🎯 Overall System Assessment:")
    if len(successful_tests) == len(results):
        if avg_time < 2.0:
            assessment = "🏆 EXCEPTIONAL - Ultra-fast and reliable!"
        elif avg_time < 5.0:
            assessment = "🔥 EXCELLENT - Fast and reliable!"
        else:
            assessment = "✅ GOOD - Reliable but could be faster"
    elif len(successful_tests) >= len(results) * 0.8:
        assessment = "⚠️ FAIR - Mostly working, needs optimization"
    else:
        assessment = "❌ POOR - Needs significant fixes"
    
    print(assessment)
    
    return len(successful_tests) == len(results)

def test_routing_accuracy():
    """Test agent routing accuracy"""
    print("\n🎯 Testing Agent Routing Accuracy")
    print("-" * 40)
    
    try:
        from ultra_fast_langgraph_system import ultra_fast_system
        
        # Test routing with specific keywords
        routing_tests = [
            ("I need help planning my trip budget", "TextTripAnalyzer"),
            ("I'm feeling anxious about traveling", "TripCalmPractice"),
            ("How do I communicate with locals?", "TripCommsCoach"),
            ("I can't decide where to go", "TripBehaviorGuide"),
            ("I'm excited but also nervous", "TripMoodDetector"),
            ("Give me an overview of everything", "TripSummarySynth"),
        ]
        
        correct_routes = 0
        
        for query, expected_agent in routing_tests:
            # Test internal routing
            selected_agent = ultra_fast_system._select_ultra_fast_agent(query.lower())
            
            if selected_agent == expected_agent:
                print(f"✅ '{query}' → {selected_agent}")
                correct_routes += 1
            else:
                print(f"❌ '{query}' → {selected_agent} (expected {expected_agent})")
        
        accuracy = correct_routes / len(routing_tests) * 100
        print(f"\n🎯 Routing Accuracy: {accuracy:.1f}% ({correct_routes}/{len(routing_tests)})")
        
        return accuracy >= 80.0  # At least 80% accuracy
        
    except Exception as e:
        print(f"❌ Routing test failed: {e}")
        return False

def test_fallback_system():
    """Test fallback system reliability"""
    print("\n🛡️ Testing Fallback System")
    print("-" * 30)
    
    try:
        from ultra_fast_langgraph_system import ultra_fast_system
        
        # Test with various fallback scenarios
        fallback_tests = [
            "",  # Empty query
            "   ",  # Whitespace only
            "xyz123nonsense",  # Nonsense query
            "a" * 1000,  # Very long query
        ]
        
        fallback_success = 0
        
        for i, query in enumerate(fallback_tests, 1):
            try:
                result = ultra_fast_system.process_ultra_fast("test", 999, query)
                response = result.get('response', '')
                
                if len(response) > 10:  # Got some reasonable response
                    print(f"✅ Fallback {i}: Got response ({len(response)} chars)")
                    fallback_success += 1
                else:
                    print(f"❌ Fallback {i}: Response too short")
                    
            except Exception as e:
                print(f"❌ Fallback {i}: Exception {e}")
        
        success_rate = fallback_success / len(fallback_tests) * 100
        print(f"\n🛡️ Fallback Success Rate: {success_rate:.1f}%")
        
        return success_rate >= 100.0  # Should handle all fallback cases
        
    except Exception as e:
        print(f"❌ Fallback test failed: {e}")
        return False

def main():
    """Run all ultra-fast system tests"""
    print("🚀 ULTRA-FAST LANGGRAPH SYSTEM - COMPREHENSIVE TEST SUITE")
    print("=" * 70)
    
    # Run all tests
    test_results = []
    
    print("\n1️⃣ SYSTEM FUNCTIONALITY TEST")
    test_results.append(test_ultra_fast_system())
    
    print("\n2️⃣ ROUTING ACCURACY TEST") 
    test_results.append(test_routing_accuracy())
    
    print("\n3️⃣ FALLBACK RELIABILITY TEST")
    test_results.append(test_fallback_system())
    
    # Final summary
    print("\n" + "=" * 70)
    print("🏆 FINAL TEST RESULTS")
    print("=" * 70)
    
    passed_tests = sum(test_results)
    total_tests = len(test_results)
    
    test_names = [
        "System Functionality",
        "Routing Accuracy", 
        "Fallback Reliability"
    ]
    
    for i, (name, result) in enumerate(zip(test_names, test_results)):
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{name}: {status}")
    
    overall_success = passed_tests / total_tests * 100
    print(f"\nOverall Success Rate: {overall_success:.1f}% ({passed_tests}/{total_tests})")
    
    if overall_success == 100.0:
        print("🏆 ALL TESTS PASSED! Ultra-Fast LangGraph System is ready for production!")
    elif overall_success >= 80.0:
        print("🔥 Most tests passed! System is functional with minor issues.")
    else:
        print("⚠️ System needs attention. Some critical tests failed.")
    
    return overall_success == 100.0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
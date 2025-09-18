#!/usr/bin/env python3
"""
Ultra-Fast Travel AI System - Production Startup Script
Optimized for sub-3-second responses with perfect multi-agent orchestration
"""

import os
import sys
import time
import logging
from pathlib import Path

# Configure production logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ultra_fast_travel_system.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def setup_environment():
    """Setup optimized environment for ultra-fast performance"""
    logger.info("🚀 Setting up Ultra-Fast Travel AI System environment...")
    
    # Performance environment variables
    os.environ.update({
        'PYTHONOPTIMIZE': '1',  # Enable optimizations
        'PYTHONUNBUFFERED': '1',  # Unbuffered output
        'LANGGRAPH_LOG_LEVEL': 'WARNING',  # Reduce log noise
        'OLLAMA_TIMEOUT': '5',  # 5-second Ollama timeout
        'SYSTEM_MODE': 'ULTRA_FAST',  # Ultra-fast mode
    })
    
    # Add current directory to Python path
    current_dir = Path(__file__).parent.absolute()
    if str(current_dir) not in sys.path:
        sys.path.insert(0, str(current_dir))
    
    logger.info("✅ Environment configured for ultra-fast performance")

def check_system_readiness():
    """Check if all system components are ready"""
    logger.info("🔍 Checking system readiness...")
    
    checks = []
    
    # Check ultra-fast LangGraph system
    try:
        from ultra_fast_langgraph_system import ultra_fast_system
        checks.append(("Ultra-Fast LangGraph System", True, "Ready"))
    except Exception as e:
        checks.append(("Ultra-Fast LangGraph System", False, str(e)))
    
    # Check Ollama client
    try:
        from ultra_fast_ollama import ultra_fast_ollama
        connectivity = ultra_fast_ollama._make_ultra_fast_request("test", "Respond with 'OK'")
        if connectivity:
            checks.append(("Ollama Client", True, "Connected"))
        else:
            checks.append(("Ollama Client", False, "No response - will use fallbacks"))
    except Exception as e:
        checks.append(("Ollama Client", False, f"Error: {e} - will use fallbacks"))
    
    # Check agent configuration
    try:
        config_path = Path("core/agents.json")
        if config_path.exists():
            checks.append(("Agent Configuration", True, "Found"))
        else:
            checks.append(("Agent Configuration", False, "Using built-in fallback config"))
    except Exception as e:
        checks.append(("Agent Configuration", False, str(e)))
    
    # Display readiness status
    logger.info("📊 System Readiness Report:")
    all_ready = True
    for component, status, message in checks:
        status_icon = "✅" if status else "⚠️" 
        logger.info(f"  {status_icon} {component}: {message}")
        if not status:
            all_ready = False
    
    return all_ready

def performance_test():
    """Run quick performance test"""
    logger.info("⚡ Running performance test...")
    
    try:
        from ultra_fast_langgraph_system import ultra_fast_system
        
        test_queries = [
            "Plan a quick trip to Paris",
            "I'm nervous about traveling alone",
            "Help me decide between two destinations"
        ]
        
        total_time = 0
        successful_tests = 0
        
        for i, query in enumerate(test_queries, 1):
            start_time = time.time()
            try:
                result = ultra_fast_system.process_ultra_fast("system_test", 999, query)
                elapsed = time.time() - start_time
                total_time += elapsed
                
                if result.get('response') and len(result['response']) > 10:
                    successful_tests += 1
                    logger.info(f"  ⚡ Test {i}: {elapsed:.2f}s - SUCCESS")
                else:
                    logger.warning(f"  ❌ Test {i}: {elapsed:.2f}s - FAILED (no response)")
                    
            except Exception as e:
                elapsed = time.time() - start_time
                total_time += elapsed
                logger.error(f"  ❌ Test {i}: {elapsed:.2f}s - ERROR: {e}")
        
        avg_time = total_time / len(test_queries)
        success_rate = successful_tests / len(test_queries) * 100
        
        logger.info(f"📊 Performance Results:")
        logger.info(f"  Average Response Time: {avg_time:.2f}s")
        logger.info(f"  Success Rate: {success_rate:.1f}% ({successful_tests}/{len(test_queries)})")
        
        if avg_time < 5.0 and success_rate >= 100.0:
            logger.info("🏆 Performance test PASSED - System ready for production!")
            return True
        else:
            logger.warning("⚠️ Performance test FAILED - System may be slow")
            return False
            
    except Exception as e:
        logger.error(f"❌ Performance test failed: {e}")
        return False

def start_interactive_mode():
    """Start interactive mode for testing"""
    logger.info("🎯 Starting Ultra-Fast Travel AI Interactive Mode")
    print("\n" + "="*60)
    print("🚀 ULTRA-FAST TRAVEL AI SYSTEM - INTERACTIVE MODE")
    print("="*60)
    print("💡 Tips:")
    print("  - Ask travel questions for instant expert responses")
    print("  - Type 'exit' or 'quit' to stop")
    print("  - Type 'help' for example queries")
    print("  - Average response time: ~3 seconds")
    print("-" * 60)
    
    try:
        from ultra_fast_langgraph_system import ultra_fast_system
        
        while True:
            try:
                query = input("\n🗣️  Your travel question: ").strip()
                
                if not query:
                    continue
                
                if query.lower() in ['exit', 'quit', 'q']:
                    print("👋 Goodbye! Safe travels!")
                    break
                
                if query.lower() == 'help':
                    print("\n💡 Example queries to try:")
                    print("  - Plan a 5-day trip to Tokyo with $1500 budget")
                    print("  - I'm nervous about my first solo travel")
                    print("  - How do I ask for hotel room upgrades?")
                    print("  - Help me choose between Paris and Rome")
                    print("  - I'm overwhelmed with travel planning")
                    print("  - Give me a summary of travel planning steps")
                    continue
                
                print("⚡ Processing...")
                start_time = time.time()
                
                result = ultra_fast_system.process_ultra_fast("interactive_user", 1, query)
                elapsed = time.time() - start_time
                
                response = result.get('response', 'No response generated')
                agents = result.get('agents_involved', [])
                
                print(f"\n🎯 Response (by {', '.join(agents)} in {elapsed:.2f}s):")
                print("-" * 50)
                print(response)
                print("-" * 50)
                
            except KeyboardInterrupt:
                print("\n👋 Interrupted. Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                logger.error(f"Interactive mode error: {e}")
    
    except Exception as e:
        logger.error(f"Failed to start interactive mode: {e}")
        print(f"❌ Could not start interactive mode: {e}")

def start_api_server():
    """Start API server mode (placeholder for future implementation)"""
    print("🌐 API Server mode coming soon!")
    print("For now, use interactive mode or integrate directly with ultra_fast_langgraph_system.py")

def main():
    """Main startup function"""
    print("🚀 ULTRA-FAST TRAVEL AI SYSTEM - PRODUCTION STARTUP")
    print("=" * 60)
    
    # Setup environment
    setup_environment()
    
    # Check system readiness
    if not check_system_readiness():
        logger.warning("⚠️ Some components not fully ready - system will use fallbacks")
    
    # Run performance test
    if not performance_test():
        logger.warning("⚠️ Performance test had issues - system may be slow")
        user_input = input("\nContinue anyway? (y/n): ").lower()
        if user_input != 'y':
            logger.info("Startup cancelled by user")
            return
    
    # Choose mode
    print("\n🎯 Choose startup mode:")
    print("1. Interactive Mode (recommended for testing)")
    print("2. API Server Mode (coming soon)")
    print("3. Exit")
    
    try:
        choice = input("\nEnter choice (1-3): ").strip()
        
        if choice == '1':
            start_interactive_mode()
        elif choice == '2':
            start_api_server()
        elif choice == '3':
            print("👋 Goodbye!")
        else:
            print("❌ Invalid choice. Starting interactive mode by default.")
            start_interactive_mode()
            
    except KeyboardInterrupt:
        print("\n👋 Startup interrupted. Goodbye!")
    except Exception as e:
        logger.error(f"Startup error: {e}")
        print(f"❌ Startup error: {e}")

if __name__ == "__main__":
    main()
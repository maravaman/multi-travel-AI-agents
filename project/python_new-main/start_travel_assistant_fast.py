#!/usr/bin/env python3
"""
Performance-Optimized Travel Assistant Startup Script
Fast startup with immediate fallback and optimized routing
"""
import os
import sys
import time
import logging
from pathlib import Path

def setup_fast_logging():
    """Setup optimized logging for performance"""
    logging.basicConfig(
        level=logging.WARNING,  # Reduce log verbosity for performance
        format='%(levelname)s:%(name)s: %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )

def start_travel_assistant():
    """Start the Travel Assistant with performance optimizations"""
    
    print("🚀 Starting Performance-Optimized Travel Assistant")
    print("=" * 70)
    
    setup_fast_logging()
    
    # Set performance environment variables
    os.environ['OLLAMA_TIMEOUT'] = '5'  # Fast timeout
    os.environ['OLLAMA_CONNECTION_TIMEOUT'] = '2'  # Quick connection
    os.environ['OLLAMA_READ_TIMEOUT'] = '5'  # Fast read
    os.environ['OLLAMA_MAX_RETRIES'] = '1'  # Minimal retries for speed
    os.environ['TRAVEL_CHAT_SLA_SECONDS'] = '5'  # Reasonable SLA
    
    print("🔧 Configuration:")
    print(f"   📡 Ollama Timeout: {os.environ['OLLAMA_TIMEOUT']}s")
    print(f"   ⚡ Chat SLA: {os.environ['TRAVEL_CHAT_SLA_SECONDS']}s") 
    print(f"   🔄 Max Retries: {os.environ['OLLAMA_MAX_RETRIES']}")
    
    # Quick system checks
    print("\n🔍 System Checks:")
    
    # Check Ollama availability
    try:
        import requests
        start_check = time.time()
        response = requests.get('http://localhost:11434/api/version', timeout=2)
        check_time = time.time() - start_check
        
        if response.status_code == 200:
            print(f"   ✅ Ollama available (responded in {check_time:.2f}s)")
        else:
            print(f"   ⚠️ Ollama responding with status {response.status_code}")
    except Exception as e:
        print(f"   ⚠️ Ollama not available, will use fallback: {e}")
    
    # Check Redis
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0, socket_timeout=1)
        r.ping()
        print("   ✅ Redis available")
    except Exception as e:
        print(f"   ⚠️ Redis not available: {e}")
    
    # Check MySQL  
    try:
        import mysql.connector
        conn = mysql.connector.connect(
            host='localhost',
            port=3306,
            user='root',
            database='travel_assistant',
            connect_timeout=2
        )
        conn.close()
        print("   ✅ MySQL available")
    except Exception as e:
        print(f"   ⚠️ MySQL connection issue: {e}")
    
    print("\n🌐 Starting Web Server...")
    
    try:
        # Import after environment setup
        from config import Config
        
        # Start the FastAPI server with optimized settings
        import uvicorn
        
        config_params = {
            "app": "api.main:app",
            "host": "0.0.0.0",
            "port": Config.APP_PORT,
            "log_level": "warning",  # Reduced logging for performance
            "access_log": False,     # Disable access logs for speed
            "workers": 1,           # Single worker for development
            "loop": "auto",         # Auto-select best event loop
            "http": "auto",         # Auto-select best HTTP implementation
            "reload": False         # Disable reload for stability
        }
        
        print(f"   🌐 Server: http://localhost:{Config.APP_PORT}")
        print(f"   📖 API Docs: http://localhost:{Config.APP_PORT}/docs")
        print(f"   ⚡ Performance Mode: Enabled")
        print("\n   🛑 Press Ctrl+C to stop")
        print("=" * 70)
        
        # Start the server
        uvicorn.run(**config_params)
        
    except KeyboardInterrupt:
        print("\n\n🛑 Travel Assistant stopped by user")
        print("Thank you for using the Travel Assistant!")
    except Exception as e:
        print(f"\n❌ Startup failed: {e}")
        print("\nTrying fallback startup...")
        
        # Fallback to basic startup
        try:
            import subprocess
            subprocess.run([
                sys.executable, "-m", "uvicorn",
                "api.main:app",
                "--host", "0.0.0.0",
                "--port", str(Config.APP_PORT),
                "--log-level", "warning"
            ])
        except Exception as fallback_error:
            print(f"❌ Fallback startup also failed: {fallback_error}")
            return False
    
    return True

if __name__ == "__main__":
    print("🎯 Travel Assistant - Performance Mode")
    print("Optimized for fast startup and reliable fallbacks")
    print()
    
    success = start_travel_assistant()
    sys.exit(0 if success else 1)
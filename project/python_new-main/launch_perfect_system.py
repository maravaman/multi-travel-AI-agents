#!/usr/bin/env python3
"""
Perfect LangGraph Travel System Launcher
Starts the web server with perfect multi-agent integration
"""

import os
import sys
import subprocess
import time

def check_dependencies():
    """Check if required dependencies are installed"""
    required_packages = [
        'fastapi',
        'uvicorn', 
        'langgraph',
        'langchain',
        'pydantic'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ Missing required packages:")
        for pkg in missing_packages:
            print(f"   - {pkg}")
        print("\n💡 Install with: pip install " + " ".join(missing_packages))
        return False
    
    return True

def launch_system():
    """Launch the perfect LangGraph travel system"""
    
    # Import configuration
    try:
        from config import Config
        config = Config()
        config.validate_config()
    except ImportError:
        print("❌ Configuration system not available - using defaults")
        config = None
    
    print("🚀 PERFECT LANGGRAPH TRAVEL SYSTEM LAUNCHER")
    print("=" * 80)
    
    # Check dependencies first
    print("🔍 Checking dependencies...")
    if not check_dependencies():
        return False
    
    print("✅ All dependencies found!")
    
    # Show system info
    print("\n📋 System Information:")
    print(f"   🐍 Python: {sys.version}")
    print(f"   📁 Working Directory: {os.getcwd()}")
    
    if config:
        host = config.APP_HOST
        port = config.APP_PORT
        print(f"   🌐 Server URL: http://{host}:{port}")
        print(f"   📖 API Docs: http://{host}:{port}/docs")
    else:
        host = "localhost"
        port = "8000"
        print(f"   🌐 Server URL: http://{host}:{port}")
        print(f"   📖 API Docs: http://{host}:{port}/docs")
    
    # Show available modes
    print("\n🎯 Available Modes:")
    print("   💬 Chat Mode: Quick travel questions (< 3s)")
    print("   📝 Recording Mode: Full transcript analysis (< 60s)")
    print("   🚀 Perfect LangGraph: Ultra-fast multi-agent (< 3s)")
    
    print("\n⚡ Starting Perfect LangGraph System...")
    print("=" * 80)
    
    try:
        # Run the FastAPI server
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        
        # Use configuration values
        host_arg = "0.0.0.0"
        port_arg = str(port)
        
        cmd = [
            sys.executable, "-m", "uvicorn",
            "api.main:app",
            "--host", host_arg,
            "--port", port_arg,
            "--reload",
            "--log-level", "info"
        ]
        
        print(f"🌐 Server starting at http://{host}:{port}")
        print("📱 Perfect LangGraph mode available in web interface")
        print("🛑 Press Ctrl+C to stop the server")
        print("=" * 80)
        
        # Launch the server
        subprocess.run(cmd)
        
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except FileNotFoundError:
        print("❌ Could not find api.main module")
        print("💡 Make sure you're running from the correct directory")
    except Exception as e:
        print(f"❌ Server failed to start: {e}")
        print("💡 Check the error details above and system configuration")

if __name__ == "__main__":
    print("🚀 Starting Travel AI System...")
    print("=" * 50)
    launch_system()

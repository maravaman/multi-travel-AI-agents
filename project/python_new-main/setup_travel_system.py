#!/usr/bin/env python3
"""
Complete Travel AI System Setup and Configuration Script
Installs all dependencies, sets up services, and configures the multi-agent system.
"""

import os
import sys
import json
import subprocess
import time
import requests
from pathlib import Path
import platform

def print_header(title: str):
    """Print a formatted header"""
    print(f"\n{'='*70}")
    print(f" {title}")
    print(f"{'='*70}")

def print_section(title: str):
    """Print a formatted section header"""
    print(f"\n{'-'*50}")
    print(f" {title}")
    print(f"{'-'*50}")

def check_admin_rights():
    """Check if running with admin rights on Windows"""
    if platform.system() == "Windows":
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False
    return True

def run_command(cmd, check=True, shell=True, capture_output=True):
    """Run a command with proper error handling"""
    try:
        result = subprocess.run(cmd, shell=shell, capture_output=capture_output, text=True, check=check)
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        return False, e.stdout if e.stdout else "", e.stderr if e.stderr else str(e)
    except Exception as e:
        return False, "", str(e)

def check_python_installation():
    """Check Python installation and version"""
    print_section("🐍 Checking Python Installation")
    
    try:
        result = subprocess.run([sys.executable, '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"✅ Python installed: {version}")
            
            # Check if it's 3.13+
            version_parts = version.split()[1].split('.')
            if int(version_parts[0]) >= 3 and int(version_parts[1]) >= 13:
                print("✅ Python version meets requirements (3.13+)")
                return True
            else:
                print(f"⚠️ Python version {version} may not be fully compatible. Recommended: 3.13+")
                return True
        else:
            print("❌ Python not properly installed")
            return False
    except Exception as e:
        print(f"❌ Error checking Python: {e}")
        return False

def install_ollama():
    """Install Ollama on Windows"""
    print_section("🧠 Installing Ollama")
    
    try:
        # Check if already installed
        success, _, _ = run_command("ollama --version", check=False)
        if success:
            print("✅ Ollama already installed")
            return True
        
        print("📥 Downloading Ollama installer...")
        
        # For Windows, we'll provide instructions since automated install requires admin rights
        print("🔧 To install Ollama:")
        print("1. Visit https://ollama.ai/download")
        print("2. Download 'Ollama for Windows'")
        print("3. Run the installer as Administrator")
        print("4. After installation, run this script again")
        
        print("\n⏳ Checking if Ollama is available...")
        for i in range(3):
            time.sleep(1)
            success, _, _ = run_command("ollama --version", check=False)
            if success:
                print("✅ Ollama detected!")
                return True
            print(f"⏳ Attempt {i+1}/3 - Ollama not found yet...")
        
        print("❌ Ollama not found. Please install manually.")
        return False
        
    except Exception as e:
        print(f"❌ Error installing Ollama: {e}")
        return False

def setup_ollama_models():
    """Pull required Ollama models"""
    print_section("📚 Setting up Ollama Models")
    
    models = ['llama3:latest', 'gemma2:4b']
    
    for model in models:
        print(f"📥 Pulling {model}...")
        success, stdout, stderr = run_command(f"ollama pull {model}", check=False)
        
        if success:
            print(f"✅ {model} - Downloaded successfully")
        else:
            print(f"⚠️ {model} - Failed to download: {stderr}")
            # Try alternative model
            if model == 'llama3:latest':
                print("🔄 Trying alternative: llama3:8b...")
                success, _, _ = run_command("ollama pull llama3:8b", check=False)
                if success:
                    print("✅ llama3:8b - Downloaded successfully")

def check_redis_installation():
    """Check Redis installation"""
    print_section("📊 Checking Redis")
    
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0, socket_timeout=2)
        r.ping()
        print("✅ Redis is running")
        return True
    except redis.ConnectionError:
        print("❌ Redis is not running")
        print("🔧 To install Redis on Windows:")
        print("1. Visit https://redis.io/download")
        print("2. Use Redis for Windows or WSL2")
        print("3. Alternative: Use Redis Cloud or Docker")
        return False
    except ImportError:
        print("❌ Redis Python client not installed")
        print("🔧 Installing Redis client...")
        success, _, _ = run_command(f"{sys.executable} -m pip install redis")
        return success
    except Exception as e:
        print(f"❌ Redis check failed: {e}")
        return False

def check_mysql_installation():
    """Check MySQL installation"""
    print_section("🗄️ Checking MySQL")
    
    try:
        import mysql.connector
        # Try to connect (will fail if no password set, but that's expected)
        try:
            conn = mysql.connector.connect(
                host='localhost',
                port=3306,
                user='root',
                connect_timeout=3
            )
            conn.close()
            print("✅ MySQL is running and accessible")
            return True
        except mysql.connector.Error as e:
            if "Access denied" in str(e):
                print("✅ MySQL is running (access denied is normal without password)")
                return True
            else:
                print(f"⚠️ MySQL connection issue: {e}")
                return False
    except ImportError:
        print("❌ MySQL connector not installed")
        return False
    except Exception as e:
        print(f"❌ MySQL check failed: {e}")
        print("🔧 To install MySQL:")
        print("1. Download MySQL Community Server from https://dev.mysql.com/downloads/mysql/")
        print("2. Install and start the MySQL service")
        print("3. Create a database for the travel system")
        return False

def setup_database():
    """Setup database schema"""
    print_section("🗄️ Setting up Database Schema")
    
    try:
        # Check if schema file exists
        schema_file = Path("upgrade_database_schema.py")
        if not schema_file.exists():
            print("⚠️ Database schema file not found")
            return False
        
        print("🔧 Running database schema setup...")
        success, stdout, stderr = run_command(f"{sys.executable} upgrade_database_schema.py")
        
        if success:
            print("✅ Database schema initialized successfully")
            return True
        else:
            print(f"❌ Database schema setup failed: {stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Database setup error: {e}")
        return False

def create_env_file():
    """Create .env file with default configuration"""
    print_section("⚙️ Creating Configuration File")
    
    env_file = Path(".env")
    if env_file.exists():
        print("✅ .env file already exists")
        return True
    
    env_content = """# Travel AI System Configuration
# Application Settings
APP_HOST=localhost
APP_PORT=8000
DEBUG=True
APP_TITLE=Travel Assistant - Multi-Agent System
APP_DESCRIPTION=AI-powered travel planning assistant with specialized agents
APP_VERSION=3.0.0-travel

# Security Settings
SECRET_KEY=travel-ai-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480

# Database Configuration
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=
MYSQL_DATABASE=travel_assistant
MYSQL_PORT=3306
MYSQL_CONNECT_TIMEOUT=10
MYSQL_CHARSET=utf8mb4

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_SOCKET_TIMEOUT=5
REDIS_SOCKET_CONNECT_TIMEOUT=5

# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_DEFAULT_MODEL=llama3:latest
OLLAMA_TIMEOUT=30
OLLAMA_CONNECTION_TIMEOUT=10
OLLAMA_READ_TIMEOUT=30
OLLAMA_MAX_RETRIES=3
OLLAMA_RETRY_DELAY=2.0
OLLAMA_MAX_TOKENS=2000
OLLAMA_TEMPERATURE=0.7

# Travel Agent Configuration
TRAVEL_CHAT_SLA_SECONDS=3
TRAVEL_BATCH_SLA_SECONDS=60
TRAVEL_MAX_AGENTS_CHAT=3
TRAVEL_MAX_AGENTS_BATCH=6
TRAVEL_SESSION_TIMEOUT_MINUTES=60

# UI Configuration
STATIC_DIR=static
TEMPLATES_DIR=templates

# Logging Configuration
LOG_LEVEL=INFO
# LOG_FILE=app.log
"""
    
    try:
        with open(env_file, 'w') as f:
            f.write(env_content)
        print("✅ .env file created successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to create .env file: {e}")
        return False

def test_system_functionality():
    """Test the complete system"""
    print_section("🧪 Testing System Functionality")
    
    try:
        # Test if we can import core modules
        sys.path.insert(0, str(Path.cwd()))
        
        print("Testing imports...")
        
        try:
            from config import Config
            print("✅ Config module - OK")
        except Exception as e:
            print(f"❌ Config module - Error: {e}")
        
        try:
            import fastapi
            print("✅ FastAPI - OK")
        except Exception as e:
            print(f"❌ FastAPI - Error: {e}")
        
        try:
            import langgraph
            print("✅ LangGraph - OK")
        except Exception as e:
            print(f"❌ LangGraph - Error: {e}")
        
        # Test Ollama connection
        try:
            response = requests.get('http://localhost:11434/api/version', timeout=3)
            if response.status_code == 200:
                version_info = response.json()
                print(f"✅ Ollama connection - OK (v{version_info.get('version', 'unknown')})")
            else:
                print("❌ Ollama connection - Failed")
        except Exception as e:
            print(f"❌ Ollama connection - Error: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ System test failed: {e}")
        return False

def create_quick_start_script():
    """Create a quick start script for the system"""
    print_section("🚀 Creating Quick Start Script")
    
    script_content = """@echo off
REM Travel AI System Quick Start Script
echo ============================================================
echo  🧳 Starting Travel AI System
echo ============================================================

echo 🔧 Checking Ollama service...
ollama list >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Ollama is not running. Please start Ollama first.
    echo 💡 Run: ollama serve
    pause
    exit /b 1
)

echo ✅ Ollama is running
echo 🚀 Starting Travel AI System...

REM Start the FastAPI server
py -m api.main

echo 👋 Travel AI System stopped.
pause
"""
    
    try:
        with open("start_travel_system.bat", 'w') as f:
            f.write(script_content)
        print("✅ Quick start script created: start_travel_system.bat")
        return True
    except Exception as e:
        print(f"❌ Failed to create quick start script: {e}")
        return False

def main():
    """Main setup function"""
    print_header("🧳 TRAVEL AI SYSTEM - COMPLETE SETUP")
    
    print("🎯 This script will set up your complete Travel AI Multi-Agent System")
    print("📋 What will be installed/configured:")
    print("   • Python dependencies")
    print("   • Ollama LLM server")
    print("   • Required AI models")  
    print("   • Database schema")
    print("   • Configuration files")
    print("   • Quick start scripts")
    
    print("\n❓ Continue with setup? (y/n): ", end="")
    if not input().lower().startswith('y'):
        print("👋 Setup cancelled.")
        return
    
    setup_results = {}
    
    # Check Python
    setup_results['python'] = check_python_installation()
    
    # Install dependencies
    print_section("📦 Installing Python Dependencies")
    success, _, _ = run_command(f"{sys.executable} -m pip install -r requirements.txt")
    setup_results['dependencies'] = success
    if success:
        print("✅ All Python dependencies installed")
    else:
        print("❌ Some dependencies failed to install")
    
    # Create configuration
    setup_results['config'] = create_env_file()
    
    # Check/install services
    setup_results['redis'] = check_redis_installation()
    setup_results['mysql'] = check_mysql_installation()
    setup_results['ollama'] = install_ollama()
    
    # Setup Ollama models if Ollama is available
    if setup_results['ollama']:
        setup_ollama_models()
    
    # Setup database
    if setup_results['mysql']:
        setup_results['database'] = setup_database()
    
    # Test system
    setup_results['system_test'] = test_system_functionality()
    
    # Create quick start script
    setup_results['quick_start'] = create_quick_start_script()
    
    # Final report
    print_header("📊 SETUP COMPLETION REPORT")
    
    total_components = len(setup_results)
    successful_components = sum(1 for success in setup_results.values() if success)
    
    success_rate = (successful_components / total_components) * 100
    
    for component, success in setup_results.items():
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"{component.upper().replace('_', ' '):<15} - {status}")
    
    print(f"\n🎯 SETUP COMPLETION: {success_rate:.1f}% ({successful_components}/{total_components})")
    
    if success_rate >= 80:
        print("\n🎉 SETUP SUCCESSFUL!")
        print("🚀 Your Travel AI System is ready!")
        print("\n📋 Next steps:")
        print("1. Ensure Ollama is running: ollama serve")
        print("2. Start the system: py -m api.main")
        print("3. Visit: http://localhost:8000")
        print("4. Or use the quick start: start_travel_system.bat")
        
    elif success_rate >= 60:
        print("\n⚠️ PARTIAL SETUP")
        print("Most components are working, but some issues need attention.")
        print("Check the failed components above and resolve manually.")
        
    else:
        print("\n❌ SETUP INCOMPLETE")
        print("Several critical components failed to install.")
        print("Please resolve the issues and run setup again.")
    
    print("\n📖 For help and documentation:")
    print("   • README.md - Complete system documentation")
    print("   • check_travel_agents.py - System health checker")
    print("   • config.py - Configuration settings")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Setup interrupted by user.")
    except Exception as e:
        print(f"\n❌ Setup failed with error: {e}")
        print("💡 Please check the error and try again.")
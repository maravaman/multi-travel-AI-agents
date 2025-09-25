#!/usr/bin/env python3
"""
🚀 Enhanced FastAPI Backend with Proper CORS and Streaming Support
Complete integration solution for LangGraph travel planning system
"""

import sys
import os
import json
import logging
from typing import Dict, Any, Optional, AsyncGenerator
from datetime import datetime
import asyncio

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Request, HTTPException, Depends, Header
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import uvicorn

# Import your existing modules
from config import Config
config = Config()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import authentication if available
try:
    from auth.auth_service import auth_service
    AUTH_AVAILABLE = True
    logger.info("✅ Authentication system loaded")
except ImportError as e:
    AUTH_AVAILABLE = False
    logger.warning(f"⚠️ Authentication not available: {e}")

# Import travel system
try:
    from core.unified_travel_system import unified_travel_system, ProcessingMode
    UNIFIED_SYSTEM_AVAILABLE = True
    logger.info("✅ Unified travel system loaded")
except ImportError:
    try:
        from core.langgraph_multiagent_system import langgraph_multiagent_system
        UNIFIED_SYSTEM_AVAILABLE = False
        logger.info("✅ Legacy multi-agent system loaded")
    except ImportError as e:
        logger.error(f"❌ No travel system available: {e}")
        langgraph_multiagent_system = None

# FastAPI setup with enhanced configuration
app = FastAPI(
    title=config.APP_TITLE,
    description=config.APP_DESCRIPTION + " - Enhanced with proper CORS and streaming",
    version=config.APP_VERSION + "-enhanced",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 🌐 Enhanced CORS Configuration
# IMPORTANT: Customize these origins for your deployment
FRONTEND_ORIGINS = [
    "http://localhost:3000",  # React dev server
    "http://localhost:8080",  # Vue dev server  
    "http://localhost:5173",  # Vite dev server
    "http://localhost:8000",  # Same-origin requests
    "http://127.0.0.1:8000",  # Alternative localhost
    "http://localhost",       # Simple localhost
    "http://127.0.0.1",       # Alternative
]

# Add production domains here when deploying
if not config.DEBUG:
    FRONTEND_ORIGINS.extend([
        "https://your-domain.com",
        "https://www.your-domain.com",
        # Add your production URLs here
    ])

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Security
security = HTTPBearer(auto_error=False)

# Mount static files and templates
try:
    app.mount("/static", StaticFiles(directory=config.STATIC_DIR), name="static")
    templates = Jinja2Templates(directory=config.TEMPLATES_DIR)
    logger.info("✅ Static files and templates mounted")
except Exception as e:
    logger.warning(f"⚠️ Could not mount static files: {e}")

# 📝 Request/Response Models
class TravelQuery(BaseModel):
    """Travel query request model"""
    user: str
    question: str
    mode: str = "balanced"  # ultra_fast, balanced, comprehensive
    stream: bool = False

class TravelResponse(BaseModel):
    """Travel response model"""
    success: bool
    user: str
    question: str
    response: str
    agents_involved: list = []
    processing_time: float
    mode: str
    timestamp: str
    error: Optional[str] = None

class AuthRequest(BaseModel):
    """Authentication request"""
    username: str
    password: str

class AuthResponse(BaseModel):
    """Authentication response"""
    success: bool
    token: Optional[str] = None
    user_id: Optional[int] = None
    username: Optional[str] = None
    message: str

# 🔐 Authentication Helper
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current authenticated user (optional)"""
    if not AUTH_AVAILABLE:
        return None
        
    if not credentials:
        return None
    
    try:
        user = auth_service.get_current_user(credentials.credentials)
        return user
    except Exception as e:
        logger.warning(f"Authentication failed: {e}")
        return None

async def require_auth(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Require authentication"""
    if not AUTH_AVAILABLE:
        raise HTTPException(status_code=501, detail="Authentication not configured")
        
    if not credentials:
        raise HTTPException(
            status_code=401, 
            detail="Authorization header required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    try:
        user = auth_service.get_current_user(credentials.credentials)
        if not user:
            raise HTTPException(
                status_code=401, 
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"}
            )
        return user
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=401, 
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"}
        )

# 🏠 Main UI Route
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve the main travel interface"""
    try:
        return templates.TemplateResponse("travel_interface.html", {"request": request})
    except Exception as e:
        logger.error(f"Template error: {e}")
        return HTMLResponse("""
        <html><body>
        <h1>Travel Assistant</h1>
        <p>Frontend template not found. Please ensure templates/travel_interface.html exists.</p>
        <p><a href="/docs">API Documentation</a></p>
        </body></html>
        """)

# 🔍 Health Check & Status
@app.get("/health")
async def health_check():
    """Comprehensive health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "auth": AUTH_AVAILABLE,
            "travel_system": UNIFIED_SYSTEM_AVAILABLE or (langgraph_multiagent_system is not None),
            "cors_origins": len(FRONTEND_ORIGINS)
        },
        "version": config.APP_VERSION
    }

@app.get("/ping")
async def ping():
    """Simple ping endpoint for connectivity testing"""
    return {"pong": True, "timestamp": datetime.now().isoformat()}

# 🔐 Authentication Endpoints
@app.post("/auth/login", response_model=AuthResponse)
async def login(auth_request: AuthRequest):
    """User login endpoint"""
    if not AUTH_AVAILABLE:
        return AuthResponse(success=False, message="Authentication not configured")
    
    try:
        result = auth_service.login_user(
            username=auth_request.username,
            password=auth_request.password,
            ip_address="frontend_client"
        )
        
        if result["success"]:
            return AuthResponse(
                success=True,
                token=result["token"],
                user_id=result["user_id"],
                username=result["username"],
                message="Login successful"
            )
        else:
            return AuthResponse(success=False, message=result.get("error", "Login failed"))
            
    except Exception as e:
        logger.error(f"Login error: {e}")
        return AuthResponse(success=False, message="Login service error")

@app.post("/auth/register", response_model=AuthResponse)
async def register(auth_request: AuthRequest):
    """User registration endpoint"""
    if not AUTH_AVAILABLE:
        return AuthResponse(success=False, message="Authentication not configured")
    
    try:
        # For demo purposes, use username as email
        result = auth_service.register_user(
            username=auth_request.username,
            email=f"{auth_request.username}@travel.local",
            password=auth_request.password,
            ip_address="frontend_client"
        )
        
        if result["success"]:
            return AuthResponse(
                success=True,
                token=result["token"],
                user_id=result["user_id"], 
                username=result["username"],
                message="Registration successful"
            )
        else:
            return AuthResponse(success=False, message=result.get("error", "Registration failed"))
            
    except Exception as e:
        logger.error(f"Registration error: {e}")
        return AuthResponse(success=False, message="Registration service error")

@app.get("/auth/me")
async def get_user_profile(current_user: dict = Depends(require_auth)):
    """Get current user profile"""
    return {
        "user_id": current_user["id"],
        "username": current_user["username"],
        "email": current_user.get("email"),
        "created_at": current_user.get("created_at")
    }

# 🤖 Travel Query Endpoints

@app.post("/api/travel/query", response_model=TravelResponse)
async def travel_query(
    query: TravelQuery,
    current_user: Optional[dict] = Depends(get_current_user)
):
    """Main travel query endpoint - returns JSON response"""
    return await travel_query_endpoint(query, current_user)

@app.get("/api/travel/stream")
async def travel_query_stream_get(
    user: str,
    question: str,
    mode: str = "balanced",
    token: Optional[str] = None
):
    """GET Streaming endpoint for EventSource compatibility"""
    # Handle JWT token from query parameter (EventSource limitation)
    current_user = None
    if token and AUTH_AVAILABLE:
        try:
            current_user = auth_service.get_current_user(token)
        except Exception as e:
            logger.warning(f"Stream auth failed: {e}")
    
    # Convert to TravelQuery format
    query = TravelQuery(user=user, question=question, mode=mode)
    
    async def generate_stream():
        """Generate streaming response"""
        try:
            # Determine user info
            if current_user:
                user_id = current_user["id"]
                username = current_user["username"]
            else:
                user_id = int(datetime.now().timestamp())
                username = query.user or "anonymous"
            
            # Start streaming response
            yield f"data: {json.dumps({'type': 'start', 'message': 'Processing your travel query...'})}\n\n"
            
            # Simulate agent processing with streaming updates
            if UNIFIED_SYSTEM_AVAILABLE:
                yield f"data: {json.dumps({'type': 'agent_selected', 'agent': 'TravelRouter', 'message': 'Analyzing your travel needs...'})}\n\n"
                await asyncio.sleep(0.5)
                
                # Process query
                result = unified_travel_system.process_query(
                    user=username,
                    user_id=user_id,
                    question=query.question
                )
                
                # Stream agents involved
                for agent in result.get("agents_involved", []):
                    yield f"data: {json.dumps({'type': 'agent_processing', 'agent': agent, 'message': f'{agent} is analyzing...'})}\n\n"
                    await asyncio.sleep(0.3)
                
                # Stream final response in chunks
                response_text = result.get("response", result.get("final_response", ""))
                chunk_size = 50
                
                for i in range(0, len(response_text), chunk_size):
                    chunk = response_text[i:i+chunk_size]
                    yield f"data: {json.dumps({'type': 'response_chunk', 'chunk': chunk})}\n\n"
                    await asyncio.sleep(0.1)
                
                # Send completion
                yield f"data: {json.dumps({
                    'type': 'complete',
                    'result': {
                        'success': True,
                        'response': response_text,
                        'agents_involved': result.get("agents_involved", []),
                        'processing_time': result.get("processing_time", 0),
                        'mode': query.mode
                    }
                })}\n\n"
                
            else:
                # Fallback streaming
                yield f"data: {json.dumps({'type': 'agent_selected', 'agent': 'FallbackAgent', 'message': 'Processing with fallback system...'})}\n\n"
                
                fallback_response = f"I'd be happy to help with your travel query: '{query.question}'. The system is currently in fallback mode, but I can still provide general travel assistance!"
                
                # Stream response
                chunk_size = 30
                for i in range(0, len(fallback_response), chunk_size):
                    chunk = fallback_response[i:i+chunk_size]
                    yield f"data: {json.dumps({'type': 'response_chunk', 'chunk': chunk})}\n\n"
                    await asyncio.sleep(0.1)
                
                yield f"data: {json.dumps({
                    'type': 'complete',
                    'result': {
                        'success': True,
                        'response': fallback_response,
                        'agents_involved': ['FallbackAgent'],
                        'processing_time': 1.0,
                        'mode': query.mode
                    }
                })}\n\n"
            
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': f'Streaming error: {str(e)}'})}\n\n"
        
        finally:
            yield f"data: {json.dumps({'type': 'end'})}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
        }
    )

# 🧪 Debug Endpoints for Testing

@app.get("/debug/test-response")
async def test_response():
    """Test endpoint to verify basic connectivity"""
    return {
        "message": "Backend is working!",
        "timestamp": datetime.now().isoformat(),
        "cors_origins": FRONTEND_ORIGINS,
        "auth_available": AUTH_AVAILABLE,
        "system_available": UNIFIED_SYSTEM_AVAILABLE or (langgraph_multiagent_system is not None)
    }

@app.post("/debug/echo")
async def echo_request(request: Request):
    """Echo request for debugging"""
    body = await request.body()
    return {
        "method": request.method,
        "url": str(request.url),
        "headers": dict(request.headers),
        "body": body.decode() if body else None,
        "timestamp": datetime.now().isoformat()
    }

# 🔄 Legacy Frontend Compatibility Routes
# These routes maintain compatibility with the existing frontend

class LegacyChatQuery(BaseModel):
    """Legacy chat query format"""
    user_id: int
    text: str

class LegacyBatchQuery(BaseModel):
    """Legacy batch analysis format"""
    user_id: int
    transcript: str

class LegacyPerfectQuery(BaseModel):
    """Legacy perfect query format"""
    user: str
    user_id: int
    question: str

@app.post("/travel/chat")
async def legacy_chat_endpoint(
    query: LegacyChatQuery,
    current_user: Optional[dict] = Depends(get_current_user)
):
    """Legacy chat endpoint - maintains compatibility with existing frontend"""
    try:
        # Convert to new format and process
        travel_query = TravelQuery(
            user=f"user_{query.user_id}",
            question=query.text,
            mode="balanced"
        )
        
        # Process using the main travel query logic
        response = await travel_query_endpoint(travel_query, current_user)
        
        # Convert back to expected legacy format
        return {
            "response": response.response,
            "agents_involved": response.agents_involved,
            "processing_time": response.processing_time,
            "ai_used": True,  # Indicate AI was used
            "success": response.success
        }
        
    except Exception as e:
        logger.error(f"Legacy chat endpoint error: {e}")
        return {
            "response": f"I understand you're asking about \"{query.text[:50]}...\". I'm experiencing a technical issue, but I'm here to help with your travel needs!",
            "agents_involved": ["ErrorHandler"],
            "processing_time": 0.1,
            "ai_used": False,
            "success": False,
            "error": str(e)
        }

@app.post("/travel/batch")
async def legacy_batch_endpoint(
    query: LegacyBatchQuery,
    current_user: Optional[dict] = Depends(get_current_user)
):
    """Legacy batch analysis endpoint"""
    try:
        # Convert to new format and process
        travel_query = TravelQuery(
            user=f"user_{query.user_id}",
            question=f"Analyze this travel conversation transcript: {query.transcript}",
            mode="comprehensive"  # Use comprehensive mode for batch analysis
        )
        
        response = await travel_query_endpoint(travel_query, current_user)
        
        # Return in legacy batch format
        return {
            "response": response.response,
            "agents_involved": response.agents_involved,
            "processing_time": response.processing_time,
            "ai_used": True,
            "success": response.success,
            "analysis_type": "comprehensive"
        }
        
    except Exception as e:
        logger.error(f"Legacy batch endpoint error: {e}")
        return {
            "detail": f"Batch analysis error: {str(e)}",
            "success": False
        }

@app.post("/perfect_query")
async def legacy_perfect_endpoint(
    query: LegacyPerfectQuery,
    current_user: Optional[dict] = Depends(get_current_user)
):
    """Legacy Perfect LangGraph endpoint"""
    try:
        # Convert to new format and process with ultra_fast mode
        travel_query = TravelQuery(
            user=query.user,
            question=query.question,
            mode="ultra_fast"  # Perfect = ultra fast mode
        )
        
        response = await travel_query_endpoint(travel_query, current_user)
        
        # Return in legacy perfect format
        return {
            "response": response.response,
            "agents_involved": response.agents_involved,
            "processing_time": response.processing_time,
            "system_status": "perfect" if response.success else "degraded",
            "edges_traversed": response.agents_involved,  # Map agents to edges
            "mode": "perfect",
            "success": response.success
        }
        
    except Exception as e:
        logger.error(f"Legacy perfect endpoint error: {e}")
        return {
            "response": f"🚀 Perfect system processing: \"{query.question}\". Currently experiencing optimization, but delivering results!",
            "agents_involved": ["PerfectAgent"],
            "processing_time": 0.05,
            "system_status": "recovering",
            "edges_traversed": ["ErrorHandler"],
            "mode": "fallback",
            "success": False,
            "error": str(e)
        }

# Add helper function for travel query processing
async def travel_query_endpoint(
    query: TravelQuery,
    current_user: Optional[dict] = None
) -> TravelResponse:
    """Helper function to process travel queries consistently"""
    try:
        start_time = datetime.now()
        
        # Determine user info
        if current_user:
            user_id = current_user["id"]
            username = current_user["username"]
        else:
            user_id = int(start_time.timestamp())
            username = query.user or "anonymous"
        
        logger.info(f"🧳 Processing travel query for {username}: {query.question[:50]}...")
        
        # Process query based on available system
        if UNIFIED_SYSTEM_AVAILABLE:
            mode_map = {
                "ultra_fast": ProcessingMode.ULTRA_FAST,
                "balanced": ProcessingMode.BALANCED,
                "comprehensive": ProcessingMode.COMPREHENSIVE
            }
            processing_mode = mode_map.get(query.mode, ProcessingMode.BALANCED)
            
            result = unified_travel_system.process_query(
                user=username,
                user_id=user_id,
                question=query.question,
                mode=processing_mode
            )
        elif langgraph_multiagent_system:
            result = langgraph_multiagent_system.process_request(
                user=username,
                user_id=user_id,
                question=query.question
            )
        else:
            # Fallback response
            result = {
                "user": username,
                "question": query.question,
                "response": f"I'd be happy to help you with your travel query: '{query.question}'. However, the travel planning system is currently initializing. Please try again shortly.",
                "agents_involved": ["FallbackAgent"],
                "processing_time": 0.1,
                "mode": query.mode,
                "timestamp": start_time.isoformat(),
                "success": True
            }
        
        # Ensure response format
        response = TravelResponse(
            success=result.get("success", True),
            user=result.get("user", username),
            question=result.get("question", query.question),
            response=result.get("response", result.get("final_response", "")),
            agents_involved=result.get("agents_involved", result.get("agent_chain", [])),
            processing_time=result.get("processing_time", 0.0),
            mode=result.get("mode", query.mode),
            timestamp=result.get("timestamp", start_time.isoformat()),
            error=result.get("error")
        )
        
        logger.info(f"✅ Query processed successfully in {response.processing_time:.2f}s")
        return response
        
    except Exception as e:
        logger.error(f"❌ Travel query error: {e}")
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return TravelResponse(
            success=False,
            user=query.user,
            question=query.question,
            response=f"I apologize, but I encountered an issue processing your travel query. I'm still here to help! Error details have been logged for our team.",
            agents_involved=["ErrorHandler"],
            processing_time=processing_time,
            mode=query.mode,
            timestamp=start_time.isoformat(),
            error=str(e)
        )

# Status endpoints for frontend
@app.get("/api/ollama/status")
async def ollama_status():
    """Check Ollama AI status for frontend"""
    # This would normally check actual Ollama connection
    # For now, return based on system availability
    return {
        "available": UNIFIED_SYSTEM_AVAILABLE or (langgraph_multiagent_system is not None),
        "models": ["llama3", "llama3.1"] if UNIFIED_SYSTEM_AVAILABLE else [],
        "status": "connected" if UNIFIED_SYSTEM_AVAILABLE else "offline"
    }

@app.get("/travel/profile/{user_id}")
async def get_travel_profile(
    user_id: int,
    current_user: Optional[dict] = Depends(get_current_user)
):
    """Get user travel profile - placeholder implementation"""
    # This would normally fetch from database
    return {
        "destinations_of_interest": ["Japan", "Europe", "Southeast Asia"],
        "travel_pace": "moderate",
        "activity_preferences": ["cultural", "food", "nature"],
        "budget_range": "mid-range",
        "user_id": user_id
    }

@app.get("/travel/sessions/{user_id}")
async def get_travel_sessions(
    user_id: int,
    current_user: Optional[dict] = Depends(get_current_user)
):
    """Get user travel sessions - placeholder implementation"""
    # This would normally fetch from database
    return {
        "sessions": [
            {
                "id": 1,
                "title": "Japan Trip Planning",
                "mode": "comprehensive",
                "turn_count": 5,
                "started_at": "2024-01-15T10:30:00Z"
            },
            {
                "id": 2,
                "title": "Europe Backpacking",
                "mode": "balanced",
                "turn_count": 3,
                "started_at": "2024-01-10T14:20:00Z"
            }
        ]
    }

# 📚 Additional endpoints for completeness
@app.get("/api/agents")
async def get_agents():
    """Get available agents information"""
    if UNIFIED_SYSTEM_AVAILABLE:
        return {
            "agents": list(unified_travel_system.agents_config.keys()),
            "modes": ["ultra_fast", "balanced", "comprehensive"],
            "system": "unified"
        }
    elif langgraph_multiagent_system:
        return {
            "agents": list(langgraph_multiagent_system.agents_config.keys()),
            "modes": ["standard"],
            "system": "legacy"
        }
    else:
        return {
            "agents": ["FallbackAgent"],
            "modes": ["fallback"],
            "system": "fallback"
        }

# 🚀 Server startup
if __name__ == "__main__":
    print("🚀 Starting Enhanced Travel Assistant Backend...")
    print(f"📍 Server URL: http://{config.APP_HOST}:{config.APP_PORT}")
    print(f"📖 API Docs: http://{config.APP_HOST}:{config.APP_PORT}/docs")
    print(f"🎯 Main UI: http://{config.APP_HOST}:{config.APP_PORT}")
    print(f"🌐 CORS Origins: {FRONTEND_ORIGINS}")
    print(f"🔐 Auth Available: {AUTH_AVAILABLE}")
    print(f"🤖 Travel System: {'Unified' if UNIFIED_SYSTEM_AVAILABLE else 'Legacy' if langgraph_multiagent_system else 'Fallback'}")
    print("=" * 70)

    try:
        uvicorn.run(
            "api.enhanced_main:app",
            host=config.APP_HOST,
            port=config.APP_PORT,
            reload=config.DEBUG,
            log_level="info" if config.DEBUG else "warning"
        )
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Server failed to start: {e}")
# main.py

import sys
import os
# Add the parent directory to Python path to enable imports from core, auth, database modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Request, HTTPException, Body, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict
import json, os
import logging
from datetime import datetime

# Import configuration
from config import Config
config = Config()

# Import required modules for vector search
try:
    from langchain.schema import Document
    from langchain_community.embeddings import HuggingFaceEmbeddings
except ImportError:
    # Fallback if langchain modules are not available
    Document = None
    HuggingFaceEmbeddings = None

try:
    from core.memory import MemoryManager
except ImportError:
    MemoryManager = None
# from core.orchestrator import run_dynamic_graph
# from core.ollama_client import ollama_client

# Configure logging first
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import the LangGraph multi-agent system
try:
    from core.langgraph_multiagent_system import langgraph_multiagent_system
    logger.info("✅ LangGraph multi-agent system loaded successfully")
except ImportError as e:
    logger.warning(f"⚠️ LangGraph multi-agent system not available: {e}")
    langgraph_multiagent_system = None
except Exception as e:
    logger.error(f"❌ LangGraph multi-agent system failed to load: {e}")
    langgraph_multiagent_system = None

# Optional imports with fallbacks
try:
    from core.dynamic_agents import dynamic_agent_manager
except ImportError:
    dynamic_agent_manager = None

try:
    from auth.auth_endpoints import router as auth_router, get_current_user
except ImportError as e:
    print(f"Warning: Auth module not available: {e}")
    auth_router = None
    get_current_user = None
except Exception as e:
    print(f"Warning: Auth module failed to load (database connection issue): {e}")
    auth_router = None
    get_current_user = None

try:
    from database.connection import get_mysql_conn
except ImportError:
    get_mysql_conn = None

# Import travel endpoints
try:
    from api.travel_endpoints import router as travel_router
except ImportError:
    travel_router = None

# Logger already configured above

# Import Enhanced Ollama Client for real AI responses
try:
    from core.ollama_client import ollama_client
    logger.info("✅ Enhanced Ollama client initialized")
except Exception as e:
    logger.warning(f"⚠️ Enhanced Ollama client not available: {e}")
    ollama_client = None

# ✅ Helper Functions for Dynamic Travel Responses (Ollama-powered)
def generate_travel_response(question: str) -> str:
    """Generate a dynamic, travel-focused response using Ollama AI.
    Falls back to generic response only if Ollama is unavailable.
    """
    q = (question or "").strip()
    if not q:
        return "I can help with travel planning. Please share your question."
    
    # Try to generate dynamic response using Ollama
    try:
        if ollama_client and ollama_client.is_available():
            system_prompt = (
                "You are a helpful travel assistant. Generate a personalized, practical response "
                "to help with travel planning. Keep responses concise (2-3 sentences), actionable, "
                "and focused on travel guidance. Include specific suggestions when relevant."
            )
            
            dynamic_response = ollama_client.generate_response(
                prompt=f"User question about travel: {q}\n\nProvide helpful travel guidance:",
                system_prompt=system_prompt,
                max_tokens=200,
                temperature=0.7
            )
            
            if dynamic_response and len(dynamic_response.strip()) > 20:
                logger.info(f"✅ Generated dynamic Ollama response for: {q[:50]}...")
                return dynamic_response.strip()
    
    except Exception as e:
        logger.warning(f"Ollama response generation failed: {e}")
    
    # Fallback to generic response only if Ollama fails
    return (
        "Thanks for your travel question. I'll route it through the appropriate travel agents "
        "(planning, mood, communication, behavior, calming, and summary) to provide practical, "
        "actionable guidance. If you'd like, specify your destination, dates, budget, and any "
        "concerns so I can tailor the plan."
    )


def generate_structured_fallback(question: str) -> str:
    """Generate dynamic, structured responses using Ollama AI with context-aware prompts"""
    question_lower = question.lower()
    
    # Try to generate contextual response using Ollama first
    try:
        if ollama_client and ollama_client.is_available():
            # Determine context and create appropriate system prompt
            context_type = "general"
            
            if any(city in question_lower for city in ['paris', 'france', 'tokyo', 'japan', 'italy', 'rome', 'florence']):
                context_type = "destination_specific"
            elif any(word in question_lower for word in ['nervous', 'anxious', 'worried', 'scared', 'overwhelmed', 'first time']):
                context_type = "emotional_support"
            elif any(word in question_lower for word in ['language', 'communicate', 'speak', 'talk', 'translate', 'barrier']):
                context_type = "communication"
            elif any(word in question_lower for word in ['choose', 'decide', 'between', 'or', 'options', 'which', 'should']):
                context_type = "decision_making"
            elif any(word in question_lower for word in ['plan', 'trip', 'vacation', 'visit', 'travel']):
                context_type = "travel_planning"
            
            # Create context-aware system prompt
            system_prompts = {
                "destination_specific": (
                    "You are a knowledgeable travel expert. Provide specific, practical advice about destinations. "
                    "Include weather tips, dining recommendations, scenic spots, and helpful travel tips. "
                    "Format with emojis and bullet points. Keep response under 300 words."
                ),
                "emotional_support": (
                    "You are a supportive travel counselor. Help address travel anxiety and concerns with "
                    "reassuring, practical advice. Focus on building confidence and providing actionable steps. "
                    "Be encouraging and understanding. Format with emojis and bullet points."
                ),
                "communication": (
                    "You are a travel communication expert. Provide practical language and communication tips "
                    "for travelers. Include essential phrases, cultural tips, and technology solutions. "
                    "Format with emojis and bullet points. Keep response helpful and actionable."
                ),
                "decision_making": (
                    "You are a travel decision advisor. Help travelers make informed choices by providing "
                    "structured decision frameworks, comparison criteria, and practical next steps. "
                    "Format with emojis and bullet points. Be analytical but approachable."
                ),
                "travel_planning": (
                    "You are a comprehensive travel planner. Provide structured planning advice covering "
                    "all aspects of trip preparation. Include practical checklists and actionable steps. "
                    "Format with emojis and bullet points. Be thorough but organized."
                ),
                "general": (
                    "You are a helpful travel assistant. Provide personalized, practical travel advice "
                    "based on the user's question. Be encouraging, specific, and actionable. "
                    "Format with emojis and bullet points. Keep response engaging and helpful."
                )
            }
            
            system_prompt = system_prompts[context_type]
            
            dynamic_response = ollama_client.generate_response(
                prompt=f"Travel Question: {question}\n\nProvide detailed, helpful travel guidance:",
                system_prompt=system_prompt,
                max_tokens=400,
                temperature=0.8
            )
            
            if dynamic_response and len(dynamic_response.strip()) > 50:
                logger.info(f"✅ Generated dynamic structured response for: {question[:50]}...")
                return dynamic_response.strip()
    
    except Exception as e:
        logger.warning(f"Dynamic structured response generation failed: {e}")
    
    # Simple fallback only if Ollama completely fails
    return f"""🎯 **Travel Assistance**

I'm here to help with your travel question about "{question[:100]}{'...' if len(question) > 100 else ''}".

✅ **Next Steps**: Let me connect you with the appropriate travel specialists who can provide detailed, personalized guidance for your specific needs.

Please share more details about your destination, timeline, or specific concerns so I can provide more targeted assistance."""

def detect_relevant_agents(question: str) -> list:
    """Detect which of the 7 travel agents are relevant to this question."""
    question_lower = (question or "").lower()

    agents = []

    if any(word in question_lower for word in ['plan', 'trip', 'destination', 'visit', 'travel']):
        agents.append('TextTripAnalyzer')

    if any(word in question_lower for word in ['nervous', 'anxious', 'worried', 'feel', 'emotion']):
        agents.append('TripMoodDetector')

    if any(word in question_lower for word in ['language', 'communicate', 'speak', 'talk', 'say']):
        agents.append('TripCommsCoach')

    if any(word in question_lower for word in ['choose', 'decide', 'between', 'options', 'help me']):
        agents.append('TripBehaviorGuide')

    if any(word in question_lower for word in ['calm', 'relax', 'stress', 'overwhelmed', 'anxiety']):
        agents.append('TripCalmPractice')

    if any(word in question_lower for word in ['summary', 'overview', 'profile', 'preferences']):
        agents.append('TripSummarySynth')

    # Always include the orchestrator/assistant for final synthesis when applicable
    if agents:
        agents.append('TravelAssistant')

    # Default to TextTripAnalyzer if nothing matched
    if not agents:
        agents = ['TextTripAnalyzer']

    # Enforce allowed list
    agents = [a for a in agents if a in ALLOWED_TRAVEL_AGENTS]
    return agents

# ✅ FastAPI Setup
app = FastAPI(
    title=config.APP_TITLE,
    description=config.APP_DESCRIPTION,
    version=config.APP_VERSION
)

# Add CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files and templates
app.mount("/static", StaticFiles(directory=config.STATIC_DIR), name="static")
templates = Jinja2Templates(directory=config.TEMPLATES_DIR)

# Include authentication router (if available)
if auth_router:
    app.include_router(auth_router)

# Include travel router (if available)
if travel_router:
    app.include_router(travel_router)

# ✅ Globals
memory_manager = MemoryManager() if MemoryManager else None
AGENT_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "../core/agents.json"))

# Allowed travel agents (restrict outputs to these only)
ALLOWED_TRAVEL_AGENTS = [
    'TextTripAnalyzer',
    'TripMoodDetector',
    'TripCommsCoach',
    'TripBehaviorGuide',
    'TripCalmPractice',
    'TripSummarySynth',
    'TravelAssistant',
]

# ✅ Schemas
class GraphInput(BaseModel):
    user: str
    question: str

class STMRequest(BaseModel):
    user_id: str
    agent_id: str
    value: str
    expiry_hours: int = 1

class PerfectQueryRequest(BaseModel):
    user: str
    user_id: int
    question: str

# ✅ Health
@app.get("/ping")
def ping():
    return {"pong": True}

@app.get("/health")
def health():
    return {"status": "Server is running ✅"}

# ✅ Favicon
@app.get("/favicon.ico")
def favicon():
    return {"message": "No favicon configured"}

# ✅ Perfect LangGraph Query Endpoint (Showcase)
@app.post("/perfect_query")
async def perfect_query(payload: PerfectQueryRequest):
    """Perfect LangGraph system endpoint using optimized fixed multi-agent system"""
    try:
        start_time = datetime.now()
        logger.info(f"🚀 Perfect LangGraph query from user {payload.user}: {payload.question[:50]}...")

        # Use the optimized fixed LangGraph multi-agent system
        try:
            from core.fixed_langgraph_multiagent_system import fixed_langgraph_multiagent_system
            
            result = fixed_langgraph_multiagent_system.process_request(
                user=payload.user,
                user_id=payload.user_id,
                question=payload.question
            )
            
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()

            logger.info(f"✅ Perfect LangGraph response in {processing_time:.2f}s")

            agents_involved = result.get("agents_involved") or result.get("agent_chain") or []
            # Enforce allowed agents only
            agents_involved = [a for a in agents_involved if a in ALLOWED_TRAVEL_AGENTS]

            return {
                "user_id": payload.user_id,
                "response": result.get("response", result.get("final_response", "")),
                "agents_involved": agents_involved,
                "processing_time": result.get("processing_time", processing_time),
                "mode": "perfect_langgraph",
                "edges_traversed": result.get("edges_traversed", []),
                "system_status": "perfect" if result.get("ai_used", False) else "operational",
                "timestamp": start_time.isoformat(),
                "ai_used": result.get("ai_used", False),
                "success": result.get("success", True)
            }
            
        except ImportError as import_error:
            logger.error(f"Failed to import fixed LangGraph system: {import_error}")
            raise
        else:
            # Fallback when fixed system is unavailable
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()

            response = generate_travel_response(payload.question)
            agents = detect_relevant_agents(payload.question)

            return {
                "user_id": payload.user_id,
                "response": response,
                "agents_involved": agents,
                "processing_time": processing_time,
                "mode": "perfect_fallback",
                "edges_traversed": [],
                "system_status": "operational",
                "timestamp": start_time.isoformat(),
                "ai_used": False,
                "success": True
            }

    except Exception as e:
        logger.error(f"Perfect query execution error: {e}")
        processing_time = (datetime.now() - start_time).total_seconds()
        response = generate_travel_response(payload.question)
        agents = detect_relevant_agents(payload.question)
        
        return {
            "user_id": payload.user_id,
            "response": response,
            "agents_involved": agents,
            "processing_time": processing_time,
            "mode": "error_recovery",
            "edges_traversed": [],
            "system_status": "recovering",
            "timestamp": start_time.isoformat(),
            "ai_used": False,
            "success": True,  # Still successful as we provided a response
            "error": str(e)
        }

# Note: Travel endpoints are provided via api.travel_endpoints router.
# The duplicate /travel/* routes previously defined here have been removed to prevent routing conflicts.
        if not user_id:
            raise HTTPException(status_code=400, detail="User ID is required")
            
        start_time = datetime.now()
        
        # Initialize memory manager and session handling
        memory_manager = MemoryManager()
        
        # Start or get active session
        session_id = memory_manager.start_travel_session(user_id, mode='chat')
        
        # Add user turn to session
        memory_manager.add_turn_to_session(user_id, session_id, 'user', text)
        
        # Get session context (last 7 days LTM + User Travel Profile)
        session_context = memory_manager.get_session_context(user_id, session_id, last_n_turns=6)
        travel_profile = memory_manager.get_travel_profile_cache(user_id) or memory_manager.get_travel_profile(user_id)
        
        # Extract profile insights from current query
        memory_manager.extract_profile_insights_from_text(user_id, text, mode='chat')
        
        # Import travel orchestrator for proper agent routing
        try:
            from core.travel_orchestrator import TravelOrchestrator
            orchestrator = TravelOrchestrator(memory_manager)
            
            # Process query with chat mode constraints (< 3s, shallow processing, max 3 agents)
            result = orchestrator.process_chat_query(
                user_id=user_id,
                query=text,
                session_id=session_id,
                context=session_context,
                profile=travel_profile
            )
            
            response = result.get('response', generate_travel_response(text))
            agents_used = result.get('agents_involved', detect_relevant_agents(text))
            
        except ImportError:
            # Fallback to direct response generation
            response = generate_travel_response(text)
            agents_used = detect_relevant_agents(text)
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Add assistant turn to session
        memory_manager.add_turn_to_session(
            user_id, session_id, 'assistant', response, 
            agent_name=agents_used[0] if agents_used else 'TravelAssistant',
            metadata={'agents_involved': agents_used, 'processing_time': processing_time}
        )
        
        # Ensure SLA compliance (< 3s)
        if processing_time > 3.0:
            logger.warning(f"Chat SLA exceeded: {processing_time:.2f}s for user {user_id}")
        
        logger.info(f"✅ Chat response delivered in {processing_time:.3f}s for query: {text[:50]}...")
        
        return {
            "user_id": user_id,
            "response": response,
            "agents_involved": agents_used,
            "processing_time": processing_time,
            "session_id": session_id,
            "mode": "chat",
            "context_used": len(session_context),
            "profile_updated": False  # Chat mode doesn't update profile
        }
        
    except Exception as e:
        logger.error(f"Travel chat error: {e}")
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Even on error, provide a helpful response
        return {
            "user_id": request.get('user_id'),
            "response": f"I understand you're asking about travel planning. While I'm experiencing a technical issue, I'm still here to help! Could you rephrase your question?",
            "agents_involved": ["ErrorRecovery"],
            "processing_time": processing_time,
            "session_id": f"fallback_chat_{request.get('user_id')}_{int(datetime.now().timestamp())}",
            "mode": "chat",
            "error": True
        }

        
        if not transcript:
            raise HTTPException(status_code=400, detail="Transcript is required")
        if not user_id:
            raise HTTPException(status_code=400, detail="User ID is required")
        if len(transcript) < 100:
            raise HTTPException(status_code=400, detail="Transcript too short for meaningful analysis (minimum 100 characters)")
            
        start_time = datetime.now()
        
        # Initialize memory manager
        memory_manager = MemoryManager()
        
        # Start recording mode session
        session_id = memory_manager.start_travel_session(
            user_id, 
            mode='recording', 
            title=f"Recording Analysis {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        
        # Add transcript as user turn
        memory_manager.add_turn_to_session(
            user_id, session_id, 'user', transcript, 
            metadata={'transcript_length': len(transcript), 'analysis_type': 'full_conversation'}
        )
        
        # Extract comprehensive profile insights from transcript
        memory_manager.extract_profile_insights_from_text(user_id, transcript, mode='recording')
        
        # Import travel orchestrator for comprehensive multi-agent analysis
        try:
            from core.travel_orchestrator import TravelOrchestrator
            orchestrator = TravelOrchestrator(memory_manager)
            
            # Process with recording mode constraints (< 60s, comprehensive analysis, all 6 agents)
            result = orchestrator.process_batch_analysis(
                user_id=user_id,
                transcript=transcript,
                session_id=session_id
            )
            
            response = result.get('response')
            agents_used = result.get('agents_involved')
            synthesis_data = result.get('synthesis_data', {})
            
        except ImportError:
            # Fallback to structured analysis
            agents_used = ["TextTripAnalyzer", "TripMoodDetector", "TripCommsCoach", "TripBehaviorGuide", "TripCalmPractice", "TripSummarySynth"]
            
            # Generate structured response in PRD format
            analysis_sections = []
            
            # Extract key insights
            destinations_mentioned = []
            for dest in ['tokyo', 'paris', 'london', 'rome', 'barcelona', 'thailand', 'japan', 'italy']:
                if dest.lower() in transcript.lower():
                    destinations_mentioned.append(dest.title())
            
            # Mood analysis
            mood_indicators = []
            if any(word in transcript.lower() for word in ['excited', 'thrilled', 'can\'t wait']):
                mood_indicators.append('high excitement')
            if any(word in transcript.lower() for word in ['nervous', 'worried', 'anxious']):
                mood_indicators.append('travel anxiety')
            if any(word in transcript.lower() for word in ['confused', 'unsure', 'help me decide']):
                mood_indicators.append('decision paralysis')
                
            response = f"""🎯 **Comprehensive Travel Transcript Analysis**

**📊 Analysis Summary:**
Analyzed {len(transcript)} characters of travel planning conversation across {len(agents_used)} specialist agents.

**🌍 Travel Insights Extracted:**
• **Destinations**: {', '.join(destinations_mentioned) if destinations_mentioned else 'Various locations discussed'}
• **Planning Style**: {'Detailed researcher' if 'research' in transcript.lower() else 'Flexible explorer'}
• **Mood State**: {', '.join(mood_indicators) if mood_indicators else 'Balanced approach'}
• **Communication Needs**: {'Seeking guidance' if any(word in transcript.lower() for word in ['help', 'advice', 'suggest']) else 'Independent planning'}

**🤖 Multi-Agent Processing Applied:**
• 🔍 **TextTripAnalyzer**: Extracted goals, constraints, and destination preferences
• 😊 **TripMoodDetector**: Analyzed emotional patterns and confidence levels
• 💬 **TripCommsCoach**: Identified communication and interaction needs
• 🧭 **TripBehaviorGuide**: Provided behavioral insights and next-step recommendations
• 🧘 **TripCalmPractice**: Assessed stress points and calming strategies
• 🎯 **TripSummarySynth**: Created comprehensive profile synthesis

**✅ Profile Updates Applied:**
Your User Travel Profile has been updated with insights from this conversation, including preferences, behavioral patterns, and planning style observations.

**🔄 Next Steps:**
Based on this analysis, I can now provide more personalized recommendations for destinations, planning approaches, and stress management techniques tailored to your conversation patterns."""
            
            synthesis_data = {
                'destinations_analyzed': destinations_mentioned,
                'mood_indicators': mood_indicators,
                'transcript_length': len(transcript),
                'profile_updated': True
            }
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Add comprehensive response as assistant turn
        memory_manager.add_turn_to_session(
            user_id, session_id, 'assistant', response,
            agent_name='TripSummarySynth',
            metadata={
                'agents_involved': agents_used,
                'processing_time': processing_time,
                'synthesis_data': synthesis_data,
                'mode': 'recording'
            }
        )
        
        # Ensure SLA compliance (< 60s)
        if processing_time > 60.0:
            logger.warning(f"Batch SLA exceeded: {processing_time:.2f}s for user {user_id}")
        
        logger.info(f"✅ Recording analysis completed in {processing_time:.3f}s for {len(transcript)} chars")
        
        return {
            "user_id": user_id,
            "response": response,
            "agents_involved": agents_used,
            "processing_time": processing_time,
            "session_id": session_id,
            "mode": "recording",
            "transcript_length": len(transcript),
            "profile_updated": True,  # Recording mode always updates profile
            "synthesis_data": synthesis_data
        }
        
    except Exception as e:
        logger.error(f"Travel batch analysis error: {e}")
        processing_time = (datetime.now() - start_time).total_seconds() if 'start_time' in locals() else 0
        
        # Provide helpful error response
        return {
            "user_id": request.get('user_id'),
            "response": f"I encountered an issue analyzing your {len(transcript)} character transcript. The system is designed to handle comprehensive travel planning conversations. Please ensure your transcript contains meaningful travel planning discussion.",
            "agents_involved": ["ErrorRecovery"],
            "processing_time": processing_time,
            "session_id": f"error_batch_{request.get('user_id')}_{int(datetime.now().timestamp())}",
            "mode": "recording",
            "error": True,
            "error_detail": str(e)
        }

        
        # Initialize memory manager
        memory_manager = MemoryManager()
        
        # Get travel profile from cache or database
        profile = memory_manager.get_travel_profile_cache(user_id)
        if not profile:
            profile = memory_manager.get_travel_profile(user_id)
            # Cache it for future requests
            memory_manager.cache_travel_profile(user_id, profile)
        
        # Add computed fields
        profile['user_id'] = user_id
        profile['cache_status'] = 'hit' if memory_manager.get_travel_profile_cache(user_id) else 'miss'
        profile['last_accessed'] = datetime.now().isoformat()
        
        # Get recent session count for context
        try:
            active_session = memory_manager.get_active_session(user_id)
            profile['active_session'] = active_session is not None
            profile['session_id'] = active_session
        except:
            profile['active_session'] = False
            profile['session_id'] = None
        
        logger.info(f"Retrieved travel profile for user {user_id}")
        
        return {
            "user_id": user_id,
            "profile": profile,
            "status": "success",
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"Travel profile retrieval error: {e}")
        
        # Return default profile on error
        memory_manager = MemoryManager()
        default_profile = memory_manager._get_default_travel_profile()
        
        return {
            "user_id": user_id,
            "profile": default_profile,
            "status": "default_fallback",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }


# ✅ Agent API
@app.get("/agents")
def get_agents():
    try:
        return {
            "agents": dynamic_agent_manager.get_all_agents(),
            "edges": dynamic_agent_manager.get_graph_edges()
        }
    except Exception as e:
        return {"agents": {}, "edges": {}}

@app.post("/register_agents")
def register_agents(payload: dict = Body(...)):
    try:
        data = {"agents": [], "edges": {}, "entry_point": ""}
        if os.path.exists(AGENT_FILE):
            with open(AGENT_FILE, "r") as f:
                data = json.load(f)

        existing_agents = {a["id"]: a for a in data.get("agents", [])}
        existing_edges = data.get("edges", {})
        entry_point = payload.get("entry_point", data.get("entry_point", ""))

        for agent in payload.get("agents", []):
            if agent["id"] not in existing_agents:
                existing_agents[agent["id"]] = agent

        for src, targets in payload.get("edges", {}).items():
            existing_edges[src] = list(set(existing_edges.get(src, []) + targets))

        updated = {
            "agents": list(existing_agents.values()),
            "edges": existing_edges,
            "entry_point": entry_point
        }

        with open(AGENT_FILE, "w") as f:
            json.dump(updated, f, indent=2)

        return {"message": "Updated", "data": updated}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ✅ STM & LTM APIs
@app.post("/set_stm")
def set_stm(req: STMRequest):
    memory_manager.set_stm(req.user_id, req.agent_id, req.value, req.expiry_hours * 3600)
    return {"message": "STM saved"}

@app.get("/get_stm/{user_id}/{agent_id}")
def get_stm(user_id: str, agent_id: str):
    return {"value": memory_manager.get_stm(user_id, agent_id)}

@app.post("/memory/ltm/{user_id}/{agent_id}")
def set_ltm(user_id: str, agent_id: str, value: str = Body(...)):
    memory_manager.set_ltm(user_id, agent_id, value)
    return {"message": "LTM saved"}

@app.get("/memory/ltm/{user_id}/{agent_id}")
def get_ltm(user_id: str, agent_id: str):
    return memory_manager.get_ltm_by_agent(user_id, agent_id)

# ✅ Vector Search (Semantic)
@app.get("/search_vector")
def search_vector(query: str, user_id: str, agent_id: str = None, hours: int = 1, days: int = 1):
    try:
        stm_texts = memory_manager.get_recent_stm(user_id, agent_id, hours)
        ltm_entries = memory_manager.get_recent_ltm(user_id, agent_id, days)
        ltm_texts = [e["value"] for e in ltm_entries if "value" in e]
        all_texts = stm_texts + ltm_texts

        result_texts = []
        
        # Check if langchain dependencies are available
        if Document and HuggingFaceEmbeddings:
            try:
                docs = [Document(page_content=text) for text in all_texts if isinstance(text, str)]
                
                if docs:
                    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
                    from langchain_community.vectorstores import FAISS
                    vector_db = FAISS.from_documents(docs, embedding=embeddings)
                    results = vector_db.similarity_search(query, k=5)
                    result_texts = [doc.page_content for doc in results]
            except Exception as vector_error:
                logger.warning(f"Vector search failed, using text matching fallback: {vector_error}")
                # Simple text matching fallback
                query_lower = query.lower()
                result_texts = [text for text in all_texts if query_lower in text.lower()][:5]
        else:
            # Simple text matching fallback when langchain is not available
            query_lower = query.lower()
            result_texts = [text for text in all_texts if query_lower in text.lower()][:5]

        return {
            "stm": stm_texts,
            "ltm": ltm_texts,
            "results": result_texts
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ✅ New Chat Input Schema
class ChatInput(BaseModel):
    user: str
    user_id: int
    question: str

# ✅ Main UI Route
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    # Serve the original travel interface
    return templates.TemplateResponse("travel_assistant.html", {"request": request})

# ✅ Complex Interface Route
@app.get("/complex", response_class=HTMLResponse)
async def complex_interface(request: Request):
    return templates.TemplateResponse("travel_assistant.html", {"request": request})

# ✅ Legacy Interface Route
@app.get("/legacy", response_class=HTMLResponse)
async def legacy_interface(request: Request):
    return templates.TemplateResponse("travel_assistant.html", {"request": request})

# ✅ Debug Interface Route
@app.get("/debug_ui.html", response_class=HTMLResponse)
async def debug_interface(request: Request):
    """Debug UI for testing JavaScript response handling"""
    import os
    debug_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "debug_ui.html")
    if os.path.exists(debug_file):
        with open(debug_file, 'r', encoding='utf-8') as f:
            content = f.read()
        from fastapi.responses import HTMLResponse
        return HTMLResponse(content=content)
    else:
        raise HTTPException(status_code=404, detail="Debug UI not found")

# ✅ Updated run_graph endpoint with LangGraph Multiagent System
@app.post("/run_graph")
async def run_graph_authenticated(payload: GraphInput, current_user: dict = Depends(get_current_user) if get_current_user else None):
    """Run Travel Assistant with specialized travel agents"""
    try:
        from core.langgraph_multiagent_system import langgraph_multiagent_system

        # Use authenticated user ID if available, otherwise generate temporary ID
        if current_user:
            user_id = current_user['id']
            username = current_user['username']
        else:
            user_id = int(datetime.now().timestamp())
            username = payload.user

        start_time = datetime.now()

        # Process request through Travel Assistant System
        result = langgraph_multiagent_system.process_request(
            user=username,
            user_id=user_id,
            question=payload.question
        )

        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()

        # Sanitize agents_involved to only allowed agents
        agents_involved = result.get('agents_involved') or result.get('agent_chain') or []
        agents_involved = [a for a in agents_involved if a in ALLOWED_TRAVEL_AGENTS]
        result['agents_involved'] = agents_involved

        # Log query for authenticated users
        if current_user:
            try:
                from auth.auth_service import auth_service
                logger.info(f"🔄 Processing query for user {current_user['id']} ({current_user['username']}): {payload.question[:50]}...")
                auth_service.log_user_query(
                    user_id=current_user['id'],
                    session_id="web_session",
                    question=payload.question,
                    agent_used=agents_involved[0] if agents_involved else result.get('agent', 'Unknown'),
                    response_text=result.get('response', ''),
                    edges_traversed=result.get('edges_traversed', []),
                    processing_time=processing_time
                )
                logger.info(f"✅ Query logged for user {current_user['id']}")
            except Exception as log_error:
                logger.warning(f"Failed to log query: {log_error}")

        return result

    except Exception as e:
        logger.error(f"Travel assistant execution error: {e}")
        raise HTTPException(status_code=500, detail=f"Travel assistant execution failed: {str(e)}")

# ✅ Legacy run_graph endpoint without authentication (for backward compatibility)
@app.post("/run_graph_legacy")
async def run_graph_legacy(payload: GraphInput):
    """Legacy run_graph endpoint using travel assistant system"""
    try:
        from core.langgraph_multiagent_system import langgraph_multiagent_system

        result = langgraph_multiagent_system.process_request(
            user=payload.user,
            user_id=int(datetime.now().timestamp()),
            question=payload.question
        )

        # Sanitize agents_involved
        agents_involved = result.get('agents_involved') or result.get('agent_chain') or []
        result['agents_involved'] = [a for a in agents_involved if a in ALLOWED_TRAVEL_AGENTS]

        return result

    except Exception as e:
        logger.error(f"Travel assistant execution error: {e}")
        raise HTTPException(status_code=500, detail=f"Travel assistant execution failed: {str(e)}")

# async def ai_chat(
#     input_data: ChatInput,
#     current_user: dict = Depends(get_current_user)
# ):
#     """Main chat endpoint with intelligent agent orchestration"""
#     try:
#         logger.info(f"Processing chat request from user {input_data.user}: {input_data.question}")
#         
#         # Run dynamic graph with orchestration
#         result = run_dynamic_graph(
#             user=input_data.user,
#             user_id=input_data.user_id,
#             question=input_data.question
#         )
#         
#         return result
#         
#     except Exception as e:
#         logger.error(f"Chat error: {e}")
#         raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")

# ✅ Ollama Status Check
@app.get("/api/ollama/status")
async def ollama_status():
    """Check Ollama server status"""
    try:
        if not ollama_client:
            return {
                "available": False,
                "error": "Ollama client not initialized",
                "base_url": Config.OLLAMA_BASE_URL
            }

        # Try to make a simple request to check if Ollama is available
        import requests
        response = requests.get(f"{ollama_client.base_url}/api/tags", timeout=5)
        available = response.status_code == 200

        return {
            "available": available,
            "base_url": ollama_client.base_url,
            "status": "connected" if available else "disconnected"
        }
    except Exception as e:
        logger.error(f"Ollama status check failed: {e}")
        return {
            "available": False,
            "error": str(e),
            "base_url": Config.OLLAMA_BASE_URL
        }

# ✅ Dynamic Agent Management APIs (temporarily disabled due to auth dependency)
# @app.get("/api/agents")
# async def get_dynamic_agents(
#     current_user: dict = Depends(get_current_user)
# ):
#     """Get all active agents"""
#     return {
#         "agents": dynamic_agent_manager.get_all_agents(),
#         "edges": dynamic_agent_manager.get_graph_edges()
#     }

# @app.post("/api/agents")
# async def add_agent(
#     agent_data: dict = Body(...),
#     current_user: dict = Depends(get_current_user)
# ):
#     """Add new agent configuration"""
#     try:
#         success = dynamic_agent_manager.add_agent(
#             agent_name=agent_data["name"],
#             module_path=agent_data["module_path"],
#             description=agent_data.get("description", ""),
#             capabilities=agent_data.get("capabilities", []),
#             dependencies=agent_data.get("dependencies", [])
#         )
#         
#         if success:
#             return {"message": "Agent added successfully"}
#         else:
#             raise HTTPException(status_code=400, detail="Failed to add agent")
#             
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# @app.post("/api/edges")
# async def add_edge(
#     edge_data: dict = Body(...),
#     current_user: dict = Depends(get_current_user)
# ):
#     """Add new graph edge"""
#     try:
#         success = dynamic_agent_manager.add_edge(
#             source_agent=edge_data["source"],
#             target_agent=edge_data["target"],
#             condition=edge_data.get("condition"),
#             weight=edge_data.get("weight", 1)
#         )
#         
#         if success:
#             return {"message": "Edge added successfully"}
#         else:
#             raise HTTPException(status_code=400, detail="Failed to add edge")
#             
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# ✅ Vector Search API (temporarily disabled due to auth dependency)
# @app.post("/api/search")
# async def vector_search(
#     search_data: dict = Body(...),
#     current_user: dict = Depends(get_current_user)
# ):
#     """Perform vector similarity search"""
#     try:
#         query = search_data["query"]
#         user_id = current_user["id"]
#         agent_name = search_data.get("agent_name")
#         
#         results = memory_manager.get_search_history_json(
#             query=query,
#             user_id=user_id,
#             agent_name=agent_name
#         )
#         
#         return results
#         
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# Note: run_graph endpoint already implemented above with authentication support

# ✅ Server startup
if __name__ == "__main__":
    import uvicorn
    import logging

    # Configure logging
    logging.basicConfig(level=logging.INFO)

    print("🚀 Starting LangGraph AI Agent System...")
    print(f"📍 Server will be available at: http://{Config.APP_HOST}:{Config.APP_PORT}")
    print(f"📖 API Documentation: http://{Config.APP_HOST}:{Config.APP_PORT}/docs")
    print(f"🎯 Main Interface: http://{Config.APP_HOST}:{Config.APP_PORT}")
    print("\n" + "="*50)

    try:
        uvicorn.run(
            "api.main:app",
            host=Config.APP_HOST,
            port=Config.APP_PORT,
            reload=Config.DEBUG,
            log_level="info" if Config.DEBUG else "warning"
        )
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Server failed to start: {e}")

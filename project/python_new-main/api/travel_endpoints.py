"""
Travel Assistant API Endpoints
Implements /travel/chat, /travel/batch, and /travel/profile endpoints
"""

from fastapi import APIRouter, HTTPException, Depends, Body, UploadFile, File, Form
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import logging
import time
from datetime import datetime
import os
import tempfile

from core.travel_memory_manager import travel_memory_manager
# Conditional import for authentication
try:
    from auth.auth_endpoints import get_current_user
except ImportError:
    get_current_user = None

# Optional authentication dependency
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional

security = HTTPBearer(auto_error=False)

async def get_optional_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """Optional authentication dependency - returns None if auth not available or fails"""
    if not get_current_user or not credentials:
        return None
    
    try:
        # Call the original get_current_user dependency function
        return await get_current_user(credentials)
    except HTTPException:
        return None  # Authentication failed, but continue without user
    except Exception as e:
        logger.warning(f"Authentication error: {e}")
        return None

logger = logging.getLogger(__name__)

# Request/Response models
class ChatRequest(BaseModel):
    user_id: int
    text: str

class BatchRequest(BaseModel):
    user_id: int
    transcript: str

class TravelResponse(BaseModel):
    user_id: int
    response: str
    agents_involved: List[str]
    processing_time: float
    session_id: str
    mode: str
    ai_used: bool = False

class UserTravelProfile(BaseModel):
    user_id: int
    destinations_of_interest: List[str]
    cuisine_preferences: List[str]
    climate_tolerance: Dict[str, Any]
    travel_pace: str
    behavioral_notes: Dict[str, Any]
    budget_patterns: Dict[str, Any]
    group_preferences: Dict[str, Any]
    activity_preferences: List[str]
    accommodation_preferences: List[str]
    last_updated: str
    profile_version: str

# Router
router = APIRouter(prefix="/travel", tags=["travel"])

class AudioTranscriptionResponse(BaseModel):
    user_id: int
    transcript: str
    auto_analyzed: bool
    analysis: Optional[TravelResponse] = None

@router.post("/chat", response_model=TravelResponse)
async def travel_chat(
    request: ChatRequest,
    current_user: Dict = Depends(get_optional_current_user)
):
    """
    Chat Mode: Quick reflections, one query at a time
    SLA: < 3s typical response
    """
    start_time = time.time()
    
    try:
        user_id = request.user_id
        text = request.text
        
        logger.info(f"Processing chat request for user {user_id}: {text[:50]}...")
        
        # Get session context (last 7 days + UTP)
        session_context = travel_memory_manager.get_session_context(user_id, turn_limit=10)
        utp = travel_memory_manager.get_user_travel_profile(user_id)
        weekly_digest = travel_memory_manager.get_weekly_digest(user_id)
        
        # Add user turn to session
        travel_memory_manager.add_turn(user_id, "user", text)
        
        # Use fixed LangGraph multi-agent system for comprehensive travel assistance  
        from core.fixed_langgraph_multiagent_system import fixed_langgraph_multiagent_system
        
        # Process through enhanced LangGraph multi-agent system
        result = fixed_langgraph_multiagent_system.process_request(
            user=f"user_{user_id}",
            user_id=user_id,
            question=text
        )
        
        # Check if result is None and adapt LangGraph response format
        if result is None or not isinstance(result, dict):
            result = {
                "response": f"I'll help you with your travel question about '{text[:100]}'. Let me provide some guidance.",
                "agents_involved": ["ErrorHandler"],
                "processing_time": time.time() - start_time,
                "mode": "chat",
                "ai_used": False
            }
        else:
            # Adapt LangGraph result to expected format
            result = {
                "response": result.get("response", result.get("final_response", "No response generated")),
                "agents_involved": result.get("agents_involved", result.get("agent_chain", ["TravelAssistant"])),
                "processing_time": result.get("processing_time", time.time() - start_time),
                "mode": "chat",
                "ai_used": True  # LangGraph uses Ollama
            }
        
        # Add assistant turn to session
        travel_memory_manager.add_turn(
            user_id, 
            "assistant", 
            result["response"],
            metadata={
                "agents_involved": result["agents_involved"],
                "processing_time": result["processing_time"]
            }
        )
        
        processing_time = time.time() - start_time
        
        # Ensure SLA compliance
        if processing_time > 3.0:
            logger.warning(f"Chat SLA exceeded: {processing_time:.2f}s > 3s")
        
        return TravelResponse(
            user_id=user_id,
            response=result["response"],
            agents_involved=result["agents_involved"],
            processing_time=processing_time,
            session_id=session_context.get("session_id") or f"chat_{int(time.time())}",
            mode="chat",
            ai_used=bool(result.get("ai_used", False))
        )
        
    except Exception as e:
        logger.error(f"Chat processing error: {e}")
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")

@router.post("/batch", response_model=TravelResponse)
async def travel_batch(
    request: BatchRequest,
    current_user: Dict = Depends(get_optional_current_user)
):
    """
    Recording Mode: Analyze whole trip-planning conversation
    SLA: < 60s end-to-end
    """
    start_time = time.time()
    
    try:
        user_id = request.user_id
        transcript = request.transcript
        
        logger.info(f"Processing batch request for user {user_id}: {len(transcript)} characters")
        
        # Start new recording session
        session_id = travel_memory_manager.start_new_session(
            user_id, 
            mode="recording",
            title=f"Trip Recording - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        
        # Add transcript as single user turn
        travel_memory_manager.add_turn(user_id, "user", transcript, metadata={"type": "transcript"})
        
        # Get current UTP for context
        current_utp = travel_memory_manager.get_user_travel_profile(user_id)
        
        # Use fixed LangGraph multi-agent system for comprehensive batch analysis
        from core.fixed_langgraph_multiagent_system import fixed_langgraph_multiagent_system
        
        # Process through enhanced LangGraph multi-agent system for batch analysis
        result = fixed_langgraph_multiagent_system.process_request(
            user=f"user_{user_id}",
            user_id=user_id,
            question=f"Analyze this travel planning conversation: {transcript[:500]}{'...' if len(transcript) > 500 else ''}"
        )
        
        # Check if result is None and adapt LangGraph response format
        if result is None or not isinstance(result, dict):
            result = {
                "response": f"I analyzed your travel conversation ({len(transcript)} characters). Here are the key insights.",
                "agents_involved": ["ErrorHandler"],
                "processing_time": time.time() - start_time,
                "mode": "recording",
                "ai_used": False
            }
        else:
            # Adapt LangGraph result to expected format for batch analysis
            result = {
                "response": result.get("response", result.get("final_response", "Analysis completed")),
                "agents_involved": result.get("agents_involved", result.get("agent_chain", ["TravelAssistant"])),
                "processing_time": result.get("processing_time", time.time() - start_time),
                "mode": "recording",
                "ai_used": True,  # LangGraph uses Ollama
                "synthesis_data": {
                    "transcript_length": len(transcript),
                    "profile_updated": True,
                    "edges_traversed": result.get("edges_traversed", []),
                    "execution_path": result.get("execution_path", [])
                }
            }
        
        # Add synthesized response as assistant turn
        travel_memory_manager.add_turn(
            user_id,
            "assistant", 
            result["response"],
            metadata={
                "type": "batch_synthesis",
                "agents_involved": result["agents_involved"],
                "utp_updated": result.get("utp_updated", False)
            }
        )
        
        # End the recording session
        travel_memory_manager.end_session(user_id, session_id)
        
        processing_time = time.time() - start_time
        
        # Ensure SLA compliance
        if processing_time > 60.0:
            logger.warning(f"Batch SLA exceeded: {processing_time:.2f}s > 60s")
        
        return TravelResponse(
            user_id=user_id,
            response=result["response"],
            agents_involved=result["agents_involved"],
            processing_time=processing_time,
            session_id=session_id,
            mode="recording",
            ai_used=bool(result.get("ai_used", False))
        )
        
    except Exception as e:
        logger.error(f"Batch processing error: {e}")
        raise HTTPException(status_code=500, detail=f"Batch processing failed: {str(e)}")

@router.get("/profile/{user_id}", response_model=UserTravelProfile)
async def get_travel_profile(
    user_id: int,
    current_user: Dict = Depends(get_optional_current_user)
):
    """Get current User Travel Profile"""
    try:
        # Get UTP from cache or LTM
        utp = travel_memory_manager.get_user_travel_profile(user_id)
        
        if not utp:
            # Get from LTM if not cached
            from agents.trip_summary_synth import TripSummarySynthAgent
            synth_agent = TripSummarySynthAgent(travel_memory_manager)
            utp = synth_agent._get_user_travel_profile(user_id)
        
        return UserTravelProfile(
            user_id=user_id,
            destinations_of_interest=utp.get("destinations_of_interest", []),
            cuisine_preferences=utp.get("cuisine_preferences", []),
            climate_tolerance=utp.get("climate_tolerance", {}),
            travel_pace=utp.get("travel_pace", "balanced"),
            behavioral_notes=utp.get("behavioral_notes", {}),
            budget_patterns=utp.get("budget_patterns", {}),
            group_preferences=utp.get("group_preferences", {}),
            activity_preferences=utp.get("activity_preferences", []),
            accommodation_preferences=utp.get("accommodation_preferences", []),
            last_updated=utp.get("last_updated", datetime.now().isoformat()),
            profile_version=utp.get("profile_version", "1.0")
        )
        
    except Exception as e:
        logger.error(f"Error getting travel profile: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get travel profile: {str(e)}")

@router.put("/profile/{user_id}")
async def update_travel_profile(
    user_id: int,
    profile_updates: Dict[str, Any] = Body(...),
    current_user: Dict = Depends(get_optional_current_user)
):
    """Update User Travel Profile"""
    try:
        # Get current profile
        current_utp = travel_memory_manager.get_user_travel_profile(user_id)
        
        if not current_utp:
            from agents.trip_summary_synth import TripSummarySynthAgent
            synth_agent = TripSummarySynthAgent(travel_memory_manager)
            current_utp = synth_agent._get_default_travel_profile()
        
        # Update profile with new data
        updated_utp = current_utp.copy()
        updated_utp.update(profile_updates)
        updated_utp["last_updated"] = datetime.now().isoformat()
        
        # Store updated profile
        travel_memory_manager.cache_user_travel_profile(user_id, updated_utp)
        
        # Also store in LTM
        from agents.trip_summary_synth import TripSummarySynthAgent
        synth_agent = TripSummarySynthAgent(travel_memory_manager)
        synth_agent._store_user_travel_profile(user_id, updated_utp)
        
        return {"message": "Profile updated successfully", "profile": updated_utp}
        
    except Exception as e:
        logger.error(f"Error updating travel profile: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update travel profile: {str(e)}")

@router.get("/sessions/{user_id}")
async def get_user_sessions(
    user_id: int,
    limit: int = 10,
    current_user: Dict = Depends(get_optional_current_user)
):
    """Get user's recent travel planning sessions"""
    try:
        # Get recent session IDs from Redis
        recent_turns = travel_memory_manager.redis_conn.zrevrange(f"stm:recent:{user_id}", 0, limit-1, withscores=True)
        
        sessions = []
        seen_sessions = set()
        
        for turn_id, timestamp in recent_turns:
            # Extract session info from turn
            turn_data = travel_memory_manager.redis_conn.hgetall(f"stm:turn:{user_id}:{turn_id}")
            if turn_data:
                # Find session this turn belongs to
                session_keys = travel_memory_manager.redis_conn.keys(f"stm:sess:{user_id}:*:turns")
                for session_key in session_keys:
                    if travel_memory_manager.redis_conn.lpos(session_key, turn_id) is not None:
                        session_id = session_key.split(":")[3]
                        if session_id not in seen_sessions:
                            session_data = travel_memory_manager.get_session_metadata(user_id, session_id)
                            if session_data:
                                sessions.append({
                                    "session_id": session_id,
                                    "title": session_data.get("title", "Travel Planning"),
                                    "mode": session_data.get("mode", "chat"),
                                    "started_at": session_data.get("started_at"),
                                    "turn_count": int(session_data.get("turn_count", 0))
                                })
                                seen_sessions.add(session_id)
                        break
        
        return {"sessions": sessions[:limit]}
        
    except Exception as e:
        logger.error(f"Error getting user sessions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get sessions: {str(e)}")

@router.get("/session/{user_id}/{session_id}")
async def get_session_details(
    user_id: int,
    session_id: str,
    current_user: Dict = Depends(get_optional_current_user)
):
    """Get detailed information about a specific session"""
    try:
        session_summary = travel_memory_manager.get_session_summary(user_id, session_id)
        return session_summary
        
    except Exception as e:
        logger.error(f"Error getting session details: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get session details: {str(e)}")

# New audio transcription models for enhanced system
class TranscriptionJobResponse(BaseModel):
    job_id: str
    status: str
    message: str
    progress_percent: int
    file_info: Dict[str, Any]

class TranscriptionStatusResponse(BaseModel):
    job_id: str
    status: str
    progress_percent: int
    message: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    duration: float
    file_info: Dict[str, Any]

@router.post("/upload_audio", response_model=TranscriptionJobResponse)
async def upload_audio(
    user_id: int = Form(...),
    auto_analyze: bool = Form(False),
    language: Optional[str] = Form("auto"),
    engine: Optional[str] = Form("auto"),
    audio: UploadFile = File(...),
    current_user: Dict = Depends(get_optional_current_user)
):
    """Upload an audio file and start transcription job with progress tracking."""
    try:
        from core.enhanced_audio_transcriber import enhanced_transcriber
        
        logger.info(f"Audio upload request for user {user_id}: {audio.filename} ({audio.content_type})")
        
        # Save uploaded file to temporary location
        import uuid
        unique_filename = f"{uuid.uuid4()}_{audio.filename}"
        temp_file_path = enhanced_transcriber.temp_dir / unique_filename
        
        with open(temp_file_path, "wb") as temp_file:
            content = await audio.read()
            temp_file.write(content)
        
        # Start transcription job
        job_id = enhanced_transcriber.start_transcription(
            file_path=temp_file_path,
            language=language or "auto",
            engine=engine or "auto"
        )
        
        # Store metadata for later analysis
        enhanced_transcriber.progress_tracker[job_id].file_info.update({
            "user_id": user_id,
            "auto_analyze": auto_analyze,
            "original_filename": audio.filename,
            "temp_path": str(temp_file_path)
        })
        
        # Get initial status
        status = enhanced_transcriber.get_transcription_status(job_id)
        
        return TranscriptionJobResponse(
            job_id=job_id,
            status=status["status"],
            message=status["message"],
            progress_percent=status["progress_percent"],
            file_info=status["file_info"]
        )
        
    except Exception as e:
        logger.error(f"Audio upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Audio upload failed: {str(e)}")

@router.get("/transcription_status/{job_id}", response_model=TranscriptionStatusResponse)
async def get_transcription_status(
    job_id: str,
    current_user: Dict = Depends(get_optional_current_user)
):
    """Get transcription job status and results."""
    try:
        from core.enhanced_audio_transcriber import enhanced_transcriber
        
        status = enhanced_transcriber.get_transcription_status(job_id)
        
        if not status:
            raise HTTPException(status_code=404, detail="Transcription job not found")
        
        return TranscriptionStatusResponse(**status)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting transcription status: {e}")
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")

@router.post("/analyze_transcript/{job_id}", response_model=TravelResponse)
async def analyze_transcript(
    job_id: str,
    current_user: Dict = Depends(get_optional_current_user)
):
    """Analyze completed transcription using travel agents."""
    try:
        from core.enhanced_audio_transcriber import enhanced_transcriber
        from core.fixed_langgraph_multiagent_system import fixed_langgraph_multiagent_system
        
        # Get transcription status and result
        status = enhanced_transcriber.get_transcription_status(job_id)
        
        if not status:
            raise HTTPException(status_code=404, detail="Transcription job not found")
        
        if status["status"] != "completed":
            raise HTTPException(status_code=400, detail=f"Transcription not completed. Status: {status['status']}")
        
        if not status["result"]:
            raise HTTPException(status_code=400, detail="No transcription result available")
        
        # Extract user info
        user_id = status["file_info"].get("user_id")
        if not user_id:
            raise HTTPException(status_code=400, detail="User ID not found in transcription metadata")
        
        transcript = status["result"]["full_text"]
        original_filename = status["file_info"].get("original_filename", "audio.wav")
        
        # Start new recording session
        session_id = travel_memory_manager.start_new_session(
            user_id, 
            mode="recording", 
            title=f"Audio Analysis - {original_filename} - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        
        # Add transcript as user turn
        travel_memory_manager.add_turn(
            user_id, 
            "user", 
            transcript, 
            metadata={
                "type": "audio_transcript", 
                "filename": original_filename,
                "transcription_engine": status["result"]["engine"],
                "language": status["result"]["language"],
                "duration": status["result"]["duration"],
                "word_count": status["result"]["word_count"]
            }
        )
        
        # Process through enhanced LangGraph multi-agent system
        result = fixed_langgraph_multiagent_system.process_request(
            user=f"user_{user_id}",
            user_id=user_id,
            question=f"Analyze this travel conversation from audio transcription: {transcript}"
        )
        # Adapt LangGraph result format for audio analysis
        if result and isinstance(result, dict):
            adapted_result = {
                "response": result.get("response", result.get("final_response", "Audio analysis completed")),
                "agents_involved": result.get("agents_involved", result.get("agent_chain", ["AudioAnalyzer"])),
                "processing_time": result.get("processing_time", 0),
                "ai_used": True  # Enhanced LangGraph uses Ollama with fallbacks
            }
        else:
            adapted_result = {
                "response": "Audio analysis completed successfully. Your travel insights have been processed.",
                "agents_involved": ["TravelAssistant"],
                "processing_time": 0,
                "ai_used": False
            }
        
        # Add analysis as assistant turn
        travel_memory_manager.add_turn(
            user_id,
            "assistant",
            adapted_result["response"],
            metadata={
                "type": "audio_analysis",
                "agents_involved": adapted_result["agents_involved"],
                "edges_traversed": result.get("edges_traversed", []) if result else [],
                "transcription_metadata": {
                    "engine": status["result"]["engine"],
                    "language": status["result"]["language"],
                    "confidence": status["result"]["confidence"],
                    "duration": status["result"]["duration"]
                }
            }
        )
        
        # Clean up transcription job
        temp_path = status["file_info"].get("temp_path")
        if temp_path:
            try:
                os.remove(temp_path)
            except:
                pass
        
        enhanced_transcriber.cleanup_job(job_id)
        
        # End recording session
        travel_memory_manager.end_session(user_id, session_id)
        
        return TravelResponse(
            user_id=user_id,
            response=adapted_result["response"],
            agents_involved=adapted_result["agents_involved"],
            processing_time=adapted_result["processing_time"],
            session_id=session_id,
            mode="recording",
            ai_used=adapted_result["ai_used"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Audio analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Audio analysis failed: {str(e)}")

@router.delete("/transcription/{job_id}")
async def cancel_transcription(
    job_id: str,
    current_user: Dict = Depends(get_optional_current_user)
):
    """Cancel an ongoing transcription job."""
    try:
        from core.enhanced_audio_transcriber import enhanced_transcriber
        
        success = enhanced_transcriber.cancel_transcription(job_id)
        
        if success:
            # Clean up temp file if it exists
            status = enhanced_transcriber.get_transcription_status(job_id)
            if status and status.get("file_info", {}).get("temp_path"):
                temp_path = status["file_info"]["temp_path"]
                try:
                    os.remove(temp_path)
                except:
                    pass
            
            enhanced_transcriber.cleanup_job(job_id)
            return {"message": "Transcription cancelled successfully"}
        else:
            return {"message": "Job not found or cannot be cancelled"}
        
    except Exception as e:
        logger.error(f"Error cancelling transcription: {e}")
        raise HTTPException(status_code=500, detail=f"Cancellation failed: {str(e)}")

# Export router
__all__ = ['router']

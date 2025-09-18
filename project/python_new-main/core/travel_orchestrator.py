"""
Travel-specific Orchestrator - Clean Implementation
Handles routing and coordination for travel agents with proper fallbacks
"""

import logging
import time
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class TravelOrchestrator:
    """Clean travel orchestrator with fallback responses"""
    
    def __init__(self, memory_manager):
        self.memory_manager = memory_manager
        self.execution_logs = []
        self.travel_agents = {}  # Initialize the travel_agents dict
        self._init_travel_agents()
        logger.info("Travel Orchestrator initialized")
    
    def _init_travel_agents(self):
        """Initialize travel agents with fallback handling"""
        try:
            self.travel_agents = {}  # Initialize empty dict
            
            agent_classes = {
                "TextTripAnalyzer": ("agents.text_trip_analyzer", "TextTripAnalyzerAgent"),
                "TripMoodDetector": ("agents.trip_mood_detector", "TripMoodDetectorAgent"),
                "TripCommsCoach": ("agents.trip_comms_coach", "TripCommsCoachAgent"),
                "TripBehaviorGuide": ("agents.trip_behavior_guide", "TripBehaviorGuideAgent"),
                "TripCalmPractice": ("agents.trip_calm_practice", "TripCalmPracticeAgent"),
                "TripSummarySynth": ("agents.trip_summary_synth", "TripSummarySynthAgent")
            }
            
            for agent_name, (module_path, class_name) in agent_classes.items():
                try:
                    module = __import__(module_path, fromlist=[class_name])
                    agent_class = getattr(module, class_name)
                    self.travel_agents[agent_name] = agent_class(self.memory_manager)
                    logger.debug(f"✅ Initialized {agent_name}")
                except ImportError as e:
                    logger.warning(f"⚠️ Could not import {agent_name}: {e} - using fallback")
                    self.travel_agents[agent_name] = None
                except Exception as e:
                    logger.warning(f"⚠️ Failed to initialize {agent_name}: {e} - using fallback")
                    self.travel_agents[agent_name] = None
            
            # Count successfully initialized agents
            active_agents = sum(1 for agent in self.travel_agents.values() if agent is not None)
            logger.info(f"Initialized {active_agents}/{len(self.travel_agents)} travel agents")
            
        except Exception as e:
            logger.error(f"Critical error initializing travel agents: {e}")
            # Set all agents to None for fallback mode
            agent_names = ["TextTripAnalyzer", "TripMoodDetector", "TripCommsCoach", 
                          "TripBehaviorGuide", "TripCalmPractice", "TripSummarySynth"]
            for agent_name in agent_names:
                self.travel_agents[agent_name] = None
    
    def _route_chat_query(self, query: str, profile: Dict) -> List[str]:
        """Router agent logic to select relevant agents (max 3 for chat mode)"""
        query_lower = query.lower()
        selected = []
        
        # Route based on query content and user profile
        if any(word in query_lower for word in ['plan', 'trip', 'destination', 'visit']):
            selected.append('TextTripAnalyzer')
        
        if any(word in query_lower for word in ['nervous', 'anxious', 'worried', 'feel', 'emotion', 'overwhelmed']):
            selected.append('TripMoodDetector')
            
        if any(word in query_lower for word in ['language', 'communicate', 'speak', 'talk', 'ask', 'hotel', 'staff']):
            selected.append('TripCommsCoach')
            
        if any(word in query_lower for word in ['choose', 'decide', 'between', 'options']):
            selected.append('TripBehaviorGuide')
            
        if any(word in query_lower for word in ['calm', 'relax', 'stress', 'overwhelmed']):
            selected.append('TripCalmPractice')
        
        # Ensure we have at least one agent and at most 3
        if not selected:
            selected = ['TextTripAnalyzer']  # Default agent
        
        # Remove duplicates and limit to 3
        selected = list(set(selected))[:3]
        logger.info(f"Chat mode: Router selected {len(selected)} agents: {selected}")
        
        return selected
    
    def process_chat_query(self, user_id: int, query: str, session_id: str,
                          context: List[Dict], profile: Dict) -> Dict[str, Any]:
        """Process chat mode query with intelligent response"""
        start_time = time.time()
        
        try:
            from api.main import generate_travel_response, ollama_client
            response = generate_travel_response(query)
            # Determine if Ollama was actually used
            ai_used = False
            try:
                ai_used = bool(
                    ollama_client and ollama_client.is_available() and 
                    ("trouble connecting to the AI system" not in (response or ""))
                )
            except Exception:
                ai_used = False
            
            processing_time = time.time() - start_time
            
            return {
                "response": response,
                "agents_involved": ["TravelAssistant"],
                "processing_time": processing_time,
                "mode": "chat",
                "ai_used": ai_used
            }
        except Exception as e:
            logger.error(f"Chat processing error: {e}")
            return {
                "response": f"I'm here to help with your travel planning. Could you please rephrase your question about '{query[:50]}'?",
                "agents_involved": ["ErrorHandler"],
                "processing_time": time.time() - start_time,
                "mode": "chat",
                "error": True,
                "ai_used": False
            }
    
    def process_batch_analysis(self, user_id: int, transcript: str, session_id: str) -> Dict[str, Any]:
        """Process batch mode analysis with comprehensive response"""
        start_time = time.time()
        
        try:
            from api.main import generate_travel_response, ollama_client
            response = generate_travel_response(transcript)
            # Determine if Ollama was actually used
            ai_used = False
            try:
                ai_used = bool(
                    ollama_client and ollama_client.is_available() and 
                    ("trouble connecting to the AI system" not in (response or ""))
                )
            except Exception:
                ai_used = False
            
            processing_time = time.time() - start_time
            
            # Update UTP with insights from transcript
            if self.memory_manager:
                try:
                    self.memory_manager.extract_profile_insights_from_text(user_id, transcript, mode='recording')
                except Exception as utp_error:
                    logger.debug(f"UTP update failed: {utp_error}")
            
            return {
                "response": response,
                "agents_involved": ["TravelAssistant", "ProfileUpdater"],
                "processing_time": processing_time,
                "mode": "recording",
                "synthesis_data": {
                    "transcript_length": len(transcript),
                    "profile_updated": True
                },
                "ai_used": ai_used
            }
        except Exception as e:
            logger.error(f"Batch processing error: {e}")
            return {
                "response": f"I analyzed your travel conversation. Here are key insights from your {len(transcript)} character discussion about travel planning.",
                "agents_involved": ["ErrorHandler"],
                "processing_time": time.time() - start_time,
                "mode": "recording",
                "error": True,
                "ai_used": False
            }
    
    def _log_execution(self, user_id: int, session_id: str, execution_id: str, 
                      agent_name: str, order: int, timestamp: float, success: bool, 
                      result: str, input_text: str, duration_ms: float = 0):
        """Log execution details"""
        log_entry = {
            "user_id": user_id,
            "session_id": session_id,
            "execution_id": execution_id,
            "agent_name": agent_name,
            "order": order,
            "timestamp": timestamp,
            "success": success,
            "result": result,
            "input_text": input_text,
            "duration_ms": duration_ms
        }
        self.execution_logs.append(log_entry)
    
    def _create_agent_state(self, user_id: int, query: str, mode: str, 
                           context: List[Dict], profile: Dict) -> Dict[str, Any]:
        """Create agent state for processing"""
        return {
            "user_id": user_id,
            "query": query,
            "mode": mode,
            "context": context,
            "profile": profile,
            "timestamp": datetime.now().isoformat()
        }
    
    def _create_synthesis_state(self, user_id: int, query: str, mode: str,
                               agent_responses: Dict[str, str], context: List[Dict], 
                               profile: Dict) -> Dict[str, Any]:
        """Create synthesis state for final response"""
        return {
            "user_id": user_id,
            "query": query,
            "mode": mode,
            "agent_responses": agent_responses,
            "context": context,
            "profile": profile,
            "timestamp": datetime.now().isoformat()
        }
    
    def _synthesize_responses(self, agent_responses: Dict[str, str], query: str) -> str:
        """Synthesize multiple agent responses into final response"""
        if not agent_responses:
            return f"I'll help you with your travel question about: {query[:100]}"
        
        # Simple synthesis - in practice this would be more sophisticated
        responses = list(agent_responses.values())
        return responses[0] if responses else f"I'll help you plan your trip: {query[:100]}"
    
    def _synthesize_batch_responses(self, agent_responses: Dict[str, str], transcript: str) -> str:
        """Synthesize batch analysis responses"""
        if not agent_responses:
            return f"I analyzed your travel conversation ({len(transcript)} characters). Here are the key insights."
        
        # Simple synthesis for batch mode
        responses = list(agent_responses.values())
        return responses[0] if responses else f"Travel analysis complete for {len(transcript)} character transcript."
    
    def _get_execution_path(self, user_id: int, session_id: str) -> List[Dict]:
        """Get execution path for user/session"""
        return [log for log in self.execution_logs 
                if log.get("user_id") == user_id and log.get("session_id") == session_id]
    
    def _get_fallback_response(self, text: str) -> str:
        """Generate fallback response"""
        return f"I'll help you with travel planning. Based on your message about '{text[:50]}', let me provide some guidance."

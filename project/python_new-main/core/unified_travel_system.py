#!/usr/bin/env python3
"""
🧳 Unified Travel AI System
Consolidates all LangGraph multi-agent implementations into one configurable system
"""

import json
import logging
import time
from typing import Dict, Any, List, Optional, TypedDict, Literal
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from langgraph.graph import StateGraph, END
from core.memory import MemoryManager
from core.ollama_client import ollama_client

logger = logging.getLogger(__name__)

class ProcessingMode(Enum):
    """Processing modes for different use cases"""
    ULTRA_FAST = "ultra_fast"  # <3s responses, basic processing
    BALANCED = "balanced"      # <10s responses, full processing
    COMPREHENSIVE = "comprehensive"  # <30s responses, deep analysis

class TravelSystemState(TypedDict, total=False):
    """Unified state for all processing modes"""
    user: str
    user_id: int
    question: str
    
    # Processing configuration
    mode: ProcessingMode
    max_agents: int
    timeout_seconds: int
    
    # Agent execution
    current_agent: str
    selected_agents: List[str]
    agent_responses: Dict[str, str]
    final_response: str
    
    # Context and memory
    context: Dict[str, Any]
    execution_path: List[Dict[str, Any]]
    processing_time: float
    
    # Results
    success: bool
    error: Optional[str]
    timestamp: str

@dataclass
class SystemConfiguration:
    """Configuration for the unified system"""
    mode: ProcessingMode
    max_agents: int
    timeout_seconds: int
    enable_memory: bool = True
    enable_vector_search: bool = True
    enable_fallbacks: bool = True
    temperature: float = 0.7
    
    @classmethod
    def ultra_fast(cls) -> 'SystemConfiguration':
        return cls(
            mode=ProcessingMode.ULTRA_FAST,
            max_agents=1,
            timeout_seconds=3,
            enable_memory=False,
            enable_vector_search=False,
            temperature=0.3
        )
    
    @classmethod
    def balanced(cls) -> 'SystemConfiguration':
        return cls(
            mode=ProcessingMode.BALANCED,
            max_agents=3,
            timeout_seconds=10,
            temperature=0.7
        )
    
    @classmethod
    def comprehensive(cls) -> 'SystemConfiguration':
        return cls(
            mode=ProcessingMode.COMPREHENSIVE,
            max_agents=6,
            timeout_seconds=30,
            temperature=0.8
        )

class UnifiedTravelSystem:
    """
    Unified Travel AI System
    - Configurable processing modes (ultra-fast, balanced, comprehensive)
    - Single codebase with mode-specific optimizations
    - Consistent API and error handling
    """
    
    def __init__(self, config: SystemConfiguration = None):
        self.config = config or SystemConfiguration.balanced()
        self.memory_manager = MemoryManager() if self.config.enable_memory else None
        self.agents_config = self._load_agents_config()
        self.graph = None
        self._build_system_graph()
        
        logger.info(f"✅ Unified Travel System initialized in {self.config.mode.value} mode")
    
    def _load_agents_config(self) -> Dict[str, Any]:
        """Load agent configuration"""
        try:
            with open("core/agents.json", 'r', encoding='utf-8') as f:
                config = json.load(f)
            return {agent['id']: agent for agent in config['agents']}
        except Exception as e:
            logger.error(f"Failed to load agents config: {e}")
            return self._get_fallback_agents()
    
    def _get_fallback_agents(self) -> Dict[str, Any]:
        """Fallback agent configuration"""
        return {
            "TextTripAnalyzer": {
                "id": "TextTripAnalyzer",
                "name": "Trip Analyzer",
                "keywords": ["plan", "trip", "budget", "destination"],
                "priority": 1
            },
            "TripSummarySynth": {
                "id": "TripSummarySynth",
                "name": "Summary Synthesizer",
                "keywords": ["summary", "synthesize", "complete"],
                "priority": 1
            }
        }
    
    def _build_system_graph(self):
        """Build the LangGraph based on configuration"""
        builder = StateGraph(TravelSystemState)
        
        # Add router
        builder.add_node("router", self._router_node)
        builder.set_entry_point("router")
        
        # Add agent nodes based on configuration
        routing_map = {}
        for agent_id in list(self.agents_config.keys())[:self.config.max_agents]:
            if agent_id != "RouterAgent":
                builder.add_node(agent_id, self._create_agent_node(agent_id))
                routing_map[agent_id] = agent_id
        
        # Add synthesizer
        builder.add_node("synthesizer", self._synthesizer_node)
        routing_map["synthesize"] = "synthesizer"
        
        # Configure routing based on mode
        if self.config.mode == ProcessingMode.ULTRA_FAST:
            # Direct routing: router -> agent -> end
            builder.add_conditional_edges("router", self._route_ultra_fast, routing_map)
            for agent_id in routing_map:
                if agent_id != "synthesize":
                    builder.add_edge(agent_id, END)
        else:
            # Full routing: router -> agents -> synthesizer -> end
            builder.add_conditional_edges("router", self._route_balanced, routing_map)
            for agent_id in routing_map:
                if agent_id != "synthesize":
                    builder.add_edge(agent_id, "synthesizer")
            builder.add_edge("synthesizer", END)
        
        self.graph = builder.compile()
        logger.info(f"🕸️ Graph built for {self.config.mode.value} mode with {len(routing_map)} nodes")
    
    def _router_node(self, state: TravelSystemState) -> TravelSystemState:
        """Intelligent routing based on mode and query analysis"""
        question = state.get("question", "")
        
        # Select best agent based on keywords and mode
        best_agent = self._select_best_agent(question)
        
        state["current_agent"] = "router"
        state["selected_agents"] = [best_agent]
        state["execution_path"] = [{
            "agent": "router",
            "action": f"Selected {best_agent}",
            "timestamp": datetime.now().isoformat()
        }]
        
        return state
    
    def _select_best_agent(self, question: str) -> str:
        """Select the best agent for the question"""
        question_lower = question.lower()
        best_score = 0
        best_agent = "TextTripAnalyzer"  # Default
        
        for agent_id, config in self.agents_config.items():
            if agent_id == "RouterAgent":
                continue
                
            score = 0
            keywords = config.get("keywords", [])
            
            # Keyword matching
            for keyword in keywords:
                if keyword.lower() in question_lower:
                    score += 1
            
            # Priority weighting
            priority = config.get("priority", 5)
            score += (6 - priority) * 0.1
            
            if score > best_score:
                best_score = score
                best_agent = agent_id
        
        return best_agent
    
    def _create_agent_node(self, agent_id: str):
        """Create agent processing node"""
        def agent_node(state: TravelSystemState) -> TravelSystemState:
            return self._process_agent(state, agent_id)
        return agent_node
    
    def _process_agent(self, state: TravelSystemState, agent_id: str) -> TravelSystemState:
        """Process query with specific agent"""
        question = state.get("question", "")
        agent_config = self.agents_config.get(agent_id, {})
        
        try:
            # Generate response based on mode
            if self.config.mode == ProcessingMode.ULTRA_FAST:
                response = self._get_fast_response(agent_id, question)
            else:
                response = self._get_full_response(agent_id, question, state)
            
            # Update state
            agent_responses = state.get("agent_responses", {})
            agent_responses[agent_id] = response
            state["agent_responses"] = agent_responses
            state["current_agent"] = agent_id
            
            # Update execution path
            execution_path = state.get("execution_path", [])
            execution_path.append({
                "agent": agent_id,
                "action": f"Generated response ({len(response)} chars)",
                "timestamp": datetime.now().isoformat()
            })
            state["execution_path"] = execution_path
            
            return state
            
        except Exception as e:
            logger.error(f"Agent {agent_id} error: {e}")
            if self.config.enable_fallbacks:
                fallback_response = self._get_fallback_response(agent_id, question)
                agent_responses = state.get("agent_responses", {})
                agent_responses[agent_id] = fallback_response
                state["agent_responses"] = agent_responses
            else:
                state["error"] = f"Agent {agent_id} failed: {str(e)}"
            
            return state
    
    def _get_fast_response(self, agent_id: str, question: str) -> str:
        """Ultra-fast response generation"""
        agent_config = self.agents_config.get(agent_id, {})
        agent_name = agent_config.get("name", agent_id)
        
        # Pre-defined fast responses
        fast_responses = {
            "TextTripAnalyzer": f"🗺️ **Quick Trip Analysis**: I'll help analyze your travel query '{question}'. Key considerations: destination planning, budget allocation, timing optimization.",
            "TripMoodDetector": f"😊 **Mood Check**: I sense enthusiasm in your travel query! Travel emotions are natural - channel that energy into productive planning.",
            "TripCommsCoach": f"💬 **Communication Tip**: For travel interactions, try: 'Excuse me, could you help me?' 'Thank you so much!' Universal politeness works everywhere.",
            "TripBehaviorGuide": f"🧭 **Next Steps**: Based on '{question}', prioritize: 1) Define core goals 2) Set realistic timeline 3) Research options 4) Make decisions!",
            "TripCalmPractice": f"🧘 **Stay Calm**: Take a deep breath. Travel planning can feel overwhelming, but break it into small steps. You've got this!",
            "TripSummarySynth": f"📋 **Quick Summary**: Analyzing your travel needs for '{question}'. Focus on essentials: dates, budget, destination, activities."
        }
        
        return fast_responses.get(agent_id, f"🤖 **{agent_name}**: Analyzing your travel query and providing tailored guidance.")
    
    def _get_full_response(self, agent_id: str, question: str, state: TravelSystemState) -> str:
        """Full AI response generation"""
        agent_config = self.agents_config.get(agent_id, {})
        system_prompt = agent_config.get("system_prompt_template", f"You are {agent_id}, a travel expert.")
        
        try:
            # Use Ollama for AI response
            response = ollama_client.generate_response(
                prompt=question,
                system_prompt=system_prompt,
                temperature=self.config.temperature
            )
            
            if response and len(response.strip()) > 20:
                return response.strip()
            else:
                return self._get_fast_response(agent_id, question)
                
        except Exception as e:
            logger.warning(f"AI generation failed for {agent_id}: {e}")
            return self._get_fast_response(agent_id, question)
    
    def _get_fallback_response(self, agent_id: str, question: str) -> str:
        """Fallback response when agent fails"""
        return f"I apologize, but {agent_id} is temporarily unavailable. However, I can still help with your travel query: '{question}'. Please let me know how I can assist you!"
    
    def _synthesizer_node(self, state: TravelSystemState) -> TravelSystemState:
        """Synthesize responses from multiple agents"""
        agent_responses = state.get("agent_responses", {})
        
        if not agent_responses:
            final_response = "I'm ready to help with your travel planning. Please share your question!"
        elif len(agent_responses) == 1:
            final_response = list(agent_responses.values())[0]
        else:
            # Multi-agent synthesis
            response_parts = ["🧳 **Comprehensive Travel Guidance**\n"]
            for agent_id, response in agent_responses.items():
                agent_name = self.agents_config.get(agent_id, {}).get("name", agent_id)
                response_parts.append(f"### {agent_name}")
                response_parts.append(response)
                response_parts.append("")
            
            response_parts.append("---")
            response_parts.append(f"*Coordinated response from {len(agent_responses)} travel specialists*")
            final_response = "\n".join(response_parts)
        
        state["final_response"] = final_response
        state["current_agent"] = "synthesizer"
        
        return state
    
    def _route_ultra_fast(self, state: TravelSystemState) -> str:
        """Ultra-fast routing - single agent"""
        selected_agents = state.get("selected_agents", [])
        return selected_agents[0] if selected_agents else "TextTripAnalyzer"
    
    def _route_balanced(self, state: TravelSystemState) -> str:
        """Balanced routing - can go to synthesizer"""
        selected_agents = state.get("selected_agents", [])
        if len(state.get("agent_responses", {})) >= 1:
            return "synthesize"
        return selected_agents[0] if selected_agents else "TextTripAnalyzer"
    
    def process_query(self, user: str, user_id: int, question: str, 
                     mode: ProcessingMode = None) -> Dict[str, Any]:
        """Process a travel query"""
        start_time = time.time()
        
        # Override mode if specified
        if mode and mode != self.config.mode:
            # Create temporary system with different mode
            temp_config = SystemConfiguration(
                mode=mode,
                max_agents=1 if mode == ProcessingMode.ULTRA_FAST else self.config.max_agents,
                timeout_seconds=3 if mode == ProcessingMode.ULTRA_FAST else self.config.timeout_seconds
            )
            temp_system = UnifiedTravelSystem(temp_config)
            return temp_system.process_query(user, user_id, question)
        
        try:
            # Initialize state
            initial_state = TravelSystemState(
                user=user,
                user_id=user_id,
                question=question,
                mode=self.config.mode,
                max_agents=self.config.max_agents,
                timeout_seconds=self.config.timeout_seconds,
                current_agent="",
                selected_agents=[],
                agent_responses={},
                final_response="",
                context={},
                execution_path=[],
                processing_time=0.0,
                success=True,
                timestamp=datetime.now().isoformat()
            )
            
            # Process through graph
            final_state = self.graph.invoke(initial_state)
            processing_time = time.time() - start_time
            
            # Update processing time
            final_state["processing_time"] = processing_time
            
            # Store interaction if memory is enabled
            if self.memory_manager:
                try:
                    self.memory_manager.store_interaction(
                        user_id=user_id,
                        agent_name=final_state.get("current_agent", "UnifiedSystem"),
                        query=question,
                        response=final_state.get("final_response", "")
                    )
                except Exception as e:
                    logger.warning(f"Failed to store interaction: {e}")
            
            return {
                "user": final_state.get("user"),
                "user_id": final_state.get("user_id"),
                "question": final_state.get("question"),
                "response": final_state.get("final_response", ""),
                "agent_responses": final_state.get("agent_responses", {}),
                "execution_path": final_state.get("execution_path", []),
                "processing_time": processing_time,
                "success": True,
                "mode": self.config.mode.value,
                "agents_involved": list(final_state.get("agent_responses", {}).keys()),
                "timestamp": final_state.get("timestamp")
            }
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"System processing error: {e}")
            
            return {
                "user": user,
                "user_id": user_id,
                "question": question,
                "response": f"I apologize, but I'm experiencing a technical issue. However, I'm still here to help with your travel planning! Could you rephrase your question?",
                "error": str(e),
                "processing_time": processing_time,
                "success": False,
                "mode": self.config.mode.value,
                "timestamp": datetime.now().isoformat()
            }

# Global instances for different modes
unified_ultra_fast = UnifiedTravelSystem(SystemConfiguration.ultra_fast())
unified_balanced = UnifiedTravelSystem(SystemConfiguration.balanced())
unified_comprehensive = UnifiedTravelSystem(SystemConfiguration.comprehensive())

# Default instance
unified_travel_system = unified_balanced
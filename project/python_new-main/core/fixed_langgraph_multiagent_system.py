"""
Fixed LangGraph Multi-Agent System for Travel Assistant
Specifically designed for travel agents with proper routing, memory management, and Ollama integration
"""

import json
import logging
import time
from typing import Dict, Any, List, Optional, TypedDict, Annotated
from datetime import datetime
from pathlib import Path
import operator

from langgraph.graph import StateGraph, END
from core.memory import MemoryManager

logger = logging.getLogger(__name__)

# Enhanced GraphState for travel agent communication
class TravelAgentState(TypedDict, total=False):
    """Enhanced state for travel agent LangGraph system"""
    user: str
    user_id: int
    question: str
    
    # Agent routing and communication
    current_agent: str
    next_agent: Optional[str]
    agent_chain: List[str]
    routing_decision: str
    
    # Responses and data
    response: str
    agent_responses: Dict[str, str]
    final_response: str
    
    # Context and memory
    context: Dict[str, Any]
    memory: Dict[str, Any]
    shared_data: Dict[str, Any]
    
    # Execution tracking
    edges_traversed: List[str]
    execution_path: List[Dict[str, Any]]
    timestamp: str
    
    # Processing metadata
    processing_time: float
    ai_used: bool
    error_occurred: bool

class FixedLangGraphMultiAgentSystem:
    """
    Fixed LangGraph Multi-Agent System for Travel Assistant
    Features:
    - Travel-specific agent routing (TextTripAnalyzer, TripMoodDetector, etc.)
    - Robust Ollama integration with fallbacks
    - Proper memory management
    - Error handling and recovery
    - Performance optimization
    """
    
    def __init__(self):
        self.memory_manager = MemoryManager()
        self.agents_config = {}
        self.agents = {}  # Dictionary to store agent instances
        self.routing_rules = {}
        self.agent_capabilities = {}
        self.graph = None
        self.ollama_client = None
        
        # Load configuration and initialize system
        self.load_travel_agent_configuration()
        self.setup_travel_routing_rules()
        self.initialize_ollama_client()
        self.build_travel_graph()
        
    def initialize_ollama_client(self):
        """Initialize Hybrid AI System for immediate responses with optional AI enhancement"""
        try:
            # Use Hybrid AI System for immediate responses + optional AI enhancement
            from core.hybrid_ai_system import hybrid_ai_system
            self.ollama_client = hybrid_ai_system
            logger.info("✅ Hybrid AI System initialized - immediate responses guaranteed")
        except Exception as hybrid_error:
            try:
                # Fallback to production client if hybrid fails
                from core.production_ollama_client import production_ollama_client
                self.ollama_client = production_ollama_client
                logger.info("✅ Production Ollama client initialized")
            except Exception as prod_error:
                try:
                    # Final fallback to enhanced client
                    from core.enhanced_ollama_client import enhanced_ollama_client
                    self.ollama_client = enhanced_ollama_client
                    logger.info("✅ Enhanced Ollama client initialized")
                except Exception as e:
                    logger.error(f"❌ No AI client available: {hybrid_error}, {prod_error}, {e}")
                    self.ollama_client = None
                    raise ConnectionError("AI client initialization failed - cannot provide responses")
    
    def load_travel_agent_configuration(self):
        """Load travel agent configuration with fallback to hardcoded config"""
        try:
            # Try to load from agents.json
            module_dir = Path(__file__).parent
            config_path = module_dir / "agents.json"
            
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    json_config = json.load(f)
                
                # Extract travel agents only
                travel_agent_ids = {
                    'TextTripAnalyzer', 'TripMoodDetector', 'TripCommsCoach',
                    'TripBehaviorGuide', 'TripCalmPractice', 'TripSummarySynth',
                    'RouterAgent'
                }
                
                self.agents_config = {}
                for agent in json_config.get('agents', []):
                    if agent['id'] in travel_agent_ids:
                        self.agents_config[agent['id']] = agent
                
                logger.info(f"✅ Loaded {len(self.agents_config)} travel agents from JSON")
            else:
                raise FileNotFoundError("agents.json not found")
                
        except Exception as e:
            logger.warning(f"⚠️ Could not load agents.json: {e}")
            logger.info("🔄 Using hardcoded travel agent configuration")
            self._load_hardcoded_travel_config()
    
    def _load_hardcoded_travel_config(self):
        """Load hardcoded travel agent configuration"""
        self.agents_config = {
            "RouterAgent": {
                "id": "RouterAgent",
                "name": "Router Agent",
                "description": "Routes queries to appropriate travel specialists",
                "keywords": [],
                "priority": 1,
                "system_prompt_template": "You are the Router Agent for a travel assistant system. Analyze travel queries and route them to appropriate specialists."
            },
            "TextTripAnalyzer": {
                "id": "TextTripAnalyzer",
                "name": "Trip Analyzer",
                "description": "Analyzes travel plans, budgets, and destinations",
                "keywords": ["plan", "trip", "budget", "destination", "analyze", "tokyo", "vacation", "travel", "where"],
                "priority": 2,
                "system_prompt_template": "You are TextTripAnalyzer, expert at analyzing travel plans, budgets, and destinations. Provide practical, actionable travel planning advice with specific recommendations.",
                "capabilities": ["text_analysis", "goal_extraction", "budget_analysis", "destination_research"]
            },
            "TripMoodDetector": {
                "id": "TripMoodDetector",
                "name": "Mood Detector",
                "description": "Detects and analyzes travel emotions and mood",
                "keywords": ["excited", "nervous", "worried", "feeling", "mood", "emotion", "anxious", "stress"],
                "priority": 2,
                "system_prompt_template": "You are TripMoodDetector, expert at analyzing travel emotions and mood. Be empathetic and supportive while providing emotional guidance for travelers.",
                "capabilities": ["mood_detection", "emotion_analysis", "stress_identification", "confidence_building"]
            },
            "TripCommsCoach": {
                "id": "TripCommsCoach",
                "name": "Communication Coach",
                "description": "Provides communication tips and phrases for travelers",
                "keywords": ["talk", "ask", "hotel", "staff", "communicate", "phrase", "say", "language", "speak"],
                "priority": 2,
                "system_prompt_template": "You are TripCommsCoach, expert in travel communication. Provide 2-3 practical phrases and communication tips for various travel situations.",
                "capabilities": ["communication_coaching", "phrasing_suggestions", "cultural_tips", "language_help"]
            },
            "TripBehaviorGuide": {
                "id": "TripBehaviorGuide", 
                "name": "Behavior Guide",
                "description": "Provides behavioral guidance and decision support",
                "keywords": ["stuck", "decide", "choose", "should", "next", "help", "what now", "action", "options"],
                "priority": 2,
                "system_prompt_template": "You are TripBehaviorGuide, expert in decision support and behavioral guidance. Provide clear next steps and actionable advice.",
                "capabilities": ["decision_support", "action_planning", "behavior_guidance", "problem_solving"]
            },
            "TripCalmPractice": {
                "id": "TripCalmPractice",
                "name": "Calm Practice",
                "description": "Provides calming techniques and stress relief",
                "keywords": ["overwhelmed", "stressed", "anxiety", "calm", "breathe", "panic", "relax", "nervous"],
                "priority": 1,  # High priority for stress
                "system_prompt_template": "You are TripCalmPractice, expert in travel stress relief and calming techniques. Provide immediate, practical calming methods.",
                "capabilities": ["stress_relief", "calming_techniques", "anxiety_management", "mindfulness"]
            },
            "TripSummarySynth": {
                "id": "TripSummarySynth",
                "name": "Summary Synthesizer",
                "description": "Synthesizes responses and creates comprehensive summaries",
                "keywords": ["summary", "summarize", "overview", "combine", "complete", "synthesize", "overall"],
                "priority": 1,  # High priority for synthesis
                "system_prompt_template": "You are TripSummarySynth, expert at synthesizing travel information comprehensively. Create unified, actionable travel guidance.",
                "capabilities": ["response_synthesis", "summary_generation", "integration", "comprehensive_analysis"]
            }
        }
        
        # Build capabilities map
        for agent_id, config in self.agents_config.items():
            self.agent_capabilities[agent_id] = {
                'capabilities': config.get('capabilities', []),
                'keywords': config.get('keywords', []),
                'description': config.get('description', ''),
                'priority': config.get('priority', 5),
                'system_prompt_template': config.get('system_prompt_template', '')
            }
    
    def setup_travel_routing_rules(self):
        """Setup intelligent routing rules for travel agents"""
        self.routing_rules = {
            "RouterAgent": {
                "trip_analysis": ["TextTripAnalyzer"],
                "mood_support": ["TripMoodDetector"],
                "communication_help": ["TripCommsCoach"],
                "decision_support": ["TripBehaviorGuide"],
                "stress_relief": ["TripCalmPractice"],
                "summary_request": ["TripSummarySynth"],
                "complex_travel": ["TextTripAnalyzer", "TripMoodDetector"],
                "default": ["TextTripAnalyzer"]
            }
        }
        
        logger.info("✅ Travel routing rules configured")
    
    def build_travel_graph(self) -> StateGraph:
        """Build the complete travel agent LangGraph"""
        try:
            builder = StateGraph(TravelAgentState)
            
            # Create routing map for conditional edges
            routing_map = {}
            
            # Add all travel agent nodes
            for agent_id in self.agents_config.keys():
                if agent_id == "RouterAgent":
                    builder.add_node("RouterAgent", self._router_agent_node)
                    continue
                
                # Create travel agent node
                agent_method = self._create_travel_agent_node(agent_id)
                builder.add_node(agent_id, agent_method)
                
                # Add to routing map
                routing_map[self._get_travel_routing_key(agent_id)] = agent_id
                routing_map[agent_id] = agent_id
            
            # Add ResponseSynthesizer
            builder.add_node("ResponseSynthesizer", self._response_synthesizer_node)
            routing_map["synthesize"] = "ResponseSynthesizer"
            
            # Set entry point
            builder.set_entry_point("RouterAgent")
            
            # Add conditional edges from RouterAgent
            builder.add_conditional_edges(
                "RouterAgent",
                self._route_from_travel_router,
                routing_map
            )
            
            # Add conditional edges from each travel agent
            for agent_id in self.agents_config.keys():
                if agent_id != "RouterAgent":
                    builder.add_conditional_edges(
                        agent_id,
                        self._route_to_next_travel_agent,
                        {**routing_map, "end": END}
                    )
            
            # ResponseSynthesizer always ends
            builder.add_edge("ResponseSynthesizer", END)
            
            self.graph = builder.compile()
            logger.info(f"✅ Built travel LangGraph with {len(self.agents_config)} agents")
            
        except Exception as e:
            logger.error(f"❌ Error building travel graph: {e}")
            raise
    
    def _create_travel_agent_node(self, agent_id: str):
        """Create a travel agent node function"""
        def travel_agent_node(state: TravelAgentState) -> TravelAgentState:
            return self._execute_travel_agent(state, agent_id)
        return travel_agent_node
    
    def _execute_travel_agent(self, state: TravelAgentState, agent_id: str) -> TravelAgentState:
        """Execute travel agent with robust Ollama integration and fallbacks"""
        start_time = time.time()
        
        try:
            question = state.get("question", "")
            user_id = state.get("user_id", 0)
            agent_config = self.agents_config.get(agent_id, {})
            
            if not question:
                logger.warning(f"Empty question in {agent_id}")
                question = f"General {agent_id} inquiry"
            
            # Build context for the agent
            context = self._build_travel_context(state, agent_id)
            
            # Generate response and track AI usage
            response, ai_used = self._generate_travel_response_with_tracking(agent_id, agent_config, question, context)
            
            # Update state
            updated_state = state.copy()
            updated_state["current_agent"] = agent_id
            
            # Update agent responses
            agent_responses = state.get("agent_responses", {})
            agent_responses[agent_id] = response
            updated_state["agent_responses"] = agent_responses
            
            # Update execution path
            execution_path = state.get("execution_path", [])
            execution_path.append({
                "agent": agent_id,
                "action": f"Provided {agent_config.get('name', agent_id)} analysis",
                "timestamp": datetime.now().isoformat(),
                "processing_time": time.time() - start_time,
                "ai_used": ai_used
            })
            updated_state["execution_path"] = execution_path
            
            # Store in memory
            self._store_travel_interaction(user_id, agent_id, question, response)
            
            # Update processing metadata - track if ANY agent used AI
            updated_state["ai_used"] = updated_state.get("ai_used", False) or ai_used
            
            logger.info(f"✅ {agent_id} completed analysis in {time.time() - start_time:.2f}s (AI: {ai_used})")
            return updated_state
            
        except Exception as e:
            logger.error(f"❌ {agent_id} error: {e}")
            
            # Error recovery
            updated_state = state.copy()
            updated_state["current_agent"] = agent_id
            updated_state["error_occurred"] = True
            
            agent_responses = state.get("agent_responses", {})
            agent_responses[agent_id] = self._get_error_fallback_response(agent_id, question)
            updated_state["agent_responses"] = agent_responses
            
            return updated_state
    
    def _generate_travel_response_with_tracking(self, agent_id: str, agent_config: Dict[str, Any], question: str, context: str) -> tuple[str, bool]:
        """Generate travel response with AI usage tracking"""
        ai_used = False
        
        try:
            # Try Ollama first
            if self.ollama_client:
                system_prompt = agent_config.get('system_prompt_template', '')
                if not system_prompt:
                    system_prompt = f"You are {agent_config.get('name', agent_id)}, a travel specialist. Provide helpful, practical travel advice."
                
                try:
                    # Use Ollama client with proper tracking
                    response = self.ollama_client.generate_response(
                        prompt=question,
                        system_prompt=system_prompt,
                        agent_name=agent_id
                    )
                    
                    # Check if we got a real response from Ollama
                    if response and len(response.strip()) > 30:
                        # Check for AI indicators in the response
                        if not any(keyword in response for keyword in ["I'd help", "I'm currently unable", "technical difficulties"]):
                            ai_used = True
                            logger.info(f"✅ {agent_id} generated AI response ({len(response)} chars)")
                            return response.strip(), ai_used
                        else:
                            logger.info(f"⚡ {agent_id} fallback response detected, marking as non-AI")
                            return response.strip(), False
                            
                except Exception as ollama_error:
                    logger.warning(f"⚠️ {agent_id} Ollama error: {ollama_error}")
            
            # Use intelligent fallback
            response = self._get_intelligent_travel_fallback(agent_id, question)
            logger.info(f"📝 {agent_id} using intelligent fallback ({len(response)} chars)")
            return response, False
            
        except Exception as e:
            logger.error(f"❌ {agent_id} response generation error: {e}")
            response = self._get_error_fallback_response(agent_id, question)
            return response, False
    
    def _generate_travel_response(self, agent_id: str, agent_config: Dict[str, Any], question: str, context: str) -> str:
        """Generate travel response with Ollama or intelligent fallback"""
        try:
            # Try Ollama first
            if self.ollama_client:
                system_prompt = agent_config.get('system_prompt_template', '')
                if not system_prompt:
                    system_prompt = f"You are {agent_config.get('name', agent_id)}, a travel specialist. Provide helpful, practical travel advice."
                
                # Enhanced prompt with context
                enhanced_prompt = f"Travel Query: {question}\n\nContext: {context}\n\nPlease provide specific, actionable travel guidance."
                
                try:
                    # Check if Hybrid AI System (returns dict) or regular client (returns string)
                    if hasattr(self.ollama_client, '_get_intelligent_response'):
                        # Hybrid AI System
                        result = self.ollama_client.generate_response(
                            prompt=question,
                            system_prompt=system_prompt,
                            agent_name=agent_id
                        )
                        if isinstance(result, dict):
                            response = result.get('response', '')
                            ai_used = result.get('ai_used', False)
                            response_type = result.get('response_type', 'unknown')
                            logger.info(f"✅ {agent_id} generated {response_type} response ({len(response)} chars) - AI: {ai_used}")
                            return response.strip()
                        else:
                            response = result
                    elif hasattr(self.ollama_client, '_enhance_prompt_for_agent'):
                        # Production Ollama Client
                        response = self.ollama_client.generate_response(
                            prompt=question,
                            system_prompt=system_prompt,
                            agent_name=agent_id
                        )
                    else:
                        # Regular clients
                        response = self.ollama_client.generate_response(
                            prompt=enhanced_prompt,
                            system_prompt=system_prompt
                        )
                    
                    if response and len(response.strip()) > 15:
                        logger.info(f"✅ {agent_id} generated response ({len(response)} chars)")
                        return response.strip()
                        
                except Exception as ollama_error:
                    logger.warning(f"⚠️ {agent_id} Ollama error: {ollama_error}")
            
            # Use intelligent fallback
            return self._get_intelligent_travel_fallback(agent_id, question)
            
        except Exception as e:
            logger.error(f"❌ {agent_id} response generation error: {e}")
            return self._get_error_fallback_response(agent_id, question)
    
    def _get_intelligent_travel_fallback(self, agent_id: str, question: str) -> str:
        """Get intelligent travel fallback responses based on agent type"""
        question_lower = question.lower()
        
        if agent_id == "TextTripAnalyzer":
            if any(dest in question_lower for dest in ["tokyo", "japan"]):
                return """🗾 **Tokyo Trip Analysis**

**Essential Planning Steps:**
• **Best Time**: Spring (Mar-May) for cherry blossoms or autumn (Sep-Nov) for comfortable weather
• **Budget**: Mid-range travelers should budget $150-200/day including accommodation
• **Must-Do**: Senso-ji Temple, Tokyo Skytree, Shibuya Crossing, and authentic ramen experiences
• **Transportation**: Get a JR Pass before arrival for unlimited train travel
• **Accommodation**: Stay in Shibuya or Shinjuku for convenience

**Pro Tips:**
✓ Book accommodation early for better rates
✓ Learn basic Japanese phrases
✓ Download Google Translate with camera feature
✓ Carry cash - many places don't accept cards

Your Tokyo adventure will be amazing with proper planning!"""
            
            elif any(word in question_lower for word in ["budget", "money", "cost"]):
                return """💰 **Smart Travel Budgeting**

**Budget Breakdown (Daily):**
• **Accommodation**: 30-40% of daily budget
• **Food**: 25-30% (mix street food with restaurants)
• **Activities**: 20-25% (prioritize must-see attractions)
• **Transportation**: 10-15% (use public transport)
• **Buffer**: 5-10% for unexpected expenses

**Money-Saving Tips:**
✓ Book flights 6-8 weeks in advance
✓ Use accommodation with kitchen facilities
✓ Take advantage of free walking tours
✓ Visit during shoulder season for better prices

**Planning Strategy:**
1. Set total budget first
2. Research destination costs
3. Prioritize must-have experiences
4. Build in flexibility for spontaneous discoveries

Smart budgeting leads to better experiences!"""
            
            else:
                return """🗺️ **Comprehensive Trip Planning**

**Step-by-Step Planning:**
1. **Define Goals**: What do you want from this trip?
2. **Set Budget**: Realistic budget based on your finances
3. **Choose Dates**: Consider weather and seasonal factors
4. **Research Destination**: Culture, customs, and key attractions
5. **Book Essentials**: Flights, accommodation, and major activities

**Planning Timeline:**
• **8-12 weeks before**: Book flights and accommodation
• **4-6 weeks before**: Plan detailed itinerary and book activities
• **1-2 weeks before**: Confirm bookings and prepare documents
• **Final week**: Pack and download essential apps

**Success Formula:**
✓ 70% planned, 30% spontaneous
✓ Focus on experiences over perfect schedules
✓ Prepare for the unexpected with backup plans

Great trips start with thoughtful planning!"""
        
        elif agent_id == "TripMoodDetector":
            if any(word in question_lower for word in ["nervous", "anxious", "worried"]):
                return """🧠 **Travel Anxiety Support**

**Your Feelings Are Completely Normal!**
Travel anxiety affects most people, especially before big trips. These mixed emotions actually show you care about having a great experience.

**Emotional Balance Strategy:**
• **Excitement**: Channel this into research and planning fun activities
• **Nervousness**: Address with practical preparation (documents, reservations, packing lists)
• **Confidence**: Remember that millions travel safely every day

**Immediate Anxiety Relief:**
1. **Deep Breathing**: 4 counts in, hold 4, out 6 counts
2. **Perspective**: Focus on the amazing experiences ahead
3. **Preparation**: Make detailed lists to feel more in control
4. **Support**: Share concerns with experienced travelers

**Mindset Shift:**
"My nervousness shows I care about this trip. I'm prepared and capable of handling whatever comes up."

You've got this! Your emotional awareness will make for a more mindful, rewarding journey. 🌟"""
            
            else:
                return """😊 **Travel Emotional Wellness**

**Understanding Your Travel Emotions:**
Every traveler experiences a mix of emotions - excitement, anticipation, nervousness, and curiosity. This emotional cocktail is part of what makes travel so transformative.

**Emotional Travel Tips:**
• **Pre-Trip**: Embrace both excitement and nerves as natural
• **During Travel**: Practice mindfulness and stay present
• **Challenges**: Remember that problems are part of the adventure story
• **Connections**: Be open to new experiences and people

**Mood Boosters:**
✓ Keep a travel journal to capture memories
✓ Take photos that tell your story
✓ Try local experiences that challenge you gently
✓ Celebrate small victories and discoveries

**Remember**: The best travel stories often come from unexpected moments and the emotions they create. Trust your instincts and enjoy the journey!"""
        
        elif agent_id == "TripCommsCoach":
            return """💬 **Essential Travel Communication**

**Universal Phrases (Learn in Local Language):**
1. **"Hello"** and **"Thank you"** - Opens doors everywhere
2. **"Excuse me, do you speak English?"** - Polite conversation starter  
3. **"Can you help me?"** - Most people want to help friendly travelers
4. **"Where is...?"** - Essential for navigation
5. **"How much?"** - Important for shopping and services

**Hotel Communication Tips:**
• **Check-in**: "I have a reservation under [name]"
• **Upgrades**: "If you have any complimentary upgrades available, we'd be grateful"
• **Issues**: "Could you please help me with..."
• **Checkout**: "Could you call a taxi/arrange transportation?"

**Restaurant Communication:**
• **Seating**: "Table for [number], please"
• **Ordering**: "I would like..." or "Could I have..."
• **Dietary**: "I'm allergic to..." or "I don't eat..."
• **Bill**: "Check, please" or "The bill, please"

**Magic Communication Tips:**
✓ Smile - universal language
✓ Point to phrases in guidebook
✓ Use phone translation apps
✓ Be patient and grateful

Confidence in communication comes with practice!"""
        
        elif agent_id == "TripBehaviorGuide":
            return """🧭 **Smart Travel Decision Making**

**Decision Framework for Travelers:**
1. **Clarify Priorities**: What matters most? (budget, experiences, comfort, adventure)
2. **Research Options**: Spend 2 hours max researching each major choice
3. **Apply Filters**: Use your priorities to eliminate poor fits
4. **Gut Check**: After analysis, what feels right?
5. **Decide & Move**: Perfect decisions don't exist - good decisions do

**Common Travel Decisions:**
• **Destinations**: Weather vs crowds vs budget vs interests
• **Accommodation**: Location vs amenities vs price vs reviews
• **Activities**: Must-dos vs hidden gems vs spontaneous discoveries
• **Transportation**: Speed vs cost vs experience vs convenience

**Decision Tools:**
✓ **Pros/Cons List**: Classic but effective
✓ **Priority Scoring**: Rate options 1-10 on your key factors
✓ **Coin Flip Test**: Notice which outcome you're hoping for
✓ **Future Self**: What would you regret NOT doing?

**Action Steps:**
1. Set decision deadline
2. Gather information efficiently
3. Apply your framework
4. Choose and commit
5. Prepare backup plans

Trust your judgment - you know yourself best!"""
        
        elif agent_id == "TripCalmPractice":
            return """🧘 **Instant Travel Calm Techniques**

**Right Now Calming (Use Anywhere):**
1. **4-7-8 Breathing**: Inhale 4 counts → Hold 7 counts → Exhale 8 counts (repeat 3x)
2. **5-4-3-2-1 Grounding**: Notice 5 things you see, 4 you hear, 3 you touch, 2 you smell, 1 you taste
3. **Progressive Muscle**: Tense and release muscle groups starting from toes up
4. **Positive Mantras**: "I am prepared, I am capable, I can adapt to anything"

**Travel Stress Prevention:**
• **Before Trip**: Create detailed but flexible plans
• **At Airport**: Arrive early and bring entertainment
• **New Places**: Research one comfort item (favorite restaurant type, familiar store)
• **Language Barriers**: Download offline translation apps

**Overwhelm Management:**
✓ **One Thing Rule**: Focus on just the next single step
✓ **Good Enough Planning**: Perfect plans kill spontaneous magic
✓ **Help is Available**: Most problems can be solved locally
✓ **Story Perspective**: This will be a great story later

**Travel Mindfulness:**
"I don't need to control everything. The joy is in the journey, not perfect execution."

Take three deep breaths right now. You've got this! 🌱"""
        
        elif agent_id == "TripSummarySynth":
            return """📋 **Comprehensive Travel Planning Synthesis**

**Your Travel Planning Status:**
✅ **Intent Identified**: Clear travel planning objectives
✅ **Expert Guidance**: Multi-specialist travel advice provided  
✅ **Action Framework**: Ready for implementation
✅ **Support Available**: Ongoing assistance for all travel needs

**Integrated Travel Strategy:**

**Phase 1 - Foundation (This Week):**
• Finalize destination and travel dates
• Set realistic budget parameters
• Book major transportation (flights/trains)
• Secure accommodation with flexible cancellation

**Phase 2 - Development (2-4 weeks out):**
• Research and book key activities/attractions
• Handle documentation (visas, travel insurance)
• Plan rough daily itinerary with buffer time
• Research local customs and basic phrases

**Phase 3 - Finalization (1-2 weeks out):**
• Confirm all bookings and reservations
• Prepare packing lists and travel documents
• Download essential apps (maps, translation, transport)
• Set up travel notifications and backup contacts

**Success Principles:**
• **70% Planned, 30% Spontaneous**: Perfect balance for memorable trips
• **Quality over Quantity**: Better to do fewer things well
• **Local Integration**: Embrace local culture and unexpected opportunities
• **Flexible Mindset**: The best travel stories come from plan deviations

**Next Action**: Choose ONE item from Phase 1 and complete it today. Momentum beats perfection!

Ready to turn your travel dreams into unforgettable reality! 🌟"""
        
        else:
            return f"I'm {agent_config.get('name', agent_id)}, ready to help with your travel planning needs. Please share more details about what you'd like assistance with!"
    
    def _get_error_fallback_response(self, agent_id: str, question: str) -> str:
        """Get error fallback response"""
        agent_name = self.agents_config.get(agent_id, {}).get('name', agent_id)
        return f"I'm {agent_name} and I'm here to help with your travel question about '{question[:50]}...'. While I'm experiencing a brief technical issue, I'm still ready to provide travel guidance. Could you please rephrase your question?"
    
    def _build_travel_context(self, state: TravelAgentState, agent_id: str) -> str:
        """Build context for travel agents"""
        context_parts = []
        
        # Add previous agent responses as context
        agent_responses = state.get("agent_responses", {})
        for other_agent_id, response in agent_responses.items():
            if other_agent_id != agent_id and response:
                agent_name = self.agents_config.get(other_agent_id, {}).get('name', other_agent_id)
                context_parts.append(f"{agent_name}: {response[:100]}{'...' if len(response) > 100 else ''}")
        
        return "\n".join(context_parts) if context_parts else "No previous context available."
    
    def _router_agent_node(self, state: TravelAgentState) -> TravelAgentState:
        """Router agent analyzes query and determines travel agent routing"""
        question = state.get("question", "")
        
        # Analyze query to determine best travel agent
        routing_decision = self._analyze_travel_query_for_routing(question)
        
        # Update state
        updated_state = state.copy()
        updated_state["current_agent"] = "RouterAgent"
        updated_state["routing_decision"] = routing_decision
        updated_state["agent_chain"] = [routing_decision] if routing_decision != "synthesize" else []
        updated_state["edges_traversed"] = state.get("edges_traversed", []) + ["RouterAgent"]
        
        # Add execution path entry
        execution_path = state.get("execution_path", [])
        execution_path.append({
            "agent": "RouterAgent",
            "action": f"Routed travel query to {routing_decision}",
            "timestamp": datetime.now().isoformat()
        })
        updated_state["execution_path"] = execution_path
        
        logger.info(f"🧭 Router decided: {routing_decision} for travel query: {question[:50]}...")
        return updated_state
    
    def _analyze_travel_query_for_routing(self, question: str) -> str:
        """Analyze travel query and select best travel agent"""
        question_lower = question.lower()
        best_agent = None
        best_score = 0
        
        # Score each travel agent based on keywords and context
        for agent_id, config in self.agents_config.items():
            if agent_id == "RouterAgent":
                continue
                
            score = 0
            
            # Keyword matching
            keywords = config.get('keywords', [])
            for keyword in keywords:
                if keyword in question_lower:
                    score += 2
            
            # Priority boost (lower number = higher priority)
            priority = config.get('priority', 5)
            if priority == 1:
                score += 1
            
            # Context-based scoring
            if agent_id == "TripCalmPractice" and any(word in question_lower for word in ["anxiety", "stressed", "overwhelmed", "nervous", "panic"]):
                score += 3
            elif agent_id == "TripMoodDetector" and any(word in question_lower for word in ["feeling", "excited", "worried", "mood"]):
                score += 3
            elif agent_id == "TripCommsCoach" and any(word in question_lower for word in ["communicate", "talk", "ask", "language", "phrase"]):
                score += 3
            elif agent_id == "TripBehaviorGuide" and any(word in question_lower for word in ["decide", "choose", "stuck", "options"]):
                score += 3
            elif agent_id == "TripSummarySynth" and any(word in question_lower for word in ["summary", "overview", "synthesize"]):
                score += 3
            elif agent_id == "TextTripAnalyzer" and any(word in question_lower for word in ["plan", "trip", "destination", "budget"]):
                score += 3
            
            if score > best_score:
                best_score = score
                best_agent = agent_id
        
        # Default to TextTripAnalyzer if no clear match
        return best_agent or "TextTripAnalyzer"
    
    def _get_travel_routing_key(self, agent_id: str) -> str:
        """Get routing key for travel agent"""
        routing_map = {
            "TextTripAnalyzer": "trip_analysis",
            "TripMoodDetector": "mood_support", 
            "TripCommsCoach": "communication_help",
            "TripBehaviorGuide": "decision_support",
            "TripCalmPractice": "stress_relief",
            "TripSummarySynth": "summary_request"
        }
        return routing_map.get(agent_id, agent_id.lower())
    
    def _route_from_travel_router(self, state: TravelAgentState) -> str:
        """Route from RouterAgent to appropriate travel agent"""
        return state.get("routing_decision", "TextTripAnalyzer")
    
    def _route_to_next_travel_agent(self, state: TravelAgentState) -> str:
        """Determine next travel agent or end execution"""
        current_agent = state.get("current_agent", "")
        question = state.get("question", "")
        agent_responses = state.get("agent_responses", {})
        
        # If summary requested or multiple agents responded, synthesize
        if any(word in question.lower() for word in ["summary", "overview", "combine"]) or len(agent_responses) >= 2:
            return "synthesize"
        
        # Check if stress/anxiety detected - route to TripCalmPractice
        if current_agent != "TripCalmPractice" and any(word in question.lower() for word in ["overwhelmed", "stressed", "anxiety"]):
            return "TripCalmPractice"
        
        # For single agent responses, go to synthesis
        return "synthesize"
    
    def _response_synthesizer_node(self, state: TravelAgentState) -> TravelAgentState:
        """Synthesize travel agent responses into coherent final response"""
        agent_responses = state.get("agent_responses", {})
        question = state.get("question", "")
        
        if not agent_responses:
            updated_state = state.copy()
            updated_state["final_response"] = "I'm ready to help with your travel planning. Please share your question!"
            updated_state["response"] = updated_state["final_response"]
            return updated_state
        
        # If only one agent responded, return its response directly
        if len(agent_responses) == 1:
            agent_id, response = list(agent_responses.items())[0]
            updated_state = state.copy()
            updated_state["current_agent"] = "ResponseSynthesizer"
            updated_state["final_response"] = response
            updated_state["response"] = response
            updated_state["primary_agent"] = agent_id
            return updated_state
        
        # Multi-agent response synthesis
        response_parts = []
        
        # Add contextual introduction
        response_parts.append("🎯 **Comprehensive Travel Guidance**\n")
        response_parts.append("Multiple travel specialists have collaborated to provide you with expert guidance:\n")
        
        # Travel agent display info with emojis
        agent_info = {
            "TextTripAnalyzer": {"emoji": "🗺️", "name": "Trip Analyzer"},
            "TripMoodDetector": {"emoji": "😊", "name": "Mood Detector"}, 
            "TripCommsCoach": {"emoji": "💬", "name": "Communication Coach"},
            "TripBehaviorGuide": {"emoji": "🧭", "name": "Behavior Guide"},
            "TripCalmPractice": {"emoji": "🧘", "name": "Calm Practice"},
            "TripSummarySynth": {"emoji": "📋", "name": "Summary Synthesizer"}
        }
        
        # Add each travel agent's contribution
        for agent_id in ["TextTripAnalyzer", "TripMoodDetector", "TripCommsCoach", "TripBehaviorGuide", "TripCalmPractice", "TripSummarySynth"]:
            if agent_id in agent_responses:
                response = agent_responses[agent_id].strip()
                if response:
                    info = agent_info.get(agent_id, {"emoji": "🤖", "name": agent_id})
                    response_parts.append(f"## {info['emoji']} {info['name']}")
                    response_parts.append("---")
                    response_parts.append(response)
                    response_parts.append("")  # Add spacing
        
        # Add integrated summary
        if len(agent_responses) > 1:
            response_parts.append("## 🔗 **Integrated Travel Plan**")
            response_parts.append("---")
            response_parts.append(f"🌟 **Multi-Expert Analysis**: {len(agent_responses)} travel specialists collaborated to provide comprehensive guidance tailored to your needs.")
            response_parts.append("")
        
        final_response = "\n".join(response_parts)
        
        # Update state
        updated_state = state.copy()
        updated_state["current_agent"] = "ResponseSynthesizer"
        updated_state["final_response"] = final_response
        updated_state["response"] = final_response
        updated_state["synthesis_type"] = "multi_agent"
        updated_state["agents_involved"] = list(agent_responses.keys())
        
        # Update execution path
        execution_path = state.get("execution_path", [])
        execution_path.append({
            "agent": "ResponseSynthesizer",
            "action": f"Synthesized responses from {len(agent_responses)} travel agents",
            "timestamp": datetime.now().isoformat()
        })
        updated_state["execution_path"] = execution_path
        
        logger.info(f"✅ Response synthesizer created comprehensive travel response from {len(agent_responses)} agents")
        return updated_state
    
    def _store_travel_interaction(self, user_id: int, agent_id: str, question: str, response: str):
        """Store travel agent interaction in memory"""
        try:
            # Store in STM (1 hour)
            self.memory_manager.set_stm(
                user_id=str(user_id),
                agent_id=agent_id,
                value=f"Q: {question}\nA: {response}",
                expiry=3600
            )
            
            # Store in LTM (permanent)
            self.memory_manager.set_ltm(
                user_id=str(user_id),
                agent_id=agent_id,
                value=f"Travel Query: {question}\nResponse: {response}"
            )
            
        except Exception as e:
            logger.error(f"Failed to store travel interaction: {e}")
    
    def process_request(self, user: str, user_id: int, question: str) -> Dict[str, Any]:
        """Main processing function for the travel multi-agent system"""
        start_time = time.time()
        
        try:
            # Build graph if not built
            if not self.graph:
                self.build_travel_graph()
            
            # Get memory context
            stm_context = self._get_stm_context(user_id)
            ltm_context = self._get_ltm_context(user_id)
            
            # Initialize state
            initial_state = TravelAgentState(
                user=user,
                user_id=user_id,
                question=question,
                current_agent="",
                next_agent=None,
                agent_chain=[],
                routing_decision="",
                response="",
                agent_responses={},
                final_response="",
                context={
                    "stm": stm_context,
                    "ltm": ltm_context
                },
                memory={
                    "interactions": [],
                    "agent_data": {}
                },
                shared_data={},
                edges_traversed=[],
                execution_path=[],
                timestamp=datetime.now().isoformat(),
                processing_time=0.0,
                ai_used=False,
                error_occurred=False
            )
            
            # Execute the graph
            final_state = self.graph.invoke(initial_state)
            
            # Calculate final processing time
            processing_time = time.time() - start_time
            
            # Return comprehensive response
            return {
                "user": final_state.get("user"),
                "user_id": final_state.get("user_id"),
                "question": final_state.get("question"),
                "agent": final_state.get("current_agent"),
                "response": final_state.get("final_response", final_state.get("response", "")),
                "agent_responses": final_state.get("agent_responses", {}),
                "execution_path": final_state.get("execution_path", []),
                "edges_traversed": final_state.get("edges_traversed", []),
                "context": final_state.get("context", {}),
                "timestamp": final_state.get("timestamp"),
                "processing_time": processing_time,
                "system_version": "3.0.0-fixed-travel-agents",
                "agents_involved": list(final_state.get("agent_responses", {}).keys()),
                "ai_used": final_state.get("ai_used", False),
                "error_occurred": final_state.get("error_occurred", False),
                "success": not final_state.get("error_occurred", False)
            }
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"❌ Travel multi-agent system execution failed: {e}")
            
            # Return error response with fallback
            fallback_response = self._get_intelligent_travel_fallback("TextTripAnalyzer", question)
            
            return {
                "user": user,
                "user_id": user_id,
                "question": question,
                "agent": "ErrorHandler",
                "response": fallback_response,
                "agent_responses": {"ErrorHandler": fallback_response},
                "execution_path": [{"agent": "ErrorHandler", "action": "Error recovery", "timestamp": datetime.now().isoformat()}],
                "edges_traversed": ["ErrorHandler"],
                "context": {},
                "timestamp": datetime.now().isoformat(),
                "processing_time": processing_time,
                "system_version": "3.0.0-fixed-travel-agents",
                "agents_involved": ["ErrorHandler"],
                "ai_used": False,
                "error_occurred": True,
                "success": True,  # Still successful as we provided fallback
                "error": str(e)
            }
    
    def _get_stm_context(self, user_id: int) -> Dict[str, Any]:
        """Get short-term memory context"""
        try:
            stm_data = self.memory_manager.get_all_stm_for_user(str(user_id))
            return {
                "recent_interactions": stm_data,
                "count": len(stm_data)
            }
        except Exception as e:
            logger.warning(f"Could not fetch STM context: {e}")
            return {}
    
    def _get_ltm_context(self, user_id: int) -> Dict[str, Any]:
        """Get long-term memory context"""
        try:
            ltm_data = self.memory_manager.get_recent_ltm(str(user_id), days=7)
            return {
                "recent_history": ltm_data[:10],
                "count": len(ltm_data)
            }
        except Exception as e:
            logger.warning(f"Could not fetch LTM context: {e}")
            return {}

# Global fixed travel multi-agent system instance
fixed_langgraph_multiagent_system = FixedLangGraphMultiAgentSystem()
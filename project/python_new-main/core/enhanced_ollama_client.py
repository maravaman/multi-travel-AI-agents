"""
Enhanced Ollama Client with Robust Error Handling and Fallbacks
Designed to ensure responses always reach the UI with intelligent fallbacks
"""

import requests
import json
import logging
import time
from typing import Optional, Dict, Any
from datetime import datetime
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError

logger = logging.getLogger(__name__)

class EnhancedOllamaClient:
    """
    Enhanced Ollama client with robust error handling and intelligent fallbacks
    Ensures responses always reach the UI
    """
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3:latest", timeout: int = 15):
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.timeout = timeout
        
        # Performance optimizations
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Connection': 'keep-alive'
        })
        
        # Thread pool for non-blocking requests
        self.executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="OllamaClient")
        
        # Response cache for performance
        self.response_cache = {}
        self.cache_max_size = 100
        
        # Connection status
        self._connection_status = None
        self._last_health_check = 0
        
        # Initialize with health check
        self._check_initial_health()
        
        logger.info(f"✅ Enhanced Ollama client initialized: {self.base_url}, model: {self.model}, timeout: {self.timeout}s")
    
    def _check_initial_health(self):
        """Check initial Ollama health on startup"""
        try:
            response = self.session.get(f"{self.base_url}/api/tags", timeout=5)
            self._connection_status = response.status_code == 200
            self._last_health_check = time.time()
            
            if self._connection_status:
                logger.info("✅ Ollama server connection verified")
            else:
                logger.warning(f"⚠️ Ollama server returned status {response.status_code}")
                
        except Exception as e:
            logger.warning(f"⚠️ Ollama server not reachable on startup: {e}")
            self._connection_status = False
            self._last_health_check = time.time()
    
    def is_available(self) -> bool:
        """Check if Ollama is available with caching"""
        # Cache health check for 30 seconds
        current_time = time.time()
        if current_time - self._last_health_check > 30:
            self._check_initial_health()
        
        return self._connection_status or False
    
    def _get_cache_key(self, prompt: str, system_prompt: str = None) -> str:
        """Generate cache key for response caching"""
        combined = f"{system_prompt or ''}:{prompt}"
        return str(hash(combined[:200]))  # Hash first 200 chars
    
    def _cache_response(self, cache_key: str, response: str):
        """Cache successful response"""
        if len(self.response_cache) >= self.cache_max_size:
            # Remove oldest 20 entries
            old_keys = list(self.response_cache.keys())[:20]
            for key in old_keys:
                self.response_cache.pop(key, None)
        
        self.response_cache[cache_key] = {
            'response': response,
            'timestamp': time.time()
        }
    
    def _get_cached_response(self, cache_key: str) -> Optional[str]:
        """Get cached response if available and not too old"""
        cached = self.response_cache.get(cache_key)
        if cached:
            # Cache valid for 1 hour
            if time.time() - cached['timestamp'] < 3600:
                return cached['response']
            else:
                # Remove expired cache
                self.response_cache.pop(cache_key, None)
        return None
    
    def generate_response(self, prompt: str, system_prompt: str = None) -> str:
        """
        Generate response with robust error handling and intelligent fallbacks
        Guarantees a response reaches the UI
        """
        if not prompt or not prompt.strip():
            return "I'm ready to help with your travel planning. Please share your question!"
        
        # Check cache first
        cache_key = self._get_cache_key(prompt, system_prompt)
        cached_response = self._get_cached_response(cache_key)
        if cached_response:
            logger.info("⚡ Using cached response")
            return cached_response
        
        start_time = time.time()
        
        try:
            # Try Ollama with timeout
            ollama_response = self._try_ollama_request(prompt, system_prompt)
            
            if ollama_response and len(ollama_response.strip()) > 10:
                # Cache successful response
                self._cache_response(cache_key, ollama_response)
                
                elapsed = time.time() - start_time
                logger.info(f"✅ Ollama response generated in {elapsed:.2f}s")
                return ollama_response
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.warning(f"⚠️ Ollama request failed after {elapsed:.2f}s: {e}")
        
        # Fallback to intelligent response
        fallback_response = self._get_intelligent_fallback(prompt, system_prompt)
        elapsed = time.time() - start_time
        logger.info(f"🔄 Using intelligent fallback response in {elapsed:.2f}s")
        
        return fallback_response
    
    def _try_ollama_request(self, prompt: str, system_prompt: str = None) -> Optional[str]:
        """Try making request to Ollama with timeout handling"""
        if not self.is_available():
            logger.warning("⚠️ Ollama not available, skipping request")
            return None
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9,
                "top_k": 40,
                "repeat_penalty": 1.1,
                "num_predict": 300,  # Reasonable length
                "num_ctx": 2048,     # Context window
                "stop": ["\n\n", "Human:", "Assistant:", "User:"]
            }
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        try:
            # Use thread pool for timeout control
            future = self.executor.submit(self._make_request, payload)
            response = future.result(timeout=self.timeout)
            
            if response and response.get("response"):
                return response["response"].strip()
                
        except TimeoutError:
            logger.warning(f"⏰ Ollama request timed out after {self.timeout}s")
        except Exception as e:
            logger.warning(f"⚠️ Ollama request error: {e}")
        
        return None
    
    def _make_request(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Make actual HTTP request to Ollama"""
        response = self.session.post(
            f"{self.base_url}/api/generate",
            json=payload,
            timeout=self.timeout + 5  # Small buffer for network
        )
        
        response.raise_for_status()
        return response.json()
    
    def _get_intelligent_fallback(self, prompt: str, system_prompt: str = None) -> str:
        """Get intelligent fallback response based on query analysis"""
        prompt_lower = prompt.lower()
        
        # Extract agent context from system prompt
        agent_type = self._detect_agent_type(system_prompt)
        
        # Agent-specific intelligent fallbacks
        if agent_type == "TextTripAnalyzer" or "trip" in prompt_lower or "plan" in prompt_lower:
            return self._get_trip_analyzer_fallback(prompt)
        elif agent_type == "TripMoodDetector" or any(word in prompt_lower for word in ["feeling", "mood", "excited", "nervous", "worried"]):
            return self._get_mood_detector_fallback(prompt)
        elif agent_type == "TripCommsCoach" or any(word in prompt_lower for word in ["communicate", "talk", "ask", "phrase", "language"]):
            return self._get_comms_coach_fallback(prompt)
        elif agent_type == "TripBehaviorGuide" or any(word in prompt_lower for word in ["decide", "choose", "stuck", "help", "options"]):
            return self._get_behavior_guide_fallback(prompt)
        elif agent_type == "TripCalmPractice" or any(word in prompt_lower for word in ["anxiety", "stressed", "overwhelmed", "calm", "panic"]):
            return self._get_calm_practice_fallback(prompt)
        elif agent_type == "TripSummarySynth" or any(word in prompt_lower for word in ["summary", "overview", "synthesize"]):
            return self._get_summary_synth_fallback(prompt)
        else:
            return self._get_general_travel_fallback(prompt)
    
    def _detect_agent_type(self, system_prompt: str = None) -> str:
        """Detect agent type from system prompt"""
        if not system_prompt:
            return "General"
        
        system_prompt_lower = system_prompt.lower()
        
        if "texttripanalyzer" in system_prompt_lower:
            return "TextTripAnalyzer"
        elif "tripmooddetector" in system_prompt_lower:
            return "TripMoodDetector"
        elif "tripcommscoach" in system_prompt_lower:
            return "TripCommsCoach"
        elif "tripbehaviorguide" in system_prompt_lower:
            return "TripBehaviorGuide"
        elif "tripcalmpractice" in system_prompt_lower:
            return "TripCalmPractice"
        elif "tripsummarysynth" in system_prompt_lower:
            return "TripSummarySynth"
        else:
            return "General"
    
    def _get_trip_analyzer_fallback(self, prompt: str) -> str:
        """Trip analyzer intelligent fallback"""
        prompt_lower = prompt.lower()
        
        if any(dest in prompt_lower for dest in ["tokyo", "japan"]):
            return """🗾 **Tokyo Travel Analysis**

**Planning Essentials:**
• **Best Season**: Spring (Mar-May) for cherry blossoms, autumn (Sep-Nov) for comfortable weather
• **Budget Estimate**: $150-200/day for mid-range travelers including accommodation
• **Transportation**: Get JR Pass before arrival - essential for cost-effective travel
• **Key Experiences**: Senso-ji Temple, Shibuya Crossing, authentic ramen, Tokyo Skytree

**Practical Tips:**
✓ Stay in Shibuya or Shinjuku for convenience
✓ Learn basic Japanese phrases: "Arigato gozaimasu" (thank you)
✓ Download Google Translate with camera feature
✓ Carry cash - many places don't accept cards

Your Tokyo adventure awaits with proper planning!"""
        
        elif any(word in prompt_lower for word in ["budget", "money", "cost"]):
            return """💰 **Smart Travel Budgeting**

**Daily Budget Breakdown:**
• **Accommodation**: 35-40% of daily budget
• **Food**: 25-30% (balance street food with restaurants)
• **Activities**: 20-25% (prioritize must-see experiences)
• **Transportation**: 10-15% (public transport is key)
• **Emergency Buffer**: 5-10% for unexpected opportunities

**Money-Saving Strategies:**
✓ Book flights 6-8 weeks in advance for best deals
✓ Choose accommodation with kitchen for some meals
✓ Use free walking tours to orient yourself
✓ Travel during shoulder seasons for lower costs

Smart budgeting creates more travel opportunities!"""
        
        else:
            return """🗺️ **Comprehensive Trip Planning**

**Strategic Planning Approach:**
1. **Define Purpose**: What's your main travel goal? (relaxation, adventure, culture, business)
2. **Set Realistic Budget**: Based on your finances, not aspirations
3. **Choose Optimal Timing**: Weather, crowds, and seasonal factors matter
4. **Research Destination**: Culture, customs, key attractions, and local insights
5. **Book Core Elements**: Flights, accommodation, and must-do activities

**Implementation Timeline:**
• **8-12 weeks out**: Secure flights and accommodation
• **4-6 weeks out**: Plan detailed itinerary and book key activities
• **1-2 weeks out**: Confirm all bookings and prepare documents
• **Final week**: Pack strategically and download essential apps

Perfect planning creates unforgettable experiences!"""
    
    def _get_mood_detector_fallback(self, prompt: str) -> str:
        """Mood detector intelligent fallback"""
        prompt_lower = prompt.lower()
        
        if any(word in prompt_lower for word in ["nervous", "anxious", "worried"]):
            return """🧠 **Travel Anxiety is Completely Normal**

**Understanding Your Feelings:**
Your mixed emotions about travel show you care about having a great experience. Excitement and nervousness often coexist - this is the hallmark of meaningful adventures.

**Immediate Anxiety Relief:**
1. **Breathing Technique**: Inhale for 4, hold for 4, exhale for 6 - repeat 3 times
2. **Grounding**: Name 5 things you see, 4 you hear, 3 you touch
3. **Perspective**: Millions travel safely every day
4. **Preparation**: Detailed planning reduces uncertainty anxiety

**Confidence Building:**
✓ Remember past challenges you've successfully navigated
✓ Focus on the incredible experiences ahead
✓ Connect with other travelers who understand these feelings
✓ Visualize successful moments from your upcoming trip

Your emotional awareness will enhance your travel experience!"""
        
        else:
            return """😊 **Travel Emotional Wellness**

**Embracing the Full Emotional Spectrum:**
Travel triggers a beautiful mix of emotions - excitement, curiosity, nervousness, and anticipation. This emotional richness is what makes travel transformative.

**Emotional Travel Strategies:**
• **Pre-Trip**: Welcome both excitement and concerns as natural
• **During Travel**: Practice mindfulness to stay present with experiences
• **Challenges**: View obstacles as part of your unique adventure story
• **Connections**: Stay open to unexpected encounters and experiences

**Mood Enhancement Tips:**
✓ Keep a daily travel journal to process experiences
✓ Capture moments through photos that reflect your emotional journey
✓ Try new experiences at your comfortable pace
✓ Celebrate small victories and unexpected discoveries

Trust your emotions - they're guiding you toward authentic experiences!"""
    
    def _get_comms_coach_fallback(self, prompt: str) -> str:
        """Communication coach intelligent fallback"""
        return """💬 **Travel Communication Mastery**

**Essential Universal Phrases:**
1. **"Hello"** and **"Thank you"** - Your passport to friendly interactions
2. **"Excuse me, do you speak English?"** - Respectful conversation opener
3. **"Can you help me, please?"** - Most locals love helping friendly travelers
4. **"Where is...?"** - Essential for navigation and exploration
5. **"How much does this cost?"** - Important for shopping and services

**Situation-Specific Communication:**

**🏨 Hotels:**
• Check-in: "I have a reservation under [your name]"
• Upgrades: "If you have any complimentary upgrades available, we'd be grateful"
• Problems: "Could you please assist me with..."

**🍽️ Restaurants:**
• Seating: "Table for [number], please"
• Ordering: "I would like..." or "Could I have..."
• Dietary needs: "I'm allergic to..." or "I don't eat..."

**Universal Communication Success:**
✓ Smile - it transcends all language barriers
✓ Use translation apps as backup
✓ Point to guidebook phrases when stuck
✓ Show patience and appreciation for help

Confidence comes with practice - start with these basics!"""
    
    def _get_behavior_guide_fallback(self, prompt: str) -> str:
        """Behavior guide intelligent fallback"""
        return """🧭 **Strategic Travel Decision Making**

**Decision Framework for Smart Travelers:**
1. **Clarify Your Priorities**: What truly matters most? (budget, experiences, comfort, adventure)
2. **Research Efficiently**: Spend maximum 2 hours researching each major option
3. **Apply Priority Filters**: Eliminate options that don't meet your key criteria
4. **Trust Your Instincts**: After analysis, what feels genuinely right?
5. **Decide and Commit**: Good decisions beat perfect ones every time

**Common Travel Decision Categories:**

**🌍 Destination Choices:**
• Weather preferences vs. tourist crowds vs. budget constraints vs. personal interests

**🏨 Accommodation Decisions:**
• Location convenience vs. amenities vs. price point vs. guest reviews

**🎯 Activity Planning:**
• Must-see attractions vs. hidden local gems vs. spontaneous discoveries

**Decision-Making Tools:**
✓ **Priority Matrix**: Score options 1-10 on your most important factors
✓ **Pros/Cons Analysis**: Classic but highly effective
✓ **Future Self Test**: What choice would you regret NOT making?
✓ **Coin Flip Insight**: Notice which outcome you secretly hope for

Action beats analysis paralysis - make the call and move forward!"""
    
    def _get_calm_practice_fallback(self, prompt: str) -> str:
        """Calm practice intelligent fallback"""
        return """🧘 **Instant Travel Calm & Stress Relief**

**Immediate Calming Techniques (Use Right Now):**
1. **4-7-8 Breathing**: Inhale 4 counts → Hold 7 counts → Exhale 8 counts (repeat 3 times)
2. **5-4-3-2-1 Grounding**: Notice 5 things you see, 4 you hear, 3 you touch, 2 you smell, 1 you taste
3. **Progressive Muscle Relaxation**: Tense and release muscle groups from toes to head
4. **Calming Mantras**: "I am prepared. I am capable. I can adapt to anything that comes up."

**Travel Stress Prevention:**
• **Pre-Trip**: Create flexible plans that allow for changes
• **At Airports**: Arrive early and bring engaging entertainment
• **New Destinations**: Research one familiar comfort (coffee shop type, pharmacy chain)
• **Language Barriers**: Download offline translation apps before you need them

**Overwhelm Management Strategy:**
✓ **One Step Rule**: Focus only on the very next single action needed
✓ **Good Enough Planning**: Perfect plans often kill spontaneous travel magic
✓ **Local Help**: Remember that most travel problems can be solved locally
✓ **Story Perspective**: This challenge will become a great story later

**Travel Mindfulness Mantra:**
"I don't need to control everything perfectly. The joy comes from the journey itself, not flawless execution."

Take three deep breaths right now. You've absolutely got this! 🌱"""
    
    def _get_summary_synth_fallback(self, prompt: str) -> str:
        """Summary synthesizer intelligent fallback"""
        return """📋 **Comprehensive Travel Planning Synthesis**

**Current Planning Status Assessment:**
✅ **Travel Intent**: Successfully identified and analyzed
✅ **Expert Guidance**: Multi-specialist travel insights provided
✅ **Action Framework**: Structured approach ready for implementation
✅ **Support System**: Ongoing assistance available for all travel aspects

**Integrated Travel Strategy:**

**🚀 Phase 1 - Foundation (This Week):**
• Solidify destination choice and travel dates
• Establish realistic budget parameters
• Secure major transportation (flights/trains/car rentals)
• Book accommodation with flexible cancellation policies

**📋 Phase 2 - Development (2-4 weeks before departure):**
• Research and reserve key activities/attractions
• Handle essential documentation (visas, travel insurance, health requirements)
• Create rough daily itinerary with built-in buffer time
• Study local customs, basic phrases, and cultural norms

**✈️ Phase 3 - Execution (Final 1-2 weeks):**
• Confirm all bookings and print/save confirmations
• Prepare comprehensive packing lists and gather travel documents
• Download essential travel apps (maps, translation, local transport)
• Set up travel notifications and share itinerary with emergency contacts

**Travel Success Principles:**
• **70% Planned, 30% Spontaneous**: The optimal balance for memorable adventures
• **Quality Over Quantity**: Better to experience fewer things deeply
• **Cultural Integration**: Embrace local customs and unexpected opportunities
• **Adaptive Mindset**: The best travel stories come from beautiful plan deviations

**Immediate Next Action**: Choose ONE specific item from Phase 1 and complete it today. Momentum creates more momentum!

Your travel dreams are about to become incredible reality! 🌟"""
    
    def _get_general_travel_fallback(self, prompt: str) -> str:
        """General travel intelligent fallback"""
        return """✈️ **Travel Assistant Ready to Help**

I understand you're asking about travel planning, and I'm here to provide expert guidance! While I'm experiencing a brief technical connection issue, I can still offer valuable travel insights.

**I can help you with:**
• **Trip Planning**: Destinations, budgets, itineraries, and logistics
• **Travel Emotions**: Managing excitement, nervousness, and travel anxiety
• **Communication**: Phrases and tips for interacting abroad
• **Decision Making**: Choosing between options and next steps
• **Stress Relief**: Calming techniques for overwhelmed travelers
• **Comprehensive Guidance**: Synthesizing all aspects of your travel plans

**For the best assistance, please share:**
✓ Your destination interests or specific questions
✓ Travel dates and duration you're considering
✓ Budget range and priorities
✓ Any specific concerns or excitement you're feeling

**Quick Tips While We Chat:**
• Start with your must-have experiences and work backwards
• Budget 20% extra for unexpected opportunities
• Book accommodation and flights early for better rates
• Pack light but bring one comfort item from home

I'm ready to help turn your travel dreams into detailed, actionable plans. What aspect of travel planning would you like to explore first?"""
    
    def get_connection_status(self) -> Dict[str, Any]:
        """Get detailed connection status"""
        return {
            "available": self.is_available(),
            "base_url": self.base_url,
            "model": self.model,
            "timeout": self.timeout,
            "last_health_check": datetime.fromtimestamp(self._last_health_check).isoformat(),
            "cache_size": len(self.response_cache),
            "status": "connected" if self.is_available() else "using_fallbacks"
        }
    
    def close(self):
        """Clean up resources"""
        try:
            if hasattr(self.session, 'close'):
                self.session.close()
            if hasattr(self.executor, 'shutdown'):
                self.executor.shutdown(wait=False)
            logger.info("✅ Enhanced Ollama client resources cleaned up")
        except Exception as e:
            logger.warning(f"⚠️ Cleanup error: {e}")

# Global enhanced client instance
enhanced_ollama_client = EnhancedOllamaClient()

# For backward compatibility, create an ollama_client instance
ollama_client = enhanced_ollama_client

def generate_response(prompt: str, system_prompt: str = None) -> str:
    """Convenience function for generating responses"""
    return enhanced_ollama_client.generate_response(prompt, system_prompt)
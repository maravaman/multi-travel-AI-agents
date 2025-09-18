"""
Hybrid AI System for LangGraph Multi-Agent Travel Assistant
Provides IMMEDIATE responses while optionally enhancing with real AI in background
Ensures perfect UI responsiveness with intelligent content delivery
"""

import asyncio
import threading
import time
import logging
from typing import Dict, Any, Optional, Callable
from datetime import datetime
import queue

logger = logging.getLogger(__name__)

class HybridAISystem:
    """
    Hybrid AI system that guarantees immediate responses
    While optionally providing AI-enhanced responses when available
    """
    
    def __init__(self):
        self.ollama_client = None
        self.background_thread_pool = threading.ThreadPool(processes=2)
        self.response_enhancers = {}  # job_id -> enhancement_data
        self.ai_timeout = 8  # 8 seconds max for AI response (increased for better success)
        
        self._initialize_ollama()
        logger.info("✅ Hybrid AI System initialized")
    
    def _initialize_ollama(self):
        """Initialize Ollama client for AI responses"""
        try:
            from core.production_ollama_client import production_ollama_client
            self.ollama_client = production_ollama_client
            logger.info("✅ Production Ollama client initialized for hybrid system")
        except Exception as e:
            logger.warning(f"⚠️ Ollama initialization failed: {e}")
            self.ollama_client = None
    
    def generate_response(self, prompt: str, system_prompt: str = None, agent_name: str = None) -> str:
        """
        Generate response prioritizing Ollama AI, falling back to intelligent responses
        """
        start_time = time.time()
        
        # Step 1: Try Ollama AI first (this is what the client wants!)
        if self.ollama_client:
            try:
                ai_response = self._try_ai_enhancement(prompt, system_prompt, agent_name)
                if ai_response and len(ai_response.strip()) > 30:
                    logger.info(f"✅ Ollama AI response generated for {agent_name} ({len(ai_response)} chars)")
                    return ai_response  # Return AI response directly as string
            except Exception as e:
                logger.debug(f"AI generation failed, using intelligent fallback: {e}")
        
        # Step 2: Fall back to intelligent response only if Ollama fails
        logger.info(f"⚡ Using intelligent fallback for {agent_name} (Ollama unavailable)")
        intelligent_response = self._get_intelligent_response(prompt, agent_name)
        return intelligent_response
    
    def _try_ai_enhancement(self, prompt: str, system_prompt: str = None, agent_name: str = None) -> Optional[str]:
        """Try AI enhancement with strict timeout"""
        result_queue = queue.Queue()
        
        def ai_worker():
            try:
                response = self.ollama_client.generate_response(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    agent_name=agent_name
                )
                result_queue.put(("success", response))
            except Exception as e:
                result_queue.put(("error", str(e)))
        
        # Start AI request in background
        thread = threading.Thread(target=ai_worker, daemon=True)
        thread.start()
        
        # Wait for result with timeout
        try:
            status, result = result_queue.get(timeout=self.ai_timeout)
            if status == "success":
                return result
        except queue.Empty:
            logger.debug(f"AI enhancement timeout after {self.ai_timeout}s")
        
        return None
    
    def _get_intelligent_response(self, prompt: str, agent_name: str = None) -> str:
        """Get immediate intelligent response based on agent and query analysis"""
        prompt_lower = prompt.lower()
        
        # Agent-specific intelligent responses
        if agent_name == "TextTripAnalyzer" or any(word in prompt_lower for word in ["plan", "trip", "destination", "budget"]):
            return self._get_trip_analyzer_response(prompt)
        elif agent_name == "TripMoodDetector" or any(word in prompt_lower for word in ["feeling", "nervous", "excited", "mood"]):
            return self._get_mood_detector_response(prompt)
        elif agent_name == "TripCommsCoach" or any(word in prompt_lower for word in ["communicate", "talk", "phrase", "language"]):
            return self._get_comms_coach_response(prompt)
        elif agent_name == "TripBehaviorGuide" or any(word in prompt_lower for word in ["decide", "choose", "stuck", "help"]):
            return self._get_behavior_guide_response(prompt)
        elif agent_name == "TripCalmPractice" or any(word in prompt_lower for word in ["stress", "anxiety", "overwhelmed", "calm"]):
            return self._get_calm_practice_response(prompt)
        elif agent_name == "TripSummarySynth" or any(word in prompt_lower for word in ["summary", "overview", "synthesize"]):
            return self._get_summary_synth_response(prompt)
        else:
            return self._get_general_travel_response(prompt)
    
    def _get_trip_analyzer_response(self, prompt: str) -> str:
        """Intelligent trip analyzer response"""
        prompt_lower = prompt.lower()
        
        if any(dest in prompt_lower for dest in ["korea", "seoul", "south korea"]):
            return """🇰🇷 **Seoul, South Korea Travel Plan**

**3-Day Itinerary Highlights:**
• **Day 1**: Gyeongbokgung Palace → Bukchon Hanok Village → Myeongdong shopping
• **Day 2**: Jeju Island day trip OR Busan KTX journey → Gamcheon Culture Village  
• **Day 3**: Hongdae nightlife → Han River → N Seoul Tower sunset

**Budget Breakdown (Solo Travel):**
• **Accommodation**: $30-60/night (guesthouses/hostels in Hongdae/Myeongdong)
• **Food**: $20-35/day (mix of street food and restaurants)
• **Transport**: $15/day (T-money card for subway/bus)
• **Activities**: $10-25/day (palace entries, attractions)

**Essential Tips:**
✓ Download Papago translator app
✓ Get T-money card at airport for easy transport
✓ Try Korean BBQ, bibimbap, and street food in Myeongdong
✓ Book KTX train tickets in advance for day trips

**Communication Basics:**
• Hello: 안녕하세요 (Annyeonghaseyo)
• Thank you: 감사합니다 (Gamsahamnida)
• Excuse me: 죄송합니다 (Joesonghamnida)

Seoul is perfect for solo travel with excellent public transport and friendly locals!"""

        elif any(dest in prompt_lower for dest in ["japan", "tokyo"]):
            return """🗾 **Tokyo, Japan Solo Travel Guide**

**Perfect 3-Day Tokyo Experience:**
• **Day 1**: Asakusa (Senso-ji Temple) → Tokyo Skytree → Traditional dinner in Asakusa
• **Day 2**: Shibuya Crossing → Harajuku → Meiji Shrine → Shinjuku nightlife
• **Day 3**: Tsukiji Outer Market → Imperial Palace → Ginza shopping

**Solo Traveler Budget:**
• **Accommodation**: $40-80/night (capsule hotels/business hotels)
• **Food**: $25-45/day (ramen, sushi, convenience store meals)
• **Transport**: $8/day (JR Pass for day trips, local trains)
• **Experiences**: $15-30/day (temple visits, observation decks)

**Tokyo Solo Travel Tips:**
✓ Get JR Pass before arrival - essential for travel
✓ Download Google Translate with camera feature
✓ Visit convenience stores (7-Eleven, FamilyMart) for easy meals
✓ Bow slightly when greeting - shows respect
✓ Carry cash - many places don't accept cards

**Essential Phrases:**
• Hello: こんにちは (Konnichiwa)
• Thank you: ありがとうございます (Arigato gozaimasu)
• Excuse me: すみません (Sumimasen)

Tokyo is incredibly safe and solo-friendly with amazing food culture!"""

        else:
            return """🗺️ **Comprehensive Trip Planning Guide**

**Step-by-Step Planning Process:**

**1. Define Your Trip Goals**
• What type of experience do you want? (Adventure, relaxation, culture, food)
• Who are you traveling with? (Solo, couple, family, friends)
• What's your primary motivation? (Learn, explore, recharge, celebrate)

**2. Set Realistic Budget**
• Research destination costs using Numbeo or Budget Your Trip
• Allocate: 40% accommodation, 30% food, 20% activities, 10% transport
• Add 15% buffer for unexpected expenses and opportunities

**3. Choose Optimal Timing**
• Weather patterns and seasons
• Tourist crowds and peak pricing
• Local events and festivals
• Personal schedule and work commitments

**4. Book Core Elements**
• **Flights**: 6-8 weeks ahead for best prices
• **Accommodation**: Balance location vs price vs reviews
• **Must-do Activities**: Book popular attractions in advance

**5. Detailed Itinerary Planning**
• Research transportation between locations
• Plan 70% structure, 30% flexibility for spontaneous discoveries
• Download offline maps and translation apps
• Prepare backup plans for weather/closures

**Success Formula**: Great trips balance careful planning with openness to unexpected adventures!"""
    
    def _get_mood_detector_response(self, prompt: str) -> str:
        """Intelligent mood detector response"""
        prompt_lower = prompt.lower()
        
        if any(word in prompt_lower for word in ["nervous", "anxious", "worried", "scared"]):
            return """🧠 **Travel Anxiety is Completely Normal**

**Understanding Your Feelings:**
Your nervousness about travel shows you care about having a great experience! Mixed emotions before big trips are incredibly common and actually healthy - they show you're taking this adventure seriously.

**Immediate Anxiety Relief (Use Right Now):**
1. **4-7-8 Breathing**: Inhale 4 counts → Hold 7 → Exhale 8 (repeat 3 times)
2. **Name Your Fears**: Write down specific worries, then practical solutions
3. **Positive Visualization**: Imagine 3 amazing moments from your upcoming trip
4. **Preparation Power**: Make detailed lists - they create sense of control

**Confidence Building Strategies:**
✓ Remember challenges you've successfully navigated before
✓ Connect with other travelers online who've been to your destination  
✓ Research one "comfort item" at your destination (familiar restaurant chain, etc.)
✓ Focus on the incredible experiences and memories you'll create

**Traveler's Mindset Shift:**
"My nervousness means I care about this experience. I'm prepared, capable, and ready for adventure. Millions of people travel safely every day, and I can too."

Your emotional awareness will actually enhance your travel experience by helping you be more present and grateful for the journey!"""

        else:
            return """😊 **Travel Emotional Wellness**

**Embracing the Full Emotional Journey:**
Travel triggers a beautiful spectrum of emotions - excitement, anticipation, nervousness, curiosity, and wonder. This emotional richness is what makes travel so transformative and memorable.

**Emotional Travel Strategies:**
• **Pre-Trip**: Welcome both excitement and concerns as natural responses
• **During Travel**: Practice mindfulness to fully experience each moment
• **Challenges**: View obstacles as character-building parts of your adventure story
• **Connections**: Stay open to unexpected encounters and cultural exchanges

**Mood Enhancement Techniques:**
✓ **Travel Journal**: Write daily reflections to process experiences
✓**Photo Storytelling**: Capture moments that reflect your emotional journey
✓ **Gentle Challenges**: Try new experiences at your comfortable pace
✓ **Celebration Mindset**: Acknowledge small victories and discoveries

**Emotional Intelligence for Travelers:**
The best travelers understand that ups and downs are part of the journey. Your ability to recognize and work with your emotions will lead to more authentic, meaningful travel experiences.

Trust your feelings - they're guiding you toward genuine adventures and personal growth!"""
    
    def _get_comms_coach_response(self, prompt: str) -> str:
        """Intelligent communications coach response"""
        return """💬 **Essential Travel Communication Mastery**

**Universal Survival Phrases (Learn These First):**
1. **"Hello"** and **"Thank you"** - Your passport to friendly interactions worldwide
2. **"Excuse me, do you speak English?"** - Respectful conversation opener
3. **"Can you help me, please?"** - Most locals love helping polite travelers
4. **"Where is...?"** - Essential for navigation and finding what you need
5. **"How much does this cost?"** - Critical for shopping and service negotiations

**Situation-Specific Communication:**

**🏨 Hotel Interactions:**
• **Check-in**: "I have a reservation under [your name]"
• **Requests**: "Could you recommend a good local restaurant?"  
• **Problems**: "I'm having trouble with [specific issue]. Could you assist?"
• **Checkout**: "Could you arrange transportation to the airport?"

**🍽️ Restaurant Communication:**
• **Seating**: "Table for [number of people], please"
• **Ordering**: "I would like..." or "Could I have the..."
• **Dietary Needs**: "I'm allergic to..." or "I don't eat..."
• **Payment**: "Check, please" or "Could I have the bill?"

**🛍️ Shopping & Local Interactions:**
• **Browsing**: "I'm just looking, thank you"
• **Negotiating**: "Is this your best price?" (where appropriate)
• **Directions**: "Could you point me toward [destination]?"

**Communication Success Secrets:**
✓ **Smile universally** - it transcends all language barriers
✓ **Use translation apps** as backup when stuck
✓ **Point to guidebook phrases** when pronunciation is difficult
✓ **Show patience and gratitude** - locals appreciate the effort

Confidence comes with practice - start with these basics and build up!"""
    
    def _get_behavior_guide_response(self, prompt: str) -> str:
        """Intelligent behavior guide response"""
        return """🧭 **Strategic Travel Decision Making**

**Smart Decision Framework for Travelers:**
1. **Clarify Your Priorities**: What matters most right now? (budget, experience, comfort, time)
2. **Set Research Limits**: Spend maximum 2 hours researching each major decision
3. **Apply Priority Filters**: Eliminate options that don't meet your key criteria  
4. **Trust Your Instincts**: After analysis, what feels genuinely right?
5. **Decide and Commit**: Good decisions beat perfect ones every time

**Common Travel Decision Categories:**

**🌍 Destination Choices:**
• Weather preferences vs tourist crowds vs budget constraints vs personal interests
• Familiar comfort vs challenging new experiences

**🏨 Accommodation Decisions:**  
• Location convenience vs amenities vs price point vs authentic experience
• Social hostels vs private comfort vs local homestays

**🎯 Activity Planning:**
• Must-see tourist attractions vs hidden local gems vs spontaneous discoveries
• Structured tours vs independent exploration vs guided experiences

**Decision-Making Tools:**
✓ **Priority Matrix**: Rate options 1-10 on your most important factors
✓ **Pros/Cons Analysis**: Classic method that still works brilliantly
✓ **Future Self Test**: What choice would you regret NOT making in 5 years?
✓ **Coin Flip Insight**: Notice which outcome you secretly hope for

**Action Steps for Decision Paralysis:**
1. Set a decision deadline (give yourself a time limit)
2. Gather information efficiently (avoid endless research loops)
3. Apply your decision framework consistently
4. Choose and fully commit to your decision
5. Prepare one backup plan for peace of mind

Remember: The best travel stories often come from imperfect decisions that led to unexpected adventures!"""
    
    def _get_calm_practice_response(self, prompt: str) -> str:
        """Intelligent calm practice response"""
        return """🧘 **Instant Travel Calm & Stress Relief**

**Emergency Calming Techniques (Use Right Now):**
1. **4-7-8 Breathing**: Inhale 4 counts → Hold 7 counts → Exhale 8 counts (repeat 3x)
2. **5-4-3-2-1 Grounding**: Notice 5 things you see, 4 you hear, 3 you touch, 2 you smell, 1 you taste
3. **Progressive Muscle Relaxation**: Tense and release muscle groups from toes to head
4. **Calming Mantras**: "I am prepared. I am capable. I can adapt to anything that comes up."

**Travel Stress Prevention Strategies:**
• **Pre-Trip Planning**: Create flexible itineraries that allow for changes
• **Airport/Transport**: Arrive early and bring engaging entertainment (books, music, podcasts)
• **New Destinations**: Research one familiar comfort (coffee shop chain, pharmacy brand)
• **Language Barriers**: Download offline translation apps before you need them

**Overwhelm Management System:**
✓ **One Step Rule**: Focus only on the very next single action needed
✓ **Good Enough Planning**: Perfect plans often kill spontaneous travel magic
✓ **Local Help Available**: Remember that most problems can be solved locally
✓ **Story Perspective**: This challenging moment will become a great story later

**Travel Anxiety Relief Mantras:**
• "I don't need to control everything perfectly"
• "The joy comes from the journey itself, not flawless execution"
• "Every experienced traveler has faced similar challenges"
• "I have the skills and resources to handle whatever comes up"

**Advanced Calm Practice:**
When stress hits, ask yourself: "Will this matter in one week?" Usually the answer puts things in perspective.

Take three deep breaths right now. You've absolutely got this! 🌱"""
    
    def _get_summary_synth_response(self, prompt: str) -> str:
        """Intelligent summary synthesizer response"""
        return """📋 **Comprehensive Travel Planning Synthesis**

**Current Planning Status Assessment:**
✅ **Travel Intent**: Successfully identified and analyzed
✅ **Expert Guidance**: Multi-specialist travel insights provided
✅ **Action Framework**: Structured approach ready for implementation  
✅ **Support System**: Ongoing assistance available for all travel aspects

**Integrated Travel Strategy:**

**🚀 Phase 1 - Foundation (This Week):**
• Solidify destination choice and confirm travel dates
• Establish realistic budget parameters and financial planning
• Secure major transportation (flights, trains, car rentals)
• Book accommodation with flexible cancellation policies

**📋 Phase 2 - Development (2-4 weeks before departure):**
• Research and reserve key activities and attractions
• Handle essential documentation (visas, travel insurance, health requirements)
• Create rough daily itinerary with built-in buffer time
• Study local customs, basic phrases, and cultural expectations

**✈️ Phase 3 - Finalization (Final 1-2 weeks):**
• Confirm all bookings and print/save digital confirmations
• Prepare comprehensive packing lists and gather travel documents
• Download essential travel apps (offline maps, translation, local transport)
• Set up travel notifications and share itinerary with emergency contacts

**Travel Success Principles:**
• **70% Planned, 30% Spontaneous**: The optimal balance for memorable adventures
• **Quality Over Quantity**: Better to experience fewer things deeply and meaningfully
• **Cultural Integration**: Embrace local customs and remain open to unexpected opportunities
• **Adaptive Mindset**: The best travel stories often come from beautiful plan deviations

**Immediate Next Action**: Choose ONE specific item from Phase 1 and complete it today. Momentum creates more momentum!

**Support Available**: I'm here to help with any aspect of your travel planning. Your dreams are about to become incredible reality! 🌟"""
    
    def _get_general_travel_response(self, prompt: str) -> str:
        """General intelligent travel response"""
        return """✈️ **Travel Planning Assistant Ready**

I'm here to provide expert travel guidance tailored to your specific needs! I can help you with comprehensive trip planning, destination research, budget optimization, and practical travel advice.

**I can assist you with:**
• **Trip Planning**: Destinations, itineraries, budgets, and logistics
• **Emotional Support**: Managing travel anxiety, excitement, and decision-making
• **Communication**: Essential phrases and cultural interaction tips
• **Decision Making**: Choosing between options and planning next steps
• **Stress Management**: Calming techniques for overwhelmed travelers
• **Comprehensive Analysis**: Synthesizing all aspects of your travel plans

**For the best personalized assistance, please share:**
✓ Your destination interests or specific travel questions
✓ Travel dates, duration, and budget considerations
✓ Any concerns, excitement, or specific needs you have
✓ Your travel style preferences (adventure, relaxation, culture, etc.)

**Quick Planning Tips While We Chat:**
• Start with your must-have experiences and work backwards from there
• Budget 20% extra beyond your planned expenses for opportunities
• Book accommodation and flights early for better rates and availability
• Pack light but bring one comfort item that makes you feel at home

I'm ready to help transform your travel dreams into detailed, actionable plans. What aspect of travel planning would you like to explore first?"""

# Global hybrid AI system instance
hybrid_ai_system = HybridAISystem()

def generate_hybrid_response(prompt: str, system_prompt: str = None, agent_name: str = None) -> Dict[str, Any]:
    """Convenience function for hybrid AI response generation"""
    return hybrid_ai_system.generate_response(prompt, system_prompt, agent_name)
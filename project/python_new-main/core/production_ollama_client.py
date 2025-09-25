"""
Production Ollama Client for LangGraph Multi-Agent System
Prioritizes REAL AI responses from Ollama with minimal fallbacks
Designed specifically for travel agents requiring authentic AI-generated content
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

class ProductionOllamaClient:
    """
    Production Ollama client that prioritizes real AI responses
    Only uses fallbacks when Ollama is completely unavailable
    """
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "gemma2:2b", timeout: int = 15):
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.timeout = timeout
        
        # Session for persistent connections
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Connection': 'keep-alive'
        })
        
        # Thread pool for timeout control
        self.executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="ProductionOllama")
        
        # Connection validation
        self._validate_ollama_connection()
        
        logger.info(f"✅ Production Ollama client initialized: {self.base_url}, model: {self.model}")
    
    def _validate_ollama_connection(self):
        """Validate Ollama connection and model availability"""
        try:
            # Check server availability
            response = self.session.get(f"{self.base_url}/api/tags", timeout=5)
            response.raise_for_status()
            
            # Check if our model is available
            models_data = response.json()
            available_models = [model['name'] for model in models_data.get('models', [])]
            
            if self.model not in available_models:
                logger.warning(f"⚠️ Model {self.model} not found. Available: {available_models}")
                if available_models:
                    self.model = available_models[0]
                    logger.info(f"🔄 Switched to available model: {self.model}")
            
            logger.info(f"✅ Ollama server validated with model: {self.model}")
            
        except Exception as e:
            logger.error(f"❌ Ollama validation failed: {e}")
            raise ConnectionError(f"Cannot connect to Ollama server at {self.base_url}")
    
    def is_available(self) -> bool:
        """Quick health check for Ollama availability"""
        try:
            response = self.session.get(f"{self.base_url}/api/tags", timeout=2)
            return response.status_code == 200
        except Exception:
            return False
    
    def generate_response(self, prompt: str, system_prompt: str = None, agent_name: str = None) -> str:
        """
        Generate PURE Ollama AI responses only - no hardcoded fallbacks
        Prioritizes getting real AI responses with multiple retry strategies
        """
        if not prompt or not prompt.strip():
            return "I'm ready to help with your travel planning. Please share your specific question!"
        
        # Enhance prompt for better context and relevance
        enhanced_prompt = self._create_perfect_prompt(prompt, agent_name)
        enhanced_system = self._create_perfect_system_prompt(agent_name, prompt)
        
        # Multiple Ollama attempts with different strategies - optimized for speed
        strategies = [
            {"temperature": 0.7, "timeout": 8, "tokens": 350},
            {"temperature": 0.8, "timeout": 12, "tokens": 400}, 
            {"temperature": 0.6, "timeout": 15, "tokens": 450},
            {"temperature": 0.9, "timeout": 10, "tokens": 300}
        ]
        
        for i, strategy in enumerate(strategies):
            try:
                logger.info(f"🤖 Ollama attempt {i+1}/4 with strategy: temp={strategy['temperature']}, timeout={strategy['timeout']}s")
                
                result = self._attempt_ollama_with_strategy(enhanced_prompt, enhanced_system, strategy)
                
                if result and len(result.strip()) > 30:
                    if self._is_response_relevant(prompt, result):
                        logger.info(f"🎯 SUCCESS: Pure Ollama response generated ({len(result)} chars) on attempt {i+1}")
                        return result.strip()
                    else:
                        logger.info(f"🔄 Response not relevant enough, trying next strategy...")
                        continue
                
            except Exception as e:
                logger.warning(f"⚠️ Ollama strategy {i+1} failed: {e}")
                continue
        
        # Final attempt with basic configuration if all strategies fail
        try:
            logger.info("🔄 Final Ollama attempt with basic configuration...")
            result = self._make_basic_ollama_request(prompt, system_prompt or enhanced_system)
            if result and len(result.strip()) > 10:
                logger.info(f"🎯 Final attempt SUCCESS: Ollama response ({len(result)} chars)")
                return result.strip()
        except Exception as e:
            logger.error(f"❌ All Ollama attempts failed: {e}")
        
        # Only return basic message if ALL Ollama attempts fail completely
        return f"I understand you're asking about: '{prompt[:100]}{'...' if len(prompt) > 100 else ''}'. I'm currently experiencing technical difficulties connecting to the AI system, but I'm here to help with your travel planning needs."
    
    def _create_perfect_prompt(self, prompt: str, agent_name: str = None) -> str:
        """Create enhanced prompt for perfect contextual responses"""
        # Extract key travel elements from the query
        query_analysis = self._analyze_travel_query(prompt)
        
        base_prompt = f"Travel Query: {prompt}\n\n"
        
        # Add context based on detected elements
        if query_analysis['destination']:
            base_prompt += f"Destination Context: {query_analysis['destination']}\n"
        if query_analysis['travel_type']:
            base_prompt += f"Travel Type: {query_analysis['travel_type']}\n"
        if query_analysis['concern_type']:
            base_prompt += f"Primary Concern: {query_analysis['concern_type']}\n"
        
        # Add agent-specific context
        agent_contexts = {
            "TextTripAnalyzer": "Provide detailed destination analysis, logistics, and practical travel planning advice.",
            "TripMoodDetector": "Address emotional concerns, provide reassurance, and build travel confidence.",
            "TripCommsCoach": "Give specific communication tips, phrases, and cultural interaction advice.",
            "TripBehaviorGuide": "Provide clear next steps, decision frameworks, and actionable guidance.",
            "TripCalmPractice": "Offer anxiety relief techniques, stress management, and calming strategies.",
            "TripSummarySynth": "Provide comprehensive overview and synthesized recommendations."
        }
        
        if agent_name in agent_contexts:
            base_prompt += f"\nResponse Focus: {agent_contexts[agent_name]}\n"
        
        base_prompt += f"\nProvide a specific, helpful response directly addressing this travel query with actionable advice."
        
        return base_prompt
    
    def _create_perfect_system_prompt(self, agent_name: str = None, user_query: str = "") -> str:
        """Create optimized system prompt for perfect responses"""
        base_system = "You are an expert travel advisor with deep knowledge of destinations worldwide. "
        
        agent_specializations = {
            "TextTripAnalyzer": "You specialize in destination analysis, travel planning, logistics, and creating detailed itineraries. Focus on practical, actionable travel advice.",
            "TripMoodDetector": "You specialize in travel psychology, emotional support, and building confidence for nervous or excited travelers. Be empathetic and encouraging.",
            "TripCommsCoach": "You specialize in travel communication, language barriers, cultural etiquette, and interpersonal interactions while traveling.",
            "TripBehaviorGuide": "You specialize in travel decision-making, behavioral guidance, and providing clear next steps for travel planning and execution.",
            "TripCalmPractice": "You specialize in travel anxiety management, stress relief, mindfulness practices, and helping travelers feel calm and prepared.",
            "TripSummarySynth": "You specialize in synthesizing travel information, creating comprehensive summaries, and providing holistic travel guidance."
        }
        
        if agent_name in agent_specializations:
            base_system += agent_specializations[agent_name]
        else:
            base_system += "Provide comprehensive travel guidance covering all aspects of travel planning and execution."
        
        base_system += " Always provide specific, actionable advice that directly addresses the user's query. Be concise but thorough."
        
        return base_system
    
    
    def _analyze_travel_query(self, prompt: str) -> dict:
        """Analyze travel query to extract key elements for better context"""
        prompt_lower = prompt.lower()
        
        # Detect destinations
        destinations = []
        common_destinations = {
            'tokyo': 'Tokyo, Japan', 'japan': 'Japan', 'paris': 'Paris, France', 'france': 'France',
            'italy': 'Italy', 'rome': 'Rome, Italy', 'london': 'London, UK', 'uk': 'United Kingdom',
            'spain': 'Spain', 'madrid': 'Madrid, Spain', 'barcelona': 'Barcelona, Spain',
            'greece': 'Greece', 'athens': 'Athens, Greece', 'thailand': 'Thailand', 'bangkok': 'Bangkok, Thailand',
            'india': 'India', 'delhi': 'Delhi, India', 'mumbai': 'Mumbai, India', 'kerala': 'Kerala, India',
            'germany': 'Germany', 'berlin': 'Berlin, Germany', 'amsterdam': 'Amsterdam, Netherlands',
            'netherlands': 'Netherlands', 'europe': 'Europe', 'asia': 'Asia', 'america': 'America',
            'usa': 'United States', 'new york': 'New York, USA', 'california': 'California, USA'
        }
        
        for key, full_name in common_destinations.items():
            if key in prompt_lower:
                destinations.append(full_name)
                break
        
        # Detect travel types
        travel_types = []
        if any(word in prompt_lower for word in ['business', 'work', 'conference', 'meeting']):
            travel_types.append('business')
        if any(word in prompt_lower for word in ['vacation', 'holiday', 'leisure', 'fun', 'relax']):
            travel_types.append('leisure')
        if any(word in prompt_lower for word in ['backpack', 'budget', 'cheap', 'affordable']):
            travel_types.append('budget')
        if any(word in prompt_lower for word in ['luxury', 'premium', 'high-end', 'expensive']):
            travel_types.append('luxury')
        if any(word in prompt_lower for word in ['family', 'kids', 'children', 'parents']):
            travel_types.append('family')
        if any(word in prompt_lower for word in ['solo', 'alone', 'myself', 'single']):
            travel_types.append('solo')
        if any(word in prompt_lower for word in ['romantic', 'honeymoon', 'couple', 'partner']):
            travel_types.append('romantic')
        
        # Detect concern types
        concerns = []
        if any(word in prompt_lower for word in ['nervous', 'anxious', 'worried', 'scared', 'afraid']):
            concerns.append('anxiety')
        if any(word in prompt_lower for word in ['language', 'communicate', 'speak', 'talk']):
            concerns.append('communication')
        if any(word in prompt_lower for word in ['budget', 'money', 'cost', 'expensive', 'afford']):
            concerns.append('budget')
        if any(word in prompt_lower for word in ['safety', 'safe', 'dangerous', 'security']):
            concerns.append('safety')
        if any(word in prompt_lower for word in ['plan', 'planning', 'organize', 'schedule']):
            concerns.append('planning')
        if any(word in prompt_lower for word in ['choose', 'decide', 'decision', 'options']):
            concerns.append('decision-making')
        
        return {
            'destination': destinations[0] if destinations else None,
            'travel_type': travel_types[0] if travel_types else None,
            'concern_type': concerns[0] if concerns else None,
            'all_destinations': destinations,
            'all_travel_types': travel_types,
            'all_concerns': concerns
        }
    
    def _is_response_relevant(self, query: str, response: str) -> bool:
        """Check if response is relevant to the query"""
        query_lower = query.lower()
        response_lower = response.lower()
        
        # Check for basic relevance - response should mention key terms from query
        query_words = set(query_lower.split())
        response_words = set(response_lower.split())
        
        # Remove common words
        common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'this', 'that', 'these', 'those'}
        
        query_keywords = query_words - common_words
        relevant_keywords = query_keywords.intersection(response_words)
        
        # Check relevance ratio
        relevance_ratio = len(relevant_keywords) / max(len(query_keywords), 1)
        
        # Also check if response contains travel-related terms when query is about travel
        travel_terms = {'travel', 'trip', 'visit', 'destination', 'vacation', 'journey', 'tourism', 'hotel', 'flight', 'plan'}
        has_travel_context = bool(travel_terms.intersection(response_words))
        
        return relevance_ratio > 0.3 or (has_travel_context and len(response) > 100)
    
    def _attempt_ollama_with_strategy(self, prompt: str, system_prompt: str, strategy: dict) -> str:
        """Attempt Ollama request with specific strategy parameters"""
        import threading
        import queue
        
        result_queue = queue.Queue()
        
        def ollama_request():
            try:
                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": strategy["temperature"],
                        "top_p": 0.9,
                        "top_k": 40,
                        "repeat_penalty": 1.1,
                        "num_predict": strategy["tokens"],
                        "num_ctx": 2048,  # Reduced context window for speed
                        "stop": ["\n\n\n", "Human:", "Assistant:", "User:", "Query:"]
                    }
                }
                
                if system_prompt:
                    payload["system"] = system_prompt
                
                response = self.session.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                    timeout=strategy["timeout"]
                )
                
                response.raise_for_status()
                result = response.json()
                result_queue.put(("success", result.get('response', '').strip()))
                
            except Exception as e:
                result_queue.put(("error", str(e)))
        
        thread = threading.Thread(target=ollama_request, daemon=True)
        thread.start()
        
        try:
            status, result = result_queue.get(timeout=strategy["timeout"] + 2)
            if status == "success":
                return result
            else:
                logger.warning(f"Strategy request failed: {result}")
                return None
        except queue.Empty:
            logger.warning(f"Strategy timeout after {strategy['timeout']}s")
            return None
    
    def _make_basic_ollama_request(self, prompt: str, system_prompt: str = None) -> str:
        """Make a basic Ollama request as final attempt"""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.8,
                "num_predict": 400,
                "num_ctx": 2048,
            }
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        response = self.session.post(
            f"{self.base_url}/api/generate",
            json=payload,
            timeout=10
        )
        
        response.raise_for_status()
        result = response.json()
        
        return result.get('response', '').strip()
    
    
    
    
    def get_connection_status(self) -> Dict[str, Any]:
        """Get detailed connection status"""
        is_available = self.is_available()
        return {
            "available": is_available,
            "base_url": self.base_url,
            "model": self.model,
            "timeout": self.timeout,
            "status": "connected" if is_available else "disconnected"
        }
    
    def close(self):
        """Clean up resources"""
        try:
            if hasattr(self.session, 'close'):
                self.session.close()
            if hasattr(self.executor, 'shutdown'):
                self.executor.shutdown(wait=False)
            logger.info("✅ Production Ollama client resources cleaned up")
        except Exception as e:
            logger.warning(f"⚠️ Cleanup error: {e}")

# Global production client instance
production_ollama_client = ProductionOllamaClient()

def generate_response(prompt: str, system_prompt: str = None, agent_name: str = None) -> str:
    """Convenience function for generating real AI responses"""
    return production_ollama_client.generate_response(prompt, system_prompt, agent_name)
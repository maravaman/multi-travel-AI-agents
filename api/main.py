@@ .. @@
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
            
            # Use the improved method with immediate fallback
            dynamic_response = ollama_client.generate_response_with_immediate_fallback(
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
            
            dynamic_response = ollama_client.generate_response_with_immediate_fallback(
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

# ✅ Ollama Status Check
@app.get("/api/ollama/status")
async def ollama_status():
    """Check Ollama server status"""
    try:
        if not ollama_client:
            return {
                "available": False,
                "error": "Ollama client not initialized",
                "base_url": Config.OLLAMA_BASE_URL,
                "models": [],
                "health": "unavailable"
            }

        # Use the improved health check
        available = ollama_client.is_available()
        
        # Get additional status info
        models = []
        health_status = "unknown"
        
        if available:
            try:
                models = ollama_client.list_models()
                health_status = "healthy"
            except Exception as e:
                health_status = f"partial: {str(e)}"

        return {
            "available": available,
            "base_url": ollama_client.base_url,
            "status": "connected" if available else "disconnected",
            "models": models,
            "health": health_status,
            "default_model": ollama_client.default_model,
            "timeout": ollama_client.timeout
        }
    except Exception as e:
        logger.error(f"Ollama status check failed: {e}")
        return {
            "available": False,
            "error": str(e),
            "base_url": Config.OLLAMA_BASE_URL,
            "models": [],
            "health": "error"
        }
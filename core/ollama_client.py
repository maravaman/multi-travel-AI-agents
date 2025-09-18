@@ .. @@
"""
Improved Ollama integration for local LLM responses
Enhanced with better timeout handling, retry logic, and connection pooling
"""
import requests
import json
import logging
import os
import time
from typing import Dict, List, Optional, Any
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Try to import decouple, fallback to os.getenv
try:
    from decouple import config
except ImportError:
    def config(key, default=None, cast=None):
        value = os.getenv(key, default)
        if cast and value is not None:
            return cast(value)
        return value

logger = logging.getLogger(__name__)

# Optional mock fallback
try:
    from core.mock_ollama_client import mock_ollama_client as MOCK_OLLAMA_CLIENT
except Exception:
    MOCK_OLLAMA_CLIENT = None

FALLBACK_TO_MOCK = os.getenv('OLLAMA_ENABLE_MOCK_FALLBACK', 'true').lower() == 'true'

class ImprovedOllamaClient:
    """Enhanced client for interacting with local Ollama server"""
    
    def __init__(self):
        self.base_url = config('OLLAMA_BASE_URL', default='http://localhost:11434')
        self.default_model = config('OLLAMA_DEFAULT_MODEL', default='llama3:latest')
        
        # Improved timeout configuration for better reliability
-        self.timeout = config('OLLAMA_TIMEOUT', default=8, cast=int)  # 8 seconds for generation
+        self.timeout = config('OLLAMA_TIMEOUT', default=15, cast=int)  # 15 seconds for generation
        self.connection_timeout = config('OLLAMA_CONNECTION_TIMEOUT', default=3, cast=int)
-        self.read_timeout = config('OLLAMA_READ_TIMEOUT', default=8, cast=int)
+        self.read_timeout = config('OLLAMA_READ_TIMEOUT', default=15, cast=int)
        
        # Enable retries for better reliability
-        self.max_retries = config('OLLAMA_MAX_RETRIES', default=1, cast=int)  # 1 retry only
+        self.max_retries = config('OLLAMA_MAX_RETRIES', default=2, cast=int)  # 2 retries
        self.retry_delay = config('OLLAMA_RETRY_DELAY', default=0.5, cast=float)
        
        # Initialize session with connection pooling and retry strategy
        self.session = self._create_session()
+        
+        # Connection status tracking
+        self._last_health_check = 0
+        self._connection_status = None
+        
+        # Perform initial health check
+        self._check_health()
        
        logger.info(f"Initialized OllamaClient with timeout={self.timeout}s, retries={self.max_retries}")
    
+    def _check_health(self):
+        """Check Ollama server health"""
+        try:
+            response = self.session.get(
+                f"{self.base_url}/api/tags",
+                timeout=(2, 3)  # Quick health check
+            )
+            self._connection_status = response.status_code == 200
+            self._last_health_check = time.time()
+            
+            if self._connection_status:
+                # Check available models
+                models_data = response.json()
+                available_models = [model['name'] for model in models_data.get('models', [])]
+                
+                if self.default_model not in available_models and available_models:
+                    logger.warning(f"⚠️ Default model {self.default_model} not found")
+                    logger.info(f"Available models: {available_models}")
+                    # Use first available model
+                    self.default_model = available_models[0]
+                    logger.info(f"🔄 Switched to: {self.default_model}")
+                
+                logger.info(f"✅ Ollama server healthy with model: {self.default_model}")
+            else:
+                logger.warning(f"⚠️ Ollama server returned status: {response.status_code}")
+                
+        except Exception as e:
+            self._connection_status = False
+            self._last_health_check = time.time()
+            logger.warning(f"⚠️ Ollama health check failed: {e}")
    
    def _create_session(self) -> requests.Session:
        """Create a requests session with optimal settings for Ollama"""
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=1.0,  # Exponential backoff
            status_forcelist=[500, 502, 503, 504, 408],  # HTTP status codes to retry on
            allowed_methods=["GET", "POST"],  # HTTP methods to retry
        )
        
        # Configure HTTP adapter with retry strategy
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,  # Number of connection pools
            pool_maxsize=20,      # Max connections per pool
        )
        
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set default headers
        session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'ImprovedOllamaClient/2.0',
            'Connection': 'keep-alive'
        })
        
        return session
    
    def _get_timeout_tuple(self) -> tuple:
        """Get timeout as a tuple (connection_timeout, read_timeout)"""
        return (self.connection_timeout, self.read_timeout)
    
    def _execute_with_retry(self, func, *args, **kwargs):
        """Execute a function with custom retry logic"""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except requests.exceptions.Timeout as e:
                last_exception = e
                if attempt < self.max_retries:
                    delay = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"Timeout on attempt {attempt + 1}/{self.max_retries + 1}, retrying in {delay}s")
                    time.sleep(delay)
                else:
                    logger.error(f"All {self.max_retries + 1} attempts failed due to timeout")
                    break
            except requests.exceptions.RequestException as e:
                last_exception = e
                if attempt < self.max_retries:
                    delay = self.retry_delay * (2 ** attempt)
                    logger.warning(f"Request failed on attempt {attempt + 1}/{self.max_retries + 1}, retrying in {delay}s: {e}")
                    time.sleep(delay)
                else:
                    logger.error(f"All {self.max_retries + 1} attempts failed: {e}")
                    break
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                last_exception = e
                break
        
        raise last_exception
    
    def is_available(self) -> bool:
        """Check if Ollama server is available with caching"""
+        # Cache health check for 30 seconds
+        current_time = time.time()
+        if current_time - self._last_health_check > 30:
+            self._check_health()
+        
+        return self._connection_status or False
-        try:
-            response = self.session.get(
-                f"{self.base_url}/api/tags", 
-                timeout=(1, 2)  # Ultra-fast connection check
-            )
-            is_available = response.status_code == 200
-            if is_available:
-                logger.debug("Ollama server is available")
-            return is_available
-        except Exception as e:
-            logger.debug(f"Ollama server not available (using fallback): {e}")
-            return False
    
    def generate_response_with_immediate_fallback(
        self, 
        prompt: str, 
        model: Optional[str] = None, 
        system_prompt: Optional[str] = None,
        context: Optional[List[str]] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
-        max_wait_seconds: float = 5.0
+        max_wait_seconds: float = 8.0
    ) -> str:
        """Generate response with immediate fallback for performance"""
        
        # Quick availability check first
        if not self.is_available():
            logger.info("Ollama not available, using immediate fallback")
            return self._get_immediate_fallback(prompt, system_prompt)
        
        # Try with optimized timeout for performance
        try:
            import threading
            import queue
            
            result_queue = queue.Queue()
            
            def ollama_request():
                try:
                    response = self.generate_response(
                        prompt=prompt,
                        model=model,
                        system_prompt=system_prompt,
                        context=context,
                        max_tokens=max_tokens,
                        temperature=temperature
                    )
                    result_queue.put(("success", response))
                except Exception as e:
                    result_queue.put(("error", str(e)))
            
            # Start Ollama request in background
            thread = threading.Thread(target=ollama_request, daemon=True)
            thread.start()
            
            # Wait for result or timeout
            try:
                status, result = result_queue.get(timeout=max_wait_seconds)
                if status == "success" and result and len(result.strip()) > 10:
                    logger.info(f"✅ Ollama response in {max_wait_seconds}s")
                    return result
                else:
                    logger.warning(f"Ollama returned insufficient response, using fallback")
                    return self._get_immediate_fallback(prompt, system_prompt)
            except queue.Empty:
                logger.warning(f"Ollama timeout after {max_wait_seconds}s, using immediate fallback")
                return self._get_immediate_fallback(prompt, system_prompt)
                
        except Exception as e:
            logger.warning(f"Ollama fallback error: {e}")
            return self._get_immediate_fallback(prompt, system_prompt)
    
    def _get_immediate_fallback(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Get immediate intelligent fallback response"""
        try:
            from core.enhanced_mock_ollama_client import enhanced_mock_client
            return enhanced_mock_client.generate_response(
                prompt=prompt,
                system_prompt=system_prompt
            )
        except Exception as e:
            logger.error(f"Enhanced mock fallback failed: {e}")
            # Final fallback
            return f"I understand you're asking about: {prompt[:100]}. I'm currently experiencing technical issues but would be happy to help once the system is fully operational."
    
    def list_models(self) -> List[Dict[str, Any]]:
        """List available models"""
        try:
            def _list_models():
                response = self.session.get(
                    f"{self.base_url}/api/tags", 
                    timeout=self._get_timeout_tuple()
                )
                response.raise_for_status()
                return response.json().get('models', [])
            
            return self._execute_with_retry(_list_models)
            
        except Exception as e:
            logger.error(f"Error listing models: {e}")
            # Fallback to mock models if enabled
            if FALLBACK_TO_MOCK and MOCK_OLLAMA_CLIENT:
                logger.warning("Using mock model list due to Ollama error")
                try:
                    return MOCK_OLLAMA_CLIENT.list_models()
                except Exception:
                    return []
            return []
    
    def generate_response(
        self, 
        prompt: str, 
        model: Optional[str] = None, 
        system_prompt: Optional[str] = None,
        context: Optional[List[str]] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> str:
        """Generate response from Ollama model with enhanced reliability"""
        try:
            model = model or self.default_model
-            max_tokens = max_tokens or config('OLLAMA_MAX_TOKENS', default=1000, cast=int)
+            max_tokens = max_tokens or config('OLLAMA_MAX_TOKENS', default=2000, cast=int)
            temperature = temperature or config('OLLAMA_TEMPERATURE', default=0.7, cast=float)
            
            # Prepare the prompt with context if provided
            full_prompt = prompt
            if context:
                context_str = "\n".join(context)
                full_prompt = f"Context:\n{context_str}\n\nQuery: {prompt}"
            
            payload = {
                "model": model,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
-                    "num_predict": max_tokens
+                    "num_predict": max_tokens,
+                    "top_k": 40,
+                    "top_p": 0.9,
+                    "repeat_penalty": 1.1,
+                    "num_ctx": 4096,
+                    "stop": ["Human:", "Assistant:", "User:"]
                }
            }
            
            if system_prompt:
                payload["system"] = system_prompt
            
            # Log request details for debugging
            logger.debug(f"Generating response with model={model}, timeout={self.timeout}s")
            
            def _generate():
                response = self.session.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                    timeout=self._get_timeout_tuple()
                )
                response.raise_for_status()
                return response.json()
            
            result = self._execute_with_retry(_generate)
            response_text = result.get('response', 'No response generated')
            
+            # Validate response quality
+            if len(response_text.strip()) < 10:
+                logger.warning("⚠️ Ollama returned very short response, using fallback")
+                return self._get_immediate_fallback(prompt, system_prompt)
            
            logger.debug(f"Successfully generated response ({len(response_text)} characters)")
            return response_text
            
        except requests.exceptions.Timeout:
            logger.error("Ollama request timed out after all retries")
            # Try enhanced mock fallback
            logger.warning("Ollama not available, falling back to enhanced mock client")
            try:
                from core.enhanced_mock_ollama_client import enhanced_mock_client
                return enhanced_mock_client.generate_response(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    context=context,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
            except Exception as mock_error:
                logger.error(f"Mock fallback also failed: {mock_error}")
            return "Request timed out after multiple attempts. Please try again or check Ollama server status."
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama request failed after all retries: {e}")
            # Try enhanced mock fallback
            logger.warning("Falling back to enhanced mock client due to request failure")
            try:
                from core.enhanced_mock_ollama_client import enhanced_mock_client
                return enhanced_mock_client.generate_response(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    context=context,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
            except Exception as mock_error:
                logger.error(f"Mock fallback also failed: {mock_error}")
            return f"Error generating response after retries: {str(e)}"
            
        except Exception as e:
            logger.error(f"Unexpected error in generate_response: {e}")
            # Try enhanced mock fallback
            logger.warning("Falling back to enhanced mock client due to unexpected error")
            try:
                from core.enhanced_mock_ollama_client import enhanced_mock_client
                return enhanced_mock_client.generate_response(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    context=context,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
            except Exception as mock_error:
                logger.error(f"Mock fallback also failed: {mock_error}")
            return "An unexpected error occurred. Please try again."
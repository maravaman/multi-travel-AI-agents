@@ .. @@
    # Ollama Configuration
    OLLAMA_BASE_URL: str = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
    OLLAMA_DEFAULT_MODEL: str = os.getenv('OLLAMA_DEFAULT_MODEL', 'llama3:latest')
-    OLLAMA_TIMEOUT: int = int(os.getenv('OLLAMA_TIMEOUT', '30'))  # Optimized for travel assistant
+    OLLAMA_TIMEOUT: int = int(os.getenv('OLLAMA_TIMEOUT', '15'))  # Optimized for travel assistant
    OLLAMA_CONNECTION_TIMEOUT: int = int(os.getenv('OLLAMA_CONNECTION_TIMEOUT', '10'))  # Connection timeout
-    OLLAMA_READ_TIMEOUT: int = int(os.getenv('OLLAMA_READ_TIMEOUT', '30'))  # Read timeout for responses
-    OLLAMA_MAX_RETRIES: int = int(os.getenv('OLLAMA_MAX_RETRIES', '3'))  # Number of retry attempts
+    OLLAMA_READ_TIMEOUT: int = int(os.getenv('OLLAMA_READ_TIMEOUT', '15'))  # Read timeout for responses
+    OLLAMA_MAX_RETRIES: int = int(os.getenv('OLLAMA_MAX_RETRIES', '2'))  # Number of retry attempts
    OLLAMA_RETRY_DELAY: float = float(os.getenv('OLLAMA_RETRY_DELAY', '2.0'))  # Initial retry delay in seconds
-    OLLAMA_MAX_TOKENS: int = int(os.getenv('OLLAMA_MAX_TOKENS', '2000'))
+    OLLAMA_MAX_TOKENS: int = int(os.getenv('OLLAMA_MAX_TOKENS', '1500'))
    OLLAMA_TEMPERATURE: float = float(os.getenv('OLLAMA_TEMPERATURE', '0.7'))
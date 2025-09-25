#!/usr/bin/env python3
"""
🔧 Enhanced Configuration Management System
Centralized configuration with validation, type safety, and environment management
"""

import os
import logging
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
import json
from pydantic import BaseModel, validator, Field

logger = logging.getLogger(__name__)

class Environment(Enum):
    """Deployment environments"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"

class LogLevel(Enum):
    """Logging levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class DatabaseConfig(BaseModel):
    """Database configuration with validation"""
    host: str = "localhost"
    user: str = "root"
    password: str = ""
    database: str = "travel_assistant"
    port: int = Field(default=3306, ge=1, le=65535)
    connect_timeout: int = Field(default=10, ge=1, le=60)
    charset: str = "utf8mb4"
    pool_size: int = Field(default=10, ge=1, le=100)
    
    @validator('port')
    def validate_port(cls, v):
        if not 1 <= v <= 65535:
            raise ValueError('Port must be between 1 and 65535')
        return v

class RedisConfig(BaseModel):
    """Redis configuration with validation"""
    host: str = "localhost"
    port: int = Field(default=6379, ge=1, le=65535)
    db: int = Field(default=0, ge=0, le=15)
    socket_timeout: int = Field(default=5, ge=1, le=30)
    socket_connect_timeout: int = Field(default=5, ge=1, le=30)
    max_connections: int = Field(default=50, ge=1, le=1000)
    
class OllamaConfig(BaseModel):
    """Ollama LLM configuration"""
    base_url: str = "http://localhost:11434"
    default_model: str = "llama3:latest"
    timeout: int = Field(default=30, ge=5, le=300)
    connection_timeout: int = Field(default=10, ge=1, le=60)
    read_timeout: int = Field(default=30, ge=5, le=300)
    max_retries: int = Field(default=3, ge=1, le=10)
    retry_delay: float = Field(default=2.0, ge=0.1, le=10.0)
    max_tokens: int = Field(default=2000, ge=100, le=8000)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)

class SecurityConfig(BaseModel):
    """Security configuration"""
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=480, ge=1, le=10080)
    password_min_length: int = Field(default=8, ge=6, le=128)
    max_login_attempts: int = Field(default=5, ge=1, le=20)
    lockout_duration_minutes: int = Field(default=15, ge=1, le=1440)
    
    @validator('secret_key')
    def validate_secret_key(cls, v):
        if len(v) < 32:
            raise ValueError('Secret key must be at least 32 characters long')
        return v

class PerformanceConfig(BaseModel):
    """Performance and optimization settings"""
    max_concurrent_requests: int = Field(default=100, ge=1, le=1000)
    request_timeout_seconds: int = Field(default=30, ge=5, le=300)
    cache_ttl_seconds: int = Field(default=3600, ge=60, le=86400)
    memory_cleanup_interval_hours: int = Field(default=6, ge=1, le=24)
    vector_search_limit: int = Field(default=10, ge=1, le=100)
    
class AgentConfig(BaseModel):
    """Individual agent configuration"""
    id: str
    name: str
    description: str = ""
    keywords: List[str] = Field(default_factory=list)
    capabilities: List[str] = Field(default_factory=list)
    priority: int = Field(default=2, ge=1, le=5)
    system_prompt_template: str = ""
    timeout_seconds: int = Field(default=30, ge=5, le=300)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    enabled: bool = True

class AgentsConfig(BaseModel):
    """Multi-agent system configuration"""
    agents: List[AgentConfig] = Field(default_factory=list)
    max_agents_per_query: int = Field(default=3, ge=1, le=10)
    routing_strategy: str = "keyword_based"
    enable_multi_agent: bool = True
    synthesis_enabled: bool = True
    
class TravelSystemConfig(BaseModel):
    """Complete travel system configuration"""
    # Environment
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False
    
    # Application
    app_title: str = "Travel Assistant - AI System"
    app_description: str = "AI-powered travel planning with multi-agent intelligence"
    app_version: str = "3.0.0"
    app_host: str = "localhost"
    app_port: int = Field(default=8000, ge=1, le=65535)
    
    # Components
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    security: SecurityConfig
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
    agents: AgentsConfig = Field(default_factory=AgentsConfig)
    
    # Features
    enable_authentication: bool = True
    enable_vector_search: bool = True
    enable_memory_management: bool = True
    enable_rate_limiting: bool = True
    
    # Logging
    log_level: LogLevel = LogLevel.INFO
    log_file: Optional[str] = None
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Paths
    static_dir: str = "static"
    templates_dir: str = "templates"
    logs_dir: str = "logs"
    data_dir: str = "data"
    
    class Config:
        env_prefix = "TRAVEL_"
        case_sensitive = False

class ConfigManager:
    """Configuration manager with loading, validation, and environment handling"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path
        self._config: Optional[TravelSystemConfig] = None
        
    def load_config(self, force_reload: bool = False) -> TravelSystemConfig:
        """Load configuration from environment and files"""
        if self._config and not force_reload:
            return self._config
        
        try:
            # Load from environment variables first
            config_dict = self._load_from_environment()
            
            # Override with file-based config if available
            if self.config_path and os.path.exists(self.config_path):
                file_config = self._load_from_file(self.config_path)
                config_dict.update(file_config)
            
            # Create and validate configuration
            self._config = TravelSystemConfig(**config_dict)
            
            # Post-load validation
            self._validate_config(self._config)
            
            logger.info(f"✅ Configuration loaded successfully for {self._config.environment.value}")
            return self._config
            
        except Exception as e:
            logger.error(f"❌ Failed to load configuration: {e}")
            raise ConfigurationError(f"Configuration loading failed: {e}")
    
    def _load_from_environment(self) -> Dict[str, Any]:
        """Load configuration from environment variables"""
        config = {}
        
        # Application settings
        config['app_host'] = os.getenv('APP_HOST', 'localhost')
        config['app_port'] = int(os.getenv('APP_PORT', '8000'))
        config['debug'] = os.getenv('DEBUG', 'False').lower() == 'true'
        config['app_title'] = os.getenv('APP_TITLE', 'Travel Assistant - AI System')
        
        # Environment detection
        env_name = os.getenv('ENVIRONMENT', 'development').lower()
        try:
            config['environment'] = Environment(env_name)
        except ValueError:
            config['environment'] = Environment.DEVELOPMENT
        
        # Database configuration
        config['database'] = {
            'host': os.getenv('MYSQL_HOST', 'localhost'),
            'user': os.getenv('MYSQL_USER', 'root'),
            'password': os.getenv('MYSQL_PASSWORD', ''),
            'database': os.getenv('MYSQL_DATABASE', 'travel_assistant'),
            'port': int(os.getenv('MYSQL_PORT', '3306')),
            'connect_timeout': int(os.getenv('MYSQL_CONNECT_TIMEOUT', '10')),
            'charset': os.getenv('MYSQL_CHARSET', 'utf8mb4')
        }
        
        # Redis configuration
        config['redis'] = {
            'host': os.getenv('REDIS_HOST', 'localhost'),
            'port': int(os.getenv('REDIS_PORT', '6379')),
            'db': int(os.getenv('REDIS_DB', '0')),
            'socket_timeout': int(os.getenv('REDIS_SOCKET_TIMEOUT', '5')),
            'socket_connect_timeout': int(os.getenv('REDIS_SOCKET_CONNECT_TIMEOUT', '5'))
        }
        
        # Ollama configuration
        config['ollama'] = {
            'base_url': os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434'),
            'default_model': os.getenv('OLLAMA_DEFAULT_MODEL', 'llama3:latest'),
            'timeout': int(os.getenv('OLLAMA_TIMEOUT', '30')),
            'max_tokens': int(os.getenv('OLLAMA_MAX_TOKENS', '2000')),
            'temperature': float(os.getenv('OLLAMA_TEMPERATURE', '0.7'))
        }
        
        # Security configuration
        config['security'] = {
            'secret_key': os.getenv('SECRET_KEY', 'change-this-secret-key-in-production'),
            'algorithm': os.getenv('ALGORITHM', 'HS256'),
            'access_token_expire_minutes': int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', '480'))
        }
        
        # Logging
        log_level_str = os.getenv('LOG_LEVEL', 'INFO').upper()
        try:
            config['log_level'] = LogLevel(log_level_str)
        except ValueError:
            config['log_level'] = LogLevel.INFO
        
        config['log_file'] = os.getenv('LOG_FILE')
        
        return config
    
    def _load_from_file(self, file_path: str) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load config file {file_path}: {e}")
            return {}
    
    def _validate_config(self, config: TravelSystemConfig):
        """Additional configuration validation"""
        issues = []
        
        # Security checks
        if config.environment == Environment.PRODUCTION:
            if config.debug:
                issues.append("Debug mode should be disabled in production")
            
            if "change-this" in config.security.secret_key:
                issues.append("Secret key must be changed in production")
            
            if config.database.password == "":
                issues.append("Database password should be set in production")
        
        # Performance checks
        if config.performance.max_concurrent_requests > 1000:
            issues.append("Max concurrent requests seems too high")
        
        # Agent validation
        if not config.agents.agents:
            logger.warning("No agents configured, loading defaults")
            config.agents.agents = self._get_default_agents()
        
        # Report issues
        if issues:
            if config.environment == Environment.PRODUCTION:
                raise ConfigurationError(f"Production configuration issues: {'; '.join(issues)}")
            else:
                for issue in issues:
                    logger.warning(f"⚠️ Configuration warning: {issue}")
    
    def _get_default_agents(self) -> List[AgentConfig]:
        """Get default agent configuration"""
        return [
            AgentConfig(
                id="TextTripAnalyzer",
                name="Trip Analyzer",
                description="Analyzes travel planning text and extracts key information",
                keywords=["plan", "trip", "travel", "destination", "budget"],
                priority=2
            ),
            AgentConfig(
                id="TripMoodDetector", 
                name="Mood Detector",
                description="Detects travel emotions and provides emotional support",
                keywords=["excited", "nervous", "worried", "feeling", "mood"],
                priority=2
            ),
            AgentConfig(
                id="TripCommsCoach",
                name="Communication Coach",
                description="Provides travel communication tips and phrases",
                keywords=["communicate", "talk", "language", "phrase"],
                priority=2
            ),
            AgentConfig(
                id="TripBehaviorGuide",
                name="Behavior Guide", 
                description="Helps with travel decisions and next steps",
                keywords=["decide", "choose", "next", "help", "stuck"],
                priority=2
            ),
            AgentConfig(
                id="TripCalmPractice",
                name="Calm Practice",
                description="Provides stress relief and calming techniques",
                keywords=["stress", "anxiety", "calm", "overwhelmed"],
                priority=1
            ),
            AgentConfig(
                id="TripSummarySynth",
                name="Summary Synthesizer",
                description="Synthesizes responses from multiple agents",
                keywords=["summary", "synthesize", "complete"],
                priority=1
            )
        ]
    
    def get_database_url(self) -> str:
        """Get database connection URL"""
        if not self._config:
            raise ConfigurationError("Configuration not loaded")
        
        db = self._config.database
        return f"mysql://{db.user}:{db.password}@{db.host}:{db.port}/{db.database}"
    
    def get_redis_url(self) -> str:
        """Get Redis connection URL"""
        if not self._config:
            raise ConfigurationError("Configuration not loaded")
        
        redis = self._config.redis
        return f"redis://{redis.host}:{redis.port}/{redis.db}"
    
    def is_development(self) -> bool:
        """Check if running in development mode"""
        return self._config and self._config.environment == Environment.DEVELOPMENT
    
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return self._config and self._config.environment == Environment.PRODUCTION

class ConfigurationError(Exception):
    """Configuration-related error"""
    pass

# Global configuration manager
config_manager = ConfigManager()

def get_config() -> TravelSystemConfig:
    """Get the global configuration instance"""
    return config_manager.load_config()

def reload_config() -> TravelSystemConfig:
    """Reload configuration (useful for testing)"""
    return config_manager.load_config(force_reload=True)

if __name__ == "__main__":
    # Test configuration loading
    try:
        config = get_config()
        print(f"✅ Configuration loaded for {config.environment.value}")
        print(f"📊 Database: {config.database.host}:{config.database.port}")
        print(f"🔴 Redis: {config.redis.host}:{config.redis.port}")
        print(f"🤖 Ollama: {config.ollama.base_url}")
        print(f"👥 Agents: {len(config.agents.agents)} configured")
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
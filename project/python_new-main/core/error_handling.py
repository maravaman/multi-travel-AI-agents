#!/usr/bin/env python3
"""
🚨 Standardized Error Handling System
Consistent error handling patterns, custom exceptions, and error recovery mechanisms
"""

import logging
import traceback
import functools
from typing import Dict, Any, Optional, Union, Callable, Type
from datetime import datetime
from enum import Enum
import json

logger = logging.getLogger(__name__)

class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorCategory(Enum):
    """Error categories for classification"""
    SYSTEM = "system"
    DATABASE = "database"
    NETWORK = "network"
    AUTHENTICATION = "authentication"
    VALIDATION = "validation"
    AGENT_PROCESSING = "agent_processing"
    MEMORY = "memory"
    CONFIGURATION = "configuration"

class TravelSystemError(Exception):
    """Base exception for the travel system"""
    
    def __init__(self, 
                 message: str,
                 error_code: str = "SYSTEM_ERROR",
                 category: ErrorCategory = ErrorCategory.SYSTEM,
                 severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                 context: Dict[str, Any] = None,
                 user_message: str = None,
                 recoverable: bool = True):
        
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.category = category
        self.severity = severity
        self.context = context or {}
        self.user_message = user_message or self._get_default_user_message()
        self.recoverable = recoverable
        self.timestamp = datetime.now().isoformat()
        
    def _get_default_user_message(self) -> str:
        """Generate user-friendly error message"""
        if self.category == ErrorCategory.NETWORK:
            return "I'm having trouble connecting to services. Please try again in a moment."
        elif self.category == ErrorCategory.DATABASE:
            return "I'm experiencing a temporary data issue. Your request is being processed."
        elif self.category == ErrorCategory.AUTHENTICATION:
            return "Please check your login credentials and try again."
        elif self.category == ErrorCategory.AGENT_PROCESSING:
            return "I'm processing your travel request. This may take a moment longer than usual."
        else:
            return "I encountered a temporary issue. I'm still here to help with your travel planning!"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for logging/API responses"""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "user_message": self.user_message,
            "category": self.category.value,
            "severity": self.severity.value,
            "context": self.context,
            "recoverable": self.recoverable,
            "timestamp": self.timestamp
        }

class DatabaseError(TravelSystemError):
    """Database-related errors"""
    def __init__(self, message: str, context: Dict[str, Any] = None):
        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.HIGH,
            context=context,
            user_message="I'm experiencing a temporary data storage issue. Please try again shortly."
        )

class NetworkError(TravelSystemError):
    """Network and external service errors"""
    def __init__(self, message: str, service: str = None, context: Dict[str, Any] = None):
        context = context or {}
        if service:
            context["service"] = service
        
        super().__init__(
            message=message,
            error_code="NETWORK_ERROR",
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            context=context,
            user_message=f"I'm having trouble connecting to {'external services' if not service else service}. Please try again."
        )

class AuthenticationError(TravelSystemError):
    """Authentication and authorization errors"""
    def __init__(self, message: str, user_id: int = None):
        context = {"user_id": user_id} if user_id else {}
        super().__init__(
            message=message,
            error_code="AUTH_ERROR",
            category=ErrorCategory.AUTHENTICATION,
            severity=ErrorSeverity.HIGH,
            context=context,
            user_message="Please check your login credentials and try again."
        )

class ValidationError(TravelSystemError):
    """Input validation errors"""
    def __init__(self, message: str, field: str = None, value: Any = None):
        context = {}
        if field:
            context["field"] = field
        if value is not None:
            context["invalid_value"] = str(value)
        
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.LOW,
            context=context,
            user_message="Please check your input and try again."
        )

class AgentProcessingError(TravelSystemError):
    """Agent processing errors"""
    def __init__(self, message: str, agent_id: str = None, query: str = None):
        context = {}
        if agent_id:
            context["agent_id"] = agent_id
        if query:
            context["query"] = query[:100] + "..." if len(query) > 100 else query
        
        super().__init__(
            message=message,
            error_code="AGENT_ERROR",
            category=ErrorCategory.AGENT_PROCESSING,
            severity=ErrorSeverity.MEDIUM,
            context=context,
            user_message="I'm processing your travel request. This may take a moment longer than usual."
        )

class MemoryError(TravelSystemError):
    """Memory management errors"""
    def __init__(self, message: str, operation: str = None):
        context = {"operation": operation} if operation else {}
        super().__init__(
            message=message,
            error_code="MEMORY_ERROR",
            category=ErrorCategory.MEMORY,
            severity=ErrorSeverity.MEDIUM,
            context=context,
            user_message="I'm having trouble accessing your travel history. Your current request is still being processed."
        )

class ConfigurationError(TravelSystemError):
    """Configuration errors"""
    def __init__(self, message: str, component: str = None):
        context = {"component": component} if component else {}
        super().__init__(
            message=message,
            error_code="CONFIG_ERROR",
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.HIGH,
            context=context,
            user_message="I'm experiencing a configuration issue. Please contact support if this persists.",
            recoverable=False
        )

class ErrorHandler:
    """Centralized error handling and logging"""
    
    def __init__(self):
        self.error_stats = {}
        
    def handle_error(self, error: Exception, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle any error and return standardized response"""
        
        # Convert to TravelSystemError if needed
        if isinstance(error, TravelSystemError):
            travel_error = error
        else:
            travel_error = self._convert_to_travel_error(error, context)
        
        # Log the error
        self._log_error(travel_error)
        
        # Update statistics
        self._update_error_stats(travel_error)
        
        # Return standardized error response
        return {
            "success": False,
            "error": travel_error.to_dict(),
            "user_message": travel_error.user_message,
            "recoverable": travel_error.recoverable,
            "timestamp": travel_error.timestamp
        }
    
    def _convert_to_travel_error(self, error: Exception, context: Dict[str, Any] = None) -> TravelSystemError:
        """Convert generic exceptions to TravelSystemError"""
        error_message = str(error)
        error_type = type(error).__name__
        
        context = context or {}
        context["original_error_type"] = error_type
        
        # Map common exceptions
        if "connection" in error_message.lower() or "timeout" in error_message.lower():
            return NetworkError(f"Connection error: {error_message}", context=context)
        elif "database" in error_message.lower() or "mysql" in error_message.lower():
            return DatabaseError(f"Database error: {error_message}", context=context)
        elif "auth" in error_message.lower() or "login" in error_message.lower():
            return AuthenticationError(f"Authentication error: {error_message}")
        elif "validation" in error_message.lower() or "invalid" in error_message.lower():
            return ValidationError(f"Validation error: {error_message}")
        else:
            return TravelSystemError(
                message=error_message,
                error_code="UNEXPECTED_ERROR",
                context=context
            )
    
    def _log_error(self, error: TravelSystemError):
        """Log error with appropriate level"""
        error_dict = error.to_dict()
        
        if error.severity == ErrorSeverity.CRITICAL:
            logger.critical(f"CRITICAL ERROR [{error.error_code}]: {error.message}", 
                           extra={"error_details": error_dict})
        elif error.severity == ErrorSeverity.HIGH:
            logger.error(f"HIGH SEVERITY [{error.error_code}]: {error.message}",
                        extra={"error_details": error_dict})
        elif error.severity == ErrorSeverity.MEDIUM:
            logger.warning(f"MEDIUM SEVERITY [{error.error_code}]: {error.message}",
                          extra={"error_details": error_dict})
        else:
            logger.info(f"LOW SEVERITY [{error.error_code}]: {error.message}",
                       extra={"error_details": error_dict})
    
    def _update_error_stats(self, error: TravelSystemError):
        """Update error statistics"""
        key = f"{error.category.value}:{error.error_code}"
        if key not in self.error_stats:
            self.error_stats[key] = {
                "count": 0,
                "first_seen": error.timestamp,
                "last_seen": error.timestamp,
                "category": error.category.value,
                "severity": error.severity.value
            }
        
        self.error_stats[key]["count"] += 1
        self.error_stats[key]["last_seen"] = error.timestamp
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics"""
        return {
            "total_errors": sum(stat["count"] for stat in self.error_stats.values()),
            "error_breakdown": self.error_stats,
            "generated_at": datetime.now().isoformat()
        }

def with_error_handling(
    fallback_response: str = "I apologize, but I encountered an issue. I'm still here to help!",
    log_errors: bool = True,
    return_error_details: bool = False
):
    """Decorator for consistent error handling across functions"""
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_errors:
                    error_handler.handle_error(e, {"function": func.__name__})
                
                if return_error_details and isinstance(e, TravelSystemError):
                    return {
                        "success": False,
                        "error": e.to_dict(),
                        "fallback_response": fallback_response
                    }
                else:
                    # Return fallback for user-facing functions
                    return fallback_response
        
        return wrapper
    return decorator

def safe_agent_execution(agent_function: Callable) -> Callable:
    """Decorator specifically for agent execution with recovery"""
    
    @functools.wraps(agent_function)
    def wrapper(*args, **kwargs):
        try:
            return agent_function(*args, **kwargs)
        except Exception as e:
            # Extract agent context from args/kwargs
            agent_id = kwargs.get("agent_id") or (args[1] if len(args) > 1 else "unknown")
            query = kwargs.get("query") or kwargs.get("question") or "unknown"
            
            agent_error = AgentProcessingError(
                message=f"Agent {agent_id} failed: {str(e)}",
                agent_id=agent_id,
                query=query
            )
            
            error_response = error_handler.handle_error(agent_error)
            
            # Return recovery response that maintains user experience
            return {
                "agent_id": agent_id,
                "response": f"I'm {agent_id} and I'm currently experiencing a brief issue. However, I can still help with your travel planning. Your query was: '{query}'. Let me provide some general guidance while I recover.",
                "success": False,
                "error": error_response["error"],
                "recovery_mode": True
            }
    
    return wrapper

def validate_input(validation_rules: Dict[str, Callable]) -> Callable:
    """Decorator for input validation with consistent error handling"""
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Validate inputs based on rules
            for field_name, validator in validation_rules.items():
                value = kwargs.get(field_name)
                if value is not None:
                    try:
                        if not validator(value):
                            raise ValidationError(
                                f"Invalid value for {field_name}",
                                field=field_name,
                                value=value
                            )
                    except ValidationError:
                        raise
                    except Exception as e:
                        raise ValidationError(
                            f"Validation failed for {field_name}: {str(e)}",
                            field=field_name,
                            value=value
                        )
            
            return func(*args, **kwargs)
        return wrapper
    return decorator

# Global error handler instance
error_handler = ErrorHandler()

# Convenience functions
def handle_database_error(operation: str, error: Exception) -> Dict[str, Any]:
    """Handle database errors consistently"""
    db_error = DatabaseError(f"Database operation '{operation}' failed: {str(error)}")
    return error_handler.handle_error(db_error)

def handle_network_error(service: str, error: Exception) -> Dict[str, Any]:
    """Handle network errors consistently"""
    net_error = NetworkError(f"Network call to {service} failed: {str(error)}", service=service)
    return error_handler.handle_error(net_error)

def handle_agent_error(agent_id: str, query: str, error: Exception) -> Dict[str, Any]:
    """Handle agent processing errors consistently"""
    agent_error = AgentProcessingError(
        f"Agent {agent_id} processing failed: {str(error)}",
        agent_id=agent_id,
        query=query
    )
    return error_handler.handle_error(agent_error)

# Recovery strategies
class RecoveryStrategy:
    """Recovery strategies for different error scenarios"""
    
    @staticmethod
    def database_recovery(operation: str, fallback_data: Any = None) -> Dict[str, Any]:
        """Database error recovery"""
        return {
            "success": False,
            "recovery_mode": True,
            "message": f"Database temporarily unavailable for {operation}. Using cached data.",
            "data": fallback_data,
            "recovery_strategy": "cache_fallback"
        }
    
    @staticmethod
    def agent_recovery(agent_id: str, fallback_response: str) -> Dict[str, Any]:
        """Agent processing error recovery"""
        return {
            "agent_id": agent_id,
            "response": fallback_response,
            "success": False,
            "recovery_mode": True,
            "recovery_strategy": "fallback_response"
        }
    
    @staticmethod
    def network_recovery(service: str, retry_count: int = 0) -> Dict[str, Any]:
        """Network error recovery"""
        return {
            "success": False,
            "recovery_mode": True,
            "message": f"Service {service} temporarily unavailable. Retry attempt {retry_count}.",
            "recovery_strategy": "retry_with_backoff",
            "retry_count": retry_count
        }

if __name__ == "__main__":
    # Test error handling system
    try:
        # Test various error types
        raise DatabaseError("Connection timeout", {"operation": "user_lookup"})
    except Exception as e:
        result = error_handler.handle_error(e)
        print("Database Error Test:")
        print(json.dumps(result, indent=2))
    
    print("\nError Statistics:")
    stats = error_handler.get_error_statistics()
    print(json.dumps(stats, indent=2))
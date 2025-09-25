#!/usr/bin/env python3
"""
📊 Memory Optimization and Monitoring System
Advanced memory management with cleanup tasks, monitoring, and performance optimization
"""

import asyncio
import logging
import time
import json
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import threading
import schedule

from core.memory import MemoryManager
from core.error_handling import MemoryError, error_handler

logger = logging.getLogger(__name__)

class MemoryType(Enum):
    """Types of memory storage"""
    STM_REDIS = "stm_redis"
    LTM_MYSQL = "ltm_mysql" 
    VECTOR_EMBEDDINGS = "vector_embeddings"
    USER_SESSIONS = "user_sessions"
    CACHE_DATA = "cache_data"

@dataclass
class MemoryStats:
    """Memory usage statistics"""
    memory_type: MemoryType
    total_entries: int
    size_mb: float
    oldest_entry: Optional[str]
    newest_entry: Optional[str]
    avg_entry_size: float
    cleanup_eligible: int
    last_cleanup: Optional[str]

@dataclass
class CleanupResult:
    """Result of cleanup operation"""
    memory_type: MemoryType
    entries_removed: int
    space_freed_mb: float
    time_taken_seconds: float
    errors_encountered: List[str]

class MemoryOptimizer:
    """Advanced memory optimization and monitoring system"""
    
    def __init__(self, memory_manager: MemoryManager):
        self.memory_manager = memory_manager
        self.cleanup_stats = {}
        self.monitoring_active = False
        self.cleanup_thread = None
        
        # Configuration
        self.cleanup_intervals = {
            MemoryType.STM_REDIS: 3600,        # 1 hour
            MemoryType.LTM_MYSQL: 86400,       # 24 hours
            MemoryType.VECTOR_EMBEDDINGS: 86400, # 24 hours
            MemoryType.USER_SESSIONS: 3600,    # 1 hour
            MemoryType.CACHE_DATA: 1800        # 30 minutes
        }
        
        # Retention policies
        self.retention_policies = {
            MemoryType.STM_REDIS: timedelta(hours=2),
            MemoryType.LTM_MYSQL: timedelta(days=90),
            MemoryType.VECTOR_EMBEDDINGS: timedelta(days=30),
            MemoryType.USER_SESSIONS: timedelta(hours=24),
            MemoryType.CACHE_DATA: timedelta(hours=6)
        }
        
        self._init_scheduler()
    
    def _init_scheduler(self):
        """Initialize cleanup scheduler"""
        # Schedule different cleanup tasks
        schedule.every(1).hours.do(self.cleanup_stm_memory)
        schedule.every(6).hours.do(self.cleanup_expired_sessions) 
        schedule.every(12).hours.do(self.cleanup_old_vectors)
        schedule.every().day.at("02:00").do(self.full_system_cleanup)
        schedule.every().week.do(self.deep_cleanup_and_optimize)
        
        logger.info("📅 Memory cleanup scheduler initialized")
    
    def start_monitoring(self):
        """Start background memory monitoring"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.cleanup_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.cleanup_thread.start()
        
        logger.info("🔄 Memory monitoring started")
    
    def stop_monitoring(self):
        """Stop background monitoring"""
        self.monitoring_active = False
        if self.cleanup_thread:
            self.cleanup_thread.join(timeout=5)
        
        logger.info("⏹️ Memory monitoring stopped")
    
    def _monitoring_loop(self):
        """Background monitoring loop"""
        while self.monitoring_active:
            try:
                # Run scheduled cleanup tasks
                schedule.run_pending()
                
                # Check memory usage every 30 seconds
                self._check_memory_pressure()
                
                time.sleep(30)
                
            except Exception as e:
                logger.error(f"Memory monitoring error: {e}")
                time.sleep(60)  # Wait longer after error
    
    def _check_memory_pressure(self):
        """Check for memory pressure and trigger emergency cleanup if needed"""
        try:
            stats = self.get_memory_statistics()
            
            # Check for emergency cleanup conditions
            total_entries = sum(stat.total_entries for stat in stats.values())
            
            if total_entries > 100000:  # Emergency threshold
                logger.warning(f"🚨 High memory usage detected: {total_entries} total entries")
                self.emergency_cleanup()
                
        except Exception as e:
            logger.error(f"Memory pressure check failed: {e}")
    
    def get_memory_statistics(self) -> Dict[MemoryType, MemoryStats]:
        """Get comprehensive memory statistics"""
        stats = {}
        
        try:
            # STM Redis statistics
            if self.memory_manager.redis_available:
                stm_stats = self._get_redis_stats()
                stats[MemoryType.STM_REDIS] = stm_stats
            
            # LTM MySQL statistics
            if self.memory_manager.mysql_available:
                ltm_stats = self._get_mysql_stats()
                stats[MemoryType.LTM_MYSQL] = ltm_stats
                
                # Vector embeddings statistics
                vector_stats = self._get_vector_stats()
                stats[MemoryType.VECTOR_EMBEDDINGS] = vector_stats
                
                # User sessions statistics
                session_stats = self._get_session_stats()
                stats[MemoryType.USER_SESSIONS] = session_stats
                
        except Exception as e:
            logger.error(f"Failed to get memory statistics: {e}")
        
        return stats
    
    def _get_redis_stats(self) -> MemoryStats:
        """Get Redis/STM memory statistics"""
        try:
            redis_conn = self.memory_manager.redis_conn
            
            # Get all STM keys
            stm_keys = redis_conn.keys("stm:*")
            session_keys = redis_conn.keys("stm:sess:*")
            utp_keys = redis_conn.keys("stm:utp:*")
            
            total_keys = len(stm_keys) + len(session_keys) + len(utp_keys)
            
            # Estimate memory usage
            info = redis_conn.info('memory')
            used_memory_mb = info.get('used_memory', 0) / (1024 * 1024)
            
            # Get oldest and newest entries
            oldest_key = None
            newest_key = None
            
            if stm_keys:
                # Sample a few keys to estimate age
                sample_keys = stm_keys[:10]
                ttls = [redis_conn.ttl(key) for key in sample_keys]
                valid_ttls = [ttl for ttl in ttls if ttl > 0]
                
                if valid_ttls:
                    max_ttl = max(valid_ttls)
                    oldest_key = datetime.now() - timedelta(seconds=3600 - max_ttl)
                    oldest_key = oldest_key.isoformat()
            
            # Count entries eligible for cleanup
            cleanup_eligible = 0
            for key in stm_keys[:100]:  # Sample to avoid performance issues
                ttl = redis_conn.ttl(key)
                if ttl > 0 and ttl < 300:  # Less than 5 minutes remaining
                    cleanup_eligible += 1
            
            return MemoryStats(
                memory_type=MemoryType.STM_REDIS,
                total_entries=total_keys,
                size_mb=used_memory_mb,
                oldest_entry=oldest_key,
                newest_entry=datetime.now().isoformat(),
                avg_entry_size=used_memory_mb / max(total_keys, 1),
                cleanup_eligible=cleanup_eligible,
                last_cleanup=self.cleanup_stats.get(MemoryType.STM_REDIS, {}).get('last_run')
            )
            
        except Exception as e:
            logger.error(f"Redis stats collection failed: {e}")
            return MemoryStats(
                memory_type=MemoryType.STM_REDIS,
                total_entries=0, size_mb=0, oldest_entry=None,
                newest_entry=None, avg_entry_size=0, cleanup_eligible=0,
                last_cleanup=None
            )
    
    def _get_mysql_stats(self) -> MemoryStats:
        """Get MySQL/LTM memory statistics"""
        try:
            cursor = self.memory_manager.mysql_conn.cursor()
            
            # Count total LTM entries
            cursor.execute("SELECT COUNT(*) as total FROM ltm")
            total_ltm = cursor.fetchone()[0]
            
            # Get oldest and newest entries
            cursor.execute("SELECT MIN(created_at), MAX(created_at) FROM ltm")
            oldest, newest = cursor.fetchone()
            
            # Estimate size (rough approximation)
            cursor.execute("""
                SELECT SUM(LENGTH(memory_value)) as total_size 
                FROM ltm 
                LIMIT 1000
            """)
            sample_size = cursor.fetchone()[0] or 0
            estimated_size_mb = (sample_size * total_ltm / 1000) / (1024 * 1024)
            
            # Count old entries eligible for cleanup
            cutoff_date = datetime.now() - self.retention_policies[MemoryType.LTM_MYSQL]
            cursor.execute("SELECT COUNT(*) FROM ltm WHERE created_at < %s", (cutoff_date,))
            cleanup_eligible = cursor.fetchone()[0]
            
            cursor.close()
            
            return MemoryStats(
                memory_type=MemoryType.LTM_MYSQL,
                total_entries=total_ltm,
                size_mb=estimated_size_mb,
                oldest_entry=oldest.isoformat() if oldest else None,
                newest_entry=newest.isoformat() if newest else None,
                avg_entry_size=estimated_size_mb / max(total_ltm, 1),
                cleanup_eligible=cleanup_eligible,
                last_cleanup=self.cleanup_stats.get(MemoryType.LTM_MYSQL, {}).get('last_run')
            )
            
        except Exception as e:
            logger.error(f"MySQL stats collection failed: {e}")
            return MemoryStats(
                memory_type=MemoryType.LTM_MYSQL,
                total_entries=0, size_mb=0, oldest_entry=None,
                newest_entry=None, avg_entry_size=0, cleanup_eligible=0,
                last_cleanup=None
            )
    
    def _get_vector_stats(self) -> MemoryStats:
        """Get vector embeddings statistics"""
        try:
            cursor = self.memory_manager.mysql_conn.cursor()
            
            # Count vector embeddings if table exists
            try:
                cursor.execute("SELECT COUNT(*) as total FROM vector_embeddings")
                total_vectors = cursor.fetchone()[0]
                
                cursor.execute("SELECT MIN(created_at), MAX(created_at) FROM vector_embeddings")
                oldest, newest = cursor.fetchone()
                
                # Estimate vector storage size
                cursor.execute("SELECT SUM(LENGTH(embedding)) as total_size FROM vector_embeddings LIMIT 1000")
                sample_size = cursor.fetchone()[0] or 0
                estimated_size_mb = (sample_size * total_vectors / 1000) / (1024 * 1024)
                
                # Count old vectors
                cutoff_date = datetime.now() - self.retention_policies[MemoryType.VECTOR_EMBEDDINGS]
                cursor.execute("SELECT COUNT(*) FROM vector_embeddings WHERE created_at < %s", (cutoff_date,))
                cleanup_eligible = cursor.fetchone()[0]
                
            except Exception:
                # Vector embeddings table might not exist
                total_vectors = 0
                estimated_size_mb = 0
                oldest = None
                newest = None
                cleanup_eligible = 0
            
            cursor.close()
            
            return MemoryStats(
                memory_type=MemoryType.VECTOR_EMBEDDINGS,
                total_entries=total_vectors,
                size_mb=estimated_size_mb,
                oldest_entry=oldest.isoformat() if oldest else None,
                newest_entry=newest.isoformat() if newest else None,
                avg_entry_size=estimated_size_mb / max(total_vectors, 1),
                cleanup_eligible=cleanup_eligible,
                last_cleanup=self.cleanup_stats.get(MemoryType.VECTOR_EMBEDDINGS, {}).get('last_run')
            )
            
        except Exception as e:
            logger.error(f"Vector stats collection failed: {e}")
            return MemoryStats(
                memory_type=MemoryType.VECTOR_EMBEDDINGS,
                total_entries=0, size_mb=0, oldest_entry=None,
                newest_entry=None, avg_entry_size=0, cleanup_eligible=0,
                last_cleanup=None
            )
    
    def _get_session_stats(self) -> MemoryStats:
        """Get user session statistics"""
        try:
            cursor = self.memory_manager.mysql_conn.cursor()
            
            # Try to get session stats from multiple possible tables
            session_count = 0
            oldest = None
            newest = None
            cleanup_eligible = 0
            
            try:
                # Check sessions table
                cursor.execute("SELECT COUNT(*) FROM sessions")
                session_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT MIN(created_at), MAX(created_at) FROM sessions") 
                oldest, newest = cursor.fetchone()
                
                # Count expired sessions
                cursor.execute("SELECT COUNT(*) FROM sessions WHERE last_at < %s", 
                             (datetime.now() - self.retention_policies[MemoryType.USER_SESSIONS],))
                cleanup_eligible = cursor.fetchone()[0]
                
            except Exception:
                # Try user_sessions table as fallback
                try:
                    cursor.execute("SELECT COUNT(*) FROM user_sessions")
                    session_count = cursor.fetchone()[0]
                    
                    cursor.execute("SELECT MIN(created_at), MAX(created_at) FROM user_sessions")
                    oldest, newest = cursor.fetchone()
                    
                    cursor.execute("SELECT COUNT(*) FROM user_sessions WHERE expires_at < NOW()")
                    cleanup_eligible = cursor.fetchone()[0]
                except Exception:
                    pass
            
            cursor.close()
            
            estimated_size_mb = session_count * 0.001  # Rough estimate
            
            return MemoryStats(
                memory_type=MemoryType.USER_SESSIONS,
                total_entries=session_count,
                size_mb=estimated_size_mb,
                oldest_entry=oldest.isoformat() if oldest else None,
                newest_entry=newest.isoformat() if newest else None,
                avg_entry_size=estimated_size_mb / max(session_count, 1),
                cleanup_eligible=cleanup_eligible,
                last_cleanup=self.cleanup_stats.get(MemoryType.USER_SESSIONS, {}).get('last_run')
            )
            
        except Exception as e:
            logger.error(f"Session stats collection failed: {e}")
            return MemoryStats(
                memory_type=MemoryType.USER_SESSIONS,
                total_entries=0, size_mb=0, oldest_entry=None,
                newest_entry=None, avg_entry_size=0, cleanup_eligible=0,
                last_cleanup=None
            )
    
    def cleanup_stm_memory(self) -> CleanupResult:
        """Clean up expired STM entries"""
        start_time = time.time()
        entries_removed = 0
        errors = []
        
        try:
            if not self.memory_manager.redis_available:
                return CleanupResult(
                    memory_type=MemoryType.STM_REDIS,
                    entries_removed=0,
                    space_freed_mb=0,
                    time_taken_seconds=0,
                    errors_encountered=["Redis not available"]
                )
            
            redis_conn = self.memory_manager.redis_conn
            
            # Get all STM keys that are about to expire
            stm_keys = redis_conn.keys("stm:*")
            expired_keys = []
            
            for key in stm_keys:
                ttl = redis_conn.ttl(key)
                if ttl <= 60:  # Expiring within 1 minute or already expired
                    expired_keys.append(key)
            
            # Remove expired keys
            if expired_keys:
                entries_removed = redis_conn.delete(*expired_keys)
            
            # Cleanup old session data
            old_session_keys = redis_conn.keys("stm:sess:*")
            for key in old_session_keys[:100]:  # Limit to avoid blocking
                try:
                    last_at = redis_conn.hget(key, 'last_at')
                    if last_at:
                        last_time = datetime.fromisoformat(last_at.decode())
                        if (datetime.now() - last_time).seconds > 7200:  # 2 hours old
                            redis_conn.delete(key)
                            entries_removed += 1
                except Exception as e:
                    errors.append(f"Session cleanup error for {key}: {e}")
            
            time_taken = time.time() - start_time
            space_freed_mb = entries_removed * 0.001  # Rough estimate
            
            # Update cleanup stats
            self.cleanup_stats[MemoryType.STM_REDIS] = {
                'last_run': datetime.now().isoformat(),
                'entries_removed': entries_removed,
                'space_freed_mb': space_freed_mb
            }
            
            logger.info(f"🧹 STM cleanup completed: {entries_removed} entries removed in {time_taken:.2f}s")
            
            return CleanupResult(
                memory_type=MemoryType.STM_REDIS,
                entries_removed=entries_removed,
                space_freed_mb=space_freed_mb,
                time_taken_seconds=time_taken,
                errors_encountered=errors
            )
            
        except Exception as e:
            errors.append(str(e))
            error_handler.handle_error(MemoryError(f"STM cleanup failed: {e}", "stm_cleanup"))
            
            return CleanupResult(
                memory_type=MemoryType.STM_REDIS,
                entries_removed=0,
                space_freed_mb=0,
                time_taken_seconds=time.time() - start_time,
                errors_encountered=errors
            )
    
    def cleanup_expired_sessions(self) -> CleanupResult:
        """Clean up expired user sessions"""
        start_time = time.time()
        entries_removed = 0
        errors = []
        
        try:
            if not self.memory_manager.mysql_available:
                return CleanupResult(
                    memory_type=MemoryType.USER_SESSIONS,
                    entries_removed=0,
                    space_freed_mb=0,
                    time_taken_seconds=0,
                    errors_encountered=["MySQL not available"]
                )
            
            cursor = self.memory_manager.mysql_conn.cursor()
            
            # Clean up different session tables
            cleanup_queries = [
                ("sessions", "DELETE FROM sessions WHERE last_at < %s"),
                ("user_sessions", "DELETE FROM user_sessions WHERE expires_at < NOW() OR is_active = FALSE")
            ]
            
            cutoff_time = datetime.now() - self.retention_policies[MemoryType.USER_SESSIONS]
            
            for table_name, query in cleanup_queries:
                try:
                    if table_name == "sessions":
                        cursor.execute(query, (cutoff_time,))
                    else:
                        cursor.execute(query)
                    
                    entries_removed += cursor.rowcount
                    
                except Exception as e:
                    errors.append(f"Failed to cleanup {table_name}: {e}")
            
            cursor.close()
            
            time_taken = time.time() - start_time
            space_freed_mb = entries_removed * 0.001  # Rough estimate
            
            self.cleanup_stats[MemoryType.USER_SESSIONS] = {
                'last_run': datetime.now().isoformat(),
                'entries_removed': entries_removed,
                'space_freed_mb': space_freed_mb
            }
            
            logger.info(f"🧹 Session cleanup completed: {entries_removed} sessions removed in {time_taken:.2f}s")
            
            return CleanupResult(
                memory_type=MemoryType.USER_SESSIONS,
                entries_removed=entries_removed,
                space_freed_mb=space_freed_mb,
                time_taken_seconds=time_taken,
                errors_encountered=errors
            )
            
        except Exception as e:
            errors.append(str(e))
            error_handler.handle_error(MemoryError(f"Session cleanup failed: {e}", "session_cleanup"))
            
            return CleanupResult(
                memory_type=MemoryType.USER_SESSIONS,
                entries_removed=0,
                space_freed_mb=0,
                time_taken_seconds=time.time() - start_time,
                errors_encountered=errors
            )
    
    def cleanup_old_vectors(self) -> CleanupResult:
        """Clean up old vector embeddings"""
        start_time = time.time()
        entries_removed = 0
        errors = []
        
        try:
            if not self.memory_manager.mysql_available:
                return CleanupResult(
                    memory_type=MemoryType.VECTOR_EMBEDDINGS,
                    entries_removed=0,
                    space_freed_mb=0,
                    time_taken_seconds=0,
                    errors_encountered=["MySQL not available"]
                )
            
            cursor = self.memory_manager.mysql_conn.cursor()
            
            # Clean up old vector embeddings
            cutoff_date = datetime.now() - self.retention_policies[MemoryType.VECTOR_EMBEDDINGS]
            
            try:
                cursor.execute("DELETE FROM vector_embeddings WHERE created_at < %s", (cutoff_date,))
                entries_removed = cursor.rowcount
            except Exception as e:
                errors.append(f"Vector embeddings cleanup failed: {e}")
            
            cursor.close()
            
            time_taken = time.time() - start_time
            space_freed_mb = entries_removed * 0.01  # Vectors are larger
            
            self.cleanup_stats[MemoryType.VECTOR_EMBEDDINGS] = {
                'last_run': datetime.now().isoformat(),
                'entries_removed': entries_removed,
                'space_freed_mb': space_freed_mb
            }
            
            logger.info(f"🧹 Vector cleanup completed: {entries_removed} embeddings removed in {time_taken:.2f}s")
            
            return CleanupResult(
                memory_type=MemoryType.VECTOR_EMBEDDINGS,
                entries_removed=entries_removed,
                space_freed_mb=space_freed_mb,
                time_taken_seconds=time_taken,
                errors_encountered=errors
            )
            
        except Exception as e:
            errors.append(str(e))
            error_handler.handle_error(MemoryError(f"Vector cleanup failed: {e}", "vector_cleanup"))
            
            return CleanupResult(
                memory_type=MemoryType.VECTOR_EMBEDDINGS,
                entries_removed=0,
                space_freed_mb=0,
                time_taken_seconds=time.time() - start_time,
                errors_encountered=errors
            )
    
    def full_system_cleanup(self) -> Dict[MemoryType, CleanupResult]:
        """Perform comprehensive system cleanup"""
        logger.info("🧹 Starting full system cleanup...")
        
        results = {}
        
        # Run all cleanup operations
        results[MemoryType.STM_REDIS] = self.cleanup_stm_memory()
        results[MemoryType.USER_SESSIONS] = self.cleanup_expired_sessions()
        results[MemoryType.VECTOR_EMBEDDINGS] = self.cleanup_old_vectors()
        
        # Additional LTM cleanup
        results[MemoryType.LTM_MYSQL] = self._cleanup_old_ltm()
        
        # Summary
        total_removed = sum(result.entries_removed for result in results.values())
        total_space_freed = sum(result.space_freed_mb for result in results.values())
        
        logger.info(f"✅ Full cleanup completed: {total_removed} entries, {total_space_freed:.2f}MB freed")
        
        return results
    
    def _cleanup_old_ltm(self) -> CleanupResult:
        """Clean up very old LTM entries"""
        start_time = time.time()
        entries_removed = 0
        errors = []
        
        try:
            cursor = self.memory_manager.mysql_conn.cursor()
            
            # Remove very old LTM entries (beyond retention policy)
            cutoff_date = datetime.now() - self.retention_policies[MemoryType.LTM_MYSQL]
            
            cursor.execute("DELETE FROM ltm WHERE created_at < %s", (cutoff_date,))
            entries_removed = cursor.rowcount
            
            cursor.close()
            
            time_taken = time.time() - start_time
            space_freed_mb = entries_removed * 0.01  # Rough estimate
            
            self.cleanup_stats[MemoryType.LTM_MYSQL] = {
                'last_run': datetime.now().isoformat(),
                'entries_removed': entries_removed,
                'space_freed_mb': space_freed_mb
            }
            
            logger.info(f"🧹 LTM cleanup completed: {entries_removed} entries removed in {time_taken:.2f}s")
            
            return CleanupResult(
                memory_type=MemoryType.LTM_MYSQL,
                entries_removed=entries_removed,
                space_freed_mb=space_freed_mb,
                time_taken_seconds=time_taken,
                errors_encountered=errors
            )
            
        except Exception as e:
            errors.append(str(e))
            return CleanupResult(
                memory_type=MemoryType.LTM_MYSQL,
                entries_removed=0,
                space_freed_mb=0,
                time_taken_seconds=time.time() - start_time,
                errors_encountered=errors
            )
    
    def emergency_cleanup(self):
        """Emergency cleanup when memory usage is critical"""
        logger.warning("🚨 Performing emergency memory cleanup!")
        
        try:
            # More aggressive cleanup
            if self.memory_manager.redis_available:
                redis_conn = self.memory_manager.redis_conn
                
                # Remove all keys with TTL < 5 minutes
                stm_keys = redis_conn.keys("stm:*")
                emergency_expired = []
                
                for key in stm_keys:
                    ttl = redis_conn.ttl(key)
                    if ttl <= 300:  # Less than 5 minutes
                        emergency_expired.append(key)
                
                if emergency_expired:
                    removed = redis_conn.delete(*emergency_expired)
                    logger.info(f"🚨 Emergency: removed {removed} STM entries")
            
            # Cleanup old database entries more aggressively
            if self.memory_manager.mysql_available:
                cursor = self.memory_manager.mysql_conn.cursor()
                
                # Remove older LTM entries (30 days instead of 90)
                emergency_cutoff = datetime.now() - timedelta(days=30)
                cursor.execute("DELETE FROM ltm WHERE created_at < %s", (emergency_cutoff,))
                removed_ltm = cursor.rowcount
                
                cursor.close()
                logger.info(f"🚨 Emergency: removed {removed_ltm} LTM entries")
                
        except Exception as e:
            logger.error(f"Emergency cleanup failed: {e}")
    
    def deep_cleanup_and_optimize(self):
        """Weekly deep cleanup and optimization"""
        logger.info("🔧 Starting deep cleanup and optimization...")
        
        try:
            # Full system cleanup first
            self.full_system_cleanup()
            
            # Database optimization
            if self.memory_manager.mysql_available:
                cursor = self.memory_manager.mysql_conn.cursor()
                
                # Optimize tables
                tables = ['ltm', 'vector_embeddings', 'sessions', 'user_sessions']
                for table in tables:
                    try:
                        cursor.execute(f"OPTIMIZE TABLE {table}")
                        logger.info(f"✅ Optimized table: {table}")
                    except Exception as e:
                        logger.warning(f"Failed to optimize {table}: {e}")
                
                cursor.close()
            
            # Redis optimization
            if self.memory_manager.redis_available:
                try:
                    # Force Redis to reclaim memory
                    self.memory_manager.redis_conn.execute_command("MEMORY PURGE")
                    logger.info("✅ Redis memory purged")
                except Exception as e:
                    logger.warning(f"Redis memory purge failed: {e}")
                    
        except Exception as e:
            logger.error(f"Deep cleanup failed: {e}")
    
    def get_optimization_report(self) -> Dict[str, Any]:
        """Generate comprehensive optimization report"""
        stats = self.get_memory_statistics()
        
        report = {
            "generated_at": datetime.now().isoformat(),
            "memory_statistics": {
                memory_type.value: {
                    "total_entries": stat.total_entries,
                    "size_mb": stat.size_mb,
                    "cleanup_eligible": stat.cleanup_eligible,
                    "last_cleanup": stat.last_cleanup,
                    "health_status": "good" if stat.cleanup_eligible < stat.total_entries * 0.1 else "needs_cleanup"
                }
                for memory_type, stat in stats.items()
            },
            "cleanup_history": self.cleanup_stats,
            "recommendations": self._generate_recommendations(stats)
        }
        
        return report
    
    def _generate_recommendations(self, stats: Dict[MemoryType, MemoryStats]) -> List[str]:
        """Generate optimization recommendations"""
        recommendations = []
        
        for memory_type, stat in stats.items():
            if stat.cleanup_eligible > stat.total_entries * 0.2:
                recommendations.append(
                    f"High cleanup eligible entries for {memory_type.value}: "
                    f"{stat.cleanup_eligible}/{stat.total_entries} ({stat.cleanup_eligible/stat.total_entries*100:.1f}%)"
                )
            
            if stat.size_mb > 1000:  # > 1GB
                recommendations.append(
                    f"Large memory usage for {memory_type.value}: {stat.size_mb:.1f}MB"
                )
        
        if not recommendations:
            recommendations.append("Memory usage is within optimal ranges")
        
        return recommendations

# Global memory optimizer instance
_memory_optimizer = None

def get_memory_optimizer(memory_manager: MemoryManager = None) -> MemoryOptimizer:
    """Get global memory optimizer instance"""
    global _memory_optimizer
    if _memory_optimizer is None and memory_manager:
        _memory_optimizer = MemoryOptimizer(memory_manager)
    return _memory_optimizer

if __name__ == "__main__":
    # Test memory optimization
    from core.memory import MemoryManager
    
    try:
        memory_mgr = MemoryManager()
        optimizer = MemoryOptimizer(memory_mgr)
        
        # Get statistics
        stats = optimizer.get_memory_statistics()
        print("Memory Statistics:")
        for mem_type, stat in stats.items():
            print(f"  {mem_type.value}: {stat.total_entries} entries, {stat.size_mb:.2f}MB")
        
        # Generate report
        report = optimizer.get_optimization_report()
        print("\nOptimization Report:")
        print(json.dumps(report, indent=2, default=str))
        
    except Exception as e:
        print(f"Memory optimizer test failed: {e}")
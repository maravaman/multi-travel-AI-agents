# memory.py
import redis
import mysql.connector
from datetime import datetime, timedelta
import json
import time
import logging
from typing import List, Dict, Optional, Any
from config import Config

# Optional imports with fallbacks
try:
    import numpy as np
except ImportError:
    np = None

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

logger = logging.getLogger(__name__)

class MemoryManager:
    def __init__(self):
        # Get connection parameters from config
        redis_params = Config.get_redis_connection_params()
        mysql_params = Config.get_mysql_connection_params()
        
        # Redis setup
        try:
            self.redis_conn = redis.StrictRedis(**redis_params)
            self.redis_conn.ping()
            logger.info("✅ Redis connected successfully")
            self.redis_available = True
        except Exception as e:
            logger.warning(f"⚠️ Redis connection failed: {e} - using fallback")
            self.redis_conn = None
            self.redis_available = False

        # MySQL setup
        try:
            self.mysql_conn = mysql.connector.connect(**mysql_params)
            logger.info("✅ MySQL connected successfully")
            self.mysql_available = True
        except Exception as e:
            logger.warning(f"⚠️ MySQL connection failed: {e} - using fallback")
            self.mysql_conn = None
            self.mysql_available = False
        
        # Initialize sentence transformer for embeddings
        self.embedding_model = None
        if SentenceTransformer:
            try:
                self.embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
                logger.info("✅ Embedding model loaded")
            except Exception as e:
                logger.warning(f"⚠️ Could not load embedding model: {e}")
        else:
            logger.info("📝 SentenceTransformer not available, vector search disabled")

    # ----------------------
    # SHORT-TERM MEMORY (Redis) - SESSION-BASED MODEL
    # ----------------------
    
    def start_travel_session(self, user_id: int, mode: str = 'chat', title: str = None) -> str:
        """Start a new travel session or return existing active session"""
        try:
            import uuid
            from datetime import datetime
            
            # Check for existing active session
            active_session = self.get_active_session(user_id)
            if active_session:
                # Check if session is still active (not idle for >60 min)
                last_activity = self.redis_conn.hget(f"stm:sess:{user_id}:{active_session}", 'last_at')
                if last_activity:
                    last_time = datetime.fromisoformat(last_activity.decode())
                    if (datetime.now() - last_time).seconds < 3600:  # 60 minutes
                        return active_session
            
            # Create new session
            session_id = str(uuid.uuid4())
            now = datetime.now().isoformat()
            
            # Set active session pointer
            self.redis_conn.setex(f"stm:active:{user_id}", 2592000, session_id)  # 30 days TTL
            
            # Create session metadata
            session_data = {
                'title': title or f"{mode.title()} Session",
                'started_at': now,
                'last_at': now,
                'mode': mode,
                'turn_count': '0'
            }
            
            # Store session metadata (30 days TTL)
            for key, value in session_data.items():
                self.redis_conn.hset(f"stm:sess:{user_id}:{session_id}", key, value)
            self.redis_conn.expire(f"stm:sess:{user_id}:{session_id}", 2592000)
            
            # Initialize empty turn list
            self.redis_conn.expire(f"stm:sess:{user_id}:{session_id}:turns", 2592000)
            
            logger.info(f"Started new {mode} session {session_id} for user {user_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"Failed to start travel session: {e}")
            return f"fallback_session_{user_id}_{int(time.time())}"
    
    def get_active_session(self, user_id: int) -> Optional[str]:
        """Get user's active session ID"""
        try:
            if not self.redis_available or not self.redis_conn:
                return None
            session_id = self.redis_conn.get(f"stm:active:{user_id}")
            return session_id.decode() if session_id else None
        except Exception as e:
            logger.debug(f"Failed to get active session: {e}")
            return None
    
    def add_turn_to_session(self, user_id: int, session_id: str, role: str, text: str, 
                          agent_name: str = None, metadata: Dict = None) -> str:
        """Add a turn to the session"""
        try:
            import uuid
            from datetime import datetime
            
            turn_id = str(uuid.uuid4())
            now = datetime.now().isoformat()
            
            # Store turn data
            turn_data = {
                'role': role,
                'text': text,
                'ts': now
            }
            
            if agent_name:
                turn_data['agent_name'] = agent_name
            if metadata:
                turn_data['metadata'] = json.dumps(metadata)
                
            # Store turn (30 days TTL)
            for key, value in turn_data.items():
                self.redis_conn.hset(f"stm:turn:{user_id}:{turn_id}", key, value)
            self.redis_conn.expire(f"stm:turn:{user_id}:{turn_id}", 2592000)
            
            # Add to session turn list
            self.redis_conn.rpush(f"stm:sess:{user_id}:{session_id}:turns", turn_id)
            
            # Update session metadata
            self.redis_conn.hset(f"stm:sess:{user_id}:{session_id}", 'last_at', now)
            current_count = self.redis_conn.hget(f"stm:sess:{user_id}:{session_id}", 'turn_count')
            new_count = int(current_count.decode() if current_count else 0) + 1
            self.redis_conn.hset(f"stm:sess:{user_id}:{session_id}", 'turn_count', str(new_count))
            
            # Add to recent index (ZSET by timestamp)
            timestamp = time.time()
            self.redis_conn.zadd(f"stm:recent:{user_id}", {turn_id: timestamp})
            # Keep only last 200 turns in recent index
            self.redis_conn.zremrangebyrank(f"stm:recent:{user_id}", 0, -201)
            
            # Trim session turns if needed (keep only last 50 turns)
            turn_list_len = self.redis_conn.llen(f"stm:sess:{user_id}:{session_id}:turns")
            if turn_list_len > 50:
                # Remove oldest turns
                old_turns = self.redis_conn.lrange(f"stm:sess:{user_id}:{session_id}:turns", 0, turn_list_len - 51)
                for old_turn in old_turns:
                    self.redis_conn.delete(f"stm:turn:{user_id}:{old_turn.decode()}")
                self.redis_conn.ltrim(f"stm:sess:{user_id}:{session_id}:turns", -50, -1)
            
            logger.debug(f"Added {role} turn {turn_id} to session {session_id}")
            return turn_id
            
        except Exception as e:
            logger.error(f"Failed to add turn to session: {e}")
            return f"fallback_turn_{int(time.time())}"
    
    def get_session_context(self, user_id: int, session_id: str = None, last_n_turns: int = 10) -> List[Dict]:
        """Get recent turns from session for context"""
        try:
            if not session_id:
                session_id = self.get_active_session(user_id)
            
            if not session_id:
                return []
            
            # Get last N turn IDs from session
            turn_ids = self.redis_conn.lrange(f"stm:sess:{user_id}:{session_id}:turns", -last_n_turns, -1)
            
            turns = []
            for turn_id in turn_ids:
                turn_data = self.redis_conn.hgetall(f"stm:turn:{user_id}:{turn_id.decode()}")
                if turn_data:
                    turn_dict = {k.decode(): v.decode() for k, v in turn_data.items()}
                    if 'metadata' in turn_dict:
                        turn_dict['metadata'] = json.loads(turn_dict['metadata'])
                    turns.append(turn_dict)
            
            return turns
            
        except Exception as e:
            logger.debug(f"Failed to get session context: {e}")
            return []
    
    def get_travel_profile_cache(self, user_id: int) -> Optional[Dict]:
        """Get cached User Travel Profile from STM"""
        try:
            if not self.redis_available or not self.redis_conn:
                return None
            
            profile_data = self.redis_conn.hgetall(f"stm:utp:{user_id}")
            if not profile_data:
                return None
            
            profile = {}
            for key, value in profile_data.items():
                key_str = key.decode()
                value_str = value.decode()
                
                # Handle JSON fields
                if key_str in ['destinations_of_interest', 'cuisine_preferences', 'climate_tolerance', 
                              'behavioral_notes', 'planning_patterns']:
                    try:
                        profile[key_str] = json.loads(value_str)
                    except:
                        profile[key_str] = value_str
                else:
                    profile[key_str] = value_str
            
            return profile
            
        except Exception as e:
            logger.debug(f"Failed to get travel profile cache: {e}")
            return None
    
    def cache_travel_profile(self, user_id: int, profile: Dict):
        """Cache User Travel Profile in STM (Redis)"""
        try:
            if not self.redis_available or not self.redis_conn:
                return
            
            # Store profile fields with 7-day TTL
            for key, value in profile.items():
                if isinstance(value, (dict, list)):
                    value_str = json.dumps(value)
                else:
                    value_str = str(value)
                self.redis_conn.hset(f"stm:utp:{user_id}", key, value_str)
            
            # Set 7-day expiry
            self.redis_conn.expire(f"stm:utp:{user_id}", 604800)
            logger.debug(f"Cached travel profile for user {user_id}")
            
        except Exception as e:
            logger.debug(f"Failed to cache travel profile: {e}")
    
    # Legacy STM methods for backward compatibility
    def set_stm(self, user_id, agent_id, value, expiry=3600):
        """Legacy STM method - maintained for backward compatibility"""
        if not self.redis_available or not self.redis_conn:
            logger.debug(f"[SET] STM fallback: {user_id}:{agent_id} => {value}")
            return True
        try:
            key = f"stm:{user_id}:{agent_id}"
            result = self.redis_conn.setex(key, expiry, value)
            logger.debug(f"[SET] {key} => {value} (expires in {expiry}s)")
            return result
        except Exception as e:
            logger.warning(f"STM set failed: {e}")
            return False

    def get_stm(self, user_id, agent_id):
        """Legacy STM method - maintained for backward compatibility"""
        if not self.redis_available or not self.redis_conn:
            logger.debug(f"[GET] STM fallback: {user_id}:{agent_id} => None")
            return None
        try:
            key = f"stm:{user_id}:{agent_id}"
            value = self.redis_conn.get(key)
            logger.debug(f"[GET] {key} => {value}")
            return value
        except Exception as e:
            logger.warning(f"STM get failed: {e}")
            return None

    def get_all_stm_for_user(self, user_id):
        """Legacy method for backward compatibility"""
        if not self.redis_available or not self.redis_conn:
            return {}
        
        try:
            pattern = f"stm:{user_id}:*"
            keys = self.redis_conn.keys(pattern)
            result = {}
            
            for key in keys:
                try:
                    # Handle both string and bytes keys
                    if isinstance(key, bytes):
                        key_str = key.decode('utf-8')
                    else:
                        key_str = str(key)
                    
                    agent_id = key_str.split(":")[-1] if key_str else "unknown"
                    value = self.redis_conn.get(key)
                    
                    # Handle both string and bytes values
                    if value:
                        if isinstance(value, bytes):
                            result[agent_id] = value.decode('utf-8')
                        else:
                            result[agent_id] = str(value)
                    else:
                        result[agent_id] = None
                        
                except Exception as key_error:
                    logger.debug(f"Error processing STM key {key}: {key_error}")
                    continue
                    
            return result
            
        except Exception as e:
            logger.warning(f"Failed to get all STM for user {user_id}: {e}")
            return {}


    # ----------------------
    # LONG-TERM MEMORY (MySQL)
    # ----------------------
    def store_ltm(self, user_id, agent_id, input_text, output_text):
        cursor = self.mysql_conn.cursor()
        cursor.execute(
            """
            INSERT INTO agent_history (user_id, agent_id, input_text, output_text)
            VALUES (%s, %s, %s, %s)
            """,
            (user_id, agent_id, input_text, output_text)
        )
        self.mysql_conn.commit()
        cursor.close()

    def get_ltm_by_user(self, user_id):
        cursor = self.mysql_conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM ltm WHERE user_id = %s ORDER BY created_at DESC",
            (user_id,)
        )
        results = cursor.fetchall()
        cursor.close()
        return results



    def get_ltm_by_agent(self, user_id, agent_id):
        cursor = self.mysql_conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT * FROM agent_history
            WHERE user_id = %s AND agent_id = %s
            ORDER BY timestamp DESC
            """,
            (user_id, agent_id)
        )
        results = cursor.fetchall()
        cursor.close()
        return results
    
    # def get_all_stm_for_user(self, user_id):
    #     pattern = f"stm:{user_id}:*"
    #     keys = self.redis_conn.keys(pattern)
    #     result = {}
    #     for key in keys:
    #         agent_id = key.decode().split(":")[-1]
    #         value = self.redis_conn.get(key).decode()
    #         result[agent_id] = value
    #     return result
    
    def set_ltm(self, user_id: str, agent_id: str, value: str):
        cursor = self.mysql_conn.cursor()
        cursor.execute(
            "REPLACE INTO ltm (user_id, agent_id, value) VALUES (%s, %s, %s)",
            (user_id, agent_id, value)
        )
        self.mysql_conn.commit()
    
    def get_recent_stm(self, user_id, agent_id=None, hours=1):
        """Get recent STM data for any user ID (supports dynamic users)"""
        pattern = f"stm:{user_id}:*"
        recent_data = []

        for key in self.redis_conn.scan_iter(pattern):
            ttl = self.redis_conn.ttl(key)
            if ttl != -2 and ttl > 0 and ttl <= hours * 3600:
                value = self.redis_conn.get(key)
                extracted_agent_id = key.decode('utf-8').split(":")[-1]
                recent_data.append({
                    "agent_id": extracted_agent_id,
                    "value": value.decode('utf-8') if value else None,
                    "ttl_seconds_remaining": ttl
                })

        return recent_data

    
    def get_recent_ltm(self, user_id, agent_id=None, days=1):
        cursor = self.mysql_conn.cursor(dictionary=True)
        cutoff_query = """
            SELECT * FROM ltm
            WHERE user_id = %s AND created_at >= NOW() - INTERVAL %s DAY
        """
        cursor.execute(cutoff_query, (user_id, days))
        return cursor.fetchall()


    
    def get_ltm_by_agent(self, user_id, agent_id):
        cursor = self.mysql_conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT * FROM ltm
            WHERE user_id = %s AND agent_id = %s
            ORDER BY created_at DESC
            """,
            (user_id, agent_id)
        )
        results = cursor.fetchall()
        cursor.close()
        return results

    
    # ----------------------
    # AGENT-BASED LTM METHODS (New constraint requirement)
    # ----------------------
    def store_agent_memory(self, agent_name: str, user_id: int, memory_key: str, memory_value: str, metadata: Dict = None):
        """Store LTM grouped by agent name rather than user_id"""
        try:
            cursor = self.mysql_conn.cursor()
            cursor.execute(
                """
                INSERT INTO ltm_by_agent (agent_name, user_id, memory_key, memory_value, context_metadata)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                memory_value = VALUES(memory_value),
                context_metadata = VALUES(context_metadata),
                updated_at = CURRENT_TIMESTAMP
                """,
                (agent_name, user_id, memory_key, memory_value, json.dumps(metadata or {}))
            )
            cursor.close()
            logger.info(f"Stored memory for agent {agent_name}: {memory_key}")
        except Exception as e:
            logger.error(f"Error storing agent memory: {e}")
    
    def get_agent_memories(self, agent_name: str, user_id: Optional[int] = None, limit: int = 50) -> List[Dict]:
        """Get memories for a specific agent, optionally filtered by user"""
        try:
            cursor = self.mysql_conn.cursor(dictionary=True)
            if user_id:
                cursor.execute(
                    """
                    SELECT * FROM ltm_by_agent 
                    WHERE agent_name = %s AND user_id = %s 
                    ORDER BY updated_at DESC LIMIT %s
                    """,
                    (agent_name, user_id, limit)
                )
            else:
                cursor.execute(
                    """
                    SELECT * FROM ltm_by_agent 
                    WHERE agent_name = %s 
                    ORDER BY updated_at DESC LIMIT %s
                    """,
                    (agent_name, limit)
                )
            results = cursor.fetchall()
            cursor.close()
            return results
        except Exception as e:
            logger.error(f"Error getting agent memories: {e}")
            return []
    
    def store_interaction(self, user_id: int, agent_name: str, query: str, response: str, interaction_type: str = 'single'):
        """Store agent interaction with user"""
        try:
            cursor = self.mysql_conn.cursor()
            cursor.execute(
                """
                INSERT INTO agent_interactions (user_id, agent_name, query_text, response)
                VALUES (%s, %s, %s, %s)
                """,
                (user_id, agent_name, query, response)
            )
            cursor.close()
        except Exception as e:
            logger.error(f"Error storing interaction: {e}")
    
    def store_query(self, user_id: int, query: str, response: str, agent_name: str = 'general'):
        """Store query for search functionality - compatibility method"""
        # This method provides compatibility for the test suite
        # It stores the query as an interaction and as a vector embedding
        try:
            # Store as interaction
            self.store_interaction(user_id, agent_name, query, response)
            
            # Store as vector embedding for similarity search
            self.store_vector_embedding(user_id, agent_name, query, {'response': response})
            
            logger.info(f"Stored query for user {user_id}: {query[:50]}...")
        except Exception as e:
            logger.error(f"Error storing query: {e}")
    
    # ----------------------
    # VECTOR SIMILARITY SEARCH METHODS
    # ----------------------
    def store_vector_embedding(self, user_id: int, agent_name: str, content: str, metadata: Dict = None):
        """Store content with its vector embedding (with graceful error handling)"""
        if not self.embedding_model or not self.mysql_available:
            logger.debug(f"Vector embedding storage disabled for {agent_name} - using fallback mode")
            return
        
        try:
            # Generate embedding
            embedding = self.embedding_model.encode(content)
            embedding_json = json.dumps(embedding.tolist())
            
            cursor = self.mysql_conn.cursor()
            cursor.execute(
                """
                INSERT INTO vector_embeddings (user_id, agent_name, content, embedding, metadata)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (user_id, agent_name, content, embedding_json, json.dumps(metadata or {}))
            )
            cursor.close()
            logger.debug(f"Stored vector embedding for {agent_name}")
        except Exception as e:
            # Gracefully handle foreign key constraints and other DB errors
            logger.debug(f"Vector embedding storage skipped for {agent_name}: {e}")
            return
    
    def similarity_search(self, query: str, user_id: int, agent_name: Optional[str] = None, limit: int = 5) -> List[Dict]:
        """Perform similarity search on stored content"""
        if not self.embedding_model:
            logger.error("Embedding model not available")
            return []
        
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode(query)
            
            # Get stored embeddings
            cursor = self.mysql_conn.cursor(dictionary=True)
            if agent_name:
                cursor.execute(
                    """
                    SELECT id, content, embedding, metadata, agent_name, created_at
                    FROM vector_embeddings 
                    WHERE user_id = %s AND agent_name = %s
                    """,
                    (user_id, agent_name)
                )
            else:
                cursor.execute(
                    """
                    SELECT id, content, embedding, metadata, agent_name, created_at
                    FROM vector_embeddings 
                    WHERE user_id = %s
                    """,
                    (user_id,)
                )
            
            stored_embeddings = cursor.fetchall()
            cursor.close()
            
            # Calculate similarities
            results = []
            for item in stored_embeddings:
                try:
                    stored_embedding = np.array(json.loads(item['embedding']))
                    similarity = np.dot(query_embedding, stored_embedding) / (
                        np.linalg.norm(query_embedding) * np.linalg.norm(stored_embedding)
                    )
                    
                    results.append({
                        'content': item['content'],
                        'agent_name': item['agent_name'],
                        'similarity': float(similarity),
                        'metadata': json.loads(item['metadata']),
                        'created_at': item['created_at']
                    })
                except Exception as e:
                    logger.warning(f"Error calculating similarity for item {item['id']}: {e}")
                    continue
            
            # Sort by similarity and return top results
            results.sort(key=lambda x: x['similarity'], reverse=True)
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Error in similarity search: {e}")
            return []
    
    def get_search_history_json(self, query: str, user_id: int, agent_name: Optional[str] = None) -> Dict:
        """Get similarity search results as JSON response (constraint requirement)"""
        similar_content = self.similarity_search(query, user_id, agent_name)
        
        # Also get recent interactions for context
        cursor = self.mysql_conn.cursor(dictionary=True)
        if agent_name:
            cursor.execute(
                """
                SELECT agent_name, query_text, response, timestamp 
                FROM agent_interactions 
                WHERE user_id = %s AND agent_name = %s 
                ORDER BY timestamp DESC LIMIT 10
                """,
                (user_id, agent_name)
            )
        else:
            cursor.execute(
                """
                SELECT agent_name, query_text, response, timestamp 
                FROM agent_interactions 
                WHERE user_id = %s 
                ORDER BY timestamp DESC LIMIT 10
                """,
                (user_id,)
            )
        
        recent_interactions = cursor.fetchall()
        cursor.close()
        
        return {
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "similar_content": similar_content,
            "recent_interactions": recent_interactions,
            "total_matches": len(similar_content)
        }
    
    # ----------------------
    # USER TRAVEL PROFILE (UTP) MANAGEMENT
    # ----------------------
    
    def get_travel_profile(self, user_id: int) -> Dict:
        """Get User Travel Profile from database"""
        try:
            if not self.mysql_available or not self.mysql_conn:
                logger.debug("MySQL not available, returning default travel profile")
                return self._get_default_travel_profile()
            
            cursor = self.mysql_conn.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT * FROM user_travel_profiles 
                WHERE user_id = %s
                """,
                (user_id,)
            )
            
            profile = cursor.fetchone()
            cursor.close()
            
            if not profile:
                # Create default profile if none exists
                default_profile = self._get_default_travel_profile()
                self.update_travel_profile(user_id, default_profile)
                return default_profile
            
            # Parse JSON fields
            for field in ['destinations_of_interest', 'cuisine_preferences', 'climate_tolerance', 
                         'behavioral_notes', 'planning_patterns']:
                if profile.get(field):
                    try:
                        profile[field] = json.loads(profile[field])
                    except:
                        profile[field] = []
            
            return profile
            
        except Exception as e:
            logger.error(f"Failed to get travel profile: {e}")
            return self._get_default_travel_profile()
    
    def update_travel_profile(self, user_id: int, profile_updates: Dict):
        """Update User Travel Profile in database and cache"""
        try:
            if not self.mysql_available or not self.mysql_conn:
                logger.debug("MySQL not available, caching profile updates only")
                self.cache_travel_profile(user_id, profile_updates)
                return
            
            # Get current profile
            current_profile = self.get_travel_profile(user_id)
            
            # Merge updates
            updated_profile = current_profile.copy()
            for key, value in profile_updates.items():
                if key in ['destinations_of_interest', 'cuisine_preferences', 'climate_tolerance', 
                          'behavioral_notes', 'planning_patterns']:
                    # For list fields, merge intelligently
                    if isinstance(value, list):
                        current_list = updated_profile.get(key, [])
                        if isinstance(current_list, list):
                            # Add new items, avoid duplicates
                            for item in value:
                                if item not in current_list:
                                    current_list.append(item)
                            updated_profile[key] = current_list[:10]  # Limit to 10 items
                        else:
                            updated_profile[key] = value
                    else:
                        updated_profile[key] = value
                else:
                    updated_profile[key] = value
            
            # Prepare data for database
            db_data = {
                'destinations_of_interest': json.dumps(updated_profile.get('destinations_of_interest', [])),
                'cuisine_preferences': json.dumps(updated_profile.get('cuisine_preferences', [])),
                'climate_tolerance': json.dumps(updated_profile.get('climate_tolerance', {})),
                'travel_pace': updated_profile.get('travel_pace', 'moderate'),
                'behavioral_notes': json.dumps(updated_profile.get('behavioral_notes', {})),
                'planning_patterns': json.dumps(updated_profile.get('planning_patterns', {})),
                'decision_style': updated_profile.get('decision_style', '')
            }
            
            cursor = self.mysql_conn.cursor()
            cursor.execute(
                """
                INSERT INTO user_travel_profiles 
                (user_id, destinations_of_interest, cuisine_preferences, climate_tolerance, 
                 travel_pace, behavioral_notes, planning_patterns, decision_style)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                destinations_of_interest = VALUES(destinations_of_interest),
                cuisine_preferences = VALUES(cuisine_preferences),
                climate_tolerance = VALUES(climate_tolerance),
                travel_pace = VALUES(travel_pace),
                behavioral_notes = VALUES(behavioral_notes),
                planning_patterns = VALUES(planning_patterns),
                decision_style = VALUES(decision_style)
                """,
                (user_id, db_data['destinations_of_interest'], db_data['cuisine_preferences'],
                 db_data['climate_tolerance'], db_data['travel_pace'], db_data['behavioral_notes'],
                 db_data['planning_patterns'], db_data['decision_style'])
            )
            cursor.close()
            self.mysql_conn.commit()
            
            # Cache updated profile
            self.cache_travel_profile(user_id, updated_profile)
            
            logger.info(f"Updated travel profile for user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to update travel profile: {e}")
            # Still cache the updates even if database fails
            self.cache_travel_profile(user_id, profile_updates)
    
    def _get_default_travel_profile(self) -> Dict:
        """Get default travel profile structure"""
        return {
            'destinations_of_interest': [],
            'cuisine_preferences': [],
            'climate_tolerance': {'preferred_weather': 'mild', 'temperature_range': 'moderate'},
            'travel_pace': 'moderate',
            'behavioral_notes': {
                'decision_style': 'analytical',
                'planning_preference': 'structured',
                'stress_triggers': [],
                'confidence_level': 'medium'
            },
            'planning_patterns': {
                'advance_planning_days': 30,
                'research_depth': 'moderate',
                'flexibility_preference': 'medium'
            },
            'decision_style': 'collaborative',
            'profile_version': '1.0',
            'last_updated_at': datetime.now().isoformat()
        }
    
    def extract_profile_insights_from_text(self, user_id: int, text: str, mode: str = 'chat'):
        """Extract travel profile insights from user text and update profile"""
        try:
            insights = {}
            text_lower = text.lower()
            
            # Extract destinations mentioned
            destinations = []
            # Simple destination detection - could be enhanced with NLP
            destination_keywords = ['tokyo', 'paris', 'london', 'new york', 'rome', 'barcelona', 
                                  'amsterdam', 'berlin', 'prague', 'vienna', 'budapest', 
                                  'thailand', 'japan', 'italy', 'france', 'spain', 'greece']
            
            for dest in destination_keywords:
                if dest in text_lower:
                    destinations.append(dest.title())
            
            if destinations:
                insights['destinations_of_interest'] = destinations
            
            # Extract travel pace indicators
            if any(word in text_lower for word in ['relax', 'slow', 'calm', 'peaceful']):
                insights['travel_pace'] = 'relaxed'
            elif any(word in text_lower for word in ['busy', 'packed', 'full', 'adventure', 'action']):
                insights['travel_pace'] = 'packed'
            
            # Extract cuisine preferences
            cuisine_keywords = ['italian', 'japanese', 'thai', 'mexican', 'indian', 'chinese', 
                              'french', 'vegetarian', 'vegan', 'seafood', 'street food']
            cuisines = [cuisine.title() for cuisine in cuisine_keywords if cuisine in text_lower]
            if cuisines:
                insights['cuisine_preferences'] = cuisines
            
            # Extract behavioral insights
            behavioral_notes = {}
            
            if any(word in text_lower for word in ['nervous', 'anxious', 'worried', 'stressed']):
                behavioral_notes['stress_indicators'] = ['travel_anxiety']
                behavioral_notes['confidence_level'] = 'low'
            elif any(word in text_lower for word in ['excited', 'confident', 'ready', 'can\'t wait']):
                behavioral_notes['confidence_level'] = 'high'
            
            if any(word in text_lower for word in ['plan', 'research', 'organize', 'schedule']):
                behavioral_notes['planning_preference'] = 'detailed'
            elif any(word in text_lower for word in ['spontaneous', 'flexible', 'go with flow']):
                behavioral_notes['planning_preference'] = 'flexible'
            
            if behavioral_notes:
                insights['behavioral_notes'] = behavioral_notes
            
            # Extract decision style
            if any(word in text_lower for word in ['we', 'us', 'partner', 'together']):
                insights['decision_style'] = 'collaborative'
            elif any(word in text_lower for word in ['i need', 'help me decide', 'what should']):
                insights['decision_style'] = 'guidance_seeking'
            
            # Only update if we found meaningful insights
            if insights:
                if mode == 'recording':
                    # In recording mode, we do comprehensive updates
                    self.update_travel_profile(user_id, insights)
                else:
                    # In chat mode, only cache insights lightly
                    current_cache = self.get_travel_profile_cache(user_id) or {}
                    current_cache.update(insights)
                    self.cache_travel_profile(user_id, current_cache)
                
                logger.info(f"Extracted profile insights for user {user_id}: {list(insights.keys())}")
            
        except Exception as e:
            logger.debug(f"Profile insight extraction failed: {e}")
    
    @staticmethod
    def load_edges_only():
        with open("core/agents.json", "r") as f:
            config = json.load(f)
        return config.get("edges", {})

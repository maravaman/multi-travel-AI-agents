"""
Database connection and initialization module
"""
import mysql.connector
import redis
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import os
from pathlib import Path
from decouple import config
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration
MYSQL_HOST = config('MYSQL_HOST', default='localhost')
MYSQL_USER = config('MYSQL_USER', default='root')
MYSQL_PASSWORD = config('MYSQL_PASSWORD', default='root')
MYSQL_DATABASE = config('MYSQL_DATABASE', default='langgraph_ai_system')

REDIS_HOST = config('REDIS_HOST', default='localhost')
REDIS_PORT = config('REDIS_PORT', default=6379, cast=int)

# SQLAlchemy setup
DATABASE_URL = f"mysql+mysqlconnector://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DATABASE}"
engine = create_engine(DATABASE_URL, echo=config('DEBUG', default=False, cast=bool))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class DatabaseManager:
    def __init__(self):
        self.mysql_conn = None
        self.redis_conn = None
        self.use_fallback = False
        self.initialize_connections()
    
    def initialize_connections(self):
        """Initialize MySQL and Redis connections"""
        try:
            # MySQL connection
            self.mysql_conn = mysql.connector.connect(
                host=MYSQL_HOST,
                user=MYSQL_USER,
                password=MYSQL_PASSWORD,
                database=MYSQL_DATABASE,
                autocommit=True
            )
            logger.info("✅ MySQL connected successfully")
            
            # Redis connection
            self.redis_conn = redis.StrictRedis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            self.redis_conn.ping()
            logger.info("✅ Redis connected successfully")
            
        except mysql.connector.Error as e:
            logger.warning(f"⚠️ MySQL connection failed: {e} - using fallback mode")
            self.use_fallback = True
        except redis.RedisError as e:
            logger.warning(f"⚠️ Redis connection failed: {e} - using fallback mode")
            self.use_fallback = True
        except Exception as e:
            logger.warning(f"⚠️ Database connection failed: {e} - using fallback mode")
            self.use_fallback = True
    
    def initialize_database(self):
        """Initialize database schema"""
        try:
            schema_file = Path(__file__).parent / 'schema.sql'
            if schema_file.exists():
                with open(schema_file, 'r') as f:
                    schema_sql = f.read()
                
                # Execute schema
                cursor = self.mysql_conn.cursor()
                statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
                
                for statement in statements:
                    try:
                        cursor.execute(statement)
                    except mysql.connector.Error as stmt_error:
                        # Log individual statement errors but continue
                        if "Duplicate entry" in str(stmt_error):
                            logger.debug(f"Skipping duplicate entry: {stmt_error}")
                        else:
                            logger.warning(f"Statement execution warning: {stmt_error}")
                
                cursor.close()
                logger.info("✅ Database schema initialized")
            else:
                logger.warning("Schema file not found")
                
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            raise
    
    def get_mysql_connection(self):
        """Get MySQL connection"""
        if self.use_fallback:
            return None
        try:
            if not self.mysql_conn or not self.mysql_conn.is_connected():
                self.initialize_connections()
            return self.mysql_conn
        except Exception as e:
            logger.warning(f"MySQL connection failed: {e}")
            return None
    
    def get_redis_connection(self):
        """Get Redis connection"""
        if self.use_fallback:
            return None
        try:
            self.redis_conn.ping()
            return self.redis_conn
        except redis.RedisError:
            try:
                self.initialize_connections()
                return self.redis_conn
            except Exception:
                logger.warning("Redis connection failed, using fallback mode")
                self.use_fallback = True
                return None
    
    def close_connections(self):
        """Close all connections"""
        if self.mysql_conn and self.mysql_conn.is_connected():
            self.mysql_conn.close()
        if self.redis_conn:
            self.redis_conn.close()

# Global database manager instance
db_manager = DatabaseManager()

def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_mysql_conn():
    """Get MySQL connection"""
    return db_manager.get_mysql_connection()

def get_redis_conn():
    """Get Redis connection"""
    return db_manager.get_redis_connection()

# Initialize database on module import
try:
    db_manager.initialize_database()
except Exception as e:
    # Don't fail module import if database initialization has issues
    logger.info(f"Database initialization completed with warnings: {e}")

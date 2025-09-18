#!/usr/bin/env python3
"""
Database Setup Script for Travel Assistant
Creates all required tables for the travel memory manager
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import mysql.connector
from config import Config
import logging

logger = logging.getLogger(__name__)

def setup_database():
    """Setup the travel assistant database with all required tables"""
    
    print("🗄️ Setting up Travel Assistant Database\n")
    
    try:
        # Connect without specifying database first
        connection_params = Config.get_mysql_connection_params()
        db_name = connection_params.pop('database')  # Remove database from params
        
        conn = mysql.connector.connect(**connection_params)
        cursor = conn.cursor()
        
        print(f"✅ Connected to MySQL server")
        
        # Create database
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}`")
        cursor.execute(f"USE `{db_name}`")
        print(f"✅ Database '{db_name}' created/selected")
        
        # Define table creation SQL
        tables = {
            'users': """
                CREATE TABLE IF NOT EXISTS `users` (
                    `id` INT PRIMARY KEY AUTO_INCREMENT,
                    `username` VARCHAR(50) UNIQUE NOT NULL,
                    `email` VARCHAR(100) UNIQUE NOT NULL,
                    `hashed_password` VARCHAR(255) NOT NULL,
                    `is_active` BOOLEAN DEFAULT TRUE,
                    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    `last_login` TIMESTAMP NULL,
                    INDEX idx_username (username),
                    INDEX idx_email (email)
                )
            """,
            'sessions': """
                CREATE TABLE IF NOT EXISTS `sessions` (
                    `id` INT PRIMARY KEY AUTO_INCREMENT,
                    `session_id` VARCHAR(100) UNIQUE NOT NULL,
                    `user_id` INT NOT NULL,
                    `title` VARCHAR(255),
                    `mode` ENUM('chat', 'recording') DEFAULT 'chat',
                    `started_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    `last_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    `turn_count` INT DEFAULT 0,
                    `is_active` BOOLEAN DEFAULT TRUE,
                    `session_summary` TEXT,
                    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_user_id (user_id),
                    INDEX idx_session_id (session_id),
                    INDEX idx_last_at (last_at),
                    INDEX idx_is_active (is_active)
                )
            """,
            'turns': """
                CREATE TABLE IF NOT EXISTS `turns` (
                    `id` INT PRIMARY KEY AUTO_INCREMENT,
                    `turn_id` VARCHAR(100) UNIQUE NOT NULL,
                    `session_id` VARCHAR(100),
                    `user_id` INT NOT NULL,
                    `role` ENUM('user', 'assistant', 'agent') NOT NULL,
                    `agent_name` VARCHAR(100),
                    `content` TEXT NOT NULL,
                    `metadata` JSON,
                    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_session_id (session_id),
                    INDEX idx_user_id (user_id),
                    INDEX idx_created_at (created_at),
                    INDEX idx_role (role)
                )
            """,
            'user_travel_profiles': """
                CREATE TABLE IF NOT EXISTS `user_travel_profiles` (
                    `id` INT PRIMARY KEY AUTO_INCREMENT,
                    `user_id` INT UNIQUE NOT NULL,
                    `profile_data` JSON NOT NULL,
                    `destinations_of_interest` JSON,
                    `cuisine_preferences` JSON,
                    `climate_tolerance` JSON,
                    `travel_pace` VARCHAR(50) DEFAULT 'moderate',
                    `behavioral_notes` JSON,
                    `budget_patterns` JSON,
                    `group_preferences` JSON,
                    `activity_preferences` JSON,
                    `accommodation_preferences` JSON,
                    `profile_version` VARCHAR(10) DEFAULT '1.0',
                    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_user_id (user_id),
                    INDEX idx_updated_at (updated_at)
                )
            """,
            'agent_interactions': """
                CREATE TABLE IF NOT EXISTS `agent_interactions` (
                    `id` INT PRIMARY KEY AUTO_INCREMENT,
                    `user_id` INT NOT NULL,
                    `agent_name` VARCHAR(100) NOT NULL,
                    `query` TEXT NOT NULL,
                    `response` TEXT NOT NULL,
                    `interaction_type` ENUM('single', 'orchestrated') DEFAULT 'single',
                    `timestamp` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_user_agent (user_id, agent_name),
                    INDEX idx_timestamp (timestamp),
                    INDEX idx_agent_name (agent_name)
                )
            """,
            'ltm': """
                CREATE TABLE IF NOT EXISTS `ltm` (
                    `id` INT PRIMARY KEY AUTO_INCREMENT,
                    `user_id` INT NOT NULL,
                    `agent_name` VARCHAR(100),
                    `memory_key` VARCHAR(255) NOT NULL,
                    `memory_value` TEXT NOT NULL,
                    `context_metadata` JSON,
                    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_user_id (user_id),
                    INDEX idx_agent_name (agent_name),
                    INDEX idx_created_at (created_at)
                )
            """,
            'multi_agent_orchestration': """
                CREATE TABLE IF NOT EXISTS `multi_agent_orchestration` (
                    `id` INT PRIMARY KEY AUTO_INCREMENT,
                    `user_id` INT NOT NULL,
                    `query` TEXT NOT NULL,
                    `agents_involved` JSON,
                    `orchestration_result` TEXT,
                    `execution_time_ms` INT,
                    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_user_id (user_id),
                    INDEX idx_created_at (created_at)
                )
            """,
            'user_queries': """
                CREATE TABLE IF NOT EXISTS `user_queries` (
                    `id` INT PRIMARY KEY AUTO_INCREMENT,
                    `user_id` INT NOT NULL,
                    `query` TEXT NOT NULL,
                    `response` TEXT,
                    `processing_time_ms` INT,
                    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_user_id (user_id),
                    INDEX idx_created_at (created_at)
                )
            """,
            'user_sessions': """
                CREATE TABLE IF NOT EXISTS `user_sessions` (
                    `id` INT PRIMARY KEY AUTO_INCREMENT,
                    `user_id` INT NOT NULL,
                    `session_token` VARCHAR(255) NOT NULL,
                    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    `expires_at` TIMESTAMP NOT NULL,
                    `is_active` BOOLEAN DEFAULT TRUE,
                    INDEX idx_user_id (user_id),
                    INDEX idx_session_token (session_token)
                )
            """,
            'vector_embeddings': """
                CREATE TABLE IF NOT EXISTS `vector_embeddings` (
                    `id` INT PRIMARY KEY AUTO_INCREMENT,
                    `user_id` INT NOT NULL,
                    `agent_name` VARCHAR(100),
                    `content` TEXT NOT NULL,
                    `embedding` JSON,
                    `metadata` JSON,
                    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_user_agent (user_id, agent_name),
                    INDEX idx_created_at (created_at)
                )
            """
        }
        
        # Create each table
        created_count = 0
        for table_name, create_sql in tables.items():
            try:
                cursor.execute(create_sql)
                print(f"✅ Table '{table_name}' created/verified")
                created_count += 1
            except Exception as e:
                print(f"❌ Error creating table '{table_name}': {e}")
        
        # Verify tables exist
        cursor.execute("SHOW TABLES")
        existing_tables = [table[0] for table in cursor.fetchall()]
        
        print(f"\n📊 Database Setup Summary:")
        print(f"✅ Tables created/verified: {created_count}/{len(tables)}")
        print(f"✅ Existing tables: {', '.join(sorted(existing_tables))}")
        
        # Test a simple insert/query to verify functionality
        try:
            cursor.execute("SELECT COUNT(*) FROM turns")
            turn_count = cursor.fetchone()[0]
            print(f"✅ Database functional - {turn_count} turns in database")
        except Exception as e:
            print(f"⚠️ Database test failed: {e}")
        
        cursor.close()
        conn.close()
        
        print(f"\n🎉 Database setup complete!")
        return True
        
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        return False

if __name__ == "__main__":
    success = setup_database()
    if success:
        print("\n✅ Travel Assistant database is ready!")
    else:
        print("\n❌ Database setup failed!")
        sys.exit(1)
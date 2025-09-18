-- Travel Assistant Database Schema
-- Creates the correct tables for the travel memory manager

CREATE DATABASE IF NOT EXISTS `travel_assistant`;
USE `travel_assistant`;

-- Users table for authentication
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
);

-- Sessions table - Travel planning sessions
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
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_session_id (session_id),
    INDEX idx_last_at (last_at),
    INDEX idx_is_active (is_active)
);

-- Turns table - Individual interactions within sessions
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
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_session_id (session_id),
    INDEX idx_user_id (user_id),
    INDEX idx_created_at (created_at),
    INDEX idx_role (role)
);

-- User Travel Profiles table - User preferences and patterns
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
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_updated_at (updated_at)
);

-- Legacy tables for compatibility with existing schema
CREATE TABLE IF NOT EXISTS `agent_interactions` (
    `id` INT PRIMARY KEY AUTO_INCREMENT,
    `user_id` INT NOT NULL,
    `agent_name` VARCHAR(100) NOT NULL,
    `query` TEXT NOT NULL,
    `response` TEXT NOT NULL,
    `interaction_type` ENUM('single', 'orchestrated') DEFAULT 'single',
    `timestamp` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_agent (user_id, agent_name),
    INDEX idx_timestamp (timestamp),
    INDEX idx_agent_name (agent_name)
);

CREATE TABLE IF NOT EXISTS `ltm` (
    `id` INT PRIMARY KEY AUTO_INCREMENT,
    `user_id` INT NOT NULL,
    `agent_name` VARCHAR(100),
    `memory_key` VARCHAR(255) NOT NULL,
    `memory_value` TEXT NOT NULL,
    `context_metadata` JSON,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_agent_name (agent_name),
    INDEX idx_created_at (created_at)
);

CREATE TABLE IF NOT EXISTS `multi_agent_orchestration` (
    `id` INT PRIMARY KEY AUTO_INCREMENT,
    `user_id` INT NOT NULL,
    `query` TEXT NOT NULL,
    `agents_involved` JSON,
    `orchestration_result` TEXT,
    `execution_time_ms` INT,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_created_at (created_at)
);

CREATE TABLE IF NOT EXISTS `user_queries` (
    `id` INT PRIMARY KEY AUTO_INCREMENT,
    `user_id` INT NOT NULL,
    `query` TEXT NOT NULL,
    `response` TEXT,
    `processing_time_ms` INT,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_created_at (created_at)
);

CREATE TABLE IF NOT EXISTS `user_sessions` (
    `id` INT PRIMARY KEY AUTO_INCREMENT,
    `user_id` INT NOT NULL,
    `session_token` VARCHAR(255) NOT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `expires_at` TIMESTAMP NOT NULL,
    `is_active` BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_session_token (session_token)
);

CREATE TABLE IF NOT EXISTS `vector_embeddings` (
    `id` INT PRIMARY KEY AUTO_INCREMENT,
    `user_id` INT NOT NULL,
    `agent_name` VARCHAR(100),
    `content` TEXT NOT NULL,
    `embedding` JSON,
    `metadata` JSON,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_agent (user_id, agent_name),
    INDEX idx_created_at (created_at)
);
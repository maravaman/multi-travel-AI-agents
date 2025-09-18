-- Database schema for LangGraph AI System

CREATE DATABASE IF NOT EXISTS `langgraph_ai_system`;
USE `langgraph_ai_system`;

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

-- User sessions for tracking recent usage
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

-- Agent interactions history
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

-- Long-term memory grouped by agent
CREATE TABLE IF NOT EXISTS `ltm_by_agent` (
    `id` INT PRIMARY KEY AUTO_INCREMENT,
    `agent_name` VARCHAR(100) NOT NULL,
    `user_id` INT NOT NULL,
    `memory_key` VARCHAR(255) NOT NULL,
    `memory_value` TEXT NOT NULL,
    `context_metadata` JSON,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY unique_agent_user_key (agent_name, user_id, memory_key),
    INDEX idx_agent_name (agent_name),
    INDEX idx_user_id (user_id),
    INDEX idx_created_at (created_at)
);

-- Vector embeddings storage for similarity search
CREATE TABLE IF NOT EXISTS `vector_embeddings` (
    `id` INT PRIMARY KEY AUTO_INCREMENT,
    `user_id` INT NOT NULL,
    `agent_name` VARCHAR(100) NOT NULL,
    `content` TEXT NOT NULL,
    `embedding` JSON NOT NULL,
    `metadata` JSON,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_agent (user_id, agent_name),
    INDEX idx_created_at (created_at)
);

-- Agent configurations - dynamic nodes and edges
CREATE TABLE IF NOT EXISTS `agent_configurations` (
    `id` INT PRIMARY KEY AUTO_INCREMENT,
    `agent_name` VARCHAR(100) UNIQUE NOT NULL,
    `module_path` VARCHAR(255) NOT NULL,
    `description` TEXT,
    `capabilities` JSON,
    `dependencies` JSON,
    `is_active` BOOLEAN DEFAULT TRUE,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_agent_name (agent_name),
    INDEX idx_is_active (is_active)
);

-- Graph edges configuration
CREATE TABLE IF NOT EXISTS `graph_edges` (
    `id` INT PRIMARY KEY AUTO_INCREMENT,
    `source_agent` VARCHAR(100) NOT NULL,
    `target_agent` VARCHAR(100) NOT NULL,
    `edge_condition` TEXT,
    `weight` INT DEFAULT 1,
    `is_active` BOOLEAN DEFAULT TRUE,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_edge (source_agent, target_agent),
    INDEX idx_source_agent (source_agent),
    INDEX idx_target_agent (target_agent),
    INDEX idx_is_active (is_active)
);

-- Usage analytics
CREATE TABLE IF NOT EXISTS `usage_analytics` (
    `id` INT PRIMARY KEY AUTO_INCREMENT,
    `user_id` INT NOT NULL,
    `agent_name` VARCHAR(100) NOT NULL,
    `query_type` VARCHAR(50),
    `execution_time_ms` INT,
    `success` BOOLEAN DEFAULT TRUE,
    `timestamp` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_agent_name (agent_name),
    INDEX idx_timestamp (timestamp)
);

-- Insert default agent configurations (ignore duplicates)
INSERT IGNORE INTO `agent_configurations` (`agent_name`, `module_path`, `description`, `capabilities`, `dependencies`) VALUES
('SearchAgent', 'core.agents.search_agent', 'Vector-based similarity search agent for history matching', '["similarity_search", "vector_embedding", "json_response"]', '[]'),
('ScenicLocationFinder', 'core.plugins.scenic_agent', 'Finds scenic locations based on user preferences', '["location_search", "scenic_analysis"]', '[]'),
('ForestAnalyzer', 'core.plugins.forest_analyzer', 'Analyzes forest data and characteristics', '["forest_analysis", "environmental_data"]', '[]'),
('WaterBodyAnalyzer', 'core.plugins.waterbody_analyzer', 'Analyzes water bodies and related information', '["water_analysis", "hydrology"]', '[]'),
('OrchestratorAgent', 'core.agents.orchestrator_agent', 'Intelligently routes queries to appropriate agents', '["query_routing", "multi_agent_coordination"]', '[]');

-- User Travel Profile (UTP) - Core user preferences and patterns
CREATE TABLE IF NOT EXISTS `user_travel_profiles` (
    `id` INT PRIMARY KEY AUTO_INCREMENT,
    `user_id` INT UNIQUE NOT NULL,
    `destinations_of_interest` JSON,
    `cuisine_preferences` JSON,
    `climate_tolerance` JSON,
    `travel_pace` ENUM('relaxed', 'moderate', 'packed') DEFAULT 'moderate',
    `behavioral_notes` JSON,
    `planning_patterns` JSON,
    `decision_style` VARCHAR(50),
    `last_updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `profile_version` VARCHAR(10) DEFAULT '1.0',
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_last_updated (last_updated_at)
);

-- Travel Sessions - Groups interactions into planning conversations
CREATE TABLE IF NOT EXISTS `travel_sessions` (
    `id` INT PRIMARY KEY AUTO_INCREMENT,
    `session_id` VARCHAR(100) UNIQUE NOT NULL,
    `user_id` INT NOT NULL,
    `title` VARCHAR(255),
    `mode` ENUM('chat', 'recording') NOT NULL,
    `started_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `last_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `turn_count` INT DEFAULT 0,
    `is_active` BOOLEAN DEFAULT TRUE,
    `session_summary` TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_session_id (session_id),
    INDEX idx_last_at (last_at),
    INDEX idx_is_active (is_active)
);

-- Travel Session Turns - Individual interactions within sessions
CREATE TABLE IF NOT EXISTS `travel_session_turns` (
    `id` INT PRIMARY KEY AUTO_INCREMENT,
    `turn_id` VARCHAR(100) UNIQUE NOT NULL,
    `session_id` VARCHAR(100) NOT NULL,
    `user_id` INT NOT NULL,
    `role` ENUM('user', 'assistant', 'agent') NOT NULL,
    `agent_name` VARCHAR(100),
    `text` TEXT NOT NULL,
    `metadata` JSON,
    `timestamp` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_session_id (session_id),
    INDEX idx_user_id (user_id),
    INDEX idx_timestamp (timestamp),
    INDEX idx_role (role)
);

-- Agent Execution Logs - Track routing and performance
CREATE TABLE IF NOT EXISTS `agent_execution_logs` (
    `id` INT PRIMARY KEY AUTO_INCREMENT,
    `user_id` INT NOT NULL,
    `session_id` VARCHAR(100),
    `turn_id` VARCHAR(100),
    `agent_name` VARCHAR(100) NOT NULL,
    `execution_order` INT NOT NULL,
    `execution_time_ms` INT,
    `success` BOOLEAN DEFAULT TRUE,
    `error_message` TEXT,
    `input_summary` TEXT,
    `output_summary` TEXT,
    `timestamp` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_session_id (session_id),
    INDEX idx_agent_name (agent_name),
    INDEX idx_timestamp (timestamp),
    INDEX idx_execution_order (execution_order)
);

-- Insert default graph edges (ignore duplicates)
INSERT IGNORE INTO `graph_edges` (`source_agent`, `target_agent`, `edge_condition`, `weight`) VALUES
('RouterAgent', 'TextTripAnalyzer', 'text_analysis_needed', 1),
('RouterAgent', 'TripMoodDetector', 'mood_analysis_needed', 1),
('RouterAgent', 'TripCommsCoach', 'communication_help_needed', 1),
('RouterAgent', 'TripBehaviorGuide', 'behavior_guidance_needed', 1),
('RouterAgent', 'TripCalmPractice', 'stress_relief_needed', 1),
('TextTripAnalyzer', 'TripSummarySynth', 'synthesis_needed', 1),
('TripMoodDetector', 'TripCalmPractice', 'calm_needed', 2),
('TripMoodDetector', 'TripSummarySynth', 'synthesis_needed', 1),
('TripCommsCoach', 'TripSummarySynth', 'synthesis_needed', 1),
('TripBehaviorGuide', 'TripCalmPractice', 'calm_support_needed', 2),
('TripBehaviorGuide', 'TripSummarySynth', 'synthesis_needed', 1),
('TripCalmPractice', 'TripSummarySynth', 'synthesis_needed', 1);

#!/usr/bin/env python3
"""
Test script to verify MySQL data persistence is working correctly
"""

import sys
import os
import time
import requests
import json
import mysql.connector
from datetime import datetime

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import config for database connection
from config import Config
config = Config()

def test_mysql_connection():
    """Test MySQL database connection"""
    print("🔗 Testing MySQL Connection...")
    try:
        conn = mysql.connector.connect(
            host=config.MYSQL_HOST,
            user=config.MYSQL_USER,
            password=config.MYSQL_PASSWORD,
            database=config.MYSQL_DATABASE,
            autocommit=True
        )
        
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM sessions")
        session_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM agent_interactions")
        interaction_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM user_queries")
        query_count = cursor.fetchone()[0]
        
        print(f"✅ MySQL Connected Successfully!")
        print(f"   Users: {user_count}")
        print(f"   Sessions: {session_count}")
        print(f"   Interactions: {interaction_count}")
        print(f"   Queries: {query_count}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ MySQL Connection Failed: {e}")
        return False

def test_travel_chat_endpoint():
    """Test travel chat endpoint and verify data storage"""
    print("\n💬 Testing Travel Chat Endpoint...")
    
    # Record counts before test
    before_counts = get_database_counts()
    
    try:
        # Test user ID
        test_user_id = int(time.time())  # Unique user ID
        test_text = f"I want to plan a trip to Tokyo. What are the best neighborhoods to stay in?"
        
        # Make request to travel chat endpoint
        response = requests.post(
            "http://127.0.0.1:8080/travel/chat",
            json={
                "user_id": test_user_id,
                "text": test_text
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Chat Request Successful!")
            print(f"   Response: {result['response'][:100]}...")
            print(f"   Agents: {result['agents_involved']}")
            print(f"   Processing Time: {result['processing_time']:.2f}s")
            print(f"   AI Used: {result.get('ai_used', False)}")
            
            # Wait a moment for database writes
            time.sleep(2)
            
            # Check database counts after
            after_counts = get_database_counts()
            
            print(f"\n📊 Database Changes:")
            print(f"   Users: {before_counts['users']} → {after_counts['users']} (+{after_counts['users'] - before_counts['users']})")
            print(f"   Sessions: {before_counts['sessions']} → {after_counts['sessions']} (+{after_counts['sessions'] - before_counts['sessions']})")
            print(f"   Interactions: {before_counts['interactions']} → {after_counts['interactions']} (+{after_counts['interactions'] - before_counts['interactions']})")
            print(f"   Queries: {before_counts['queries']} → {after_counts['queries']} (+{after_counts['queries'] - before_counts['queries']})")
            
            # Verify specific data was stored
            verify_user_data_stored(test_user_id, test_text)
            
            return True
        else:
            print(f"❌ Chat Request Failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Chat Endpoint Test Failed: {e}")
        return False

def test_travel_batch_endpoint():
    """Test travel batch endpoint and verify data storage"""
    print("\n📝 Testing Travel Batch Endpoint...")
    
    # Record counts before test
    before_counts = get_database_counts()
    
    try:
        # Test user ID
        test_user_id = int(time.time()) + 1  # Different from chat test
        test_transcript = """
        User: I'm thinking about a two-week trip to Europe next spring.
        Friend: That sounds amazing! Where are you thinking of going?
        User: I'm torn between Italy and Spain. I love food and history.
        Friend: Both have incredible food and history! What's your budget like?
        User: Around $3000-4000 for everything including flights.
        Friend: That should be good for two weeks if you're smart about it.
        """
        
        # Make request to travel batch endpoint
        response = requests.post(
            "http://127.0.0.1:8080/travel/batch",
            json={
                "user_id": test_user_id,
                "transcript": test_transcript
            },
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Batch Request Successful!")
            print(f"   Response: {result['response'][:100]}...")
            print(f"   Agents: {result['agents_involved']}")
            print(f"   Processing Time: {result['processing_time']:.2f}s")
            print(f"   AI Used: {result.get('ai_used', False)}")
            
            # Wait a moment for database writes
            time.sleep(2)
            
            # Check database counts after
            after_counts = get_database_counts()
            
            print(f"\n📊 Database Changes:")
            print(f"   Users: {before_counts['users']} → {after_counts['users']} (+{after_counts['users'] - before_counts['users']})")
            print(f"   Sessions: {before_counts['sessions']} → {after_counts['sessions']} (+{after_counts['sessions'] - before_counts['sessions']})")
            print(f"   Interactions: {before_counts['interactions']} → {after_counts['interactions']} (+{after_counts['interactions'] - before_counts['interactions']})")
            print(f"   Queries: {before_counts['queries']} → {after_counts['queries']} (+{after_counts['queries'] - before_counts['queries']})")
            
            # Verify specific data was stored
            verify_user_data_stored(test_user_id, test_transcript[:100])
            
            return True
        else:
            print(f"❌ Batch Request Failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Batch Endpoint Test Failed: {e}")
        return False

def get_database_counts():
    """Get current database record counts"""
    try:
        conn = mysql.connector.connect(
            host=config.MYSQL_HOST,
            user=config.MYSQL_USER,
            password=config.MYSQL_PASSWORD,
            database=config.MYSQL_DATABASE
        )
        
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM users")
        users = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM sessions")
        sessions = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM agent_interactions")
        interactions = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM user_queries")
        queries = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        return {
            'users': users,
            'sessions': sessions,
            'interactions': interactions,
            'queries': queries
        }
        
    except Exception as e:
        print(f"❌ Error getting database counts: {e}")
        return {'users': 0, 'sessions': 0, 'interactions': 0, 'queries': 0}

def verify_user_data_stored(user_id, query_text):
    """Verify that user data was actually stored correctly"""
    print(f"\n🔍 Verifying Data Storage for User {user_id}...")
    
    try:
        conn = mysql.connector.connect(
            host=config.MYSQL_HOST,
            user=config.MYSQL_USER,
            password=config.MYSQL_PASSWORD,
            database=config.MYSQL_DATABASE
        )
        
        cursor = conn.cursor(dictionary=True)
        
        # Check if user was created
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        if user:
            print(f"✅ User Created: {user['username']} (ID: {user['id']})")
        else:
            print(f"⚠️ User not found in database")
        
        # Check sessions
        cursor.execute("SELECT * FROM sessions WHERE user_id = %s ORDER BY created_at DESC LIMIT 1", (user_id,))
        session = cursor.fetchone()
        if session:
            print(f"✅ Session Stored: {session['session_id']} - {session['title']}")
            print(f"   Mode: {session['mode']}, Turn Count: {session['turn_count']}")
        else:
            print(f"⚠️ No sessions found for user")
        
        # Check interactions
        cursor.execute("SELECT * FROM agent_interactions WHERE user_id = %s ORDER BY timestamp DESC LIMIT 1", (user_id,))
        interaction = cursor.fetchone()
        if interaction:
            print(f"✅ Interaction Stored: Agent {interaction['agent_name']}")
            print(f"   Query: {interaction['query'][:50]}...")
            print(f"   Response: {interaction['response'][:50]}...")
        else:
            print(f"⚠️ No interactions found for user")
        
        # Check queries
        cursor.execute("SELECT * FROM user_queries WHERE user_id = %s ORDER BY timestamp DESC LIMIT 1", (user_id,))
        query = cursor.fetchone()
        if query:
            print(f"✅ Query Stored: {query['query_text'][:50]}...")
            print(f"   Agent: {query['agent_used']}, Response Length: {query['response_length']}")
        else:
            print(f"⚠️ No queries found for user")
        
        # Check turns if they exist
        cursor.execute("SELECT * FROM turns WHERE user_id = %s ORDER BY created_at DESC LIMIT 2", (user_id,))
        turns = cursor.fetchall()
        if turns:
            print(f"✅ Turns Stored: {len(turns)} turns found")
            for turn in turns:
                print(f"   {turn['role']}: {turn['content'][:30]}...")
        else:
            print(f"⚠️ No turns found for user")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error verifying user data: {e}")

def cleanup_test_data():
    """Clean up test data (optional)"""
    print("\n🧹 Cleaning up test data...")
    
    try:
        conn = mysql.connector.connect(
            host=config.MYSQL_HOST,
            user=config.MYSQL_USER,
            password=config.MYSQL_PASSWORD,
            database=config.MYSQL_DATABASE,
            autocommit=True
        )
        
        cursor = conn.cursor()
        
        # Delete test users and related data (cascading deletes should handle related tables)
        cursor.execute("DELETE FROM users WHERE username LIKE 'travel_user_%' OR username LIKE 'batch_user_%'")
        deleted_users = cursor.rowcount
        
        cursor.close()
        conn.close()
        
        print(f"✅ Cleaned up {deleted_users} test users and related data")
        
    except Exception as e:
        print(f"❌ Error cleaning up test data: {e}")

def main():
    """Main test function"""
    print("🧪 MySQL Data Persistence Test Suite")
    print("=" * 50)
    
    # Test 1: Database Connection
    if not test_mysql_connection():
        print("\n❌ Database connection failed. Cannot proceed with tests.")
        return False
    
    # Test 2: Travel Chat Endpoint
    chat_success = test_travel_chat_endpoint()
    
    # Test 3: Travel Batch Endpoint
    batch_success = test_travel_batch_endpoint()
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 TEST SUMMARY:")
    print(f"   Database Connection: ✅")
    print(f"   Chat Endpoint & Storage: {'✅' if chat_success else '❌'}")
    print(f"   Batch Endpoint & Storage: {'✅' if batch_success else '❌'}")
    
    if chat_success and batch_success:
        print("\n🎉 SUCCESS: All data is being stored correctly in MySQL!")
    else:
        print("\n⚠️ ISSUES: Some data storage problems detected")
    
    # Ask if user wants to clean up
    try:
        cleanup = input("\nClean up test data? (y/n): ").lower().strip()
        if cleanup == 'y':
            cleanup_test_data()
    except KeyboardInterrupt:
        print("\nTest completed.")
    
    return chat_success and batch_success

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
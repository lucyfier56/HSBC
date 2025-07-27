import sqlite3
import json
from typing import Dict, Optional, Any
from datetime import datetime
import os

class StateManager:
    def __init__(self, db_path: str = 'banking_agent.db'):
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Initialize SQLite database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create state table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS session_state (
                session_id TEXT PRIMARY KEY,
                state_data TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create conversation history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                user_message TEXT NOT NULL,
                ai_response TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                topics TEXT,
                urgency_level TEXT DEFAULT 'normal'
            )
        ''')
        
        # Create user profiles table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id TEXT PRIMARY KEY,
                profile_data TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()

    def get_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get current state for a session from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT state_data FROM session_state WHERE session_id = ?',
            (session_id,)
        )
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return json.loads(result[0])
        return None

    def update_state(self, session_id: str, new_state_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update state for a session in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get existing state
        existing_state = self.get_state(session_id) or {}
        
        # Merge with new data
        existing_state.update(new_state_data)
        
        # Update or insert
        cursor.execute('''
            INSERT OR REPLACE INTO session_state (session_id, state_data, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        ''', (session_id, json.dumps(existing_state)))
        
        conn.commit()
        conn.close()
        
        return existing_state

    def clear_state(self, session_id: str):
        """Clear state for a session from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM session_state WHERE session_id = ?', (session_id,))
        
        conn.commit()
        conn.close()

    def set_state(self, session_id: str, state_data: Dict[str, Any]):
        """Set complete state for a session in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO session_state (session_id, state_data, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        ''', (session_id, json.dumps(state_data)))
        
        conn.commit()
        conn.close()

    def get_all_sessions(self) -> list:
        """Get all active sessions"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT session_id, updated_at FROM session_state ORDER BY updated_at DESC')
        results = cursor.fetchall()
        conn.close()
        
        return [{'session_id': row[0], 'updated_at': row[1]} for row in results]

    def cleanup_old_sessions(self, days_old: int = 30):
        """Clean up sessions older than specified days"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            DELETE FROM session_state 
            WHERE datetime(updated_at) < datetime('now', '-{} days')
        '''.format(days_old))
        
        cursor.execute('''
            DELETE FROM conversation_history 
            WHERE datetime(timestamp) < datetime('now', '-{} days')
        '''.format(days_old))
        
        conn.commit()
        conn.close()

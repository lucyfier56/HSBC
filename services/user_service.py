import sqlite3
import json
from typing import Dict, Any, Optional
from datetime import datetime

class UserService:
    def __init__(self, db_path: str = 'banking_agent.db'):
        self.db_path = db_path

    def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT profile_data FROM user_profiles WHERE user_id = ?',
            (user_id,)
        )
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return json.loads(result[0])
        return None

    def update_user_profile(self, user_id: str, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update or create user profile in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get existing profile
        existing_profile = self.get_user_profile(user_id) or {}
        
        # Merge with new data
        existing_profile.update(profile_data)
        
        # Update or insert
        cursor.execute('''
            INSERT OR REPLACE INTO user_profiles (user_id, profile_data, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        ''', (user_id, json.dumps(existing_profile)))
        
        conn.commit()
        conn.close()
        
        return existing_profile

    def get_user_interaction_history(self, user_id: str, days: int = 30) -> list:
        """Get user's interaction history across all sessions"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT ch.session_id, ch.timestamp, ch.topics, ch.urgency_level,
                   COUNT(*) as message_count
            FROM conversation_history ch
            JOIN session_state ss ON ch.session_id = ss.session_id
            WHERE datetime(ch.timestamp) > datetime('now', '-{} days')
            GROUP BY ch.session_id
            ORDER BY ch.timestamp DESC
        '''.format(days), (user_id,))
        
        results = cursor.fetchall()
        conn.close()
        
        return [
            {
                'session_id': row[0],
                'timestamp': row[1],
                'topics': json.loads(row[2]) if row[2] else [],
                'urgency_level': row[3],
                'message_count': row[4]
            }
            for row in results
        ]

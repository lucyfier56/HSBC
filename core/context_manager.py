import sqlite3
import json
from typing import Dict, List, Tuple, Any, Optional
from core.state_manager import StateManager
from tools.definitions import TOOL_DEFINITIONS
import re
from datetime import datetime

class ContextManager:
    def __init__(self, db_path: str = 'banking_agent.db'):
        self.db_path = db_path
        self.state_manager = StateManager(db_path)
        self.context_patterns = self._initialize_context_patterns()

    def _initialize_context_patterns(self) -> Dict[str, List[str]]:
        """Initialize patterns for context detection"""
        return {
            'urgency': ['urgent', 'emergency', 'lost', 'stolen', 'immediately', 'asap', 'help'],
            'uncertainty': ['maybe', 'not sure', 'think', 'possibly', 'perhaps', 'confused'],
            'continuation': ['also', 'and', 'additionally', 'furthermore', 'plus'],
            'interruption': ['wait', 'actually', 'instead', 'change', 'different'],
            'completion': ['done', 'finished', 'complete', 'thanks', 'thank you']
        }

    def get_conversation_history(self, session_id: str, limit: int = 20) -> List[Dict]:
        """Get conversation history from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT user_message, ai_response, timestamp, topics, urgency_level
            FROM conversation_history 
            WHERE session_id = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (session_id, limit))
        
        results = cursor.fetchall()
        conn.close()
        
        # Convert to list of dicts and reverse to get chronological order
        history = []
        for row in reversed(results):
            history.append({
                'user': row[0],
                'assistant': row[1],
                'timestamp': row[2],
                'topics': json.loads(row[3]) if row[3] else [],
                'urgency': row[4] or 'normal'
            })
        
        return history

    def update_history(self, session_id: str, user_message: str, ai_response: str):
        """Update conversation history in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Extract topics and urgency
        topics = self._extract_topics_from_text(user_message)
        urgency = self._detect_urgency(user_message)
        
        cursor.execute('''
            INSERT INTO conversation_history 
            (session_id, user_message, ai_response, topics, urgency_level)
            VALUES (?, ?, ?, ?, ?)
        ''', (session_id, user_message, ai_response, json.dumps(topics), urgency))
        
        conn.commit()
        conn.close()

    def prepare_prompt(self, user_id: str, session_id: str, message: str) -> Tuple[str, List]:
        """Prepare enhanced prompt with context intelligence"""
        
        # Get conversation history from database
        history = self.get_conversation_history(session_id, limit=10)
        current_state = self.state_manager.get_state(session_id)
        
        # Analyze message context
        message_context = self._analyze_message_context(message, history)
        
        # Build intelligent system prompt
        system_prompt = self._build_intelligent_system_prompt(
            user_id, current_state, message_context
        )
        
        # Build conversation context with intelligence
        conversation_context = self._build_intelligent_conversation_context(
            history, message, message_context
        )
        
        full_prompt = f"{system_prompt}\n\n{conversation_context}"
        
        return full_prompt, TOOL_DEFINITIONS

    def _analyze_message_context(self, message: str, history: List[Dict]) -> Dict[str, Any]:
        """Analyze message for contextual cues"""
        
        context = {
            'urgency_level': 'normal',
            'uncertainty_indicators': [],
            'topic_shift': False,
            'continuation_indicators': [],
            'emotional_state': 'neutral',
            'complexity': 'simple'
        }
        
        message_lower = message.lower()
        
        # Detect urgency
        urgency_matches = [word for word in self.context_patterns['urgency'] 
                          if word in message_lower]
        if urgency_matches:
            context['urgency_level'] = 'high'
            context['urgency_indicators'] = urgency_matches
        
        # Detect uncertainty
        uncertainty_matches = [word for word in self.context_patterns['uncertainty'] 
                              if word in message_lower]
        if uncertainty_matches:
            context['uncertainty_indicators'] = uncertainty_matches
            context['emotional_state'] = 'uncertain'
        
        # Detect topic shifts
        if history and len(history) > 0:
            last_topics = self._extract_topics_from_text(history[-1]['user'])
            current_topics = self._extract_topics_from_text(message)
            if current_topics and last_topics and not any(t in last_topics for t in current_topics):
                context['topic_shift'] = True
        
        # Detect continuation
        continuation_matches = [word for word in self.context_patterns['continuation'] 
                               if word in message_lower]
        if continuation_matches:
            context['continuation_indicators'] = continuation_matches
        
        # Assess complexity
        if len(message.split()) > 20 or '?' in message:
            context['complexity'] = 'complex'
        
        return context

    def _extract_topics_from_text(self, text: str) -> List[str]:
        """Extract banking topics from text"""
        
        topics = []
        text_lower = text.lower()
        
        topic_map = {
            'loan': ['loan', 'borrow', 'mortgage', 'credit'],
            'card': ['card', 'debit', 'credit', 'block'],
            'account': ['account', 'balance', 'statement'],
            'transfer': ['transfer', 'send', 'payment']
        }
        
        for topic, keywords in topic_map.items():
            if any(keyword in text_lower for keyword in keywords):
                topics.append(topic)
        
        return topics

    def _build_intelligent_system_prompt(self, user_id: str, current_state: Dict, 
                                       message_context: Dict) -> str:
        """Build context-aware system prompt"""
        
        base_prompt = """You are an advanced conversational banking assistant with exceptional contextual understanding.

CORE INTELLIGENCE:
• Perfect conversation memory and context retention
• Emotional intelligence - detect user mood and urgency
• Adaptive communication - match user's style and needs
• Proactive assistance - anticipate user needs
• Seamless task management - handle interruptions and context switches

CURRENT CONVERSATION CONTEXT:"""
        
        # Add urgency handling
        if message_context['urgency_level'] == 'high':
            base_prompt += f"""
⚠️  HIGH URGENCY DETECTED: {', '.join(message_context.get('urgency_indicators', []))}
- Prioritize immediate assistance
- Offer quick solutions and escalation options
- Show empathy and understanding"""
        
        # Add uncertainty handling
        if message_context['uncertainty_indicators']:
            base_prompt += f"""
🤔 UNCERTAINTY DETECTED: {', '.join(message_context['uncertainty_indicators'])}
- Ask clarifying questions
- Provide options and explanations
- Guide user step-by-step"""
        
        # Add topic shift handling
        if message_context['topic_shift']:
            base_prompt += f"""
🔄 TOPIC SHIFT DETECTED:
- Acknowledge the topic change
- Ask if user wants to complete previous task
- Smoothly transition to new topic"""
        
        # Add state context
        if current_state:
            if current_state.get('loan_application'):
                loan_info = current_state['loan_application']
                base_prompt += f"""

📋 ACTIVE LOAN APPLICATION:
- ID: {loan_info.get('application_id')}
- Amount: ${loan_info.get('amount', 'TBD')}
- Status: {loan_info.get('status', 'In Progress')}
- Next Step: {loan_info.get('next_step', 'Pending')}"""
            
            if current_state.get('suspended_tasks'):
                base_prompt += f"""

⏸️  SUSPENDED TASKS: {len(current_state['suspended_tasks'])} task(s) available to resume"""
        
        base_prompt += """

RESPONSE GUIDELINES:
• Match the user's communication style and emotional state
• Provide clear, actionable responses
• Use tools when real-time data is needed
• Offer proactive suggestions when appropriate
• Handle errors gracefully with alternatives"""
        
        return base_prompt

    def _build_intelligent_conversation_context(self, history: List[Dict], 
                                              current_message: str, 
                                              message_context: Dict) -> str:
        """Build intelligent conversation context"""
        
        context_parts = []
        
        # Add relevant history based on context
        if history:
            context_parts.append("CONVERSATION HISTORY:")
            
            # Show more history for complex conversations
            history_length = 8 if message_context['complexity'] == 'complex' else 5
            
            for turn in history[-history_length:]:
                context_parts.append(f"User: {turn['user']}")
                context_parts.append(f"Assistant: {turn['assistant']}")
        
        # Add context analysis
        if message_context['urgency_level'] == 'high':
            context_parts.append(f"\n⚠️ URGENT REQUEST DETECTED")
        
        if message_context['topic_shift']:
            context_parts.append(f"\n🔄 TOPIC CHANGE DETECTED")
        
        if message_context['uncertainty_indicators']:
            context_parts.append(f"\n🤔 USER SEEMS UNCERTAIN - PROVIDE CLEAR GUIDANCE")
        
        # Add current message
        context_parts.append(f"\nCURRENT MESSAGE: {current_message}")
        context_parts.append("Assistant:")
        
        return "\n".join(context_parts)

    def add_tool_result_to_history(self, session_id: str, tool_name: str, 
                                 tool_result: Any, user_message: str) -> str:
        """Enhanced tool result integration"""
        
        history = self.get_conversation_history(session_id, limit=5)
        current_state = self.state_manager.get_state(session_id)
        
        # Build enhanced prompt with tool result
        prompt_parts = [
            "TOOL EXECUTION COMPLETED:",
            f"Tool: {tool_name}",
            f"Result: {json.dumps(tool_result, indent=2)}",
            f"User's Original Request: {user_message}",
            ""
        ]
        
        # Add context from current state
        if current_state:
            prompt_parts.append("CURRENT CONTEXT:")
            if current_state.get('context_switch'):
                prompt_parts.append("- User recently switched topics")
            if current_state.get('urgency_level') == 'high':
                prompt_parts.append("- This is an urgent request")
            prompt_parts.append("")
        
        # Add recent conversation for context
        if history:
            prompt_parts.append("RECENT CONVERSATION:")
            for turn in history[-3:]:
                prompt_parts.append(f"User: {turn['user']}")
                prompt_parts.append(f"Assistant: {turn['assistant']}")
            prompt_parts.append("")
        
        prompt_parts.extend([
            "Generate a response that:",
            "1. Addresses the tool result comprehensively",
            "2. Maintains conversation flow and context",
            "3. Offers appropriate follow-up actions",
            "4. Matches the user's communication style",
            "5. Shows empathy and understanding",
            "",
            "Response:"
        ])
        
        return "\n".join(prompt_parts)

    def _detect_urgency(self, message: str) -> str:
        """Detect urgency level in message"""
        
        urgent_keywords = ['urgent', 'emergency', 'lost', 'stolen', 'immediately', 'asap']
        message_lower = message.lower()
        
        if any(keyword in message_lower for keyword in urgent_keywords):
            return 'high'
        elif '!' in message or message.isupper():
            return 'medium'
        else:
            return 'normal'

    def get_conversation_statistics(self, session_id: str) -> Dict[str, Any]:
        """Get conversation statistics from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(*) as total_messages,
                   AVG(CASE WHEN urgency_level = 'high' THEN 1 ELSE 0 END) as urgency_rate,
                   GROUP_CONCAT(DISTINCT topics) as all_topics
            FROM conversation_history 
            WHERE session_id = ?
        ''', (session_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'total_messages': result[0],
                'urgency_rate': result[1] or 0,
                'topics_discussed': result[2].split(',') if result[2] else []
            }
        
        return {'total_messages': 0, 'urgency_rate': 0, 'topics_discussed': []}

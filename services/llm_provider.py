import os
import json
from typing import List, Dict, Optional
from groq import Groq
from app.schemas import LLMResponse, ToolCall
from dotenv import load_dotenv

load_dotenv()

# Initialize Groq client
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

async def get_llm_response(prompt: str, tools: List[Dict] = None, system_prompt: Optional[str] = None) -> LLMResponse:
    """Get response from Groq Llama 3.3 70B model"""
    
    try:
        messages = []
        
        # Add system prompt if provided
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        # Prepare the API call
        kwargs = {
            "model": "llama-3.3-70b-versatile",
            "messages": messages,
            "temperature": 0.3,  # Lower temperature for more consistent banking responses
            "max_tokens": 1024,  # Increased for more detailed responses
            "top_p": 0.9,
            "stream": False
        }
        
        # Handle tool calls if provided
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        
        response = client.chat.completions.create(**kwargs)
        
        message = response.choices[0].message
        
        # Check if the response includes a tool call
        if hasattr(message, 'tool_calls') and message.tool_calls:
            tool_call = message.tool_calls[0]
            return LLMResponse(
                text="",
                has_tool_call=True,
                tool_call=ToolCall(
                    name=tool_call.function.name,
                    arguments=json.loads(tool_call.function.arguments)
                )
            )
        
        return LLMResponse(
            text=message.content,
            has_tool_call=False
        )
        
    except Exception as e:
        # Enhanced error handling with fallback responses
        error_msg = str(e)
        
        # Provide contextual fallback responses based on the prompt
        if "loan" in prompt.lower():
            fallback_text = "I'd be happy to help you with your loan inquiry. However, I'm experiencing technical difficulties accessing our loan systems right now. Please try again in a moment, or you can call our loan department at 1-800-BANK-LOAN."
        elif "card" in prompt.lower() and "block" in prompt.lower():
            fallback_text = "For immediate card blocking due to loss or theft, please call our 24/7 hotline at 1-800-BLOCK-CARD. I'm currently experiencing technical issues but your card security is our priority."
        elif "balance" in prompt.lower() or "statement" in prompt.lower():
            fallback_text = "I'm having trouble accessing account information right now. You can check your balance and statements through our mobile app or online banking portal. Technical support: 1-800-HELP-BANK."
        else:
            fallback_text = f"I apologize for the technical difficulty. Our banking services are temporarily affected. Please try again shortly or contact customer service at 1-800-BANK-HELP for immediate assistance."
        
        return LLMResponse(
            text=fallback_text,
            has_tool_call=False
        )

def create_enhanced_system_prompt(user_context: Dict = None) -> str:
    """Create an enhanced system prompt for banking conversations"""
    
    base_prompt = """You are SecureBank's intelligent conversational assistant, designed to provide exceptional banking support with human-like understanding and efficiency.

CORE CAPABILITIES:
• Multi-turn conversation management with perfect context retention
• Goal-oriented task completion for complex banking workflows  
• Real-time adaptation to changing user intents and context switches
• Intelligent clarification when facing ambiguous or incomplete requests
• Seamless integration with banking systems and knowledge bases

PRIMARY BANKING SERVICES:
1. LOAN APPLICATIONS - Guide users through complete loan processes, handle existing applications
2. CARD MANAGEMENT - Block/unblock cards, manage multiple cards, security features
3. ACCOUNT SERVICES - Balances, statements, transaction history, account details
4. INFORMATION SERVICES - Interest rates, fees, policies, general banking questions

CONVERSATION PRINCIPLES:
• Maintain context across all interactions - remember previous requests and user preferences
• Handle interruptions gracefully - if user switches topics, acknowledge and adapt seamlessly  
• Ask intelligent clarifying questions for ambiguous requests
• Provide progressive disclosure - gather information step-by-step for complex tasks
• Recognize and respond to emotional cues (urgency for lost cards, excitement for loans)
• Use natural, conversational language while maintaining professionalism

CONTEXT AWARENESS:
• Remember user's banking history and preferences throughout conversation
• Detect when users change topics and smoothly transition
• Maintain awareness of incomplete tasks and offer to continue them later
• Understand implicit requests (e.g., "I lost my wallet" implies card blocking)

RESPONSE STRATEGY:
• For urgent requests (lost cards): Prioritize immediate action
• For complex processes (loans): Break into manageable steps  
• For information requests: Provide comprehensive yet concise answers
• For ambiguous requests: Ask targeted clarifying questions
• Always confirm critical actions before execution

ERROR HANDLING:
• If external systems are unavailable, provide alternative solutions
• Escalate to human agents when necessary
• Maintain user confidence even during technical difficulties

PERSONALIZATION:
• Address users by name when available
• Reference their specific account details and history
• Adapt communication style to user preferences
• Remember user's preferred interaction patterns"""

    # Add user-specific context if available
    if user_context:
        if user_context.get('name'):
            base_prompt += f"\n\nUSER CONTEXT:\n• Customer Name: {user_context['name']}"
        if user_context.get('account_type'):
            base_prompt += f"\n• Account Type: {user_context['account_type']}"
        if user_context.get('recent_activity'):
            base_prompt += f"\n• Recent Activity: {user_context['recent_activity']}"
    
    return base_prompt

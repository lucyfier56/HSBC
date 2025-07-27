from core.context_manager import ContextManager
from core.tool_executor import ToolExecutor
from core.state_manager import StateManager
from services.llm_provider import get_llm_response, create_enhanced_system_prompt
from app.schemas import ChatResponse
import json
import asyncio
import re
from typing import Dict, Any
from datetime import datetime

class ConversationalAgent:
    def __init__(self):
        self.context_manager = ContextManager()
        self.tool_executor = ToolExecutor()
        self.state_manager = StateManager()
        self.conversation_memory = {}  # Enhanced memory for context switching

    async def process_turn(self, user_id: str, session_id: str, message: str) -> ChatResponse:
        """Process a complete conversational turn with enhanced context awareness"""
        
        # Direct handling for common queries when LLM fails (fallback mechanism)
        message_lower = message.lower()
        
        # Get current state to check for ongoing processes
        current_state = self.state_manager.get_state(session_id) or {}
        loan_process = current_state.get('multi_step_process', {})
        pending_action = current_state.get('pending_action', {})
        #Handle comprehensive account details queries - BEFORE balance queries
        if any(phrase in message_lower for phrase in ['account details', 'account information', 'complete account', 'full account', 'account overview', 'my account details', 'show account details']):
            return await self._handle_account_details_query(user_id, session_id, message)
        # Handle balance queries directly
        if any(phrase in message_lower for phrase in ['balance', 'account balance', 'my balance', 'show balance', "what's my balance", "whats my balance"]):
            return await self._handle_balance_query(user_id, session_id, message)
        
        # Handle transaction queries directly
        if any(phrase in message_lower for phrase in ['transactions', 'recent transactions', 'mini statement', 'statement', 'transaction history']):
            return await self._handle_transaction_query(user_id, session_id, message)
        
        # Handle card management queries (shows menu of actions)
        if any(phrase in message_lower for phrase in ['card management', 'manage cards', 'card services']):
            return await self._handle_card_management_query(user_id, session_id, message)
        
        # Handle NEW CARD APPLICATION queries - IMPORTANT: This should come BEFORE loan detection
        if any(phrase in message_lower for phrase in ['apply for new card', 'new card application', 'apply new card', 'get new card']):
            return await self._handle_new_card_application(user_id, session_id, message)
        
        # Handle direct card blocking queries (shows list of cards)
        if any(phrase in message_lower for phrase in ['block card', 'block my card']) and not any(phrase in message_lower for phrase in ['card management', 'manage cards']):
            return await self._handle_direct_card_blocking(user_id, session_id, message)
        
        # Handle general card queries (shows list of cards)
        if any(phrase in message_lower for phrase in ['my cards', 'show cards', 'list cards']):
            return await self._handle_card_list_query(user_id, session_id, message)
        
        # Handle loan listing queries BEFORE loan application queries
        if any(phrase in message_lower for phrase in [
            'list loans', 'list all loans', 'show loans', 'show all loans', 'my loans', 
            'list the loans', 'show the loans', 'loans i have applied', 'loan applications', 
            'applied for loans', 'show my loan applications', 'list my loan applications',
            'what loans do i have', 'all my loans', 'existing loans'
        ]) and not any(phrase in message_lower for phrase in ['apply', 'new loan', 'apply for']):
            return await self._handle_loan_listing_query(user_id, session_id, message)

        # Handle loan process with context switching support - AFTER loan listing detection
        is_loan_process_active = loan_process.get('type') == 'loan_application'
        is_loan_query = any(phrase in message_lower for phrase in ['loan', 'apply for loan', 'new loan', 'loan application', 'borrow money', 'need money', 'apply loan'])
        is_numerical_response = re.match(r'^\$?[0-9,]+(?:\.[0-9]{2})?$', message.strip())

        if is_loan_process_active or is_loan_query or (is_loan_process_active and is_numerical_response):
            return await self._handle_loan_process(user_id, session_id, message, loan_process)

        
        # Handle pending actions (card blocking, limit modifications, etc.)
        if pending_action:
            return await self._handle_pending_actions(user_id, session_id, message, pending_action)
        
        # Handle multi-step processes (card applications, limit modifications)
        if current_state.get('multi_step_process'):
            return await self._handle_multi_step_processes(user_id, session_id, message, current_state)
    
    # Continue with existing LLM processing...
    # [rest of your existing code]

        
        # Detect context switches and intent changes
        await self._analyze_context_switch(session_id, message)
        
        # Enhanced prompt preparation with conversation intelligence
        try:
            prompt, tool_definitions = await self._prepare_intelligent_prompt(user_id, session_id, message)
            
            # Create enhanced system prompt
            user_context = await self._get_user_context(user_id)
            system_prompt = create_enhanced_system_prompt(user_context)
            
            # First LLM call with enhanced context
            llm_decision = await get_llm_response(prompt, tools=tool_definitions, system_prompt=system_prompt)
            
            response_data = ChatResponse(response="")
            
            if llm_decision.has_tool_call:
                # Execute tool with context awareness
                tool_result = await self._execute_tool_with_context(
                    user_id, session_id, llm_decision.tool_call.name, llm_decision.tool_call.arguments
                )
                
                # Handle multi-step processes
                if isinstance(tool_result, dict) and tool_result.get("requires_selection"):
                    response_data = await self._handle_selection_process(session_id, tool_result, llm_decision.tool_call)
                elif isinstance(tool_result, dict) and tool_result.get("requires_continuation"):
                    response_data = await self._handle_multi_step_process(session_id, tool_result, message)
                else:
                    # Generate final response with full context
                    final_response = await self._generate_contextual_response(
                        session_id, llm_decision.tool_call.name, tool_result, message, system_prompt
                    )
                    response_data.response = final_response
            else:
                # Direct response with context awareness
                response_data.response = llm_decision.text

            # Update conversation memory and context
            await self._update_conversation_context(session_id, message, response_data.response)
            
            return response_data
            
        except Exception as e:
            # Enhanced fallback for LLM failures
            return await self._handle_llm_failure(session_id, message, current_state, e)
    
    async def _handle_card_blocking_selection(self, user_id: str, session_id: str, message: str, pending_action: Dict) -> ChatResponse:
        """Handle card blocking selection"""
        
        # Extract option ID from message
        card_match = re.search(r'card_(\d+)', message.lower())
        if card_match:
            card_id = f"card_{card_match.group(1).zfill(3)}"
            
            # Execute the card blocking
            from tools.banking_api import block_card
            block_result = block_card(user_id, card_id)
            
            if block_result.get('status') == 'success':
                response_text = f"""✅ {block_result['message']}

    🔐 **Confirmation Details:**
    • Confirmation Code: {block_result['confirmation_code']}
    • Card Details: {block_result['card_details']['brand']} {block_result['card_details']['type']} ending in {block_result['card_details']['last_four']}
    • Blocked Date: {block_result['card_details']['blocked_date']}

    📋 **Next Steps:**
    {chr(10).join(['• ' + step for step in block_result['next_steps']])}

    {await self._get_context_switch_message(session_id)}"""
            else:
                response_text = f"❌ {block_result.get('message', 'Unable to block the card. Please try again.')}"
                
                # Add context switch message
                response_text += f"\n\n{await self._get_context_switch_message(session_id)}"
            
            # Clear pending action
            current_state = self.state_manager.get_state(session_id) or {}
            if 'pending_action' in current_state:
                del current_state['pending_action']
            self.state_manager.update_state(session_id, current_state)
            
            response_data = ChatResponse(response=response_text)
            self.context_manager.update_history(session_id, message, response_text)
            return response_data
        
        return ChatResponse(response="Please select a valid card option.")

    async def _handle_new_card_application(self, user_id: str, session_id: str, message: str) -> ChatResponse:
        """Handle new card application directly"""
        
        try:
            await self._save_current_process_on_context_switch(session_id, 'new_card_application')
            
            from tools.banking_api import new_card_type
            type_result = new_card_type(user_id)
            
            if type_result.get("requires_selection"):
                response_data = ChatResponse(
                    response=type_result["message"],
                    requires_selection=True,
                    options=type_result["options"]
                )
                
                # Update pending action for new card application
                self.state_manager.update_state(session_id, {
                    "pending_action": {
                        "tool": "new_card_application",
                        "step": "type_selection",
                        "options": type_result["options"],
                        "process_type": "new_card_application"
                    }
                })
                return response_data
            
            return ChatResponse(response="Unable to access card application options. Please try again.")
            
        except Exception as e:
            print(f"New Card Application Error: {str(e)}")
            return ChatResponse(response="I'm having trouble processing your card application. Please try again.")

    async def _handle_new_card_application_selection(self, user_id: str, session_id: str, message: str, pending_action: Dict) -> ChatResponse:
        """Handle new card application selections"""
        
        current_step = pending_action.get('step')
        message_lower = message.lower()
        
        if current_step == 'type_selection':
            selected_type = None
            if any(phrase in message_lower for phrase in ['credit_card', 'credit', 'option 1']):
                selected_type = 'credit_card'
            elif any(phrase in message_lower for phrase in ['debit_card', 'debit', 'option 2']):
                selected_type = 'debit_card'
            
            if selected_type:
                # Show brand options
                from tools.banking_api import card_brand_selection
                brand_result = card_brand_selection(user_id, selected_type)
                
                if brand_result.get("requires_selection"):
                    response_data = ChatResponse(
                        response=brand_result["message"],
                        requires_selection=True,
                        options=brand_result["options"]
                    )
                    
                    # Update pending action
                    self.state_manager.update_state(session_id, {
                        "pending_action": {
                            "tool": "new_card_application",
                            "step": "brand_selection",
                            "card_type": selected_type,
                            "options": brand_result["options"],
                            "process_type": "new_card_application"
                        }
                    })
                    return response_data
                    
        elif current_step == 'brand_selection':
            selected_brand = None
            if any(phrase in message_lower for phrase in ['visa', 'option 1']):
                selected_brand = 'visa'
            elif any(phrase in message_lower for phrase in ['mastercard', 'option 2']):
                selected_brand = 'mastercard'
            elif any(phrase in message_lower for phrase in ['rupay', 'option 3']):
                selected_brand = 'rupay'
            
            if selected_brand:
                # Apply for the card and create actual card
                card_type = pending_action.get('card_type')
                from tools.banking_api import apply_new_card
                application_result = apply_new_card(user_id, card_type, selected_brand)
                
                response_text = application_result.get('message', 'Card application processed successfully!')
                
                # Add context switch message if needed
                response_text += f"\n\n{await self._get_context_switch_message(session_id)}"
                
                response_data = ChatResponse(response=response_text)
                
                # Clear pending action
                current_state = self.state_manager.get_state(session_id) or {}
                if 'pending_action' in current_state:
                    del current_state['pending_action']
                self.state_manager.update_state(session_id, current_state)
                
                self.context_manager.update_history(session_id, message, response_text)
                return response_data
        
        return ChatResponse(response="Please select a valid option.")

    async def _handle_account_details_query(self, user_id: str, session_id: str, message: str) -> ChatResponse:
        """Handle comprehensive account details query - shows everything"""
        
        try:
            await self._save_current_process_on_context_switch(session_id, 'account_details')
            
            from tools.banking_api import get_comprehensive_account_details
            account_result = get_comprehensive_account_details(user_id)
            
            if account_result.get('status') == 'success':
                response_text = account_result['message']
                
                # Add context switch message if needed
                response_text += f"\n\n{await self._get_context_switch_message(session_id)}"
                
                response_data = ChatResponse(response=response_text)
                self.context_manager.update_history(session_id, message, response_text)
                return response_data
            
            return ChatResponse(response="Unable to retrieve your account details. Please try again.")
            
        except Exception as e:
            print(f"Account Details Error: {str(e)}")
            return ChatResponse(response="I'm having trouble accessing your account information right now. Please try again.")

    async def _handle_balance_query(self, user_id: str, session_id: str, message: str) -> ChatResponse:
        """Handle balance queries with context switching support"""
        
        # Check if we need to save current process before switching
        await self._save_current_process_on_context_switch(session_id, 'balance')
        
        from tools.banking_api import get_account_balance
        balance_result = get_account_balance(user_id)
        
        if balance_result.get('status') == 'success':
            response_text = f"""Hi {balance_result['account_holder']}! Here's your account information:

💰 **Current Balance**: ${balance_result['current_balance']:,.2f}
💳 **Available Balance**: ${balance_result['available_balance']:,.2f}
⏳ **Pending Transactions**: ${balance_result['pending_transactions']:,.2f}

📊 **Account Details**:
• Account Type: {balance_result['account_type']}
• Account Number: {balance_result['account_number']}
• Last Updated: {balance_result['last_updated']}

💳 **Credit Cards Summary**:
• Total Credit Limit: ${balance_result['credit_cards_summary']['total_limit']:,.2f}
• Available Credit: ${balance_result['credit_cards_summary']['total_available']:,.2f}
• Credit Utilization: {balance_result['credit_cards_summary']['utilization_rate']}

{await self._get_context_switch_message(session_id)}"""
            
            response_data = ChatResponse(response=response_text)
            self.context_manager.update_history(session_id, message, response_text)
            return response_data
        
        return ChatResponse(response="Unable to retrieve balance information. Please try again.")

    async def _handle_transaction_query(self, user_id: str, session_id: str, message: str) -> ChatResponse:
        """Handle transaction queries with context switching support"""
        
        await self._save_current_process_on_context_switch(session_id, 'transactions')
        
        from tools.banking_api import get_mini_statement
        statement_result = get_mini_statement(user_id)
        
        if statement_result.get('status') == 'success':
            transactions_text = "\n".join([
                f"• {t['date']} - {t['description']}: ${abs(t['amount']):,.2f} ({'Credit' if t['amount'] > 0 else 'Debit'})"
                for t in statement_result['transactions'][:5]
            ])
            
            response_text = f"""Hi {statement_result['account_holder']}! Here are your recent transactions:

📋 **Recent Transactions:**
{transactions_text}

📊 **Summary** ({statement_result['statement_period']}):
• Total Transactions: {statement_result['summary']['total_transactions']}
• Total Debits: ${statement_result['summary']['total_debits']:,.2f}
• Total Credits: ${statement_result['summary']['total_credits']:,.2f}
• Largest Transaction: ${statement_result['summary']['largest_transaction']:,.2f}

💰 **Current Balance**: ${statement_result['current_balance']:,.2f}

{await self._get_context_switch_message(session_id)}"""
            
            response_data = ChatResponse(response=response_text)
            self.context_manager.update_history(session_id, message, response_text)
            return response_data
        
        return ChatResponse(response="Unable to retrieve transaction information. Please try again.")
    async def _cleanup_completed_processes(self, session_id: str):
        """Clean up completed processes from state"""
        
        try:
            current_state = self.state_manager.get_state(session_id) or {}
            
            # Clean up completed multi-step processes
            multi_step = current_state.get('multi_step_process', {})
            if multi_step.get('process_complete') or multi_step.get('status') == 'complete':
                del current_state['multi_step_process']
            
            # Clean up old pending actions
            pending_action = current_state.get('pending_action', {})
            if pending_action.get('completed'):
                del current_state['pending_action']
            
            # Clean up old context switches
            if current_state.get('context_switched'):
                current_state['context_switched'] = False
            
            # Update the cleaned state
            self.state_manager.update_state(session_id, current_state)
            
        except Exception as e:
            print(f"State cleanup error: {str(e)}")
    async def _handle_card_management_query(self, user_id: str, session_id: str, message: str) -> ChatResponse:
        """Handle card management queries - shows menu of actions"""
        
        try:
            # Clean up any residual state first
            current_state = self.state_manager.get_state(session_id) or {}
            
            # Clear any completed processes
            if current_state.get('multi_step_process', {}).get('process_complete'):
                del current_state['multi_step_process']
                self.state_manager.update_state(session_id, current_state)
            
            await self._save_current_process_on_context_switch(session_id, 'card_management')
            
            from tools.banking_api import card_management
            management_result = card_management(user_id)
            
            if management_result.get("requires_selection"):
                response_data = ChatResponse(
                    response=management_result["message"],
                    requires_selection=True,
                    options=management_result["options"]
                )
                
                # Clear any existing pending actions first
                current_state = self.state_manager.get_state(session_id) or {}
                
                # Save new pending action state
                current_state["pending_action"] = {
                    "tool": "card_management",
                    "args": {},
                    "options": management_result["options"],
                    "process_type": "card_management"
                }
                
                self.state_manager.update_state(session_id, current_state)
                return response_data
            
            return ChatResponse(response="Unable to access card management options. Please try again.")
            
        except Exception as e:
            print(f"Card Management Error: {str(e)}")  # For debugging
            
            # Fallback response
            return ChatResponse(
                response="I'm having trouble accessing your card management options right now. Let me help you directly - would you like to:\n\n1. Block a card\n2. Apply for a new card\n3. Modify credit limits\n\nPlease tell me which option you'd prefer."
            )

    async def _handle_direct_card_blocking(self, user_id: str, session_id: str, message: str) -> ChatResponse:
        """Handle direct card blocking queries - shows list of cards to block"""
        
        try:
            await self._save_current_process_on_context_switch(session_id, 'card_blocking')
            
            from tools.banking_api import get_user_cards
            cards_result = get_user_cards(user_id)
            
            if isinstance(cards_result, dict) and cards_result.get("requires_selection"):
                # Modify the message to be specific about blocking
                blocking_message = "Here are your cards. Please select which card you'd like to block:"
                
                response_data = ChatResponse(
                    response=blocking_message,
                    requires_selection=True,
                    options=cards_result["options"]
                )
                
                # Save pending action state for card blocking
                self.state_manager.update_state(session_id, {
                    "pending_action": {
                        "tool": "block_card",
                        "args": {},
                        "options": cards_result["options"],
                        "process_type": "card_blocking"
                    }
                })
                return response_data
            
            return ChatResponse(response="Unable to retrieve your cards. Please try again.")
            
        except Exception as e:
            print(f"Card Blocking Error: {str(e)}")
            return ChatResponse(response="I'm having trouble accessing your cards right now. Please try again or contact support.")

    async def _handle_card_list_query(self, user_id: str, session_id: str, message: str) -> ChatResponse:
        """Handle general card list queries - shows cards for general viewing"""
        
        try:
            await self._save_current_process_on_context_switch(session_id, 'cards')
            
            from tools.banking_api import get_user_cards_display
            cards_result = get_user_cards_display(user_id)
            
            if cards_result.get('status') == 'success':
                cards = cards_result['cards']
                
                cards_text = "\n".join([
                    f"• {card['type'].title()} Card ({card['brand']}) ending in {card['last_four']} - Status: {card['status']}"
                    for card in cards
                ])
                
                response_text = f"""Here are all your cards:

    💳 **Your Cards:**
    {cards_text}

    📊 **Summary:**
    • Total Cards: {cards_result['total_cards']}
    • Active Cards: {cards_result['active_cards']}

    Would you like to perform any actions with your cards? You can:
    • Block a card
    • Apply for a new card  
    • Modify credit limits

    {await self._get_context_switch_message(session_id)}"""
                
                response_data = ChatResponse(response=response_text)
                self.context_manager.update_history(session_id, message, response_text)
                return response_data
            
            return ChatResponse(response="Unable to retrieve your cards. Please try again.")
            
        except Exception as e:
            print(f"Card List Error: {str(e)}")
            return ChatResponse(response="I'm having trouble accessing your cards right now. Please try again.")

    async def _handle_card_query(self, user_id: str, session_id: str, message: str) -> ChatResponse:
        """Handle card management queries with enhanced error handling"""
        
        try:
            # Clean up any residual state first
            current_state = self.state_manager.get_state(session_id) or {}
            
            # Clear any completed processes
            if current_state.get('multi_step_process', {}).get('process_complete'):
                del current_state['multi_step_process']
                self.state_manager.update_state(session_id, current_state)
            
            await self._save_current_process_on_context_switch(session_id, 'card_management')
            
            from tools.banking_api import card_management
            management_result = card_management(user_id)
            
            if management_result.get("requires_selection"):
                response_data = ChatResponse(
                    response=management_result["message"],
                    requires_selection=True,
                    options=management_result["options"]
                )
                
                # Clear any existing pending actions first
                current_state = self.state_manager.get_state(session_id) or {}
                
                # Save new pending action state
                current_state["pending_action"] = {
                    "tool": "card_management",
                    "args": {},
                    "options": management_result["options"],
                    "process_type": "card_management"
                }
                
                self.state_manager.update_state(session_id, current_state)
                return response_data
            
            return ChatResponse(response="Unable to access card management options. Please try again.")
            
        except Exception as e:
            print(f"Card Management Error: {str(e)}")  # For debugging
            
            # Fallback response
            return ChatResponse(
                response="I'm having trouble accessing your card management options right now. Let me help you directly - would you like to:\n\n1. Block a card\n2. Apply for a new card\n3. Modify credit limits\n\nPlease tell me which option you'd prefer."
            )


    async def _handle_loan_process(self, user_id: str, session_id: str, message: str, loan_process: Dict) -> ChatResponse:
        """Handle loan application process with enhanced context switching support"""
        
        message_lower = message.lower()
        current_state = self.state_manager.get_state(session_id) or {}
        
        # Check if user wants to resume a suspended loan application
        is_resume_request = any(phrase in message_lower for phrase in [
            'apply new loan', 'new loan', 'apply loan', 'continue loan', 'resume loan'
        ])
        
        # Check for suspended loan processes
        suspended_processes = current_state.get('suspended_processes', [])
        suspended_loan = None
        
        for process in reversed(suspended_processes):  # Check most recent first
            if process.get('multi_step_process', {}).get('type') == 'loan_application':
                suspended_loan = process
                break
        
        # If there's a suspended loan process and user wants to apply for loan
        if suspended_loan and is_resume_request and not loan_process.get('type'):
            suspended_loan_data = suspended_loan['multi_step_process']
            completion = suspended_loan.get('completion_percentage', 0)
            
            # Ask user if they want to resume or start fresh
            if completion > 0:
                collected_data = suspended_loan_data.get('collected_data', {})
                current_step = suspended_loan_data.get('current_step')
                
                resume_message = f"I notice you were in the middle of a loan application:\n\n"
                
                if collected_data.get('amount'):
                    resume_message += f"• Amount: ${collected_data['amount']:,.2f}\n"
                if collected_data.get('purpose'):
                    resume_message += f"• Purpose: {collected_data['purpose']}\n"
                
                resume_message += f"\n**Progress**: {completion:.0f}% complete\n\n"
                resume_message += "Would you like to:\n1. **Continue** where you left off\n2. **Start** a completely new loan application\n\nPlease say 'continue' or 'start new'."
                
                # Set up a special state for user choice
                current_state['loan_resume_choice'] = {
                    'suspended_process': suspended_loan_data,
                    'message_shown': True
                }
                self.state_manager.update_state(session_id, current_state)
                
                response_data = ChatResponse(response=resume_message)
                self.context_manager.update_history(session_id, message, resume_message)
                return response_data
        
        # Handle resume choice
        if current_state.get('loan_resume_choice', {}).get('message_shown'):
            if 'continue' in message_lower:
                # Resume the suspended process
                suspended_process = current_state['loan_resume_choice']['suspended_process']
                
                # Restore the multi-step process
                current_state['multi_step_process'] = suspended_process
                
                # Clear the resume choice state
                del current_state['loan_resume_choice']
                
                # Remove the suspended process since we're resuming it
                suspended_processes = current_state.get('suspended_processes', [])
                current_state['suspended_processes'] = [
                    p for p in suspended_processes 
                    if p.get('multi_step_process', {}).get('type') != 'loan_application'
                ]
                
                self.state_manager.update_state(session_id, current_state)
                
                # Continue with the next step
                collected_data = suspended_process.get('collected_data', {})
                current_step = suspended_process.get('current_step')
                
                if current_step == 'purpose':
                    response_text = f"Great! Continuing with your loan application for ${collected_data['amount']:,.2f}.\n\n**Step 2: Loan Purpose**\nWhat will you use this loan for? (e.g., Home Improvement, Debt Consolidation, Auto Purchase, Medical Expenses, etc.)"
                elif current_step == 'income':
                    response_text = f"Perfect! Loan amount: ${collected_data['amount']:,.2f} for {collected_data['purpose']}.\n\n**Step 3: Annual Income**\nWhat is your annual gross income? This helps us determine your loan eligibility and interest rate."
                else:
                    response_text = "Let's continue with your loan application. What information do you need to provide next?"
                
                response_data = ChatResponse(response=response_text)
                self.context_manager.update_history(session_id, message, response_text)
                return response_data
                
            elif any(phrase in message_lower for phrase in ['start new', 'new', 'fresh', 'different']):
                # Start fresh - clear the suspended process
                del current_state['loan_resume_choice']
                
                # Remove suspended loan processes
                suspended_processes = current_state.get('suspended_processes', [])
                current_state['suspended_processes'] = [
                    p for p in suspended_processes 
                    if p.get('multi_step_process', {}).get('type') != 'loan_application'
                ]
                
                self.state_manager.update_state(session_id, current_state)
                
                # Start new loan application
                from tools.banking_api import apply_for_loan
                loan_result = apply_for_loan(user_id, force_new=True)
                
                if loan_result.get('status') in ['info', 'success']:
                    response_text = loan_result['message']
                    
                    # Update state for new loan process
                    if loan_result.get('requires_continuation'):
                        current_state['multi_step_process'] = {
                            'type': loan_result.get('process_type'),
                            'current_step': loan_result.get('current_step'),
                            'collected_data': loan_result.get('collected_data', {}),
                            'next_step': loan_result.get('next_step'),
                            'is_new_application': True
                        }
                        self.state_manager.update_state(session_id, current_state)
                    
                    response_data = ChatResponse(response=response_text)
                    self.context_manager.update_history(session_id, message, response_text)
                    return response_data
            else:
                # Invalid choice, ask again
                response_text = "Please choose either:\n• **'continue'** - to resume your previous loan application\n• **'start new'** - to begin a fresh loan application"
                response_data = ChatResponse(response=response_text)
                return response_data
        
        # Check if user explicitly wants a new loan application (when no suspended process dialogue is active)
        is_new_loan_request = any(phrase in message_lower for phrase in [
            'new loan', 'apply for new loan', 'another loan', 'different loan', 
            'start over', 'fresh loan', 'apply loan'
        ])
        
        # If it's a new loan request and there's an active process, clear it and start fresh
        if is_new_loan_request and loan_process.get('type') == 'loan_application' and not current_state.get('loan_resume_choice'):
            # Clear the current loan process
            if 'multi_step_process' in current_state:
                del current_state['multi_step_process']
            self.state_manager.update_state(session_id, current_state)
            
            # Start a new loan application with force_new=True
            from tools.banking_api import apply_for_loan
            loan_result = apply_for_loan(user_id, force_new=True)
            
            if loan_result.get('status') in ['info', 'success']:
                response_text = loan_result['message']
                
                # Update state for new loan process
                if loan_result.get('requires_continuation'):
                    current_state['multi_step_process'] = {
                        'type': loan_result.get('process_type'),
                        'current_step': loan_result.get('current_step'),
                        'collected_data': loan_result.get('collected_data', {}),
                        'next_step': loan_result.get('next_step'),
                        'is_new_application': True
                    }
                    self.state_manager.update_state(session_id, current_state)
                
                response_data = ChatResponse(response=response_text)
                self.context_manager.update_history(session_id, message, response_text)
                return response_data
        
        # Continue with existing loan process logic...
        # [Rest of your existing _handle_loan_process method remains the same]
        
        # Extract information from current message
        amount_match = re.search(r'\$?([0-9,]+(?:\.[0-9]{2})?)', message)
        extracted_amount = None
        if amount_match:
            try:
                extracted_amount = float(amount_match.group(1).replace(',', ''))
            except:
                pass
        
        # Extract purpose keywords
        purpose_keywords = {
            'home': 'Home Improvement',
            'house': 'Home Improvement', 
            'renovation': 'Home Renovation',
            'car': 'Auto Purchase',
            'vehicle': 'Auto Purchase',
            'auto': 'Auto Purchase',
            'debt': 'Debt Consolidation',
            'consolidation': 'Debt Consolidation',
            'medical': 'Medical Expenses',
            'health': 'Medical Expenses',
            'education': 'Education',
            'school': 'Education',
            'college': 'Education',
            'business': 'Business',
            'wedding': 'Wedding',
            'marriage': 'Wedding',
            'vacation': 'Vacation',
            'travel': 'Vacation',
            'personal': 'Personal',
            'emergency': 'Emergency Fund'
        }
        
        extracted_purpose = None
        for keyword, purpose in purpose_keywords.items():
            if keyword in message_lower:
                extracted_purpose = purpose
                break
        
        # Extract income from message
        income_match = re.search(r'(?:income|earn|salary|make).*?\$?([0-9,]+(?:\.[0-9]{2})?)', message_lower)
        extracted_income = None
        if income_match:
            try:
                extracted_income = float(income_match.group(1).replace(',', ''))
            except:
                pass
        
        # If we're in an active loan process, also check for simple numerical responses
        is_numerical_response = re.match(r'^\$?[0-9,]+(?:\.[0-9]{2})?$', message.strip())
        if loan_process.get('type') == 'loan_application' and is_numerical_response and not extracted_income:
            current_step = loan_process.get('current_step')
            if current_step == 'amount':
                extracted_amount = float(message.strip().replace('$', '').replace(',', ''))
            elif current_step == 'income':
                extracted_income = float(message.strip().replace('$', '').replace(',', ''))
        
        # Get collected data from ongoing process
        collected_data = loan_process.get('collected_data', {})
        
        # Determine what information we have
        current_amount = extracted_amount or collected_data.get('amount')
        current_purpose = extracted_purpose or collected_data.get('purpose')
        current_income = extracted_income or collected_data.get('income')
        
        # Call the loan application function with database integration
        from tools.banking_api import apply_for_loan
        loan_result = apply_for_loan(user_id, current_amount, current_purpose, current_income)
        
        if loan_result.get('status') in ['info', 'success']:
            response_text = loan_result['message']
            
            # Update state if this is a multi-step process
            current_state = self.state_manager.get_state(session_id) or {}
            if loan_result.get('requires_continuation'):
                current_state['multi_step_process'] = {
                    'type': loan_result.get('process_type'),
                    'current_step': loan_result.get('current_step'),
                    'collected_data': loan_result.get('collected_data', {}),
                    'next_step': loan_result.get('next_step')
                }
                self.state_manager.update_state(session_id, current_state)
            elif loan_result.get('process_complete'):
                # Clear the multi-step process state when application is complete
                if 'multi_step_process' in current_state:
                    del current_state['multi_step_process']
                
                # Add success flag to indicate completion
                current_state['last_completed_action'] = {
                    'type': 'loan_application',
                    'application_id': loan_result.get('application', {}).get('application_id'),
                    'timestamp': datetime.now().isoformat()
                }
                
                self.state_manager.update_state(session_id, current_state)
                
                # Add context switch message for completed loan application
                response_text += f"\n\n💡 **Note**: Your loan application has been successfully submitted and saved to our database. Is there anything else I can help you with today?"
            
            response_data = ChatResponse(response=response_text)
            self.context_manager.update_history(session_id, message, response_text)
            return response_data
        else:
            # Handle error cases with helpful messages
            error_message = loan_result.get('message', 'Unable to process loan application.')
            
            # Provide specific guidance based on current step
            current_step = loan_process.get('current_step')
            if current_step == 'amount':
                error_message += "\n\nPlease provide a valid loan amount between $1,000 and $50,000. For example: '$15,000' or '15000'"
            elif current_step == 'purpose':
                error_message += "\n\nPlease specify what you'll use the loan for. Examples: 'home renovation', 'debt consolidation', 'car purchase', 'medical expenses'"
            elif current_step == 'income':
                error_message += "\n\nPlease provide your annual gross income. For example: '$75,000' or 'I make 75000 annually'"
            
            response_data = ChatResponse(response=error_message)
            self.context_manager.update_history(session_id, message, error_message)
            return response_data



    async def _handle_loan_status_query(self, user_id: str, session_id: str, message: str) -> ChatResponse:
        """Handle loan status queries"""
        
        from tools.banking_api import get_loan_status
        loan_result = get_loan_status(user_id)
        
        if loan_result.get('status') == 'success':
            if loan_result.get('applications'):
                apps_text = "\n".join([
                    f"• {app['application_id']}: ${app['amount']:,.2f} for {app['purpose']} - Status: {app['status']}"
                    for app in loan_result['applications']
                ])
                response_text = f"""Hello! Here are your loan applications:

📋 **Your Loan Applications:**
{apps_text}

Would you like to apply for a new loan or check the status of an existing application?"""
            else:
                response_text = loan_result['message']
            
            response_data = ChatResponse(response=response_text)
            self.context_manager.update_history(session_id, message, response_text)
            return response_data
        
        return ChatResponse(response="Unable to retrieve loan information. Please try again.")

    async def _handle_pending_actions(self, user_id: str, session_id: str, message: str, pending_action: Dict) -> ChatResponse:
        """Handle pending actions (selections, confirmations, etc.)"""
        
        action_type = pending_action.get('process_type')
        
        if action_type == 'card_management':
            return await self._handle_card_management_selection(user_id, session_id, message, pending_action)
        elif action_type == 'new_card_application':
            return await self._handle_new_card_application_selection(user_id, session_id, message, pending_action)
        elif action_type == 'card_application':  # Legacy support
            return await self._handle_card_application_selection(user_id, session_id, message, pending_action)
        elif action_type == 'limit_modification':
            return await self._handle_limit_modification_selection(user_id, session_id, message, pending_action)
        elif action_type == 'card_blocking':
            return await self._handle_card_blocking_selection(user_id, session_id, message, pending_action)
        else:
            # Fallback for any unrecognized action types
            return await self._handle_card_blocking_selection(user_id, session_id, message, pending_action)



    async def _handle_card_management_selection(self, user_id: str, session_id: str, message: str, pending_action: Dict) -> ChatResponse:
        """Handle card management option selection"""
        
        message_lower = message.lower()
        selected_option = None
        
        # Check for selection keywords
        if any(phrase in message_lower for phrase in ['block_card', 'block card', 'option 1']):
            selected_option = 'block_card'
        elif any(phrase in message_lower for phrase in ['apply_new_card', 'new card', 'apply', 'option 2']):
            selected_option = 'apply_new_card'
        elif any(phrase in message_lower for phrase in ['modify_limit', 'limit', 'credit limit', 'option 3']):
            selected_option = 'modify_limit'
        
        if selected_option == 'block_card':
            # Show user cards for blocking
            from tools.banking_api import get_user_cards
            cards_result = get_user_cards(user_id)
            
            if cards_result.get("requires_selection"):
                response_data = ChatResponse(
                    response=cards_result["message"],
                    requires_selection=True,
                    options=cards_result["options"]
                )
                
                # Update pending action
                self.state_manager.update_state(session_id, {
                    "pending_action": {
                        "tool": "block_card",
                        "args": {},
                        "options": cards_result["options"]
                    }
                })
                return response_data
                
        elif selected_option == 'apply_new_card':
            # Show card type options
            from tools.banking_api import new_card_type
            type_result = new_card_type(user_id)
            
            if type_result.get("requires_selection"):
                response_data = ChatResponse(
                    response=type_result["message"],
                    requires_selection=True,
                    options=type_result["options"]
                )
                
                # Update pending action
                self.state_manager.update_state(session_id, {
                    "pending_action": {
                        "tool": "card_application",
                        "step": "type_selection",
                        "options": type_result["options"],
                        "process_type": "card_application"
                    }
                })
                return response_data
                
        elif selected_option == 'modify_limit':
            # Show credit cards for limit modification
            from tools.banking_api import limit_modification_cards
            limit_result = limit_modification_cards(user_id)
            
            if limit_result.get("requires_selection"):
                response_data = ChatResponse(
                    response=limit_result["message"],
                    requires_selection=True,
                    options=limit_result["options"]
                )
                
                # Update pending action
                self.state_manager.update_state(session_id, {
                    "pending_action": {
                        "tool": "limit_modification",
                        "step": "card_selection",
                        "options": limit_result["options"],
                        "process_type": "limit_modification"
                    }
                })
                return response_data
            else:
                response_text = limit_result.get('message', 'No credit cards available for limit modification.')
                response_data = ChatResponse(response=response_text)
                # Clear pending action
                current_state = self.state_manager.get_state(session_id) or {}
                if 'pending_action' in current_state:
                    del current_state['pending_action']
                self.state_manager.update_state(session_id, current_state)
                return response_data
        
        return ChatResponse(response="Please select a valid option from the menu.")
    async def _handle_loan_listing_query(self, user_id: str, session_id: str, message: str) -> ChatResponse:
        """Handle loan listing queries - shows all user's loan applications"""
        
        try:
            await self._save_current_process_on_context_switch(session_id, 'loan_listing')
            
            from tools.banking_api import get_loan_status
            loan_result = get_loan_status(user_id)
            
            if loan_result.get('status') == 'success':
                if loan_result.get('applications'):
                    # Format the loans in a detailed manner
                    apps_text = []
                    for app in loan_result['applications']:
                        status_display = app['status'].title()
                        app_line = f"• **{app['application_id']}**: ${app['amount']:,.2f} for {app['purpose']}"
                        app_line += f"\n  - Status: {status_display}"
                        
                        if app.get('interest_rate'):
                            app_line += f"\n  - Interest Rate: {app['interest_rate']}%"
                        
                        if app.get('monthly_payment'):
                            app_line += f"\n  - Monthly Payment: ${app['monthly_payment']:,.2f}"
                        elif app.get('estimated_monthly_payment'):
                            app_line += f"\n  - Estimated Monthly Payment: ${app['estimated_monthly_payment']:,.2f}"
                        
                        if app.get('applied_date') or app.get('created_date'):
                            app_date = app.get('applied_date') or app.get('created_date')
                            app_line += f"\n  - Applied Date: {app_date}"
                        
                        if app.get('approved_date'):
                            app_line += f"\n  - Approved Date: {app['approved_date']}"
                        
                        apps_text.append(app_line)
                    
                    formatted_apps = "\n\n".join(apps_text)
                    
                    response_text = f"""Here are all your loan applications:

    {formatted_apps}

    📊 **Summary**: You have {len(loan_result['applications'])} loan application(s) on file.

    Would you like to:
    • Apply for a new loan
    • Check the status of a specific application
    • Get more details about any loan

    {await self._get_context_switch_message(session_id)}"""
                else:
                    response_text = loan_result['message']
                
                response_data = ChatResponse(response=response_text)
                self.context_manager.update_history(session_id, message, response_text)
                return response_data
            
            return ChatResponse(response="Unable to retrieve your loan applications. Please try again.")
            
        except Exception as e:
            print(f"Loan Listing Error: {str(e)}")
            return ChatResponse(response="I'm having trouble accessing your loan information right now. Please try again.")

    async def _handle_card_application_selection(self, user_id: str, session_id: str, message: str, pending_action: Dict) -> ChatResponse:
        """Handle card application selections"""
        
        current_step = pending_action.get('step')
        message_lower = message.lower()
        
        if current_step == 'type_selection':
            selected_type = None
            if any(phrase in message_lower for phrase in ['credit_card', 'credit', 'option 1']):
                selected_type = 'credit_card'
            elif any(phrase in message_lower for phrase in ['debit_card', 'debit', 'option 2']):
                selected_type = 'debit_card'
            
            if selected_type:
                # Show brand options
                from tools.banking_api import card_brand_selection
                brand_result = card_brand_selection(user_id, selected_type)
                
                if brand_result.get("requires_selection"):
                    response_data = ChatResponse(
                        response=brand_result["message"],
                        requires_selection=True,
                        options=brand_result["options"]
                    )
                    
                    # Update pending action
                    self.state_manager.update_state(session_id, {
                        "pending_action": {
                            "tool": "card_application",
                            "step": "brand_selection",
                            "card_type": selected_type,
                            "options": brand_result["options"],
                            "process_type": "card_application"
                        }
                    })
                    return response_data
                    
        elif current_step == 'brand_selection':
            selected_brand = None
            if any(phrase in message_lower for phrase in ['visa', 'option 1']):
                selected_brand = 'visa'
            elif any(phrase in message_lower for phrase in ['mastercard', 'option 2']):
                selected_brand = 'mastercard'
            elif any(phrase in message_lower for phrase in ['rupay', 'option 3']):
                selected_brand = 'rupay'
            
            if selected_brand:
                # Apply for the card
                card_type = pending_action.get('card_type')
                from tools.banking_api import apply_new_card
                application_result = apply_new_card(user_id, card_type, selected_brand)
                
                response_text = application_result.get('message', 'Card application processed successfully!')
                
                # Add context switch message if needed
                response_text += f"\n\n{await self._get_context_switch_message(session_id)}"
                
                response_data = ChatResponse(response=response_text)
                
                # Clear pending action
                current_state = self.state_manager.get_state(session_id) or {}
                if 'pending_action' in current_state:
                    del current_state['pending_action']
                self.state_manager.update_state(session_id, current_state)
                
                self.context_manager.update_history(session_id, message, response_text)
                return response_data
        
        return ChatResponse(response="Please select a valid option.")

    async def _handle_limit_modification_selection(self, user_id: str, session_id: str, message: str, pending_action: Dict) -> ChatResponse:
        """Handle credit limit modification selections"""
        
        current_step = pending_action.get('step')
        
        if current_step == 'card_selection':
            # Extract card ID from selection
            card_match = re.search(r'card_(\d+)', message.lower())
            if card_match:
                card_id = f"card_{card_match.group(1).zfill(3)}"
                
                # Get current limit info
                from tools.banking_api import get_limit_info
                limit_info = get_limit_info(user_id, card_id)
                
                if limit_info.get('requires_continuation'):
                    response_text = limit_info.get('message')
                    
                    # Update state for limit modification - IMPORTANT: Use 'multi_step_process' not pending_action
                    current_state = self.state_manager.get_state(session_id) or {}
                    current_state['multi_step_process'] = {
                        'type': limit_info.get('process_type'),
                        'current_step': limit_info.get('current_step'),
                        'collected_data': limit_info.get('collected_data', {}),
                        'card_id': card_id
                    }
                    
                    # Clear pending action since we're moving to multi-step process
                    if 'pending_action' in current_state:
                        del current_state['pending_action']
                    
                    self.state_manager.update_state(session_id, current_state)
                    
                    response_data = ChatResponse(response=response_text)
                    self.context_manager.update_history(session_id, message, response_text)
                    return response_data
        
        return ChatResponse(response="Please select a valid card option.")


    async def _handle_multi_step_processes(self, user_id: str, session_id: str, message: str, current_state: Dict) -> ChatResponse:
        """Handle ongoing multi-step processes"""
        
        multi_step = current_state.get('multi_step_process', {})
        process_type = multi_step.get('type')
        
        if process_type == 'limit_modification':
            return await self._handle_limit_modification_process(user_id, session_id, message, multi_step)
        
        # Handle other multi-step processes here
        return ChatResponse(response="Process not recognized. Please try again.")

    async def _handle_limit_modification_process(self, user_id: str, session_id: str, message: str, multi_step: Dict) -> ChatResponse:
        """Handle limit modification multi-step process"""
        
        current_step = multi_step.get('current_step')
        
        if current_step == 'new_limit':
            # Extract new limit amount from user input
            amount_match = re.search(r'\$?([0-9,]+(?:\.[0-9]{2})?)', message)
            if amount_match:
                try:
                    new_limit = float(amount_match.group(1).replace(',', ''))
                    card_id = multi_step.get('collected_data', {}).get('card_id')
                    
                    if not card_id:
                        return ChatResponse(response="Error: Card information not found. Please start the process again.")
                    
                    # Modify the credit limit
                    from tools.banking_api import modify_credit_limit
                    modify_result = modify_credit_limit(user_id, card_id, new_limit)
                    
                    if modify_result.get('status') == 'success':
                        response_text = modify_result.get('message', 'Credit limit modified successfully!')
                        
                        # Add context switch message
                        response_text += f"\n\n{await self._get_context_switch_message(session_id)}"
                        
                        # Clear multi-step process
                        current_state = self.state_manager.get_state(session_id) or {}
                        if 'multi_step_process' in current_state:
                            del current_state['multi_step_process']
                        self.state_manager.update_state(session_id, current_state)
                        
                        response_data = ChatResponse(response=response_text)
                        self.context_manager.update_history(session_id, message, response_text)
                        return response_data
                    else:
                        error_message = modify_result.get('message', 'Failed to modify credit limit.')
                        response_data = ChatResponse(response=error_message)
                        return response_data
                        
                except ValueError:
                    return ChatResponse(response="Please enter a valid numeric amount for the credit limit. For example: 20000 or $20,000")
            else:
                return ChatResponse(response="Please specify the new credit limit amount. For example: 20000 or $20,000")
        
        return ChatResponse(response="Unable to process limit modification. Please try again.")


    async def _save_current_process_on_context_switch(self, session_id: str, new_context: str):
        """Enhanced save current process when context switches occur"""
        
        current_state = self.state_manager.get_state(session_id) or {}
        
        # Check if there's an active multi-step process
        active_process = current_state.get('multi_step_process')
        
        if active_process:
            if 'suspended_processes' not in current_state:
                current_state['suspended_processes'] = []
            
            # Save the current process with more details
            suspended_process = {
                'context': new_context,
                'timestamp': datetime.now().isoformat(),
                'multi_step_process': active_process.copy(),
                'original_context': active_process.get('type'),
                'completion_percentage': self._calculate_process_completion(active_process)
            }
            
            current_state['suspended_processes'].append(suspended_process)
            current_state['context_switched'] = True
            current_state['last_context_switch'] = new_context
            
            self.state_manager.update_state(session_id, current_state)

    def _calculate_process_completion(self, process: Dict) -> float:
        """Calculate how much of a multi-step process is complete"""
        
        if process.get('type') == 'loan_application':
            collected_data = process.get('collected_data', {})
            total_steps = 3  # amount, purpose, income
            completed_steps = len([v for v in collected_data.values() if v is not None])
            return (completed_steps / total_steps) * 100
        
        return 0.0


    async def _get_context_switch_message(self, session_id: str) -> str:
        """Enhanced context switch message with loan-specific guidance"""
        
        current_state = self.state_manager.get_state(session_id) or {}
        suspended_processes = current_state.get('suspended_processes', [])
        
        if suspended_processes:
            # Check for suspended loan application
            suspended_loan = None
            for process in reversed(suspended_processes):
                if process.get('multi_step_process', {}).get('type') == 'loan_application':
                    suspended_loan = process
                    break
            
            if suspended_loan:
                completion = suspended_loan.get('completion_percentage', 0)
                if completion > 0:
                    return f"💡 **Note**: You have a loan application {completion:.0f}% complete. Say 'continue loan' to resume or 'new loan' to start fresh."
            
            latest_process = suspended_processes[-1]
            multi_step = latest_process.get('multi_step_process')
            
            if multi_step:
                process_type = multi_step.get('type')
                if process_type == 'loan_application':
                    return "💡 **Note**: You have a loan application in progress. Would you like to continue with it?"
                else:
                    return "💡 **Note**: You have a pending action. Would you like to complete it?"
        
        return ""


    async def _handle_llm_failure(self, session_id: str, message: str, current_state: Dict, error: Exception) -> ChatResponse:
        """Handle LLM failures with context-aware fallbacks"""
        
        error_msg = str(error)
        print(f"LLM Error: {error_msg}")  # For debugging
        
        message_lower = message.lower()
        loan_process = current_state.get('multi_step_process', {})
        
        # Provide intelligent fallback based on message content and active processes
        if loan_process.get('type') == 'loan_application':
            current_step = loan_process.get('current_step', 'unknown')
            if current_step == 'amount':
                fallback_text = "I'm having trouble processing your loan amount. Could you please specify the loan amount you need? For example: '$15,000' or 'I need $15000'"
            elif current_step == 'purpose':
                fallback_text = "I need to know the purpose of your loan. What will you use this loan for? (e.g., home renovation, car purchase, debt consolidation)"
            elif current_step == 'income':
                fallback_text = "To complete your loan application, I need your annual income information. What is your yearly gross income?"
            else:
                fallback_text = "I'm having trouble with your loan application. Let me help you start over. What loan amount do you need?"
        elif "balance" in message_lower:
            fallback_text = "I'd be happy to help you check your account balance. Let me retrieve that information for you."
        elif "card" in message_lower:
            fallback_text = "I can help you with your card services. What would you like to do with your cards today?"
        elif "loan" in message_lower:
            fallback_text = "I'm here to assist with your loan inquiries. What specific information about loans can I help you with?"
        else:
            fallback_text = "I'm here to help with your banking needs. You can ask me about your account balance, cards, transactions, or loan applications. What would you like to know?"
        
        response_data = ChatResponse(response=fallback_text)
        self.context_manager.update_history(session_id, message, fallback_text)
        return response_data

    # [Rest of the methods remain the same as in the previous version]
    # Including: _analyze_context_switch, _extract_topics, _prepare_intelligent_prompt, 
    # _execute_tool_with_context, _handle_selection_process, _handle_multi_step_process,
    # _generate_contextual_response, _get_user_context, _get_user_profile, _update_conversation_context

    async def _analyze_context_switch(self, session_id: str, message: str):
        """Detect and handle context switches in conversation"""
        
        current_state = self.state_manager.get_state(session_id)
        if not current_state:
            return
        
        # Detect topic changes using keyword analysis
        current_topics = current_state.get('active_topics', [])
        new_topics = self._extract_topics(message)
        
        # Check for context switch
        if new_topics and not any(topic in current_topics for topic in new_topics):
            # Context switch detected
            current_state['context_switch'] = {
                'from_topics': current_topics,
                'to_topics': new_topics,
                'previous_task': current_state.get('current_task'),
                'switch_message': message
            }
            
            # Preserve previous task for potential resumption
            if current_state.get('current_task'):
                current_state['suspended_tasks'] = current_state.get('suspended_tasks', [])
                current_state['suspended_tasks'].append(current_state['current_task'])
            
            current_state['active_topics'] = new_topics
            self.state_manager.update_state(session_id, current_state)

    def _extract_topics(self, message: str) -> list:
        """Extract banking topics from user message"""
        
        topic_keywords = {
            'loan': ['loan', 'borrow', 'credit', 'mortgage', 'financing'],
            'card': ['card', 'debit', 'credit', 'block', 'lost', 'stolen'],
            'account': ['balance', 'statement', 'transaction', 'account', 'deposit'],
            'transfer': ['transfer', 'send', 'payment', 'wire'],
            'information': ['rate', 'fee', 'policy', 'information', 'help']
        }
        
        detected_topics = []
        message_lower = message.lower()
        
        for topic, keywords in topic_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                detected_topics.append(topic)
        
        return detected_topics

    async def _prepare_intelligent_prompt(self, user_id: str, session_id: str, message: str):
        """Prepare prompt with enhanced intelligence and context awareness"""
        
        # Get comprehensive context
        history = self.context_manager.get_conversation_history(session_id)
        current_state = self.state_manager.get_state(session_id)
        user_profile = await self._get_user_profile(user_id)
        
        # Build intelligent prompt with context awareness
        prompt_parts = []
        
        # Add conversation context
        if history:
            prompt_parts.append("RECENT CONVERSATION:")
            for turn in history[-5:]:  # Last 5 turns for context
                prompt_parts.append(f"User: {turn['user']}")
                prompt_parts.append(f"Assistant: {turn['assistant']}")
        
        # Add state context
        if current_state:
            prompt_parts.append(f"\nCURRENT CONTEXT:")
            if current_state.get('context_switch'):
                switch_info = current_state['context_switch']
                prompt_parts.append(f"Context Switch Detected: From {switch_info['from_topics']} to {switch_info['to_topics']}")
            
            if current_state.get('suspended_tasks'):
                prompt_parts.append(f"Suspended Tasks: {current_state['suspended_tasks']}")
            
            if current_state.get('current_task'):
                prompt_parts.append(f"Current Task: {current_state['current_task']}")
        
        # Add user profile context
        if user_profile:
            prompt_parts.append(f"\nUSER PROFILE:")
            prompt_parts.append(f"Account Type: {user_profile.get('account_type', 'Standard')}")
            prompt_parts.append(f"Preferred Communication: {user_profile.get('communication_style', 'Professional')}")
        
        # Add current message with intelligent analysis
        prompt_parts.append(f"\nCURRENT USER MESSAGE: {message}")
        
        # Add instructions for intelligent response
        prompt_parts.append(f"\nINSTRUCTIONS:")
        prompt_parts.append("1. Analyze the user's intent considering full conversation context")
        prompt_parts.append("2. Handle context switches gracefully - acknowledge topic changes")
        prompt_parts.append("3. For ambiguous requests, ask intelligent clarifying questions")
        prompt_parts.append("4. Use tools when real-time data or actions are needed")
        prompt_parts.append("5. Maintain awareness of suspended tasks and offer to resume them")
        prompt_parts.append("6. Provide personalized responses based on user profile")
        
        full_prompt = "\n".join(prompt_parts)
        
        # Get tool definitions
        from tools.definitions import TOOL_DEFINITIONS
        return full_prompt, TOOL_DEFINITIONS

    async def _execute_tool_with_context(self, user_id: str, session_id: str, tool_name: str, tool_args: dict):
        """Execute tools with full context awareness"""
        
        # Add session context to tool arguments
        tool_args['session_id'] = session_id
        
        # Execute tool
        result = self.tool_executor.execute(user_id, tool_name, **tool_args)
        
        # Update task tracking
        current_state = self.state_manager.get_state(session_id) or {}
        current_state['last_tool_used'] = tool_name
        current_state['last_tool_result'] = result
        self.state_manager.update_state(session_id, current_state)
        
        return result

    async def _handle_selection_process(self, session_id: str, tool_result: dict, tool_call):
        """Handle multi-option selection processes"""
        
        response_data = ChatResponse(
            response=tool_result["message"],
            requires_selection=True,
            options=tool_result["options"]
        )
        
        # Save selection state
        self.state_manager.update_state(session_id, {
            "pending_action": {
                "tool": tool_call.name,
                "args": tool_call.arguments,
                "options": tool_result["options"],
                "process_type": "selection"
            }
        })
        
        return response_data

    async def _handle_multi_step_processes(self, user_id: str, session_id: str, message: str, current_state: Dict) -> ChatResponse:
        """Handle ongoing multi-step processes"""
        
        multi_step = current_state.get('multi_step_process', {})
        process_type = multi_step.get('type')
        
        if process_type == 'limit_modification':
            return await self._handle_limit_modification_process(user_id, session_id, message, multi_step)
        elif process_type == 'loan_application':
            # Handle loan application multi-step process
            return await self._handle_loan_process(user_id, session_id, message, multi_step)
        
        # Handle other multi-step processes here
        return ChatResponse(response="Process not recognized. Please try again.")

    async def _generate_contextual_response(self, session_id: str, tool_name: str, tool_result: Any, 
                                          user_message: str, system_prompt: str):
        """Generate contextually aware final response"""
        
        # Build context-rich prompt for final response
        context_prompt = f"""
Based on the tool execution result, generate a helpful, personalized response.

Tool Used: {tool_name}
Tool Result: {json.dumps(tool_result, indent=2)}
User's Message: {user_message}

Consider:
- The user's conversation history and context
- Any suspended tasks that might be relevant
- The user's emotional state (urgency, excitement, concern)
- Opportunities to provide additional helpful information
- Natural conversation flow and transitions

Provide a response that feels natural, helpful, and contextually appropriate:
"""
        
        try:
            final_response = await get_llm_response(context_prompt, system_prompt=system_prompt)
            return final_response.text
        except Exception as e:
            # Fallback response generation
            if tool_name == "get_account_balance":
                return f"Your current account balance is ${tool_result.get('current_balance', 0):,.2f}. Is there anything else I can help you with?"
            elif tool_name == "get_mini_statement":
                return "I've retrieved your recent transactions. You can see them above. Let me know if you need any clarification!"
            else:
                return "I've completed your request. Is there anything else I can help you with today?"

    async def _get_user_context(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive user context"""
        
        # In a real implementation, this would fetch from user database
        return {
            'name': 'Valued Customer',
            'account_type': 'Premium',
            'communication_style': 'Professional',
            'recent_activity': 'Account inquiries'
        }

    async def _get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get user profile for personalization"""
        
        # Mock user profile - in production, fetch from database
        return {
            'account_type': 'Premium',
            'communication_style': 'Professional',
            'preferred_topics': ['loans', 'investments'],
            'interaction_history': []
        }

    async def _update_conversation_context(self, session_id: str, user_message: str, ai_response: str):
        """Update conversation context with enhanced tracking"""
        
        # Update standard conversation history
        self.context_manager.update_history(session_id, user_message, ai_response)
        
        # Update enhanced memory
        if session_id not in self.conversation_memory:
            self.conversation_memory[session_id] = {
                'topics_discussed': [],
                'tasks_completed': [],
                'user_preferences': {},
                'context_switches': []
            }
        
        # Track topics and patterns
        topics = self._extract_topics(user_message)
        for topic in topics:
            if topic not in self.conversation_memory[session_id]['topics_discussed']:
                self.conversation_memory[session_id]['topics_discussed'].append(topic)

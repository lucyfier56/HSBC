from tools import banking_api, knowledge_base
from typing import Any, Dict

class ToolExecutor:
    def __init__(self):
        # Map tool names to their implementation functions
        self.tool_functions = {
            "get_user_cards": banking_api.get_user_cards,
            "block_card": banking_api.block_card,
            "get_account_balance": banking_api.get_account_balance,
            "get_mini_statement": banking_api.get_mini_statement,
            "apply_for_loan": banking_api.apply_for_loan,
            "get_loan_status": banking_api.get_loan_status,
            "retrieve_knowledge": knowledge_base.retrieve
        }

    def execute(self, user_id: str, tool_name: str, **kwargs) -> Any:
        """Execute a tool with the given arguments"""
        
        if tool_name not in self.tool_functions:
            return f"Error: Tool '{tool_name}' not found."
        
        try:
            # Add user_id to kwargs for all banking API calls
            if tool_name.startswith(('get_', 'block_', 'apply_')):
                kwargs['user_id'] = user_id
            
            # Call the corresponding function
            result = self.tool_functions[tool_name](**kwargs)
            return result
        except Exception as e:
            return f"Error executing tool '{tool_name}': {str(e)}"

from services.mock_banking_api import (
    get_user_cards_data,
    block_card_data,
    get_account_balance_data,
    get_mini_statement_data,
    apply_for_loan_data,
    get_loan_applications_data,
    get_card_management_options,
    get_new_card_type_options,
    get_card_brand_options,
    apply_new_card_data,
    get_cards_for_limit_modification,
    get_current_limit_info,
    modify_credit_limit_data
)
from typing import Dict, Any

def get_user_cards(user_id: str) -> Dict[str, Any]:
    """Get all cards for a user with selection interface"""
    cards_data = get_user_cards_data(user_id)
    
    if cards_data["status"] == "success":
        return {
            "requires_selection": True,
            "message": "Here are your cards. Please select which card you'd like to manage:",
            "options": [
                {
                    "id": card["card_id"],
                    "text": f"{card['type'].title()} Card ending in {card['last_four']} - {card['status']}"
                }
                for card in cards_data["cards"]
            ]
        }
    
    return cards_data

def card_management(user_id: str) -> Dict[str, Any]:
    """Get card management options"""
    return get_card_management_options(user_id)

def new_card_type(user_id: str) -> Dict[str, Any]:
    """Get new card type options"""
    return get_new_card_type_options(user_id)

def card_brand_selection(user_id: str, card_type: str) -> Dict[str, Any]:
    """Get card brand options"""
    return get_card_brand_options(user_id, card_type)

def apply_new_card(user_id: str, card_type: str, brand: str) -> Dict[str, Any]:
    """Apply for new card"""
    return apply_new_card_data(user_id, card_type, brand)

def limit_modification_cards(user_id: str) -> Dict[str, Any]:
    """Get cards available for limit modification"""
    return get_cards_for_limit_modification(user_id)

def get_limit_info(user_id: str, card_id: str) -> Dict[str, Any]:
    """Get current limit information"""
    return get_current_limit_info(user_id, card_id)

def modify_credit_limit(user_id: str, card_id: str, new_limit: float) -> Dict[str, Any]:
    """Modify credit limit"""
    return modify_credit_limit_data(user_id, card_id, new_limit)

def block_card(user_id: str, card_id: str) -> Dict[str, Any]:
    """Block a specific card"""
    result = block_card_data(user_id, card_id)
    return result

def get_account_balance(user_id: str) -> Dict[str, Any]:
    """Get account balance"""
    return get_account_balance_data(user_id)

def get_mini_statement(user_id: str) -> Dict[str, Any]:
    """Get mini statement"""
    return get_mini_statement_data(user_id)

def apply_for_loan(user_id: str, amount: float = None, purpose: str = None, income: float = None, force_new: bool = False) -> Dict[str, Any]:
    """Apply for a loan or continue existing application"""
    return apply_for_loan_data(user_id, amount, purpose, income, force_new)

def get_loan_status(user_id: str) -> Dict[str, Any]:
    """Get loan application status"""
    return get_loan_applications_data(user_id)
def get_user_cards_display(user_id: str) -> Dict[str, Any]:
    """Get all cards for a user for display purposes (no selection interface)"""
    from services.mock_banking_api import get_user_cards_data
    return get_user_cards_data(user_id)
def get_comprehensive_account_details(user_id: str) -> Dict[str, Any]:
    """Get complete account details including everything"""
    from services.mock_banking_api import get_comprehensive_account_data
    return get_comprehensive_account_data(user_id)

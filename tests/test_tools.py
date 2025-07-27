import pytest
from tools.banking_api import get_user_cards, get_account_balance
from services.mock_banking_api import USER_DATA

def test_get_user_cards():
    user_id = "user123"
    result = get_user_cards(user_id)
    
    assert result["requires_selection"] == True
    assert "options" in result
    assert len(result["options"]) == len(USER_DATA[user_id]["cards"])

def test_get_account_balance():
    user_id = "user123"
    from tools.banking_api import get_account_balance
    result = get_account_balance(user_id)
    
    assert result["status"] == "success"
    assert "balance" in result
    assert result["balance"] == USER_DATA[user_id]["balance"]

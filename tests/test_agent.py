import pytest
from core.agent import ConversationalAgent
from core.state_manager import StateManager

@pytest.fixture
def agent():
    return ConversationalAgent()

@pytest.fixture  
def state_manager():
    return StateManager()

def test_agent_initialization(agent):
    assert agent.context_manager is not None
    assert agent.tool_executor is not None
    assert agent.state_manager is not None

def test_state_manager_operations(state_manager):
    session_id = "test_session"
    
    # Test getting non-existent state
    state = state_manager.get_state(session_id)
    assert state is None
    
    # Test updating state
    test_data = {"key": "value"}
    updated_state = state_manager.update_state(session_id, test_data)
    assert updated_state == test_data
    
    # Test getting existing state
    retrieved_state = state_manager.get_state(session_id)
    assert retrieved_state == test_data
    
    # Test clearing state
    state_manager.clear_state(session_id)
    cleared_state = state_manager.get_state(session_id)
    assert cleared_state is None

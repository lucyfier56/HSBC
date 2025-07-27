# Tool definitions following OpenAI function calling format
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_user_cards",
            "description": "Get all cards associated with the user's account",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "card_management",
            "description": "Show card management options (block card, apply for new card, modify limits)",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "new_card_type",
            "description": "Show options for new card type selection",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "card_brand_selection",
            "description": "Show card brand options for new card application",
            "parameters": {
                "type": "object",
                "properties": {
                    "card_type": {
                        "type": "string",
                        "description": "Type of card (credit_card or debit_card)",
                    },
                },
                "required": ["card_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "apply_new_card",
            "description": "Apply for a new card",
            "parameters": {
                "type": "object",
                "properties": {
                    "card_type": {
                        "type": "string",
                        "description": "Type of card",
                    },
                    "brand": {
                        "type": "string",
                        "description": "Card brand",
                    },
                },
                "required": ["card_type", "brand"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "limit_modification_cards",
            "description": "Show credit cards available for limit modification",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_limit_info",
            "description": "Get current limit information for a card",
            "parameters": {
                "type": "object",
                "properties": {
                    "card_id": {
                        "type": "string",
                        "description": "Card ID",
                    },
                },
                "required": ["card_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "modify_credit_limit",
            "description": "Modify credit limit for a card",
            "parameters": {
                "type": "object",
                "properties": {
                    "card_id": {
                        "type": "string",
                        "description": "Card ID",
                    },
                    "new_limit": {
                        "type": "number",
                        "description": "New credit limit",
                    },
                },
                "required": ["card_id", "new_limit"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "block_card",
            "description": "Block a specific card",
            "parameters": {
                "type": "object",
                "properties": {
                    "card_id": {
                        "type": "string",
                        "description": "The unique ID of the card to block",
                    },
                },
                "required": ["card_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_account_balance",
            "description": "Get the current account balance for the user",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_mini_statement",
            "description": "Get the last 5 transactions for the user's account",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "apply_for_loan",
            "description": "Start or continue a loan application process",
            "parameters": {
                "type": "object", 
                "properties": {
                    "amount": {
                        "type": "number",
                        "description": "Loan amount requested",
                    },
                    "purpose": {
                        "type": "string",
                        "description": "Purpose of the loan",
                    },
                    "income": {
                        "type": "number",
                        "description": "Annual income",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_loan_status",
            "description": "Get status of existing loan applications",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
{
    "type": "function",
    "function": {
        "name": "get_comprehensive_account_details",
        "description": "Get complete account overview including balance, cards, loans, applications, and transactions",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
},
]


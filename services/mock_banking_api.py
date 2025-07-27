import json
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from services.database_service import DatabaseService

# Initialize database service
db = DatabaseService()

def get_user_cards_data(user_id: str) -> Dict[str, Any]:
    """Get all cards for a user from database"""
    try:
        cards = db.get_user_cards(user_id)
        
        if not cards:
            return {"status": "error", "message": "No cards found for user"}
        
        # Format cards data
        formatted_cards = []
        for card in cards:
            formatted_card = {
                "card_id": card["card_id"],
                "type": card["type"],
                "card_number": card["card_number"],
                "last_four": card["last_four"],
                "status": card["status"],
                "brand": card["brand"],
                "expiry": card["expiry"],
                "annual_fee": card["annual_fee"] or 0.0
            }
            
            if card["type"] == "credit":
                formatted_card["limit"] = card["limit_amount"]
                formatted_card["available_credit"] = card["available_credit"]
            else:
                formatted_card["daily_limit"] = card["daily_limit"]
            
            if card["blocked_date"]:
                formatted_card["blocked_date"] = card["blocked_date"]
                formatted_card["blocked_reason"] = card["blocked_reason"]
            
            formatted_cards.append(formatted_card)
        
        return {
            "status": "success",
            "cards": formatted_cards,
            "total_cards": len(formatted_cards),
            "active_cards": len([card for card in formatted_cards if card["status"] == "active"])
        }
        
    except Exception as e:
        return {"status": "error", "message": f"Database error: {str(e)}"}

def block_card_data(user_id: str, card_id: str) -> Dict[str, Any]:
    """Block a specific card in database"""
    try:
        # Get card details first
        card = db.get_card(card_id)
        if not card:
            return {"status": "error", "message": "Card not found"}
        
        if card["user_id"] != user_id:
            return {"status": "error", "message": "Unauthorized access to card"}
        
        if card["status"] == "blocked":
            return {
                "status": "warning",
                "message": f"The {card['brand']} {card['type']} card ending in {card['last_four']} is already blocked.",
                "card_details": {
                    "type": card["type"],
                    "brand": card["brand"],
                    "last_four": card["last_four"],
                    "status": card["status"]
                }
            }
        
        # Block the card in database
        success = db.block_card(card_id)
        
        if success:
            # Get updated card data
            updated_card = db.get_card(card_id)
            confirmation_code = f"BLK{card['last_four']}{datetime.now().strftime('%H%M')}"
            
            return {
                "status": "success",
                "message": f"✅ Successfully blocked your {card['brand']} {card['type']} card ending in {card['last_four']}",
                "confirmation_code": confirmation_code,
                "next_steps": [
                    "A replacement card will be sent to your registered address within 3-5 business days",
                    "Your online banking and mobile app access remains active",
                    "Contact customer service at 1-800-BANK-HELP for any concerns"
                ],
                "card_details": {
                    "type": card["type"],
                    "brand": card["brand"],
                    "last_four": card["last_four"],
                    "blocked_date": updated_card["blocked_date"]
                }
            }
        else:
            return {"status": "error", "message": "Failed to block card"}
            
    except Exception as e:
        return {"status": "error", "message": f"Database error: {str(e)}"}

def get_account_balance_data(user_id: str) -> Dict[str, Any]:
    """Get comprehensive account balance information from database"""
    try:
        user = db.get_user(user_id)
        if not user:
            return {"status": "error", "message": "User not found"}
        
        cards = db.get_user_cards(user_id)
        credit_cards = [card for card in cards if card["type"] == "credit" and card["limit_amount"]]
        
        total_limit = sum([card["limit_amount"] for card in credit_cards])
        total_available = sum([card["available_credit"] or 0 for card in credit_cards])
        
        utilization_rate = "0%" if total_limit == 0 else f"{((total_limit - total_available) / total_limit * 100):.1f}%"
        
        return {
            "status": "success",
            "account_holder": user["name"],
            "account_number": user["account_number"],
            "account_type": user["account_type"],
            "current_balance": user["balance"],
            "available_balance": user["available_balance"],
            "pending_transactions": user["pending_transactions"],
            "currency": "USD",
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "credit_cards_summary": {
                "total_limit": total_limit,
                "total_available": total_available,
                "utilization_rate": utilization_rate
            }
        }
        
    except Exception as e:
        return {"status": "error", "message": f"Database error: {str(e)}"}

def get_mini_statement_data(user_id: str) -> Dict[str, Any]:
    """Get enhanced mini statement from database"""
    try:
        user = db.get_user(user_id)
        if not user:
            return {"status": "error", "message": "User not found"}
        
        transactions = db.get_user_transactions(user_id, limit=8)
        
        # Format transactions
        formatted_transactions = []
        for txn in transactions:
            formatted_transactions.append({
                "id": txn["id"],
                "date": txn["date"],
                "description": txn["description"],
                "amount": txn["amount"],
                "category": txn["category"],
                "card_used": txn["card_used"],
                "status": txn["status"]
            })
        
        # Calculate summary
        debits = [txn for txn in formatted_transactions if txn["amount"] < 0]
        credits = [txn for txn in formatted_transactions if txn["amount"] > 0]
        
        return {
            "status": "success",
            "account_holder": user["name"],
            "account_number": user["account_number"],
            "statement_period": f"{(datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')} to {datetime.now().strftime('%Y-%m-%d')}",
            "transactions": formatted_transactions,
            "summary": {
                "total_transactions": len(formatted_transactions),
                "total_debits": sum([abs(t["amount"]) for t in debits]),
                "total_credits": sum([t["amount"] for t in credits]),
                "largest_transaction": max([abs(t["amount"]) for t in formatted_transactions]) if formatted_transactions else 0,
                "most_frequent_category": "Food & Dining"
            },
            "current_balance": user["balance"]
        }
        
    except Exception as e:
        return {"status": "error", "message": f"Database error: {str(e)}"}

def apply_for_loan_data(user_id: str, amount: Optional[float] = None, 
                       purpose: Optional[str] = None, income: Optional[float] = None, 
                       force_new: bool = False) -> Dict[str, Any]:
    """Enhanced loan application with database persistence"""
    try:
        user = db.get_user(user_id)
        if not user:
            return {"status": "error", "message": "User not found"}
        
        # Get existing applications from database
        existing_apps = db.get_user_loans(user_id)
        
        # Only check for active applications if not forcing a new application
        active_app = None
        if not force_new:
            for app in existing_apps:
                if app["status"] in ["pending", "in_review"]:
                    active_app = app
                    break
        
        # Check if user wants a new loan (when they have existing approved loans)
        approved_loans = [app for app in existing_apps if app["status"] == "approved"]
        
        # If user explicitly wants a new loan or we're forcing new, start fresh
        if force_new or (not any([amount, purpose, income]) and approved_loans):
            # User has approved loans and wants to apply for new one
            if approved_loans:
                approved_loan = approved_loans[0]  # Get first approved loan for context
                return {
                    "status": "info",
                    "message": f"Hello {user['name']}! I see you have an approved loan for ${approved_loan['amount']:,.2f} for {approved_loan['purpose']}.\n\nTo help you apply for a **new loan**, I'll need some information:\n\n**Step 1: Loan Amount**\nHow much would you like to borrow? (Minimum: $1,000, Maximum: $50,000)",
                    "requires_continuation": True,
                    "process_type": "loan_application",
                    "current_step": "amount",
                    "collected_data": {},
                    "existing_loan": {
                        "application_id": approved_loan["application_id"],
                        "amount": approved_loan["amount"],
                        "purpose": approved_loan["purpose"]
                    },
                    "is_new_application": True
                }
            else:
                return {
                    "status": "info",
                    "message": f"Hello {user['name']}! I'd be happy to help you apply for a loan.\n\n**Step 1: Loan Amount**\nHow much would you like to borrow? (Minimum: $1,000, Maximum: $50,000)",
                    "requires_continuation": True,
                    "process_type": "loan_application", 
                    "current_step": "amount",
                    "collected_data": {},
                    "is_new_application": True
                }
        
        # Handle step-by-step collection
        if not amount:
            return {
                "status": "info",
                "message": f"Hello {user['name']}! I'd be happy to help you apply for a loan.\n\n**Step 1: Loan Amount**\nHow much would you like to borrow? (Minimum: $1,000, Maximum: $50,000)",
                "requires_continuation": True,
                "process_type": "loan_application", 
                "current_step": "amount",
                "collected_data": {}
            }
        
        if not purpose:
            return {
                "status": "info",
                "message": f"Great! You'd like to borrow ${amount:,.2f}.\n\n**Step 2: Loan Purpose**\nWhat will you use this loan for? (e.g., Home Improvement, Debt Consolidation, Auto Purchase, Medical Expenses, etc.)",
                "requires_continuation": True,
                "process_type": "loan_application",
                "current_step": "purpose", 
                "collected_data": {"amount": amount}
            }
        
        if not income:
            return {
                "status": "info",
                "message": f"Perfect! Loan amount: ${amount:,.2f} for {purpose}.\n\n**Step 3: Annual Income**\nWhat is your annual gross income? This helps us determine your loan eligibility and interest rate.",
                "requires_continuation": True,
                "process_type": "loan_application",
                "current_step": "income",
                "collected_data": {"amount": amount, "purpose": purpose}
            }
        
        # All information collected - process the application
        application_id = f"LOAN{len(existing_apps) + 1:03d}"
        
        # Calculate interest rate based on amount and income
        debt_to_income_ratio = (amount * 12) / (income if income > 0 else 50000)
        
        if debt_to_income_ratio < 0.1:
            interest_rate = 5.2
        elif debt_to_income_ratio < 0.2:
            interest_rate = 6.5
        elif debt_to_income_ratio < 0.3:
            interest_rate = 8.2
        else:
            interest_rate = 10.5
        
        # Calculate monthly payment
        monthly_rate = interest_rate / 100 / 12
        num_payments = 60  # 5 years
        monthly_payment = round((amount * monthly_rate * (1 + monthly_rate)**num_payments) / 
                               ((1 + monthly_rate)**num_payments - 1), 2)
        
        new_app = {
            "application_id": application_id,
            "amount": amount,
            "purpose": purpose,
            "annual_income": income,
            "status": "in_review",
            "interest_rate": interest_rate,
            "term_months": num_payments,
            "estimated_monthly_payment": monthly_payment,
            "debt_to_income_ratio": round(debt_to_income_ratio * 100, 1),
            "created_date": datetime.now().strftime("%Y-%m-%d"),
            "next_step": "credit_check"
        }
        
        # Save to database
        db.add_loan_application(user_id, new_app)
        
        return {
            "status": "success",
            "message": f"Excellent! Your loan application has been submitted successfully.\n\n**Application Summary:**\n• Application ID: {application_id}\n• Loan Amount: ${amount:,.2f}\n• Purpose: {purpose}\n• Annual Income: ${income:,.2f}\n• Estimated Interest Rate: {interest_rate}%\n• Estimated Monthly Payment: ${monthly_payment:,.2f}\n• Term: {num_payments} months (5 years)\n\n**Next Steps:**\n1. We'll run a credit check within 24 hours\n2. A loan specialist will review your application\n3. You'll receive a decision within 2-3 business days\n4. If approved, funds can be disbursed within 1 business day\n\nYour application reference number is: {application_id}",
            "application": new_app,
            "process_complete": True
        }
        
    except Exception as e:
        return {"status": "error", "message": f"Database error: {str(e)}"}

def get_loan_applications_data(user_id: str) -> Dict[str, Any]:
    """Get comprehensive loan application status from database"""
    try:
        user = db.get_user(user_id)
        if not user:
            return {"status": "error", "message": "User not found"}
        
        applications = db.get_user_loans(user_id)
        
        if not applications:
            return {
                "status": "success",
                "message": f"Hello {user['name']}! You don't have any loan applications on file. Would you like to apply for a loan today?",
                "applications": [],
                "loan_options": [
                    {"type": "Personal Loan", "rate": "5.2% - 12.9% APR", "max_amount": "$50,000"},
                    {"type": "Auto Loan", "rate": "3.9% - 8.5% APR", "max_amount": "$100,000"},
                    {"type": "Home Equity", "rate": "4.5% - 9.2% APR", "max_amount": "$250,000"}
                ]
            }
        
        # Format applications with all details
        formatted_apps = []
        for app in applications:
            formatted_app = {
                "application_id": app["application_id"],
                "amount": app["amount"],
                "purpose": app["purpose"],
                "status": app["status"],
                "annual_income": app.get("annual_income"),
                "interest_rate": app.get("interest_rate"),
                "term_months": app.get("term_months"),
                "monthly_payment": app.get("monthly_payment") if app["status"] == "approved" else app.get("estimated_monthly_payment"),
                "estimated_monthly_payment": app.get("estimated_monthly_payment"),
                "applied_date": app.get("applied_date") or app.get("created_date"),
                "approved_date": app.get("approved_date"),
                "created_date": app.get("created_date"),
                "debt_to_income_ratio": app.get("debt_to_income_ratio")
            }
            formatted_apps.append(formatted_app)
        
        return {
            "status": "success",
            "message": f"Here are your loan applications, {user['name']}:",
            "applications": formatted_apps,
            "total_applications": len(formatted_apps)
        }
        
    except Exception as e:
        return {"status": "error", "message": f"Database error: {str(e)}"}

def modify_credit_limit_data(user_id: str, card_id: str, new_limit: float) -> Dict[str, Any]:
    """Modify credit limit for a card in database"""
    try:
        card = db.get_card(card_id)
        if not card or card["user_id"] != user_id:
            return {"status": "error", "message": "Card not found"}
        
        if card["type"] != "credit":
            return {"status": "error", "message": "This operation is only available for credit cards"}
        
        old_limit = card["limit_amount"]
        
        # Validate new limit
        if new_limit < 1000:
            return {"status": "error", "message": "Minimum credit limit is $1,000"}
        if new_limit > 100000:
            return {"status": "error", "message": "Maximum credit limit is $100,000"}
        
        # Calculate new available credit
        utilization_ratio = (old_limit - (card["available_credit"] or 0)) / old_limit
        new_available_credit = new_limit - (new_limit * utilization_ratio)
        
        # Update in database
        success = db.update_card_limit(card_id, new_limit, new_available_credit)
        
        if success:
            change_type = "increased" if new_limit > old_limit else "decreased"
            
            return {
                "status": "success",
                "message": f"✅ Credit limit successfully {change_type}!\n\n💳 **Card**: {card['brand']} ending in {card['last_four']}\n📊 **Previous Limit**: ${old_limit:,.2f}\n🎯 **New Limit**: ${new_limit:,.2f}\n💵 **Available Credit**: ${new_available_credit:,.2f}\n\n⚡ The new limit is effective immediately and will reflect in your next statement.",
                "process_complete": True,
                "limit_change": {
                    "old_limit": old_limit,
                    "new_limit": new_limit,
                    "change_amount": abs(new_limit - old_limit),
                    "change_type": change_type
                }
            }
        else:
            return {"status": "error", "message": "Failed to update credit limit"}
            
    except Exception as e:
        return {"status": "error", "message": f"Database error: {str(e)}"}

def apply_new_card_data(user_id: str, card_type: str, brand: str) -> Dict[str, Any]:
    """Process new card application and save to database"""
    try:
        user = db.get_user(user_id)
        if not user:
            return {"status": "error", "message": "User not found"}
        
        # Get existing card applications
        existing_apps = db.get_user_card_applications(user_id)
        
        # Generate new card application
        application_id = f"CARD{len(existing_apps) + 1:03d}"
        card_type_clean = card_type.replace("_card", "")
        brand_display = brand.title()
        
        new_application = {
            "application_id": application_id,
            "type": card_type_clean,
            "brand": brand_display,
            "status": "approved",
            "applied_date": datetime.now().strftime("%Y-%m-%d"),
            "expected_delivery": (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        }
        
        # Save to database
        db.add_card_application(user_id, new_application)
        
        return {
            "status": "success",
            "message": f"🎉 Congratulations {user['name']}! Your {brand_display} {card_type_clean} card application has been approved!\n\n📋 **Application Details:**\n• Application ID: {application_id}\n• Card Type: {brand_display} {card_type_clean.title()}\n• Status: Approved\n• Expected Delivery: {new_application['expected_delivery']}\n\n📬 Your new card will be delivered to your registered address within 7 business days. You'll receive SMS and email notifications once it's dispatched.",
            "application": new_application,
            "process_complete": True
        }
        
    except Exception as e:
        return {"status": "error", "message": f"Database error: {str(e)}"}

# Keep other functions with database integration...
def get_card_management_options(user_id: str) -> Dict[str, Any]:
    """Get card management options"""
    try:
        user = db.get_user(user_id)
        if not user:
            return {"status": "error", "message": "User not found"}
        
        return {
            "requires_selection": True,
            "message": f"Hello {user['name']}! What would you like to do with your cards today?",
            "options": [
                {"id": "block_card", "text": "Block a Card"},
                {"id": "apply_new_card", "text": "Apply for New Card"},
                {"id": "modify_limit", "text": "Increase/Decrease Credit Limit"}
            ]
        }
    except Exception as e:
        return {"status": "error", "message": f"Database error: {str(e)}"}

def get_new_card_type_options(user_id: str) -> Dict[str, Any]:
    """Get new card type options"""
    return {
        "requires_selection": True,
        "message": "What type of card would you like to apply for?",
        "options": [
            {"id": "credit_card", "text": "Credit Card"},
            {"id": "debit_card", "text": "Debit Card"}
        ]
    }

def get_card_brand_options(user_id: str, card_type: str) -> Dict[str, Any]:
    """Get card brand options"""
    card_type_display = "Credit" if card_type == "credit_card" else "Debit"
    
    return {
        "requires_selection": True,
        "message": f"Which {card_type_display} card brand would you prefer?",
        "options": [
            {"id": "visa", "text": "Visa"},
            {"id": "mastercard", "text": "Mastercard"},
            {"id": "rupay", "text": "RuPay"}
        ]
    }

def get_cards_for_limit_modification(user_id: str) -> Dict[str, Any]:
    """Get credit cards available for limit modification from database"""
    try:
        cards = db.get_user_cards(user_id)
        credit_cards = [card for card in cards if card["type"] == "credit" and card["status"] == "active"]
        
        if not credit_cards:
            return {
                "status": "info",
                "message": "You don't have any active credit cards available for limit modification."
            }
        
        return {
            "requires_selection": True,
            "message": "Which credit card's limit would you like to modify?",
            "options": [
                {
                    "id": card["card_id"],
                    "text": f"{card['brand']} ending in {card['last_four']} - Current limit: ${card['limit_amount']:,.2f}"
                }
                for card in credit_cards
            ]
        }
    except Exception as e:
        return {"status": "error", "message": f"Database error: {str(e)}"}

def get_current_limit_info(user_id: str, card_id: str) -> Dict[str, Any]:
    """Get current limit information for a card from database"""
    try:
        card = db.get_card(card_id)
        if not card or card["user_id"] != user_id:
            return {"status": "error", "message": "Card not found"}
        
        if card["type"] == "credit":
            utilization = ((card["limit_amount"] - (card["available_credit"] or 0)) / card["limit_amount"] * 100)
            
            return {
                "status": "info",
                "message": f"**Current Credit Limit Information:**\n\n💳 **Card**: {card['brand']} ending in {card['last_four']}\n💰 **Current Limit**: ${card['limit_amount']:,.2f}\n💵 **Available Credit**: ${card['available_credit'] or 0:,.2f}\n📊 **Utilization**: {utilization:.1f}%\n\n**What would you like to set as the new credit limit?**\n(Minimum: $1,000, Maximum: $100,000)",
                "requires_continuation": True,
                "process_type": "limit_modification",
                "current_step": "new_limit",
                "collected_data": {"card_id": card_id, "current_limit": card["limit_amount"]},
                "card_info": {
                    "card_id": card["card_id"],
                    "brand": card["brand"],
                    "last_four": card["last_four"],
                    "limit": card["limit_amount"]
                }
            }
        
        return {"status": "error", "message": "Credit card not found"}
    except Exception as e:
        return {"status": "error", "message": f"Database error: {str(e)}"}
def apply_new_card_data(user_id: str, card_type: str, brand: str) -> Dict[str, Any]:
    """Process new card application and create actual card in database"""
    try:
        user = db.get_user(user_id)
        if not user:
            return {"status": "error", "message": "User not found"}
        
        # Get existing cards to generate new card ID
        existing_cards = db.get_user_cards(user_id)
        card_id = f"card_{len(existing_cards) + 1:03d}"
        
        # Generate card application
        existing_apps = db.get_user_card_applications(user_id)
        application_id = f"CARD{len(existing_apps) + 1:03d}"
        
        card_type_clean = card_type.replace("_card", "")
        brand_display = brand.title()
        
        # Generate card number
        card_details = db.generate_card_number(card_type_clean, brand)
        
        # Generate expiry date (3 years from now)
        from datetime import datetime, timedelta
        expiry_date = datetime.now() + timedelta(days=365*3)
        expiry_str = expiry_date.strftime("%m/%Y")
        
        # Set card limits based on type
        if card_type_clean == "credit":
            # Credit card defaults
            limit_amount = 10000.00 if brand.lower() == 'visa' else (15000.00 if brand.lower() == 'mastercard' else 8000.00)
            available_credit = limit_amount * 0.9  # 90% available initially
            daily_limit = None
            annual_fee = 99.00 if brand.lower() == 'mastercard' else 0.00
        else:
            # Debit card defaults
            limit_amount = None
            available_credit = None
            daily_limit = 5000.00
            annual_fee = 0.00
        
        # Create actual card data
        card_data = {
            "card_id": card_id,
            "type": card_type_clean,
            "card_number": card_details['masked_number'],
            "last_four": card_details['last_four'],
            "status": "active",
            "limit_amount": limit_amount,
            "available_credit": available_credit,
            "brand": brand_display,
            "expiry": expiry_str,
            "annual_fee": annual_fee,
            "daily_limit": daily_limit
        }
        
        # Save the actual card to database (not just application)
        db.add_actual_card(user_id, card_data)
        
        # Also save the application record for tracking
        new_application = {
            "application_id": application_id,
            "type": card_type_clean,
            "brand": brand_display,
            "status": "approved",
            "applied_date": datetime.now().strftime("%Y-%m-%d"),
            "expected_delivery": (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        }
        
        db.add_card_application(user_id, new_application)
        
        return {
            "status": "success",
            "message": f"🎉 Congratulations {user['name']}! Your {brand_display} {card_type_clean} card has been approved and activated!\n\n💳 **Card Details:**\n• Card Number: {card_details['masked_number']}\n• Card ID: {card_id}\n• Brand: {brand_display} {card_type_clean.title()}\n• Expiry Date: {expiry_str}\n• Status: Active{f' • Credit Limit: ${limit_amount:,.2f}' if limit_amount else ''}{f' • Daily Limit: ${daily_limit:,.2f}' if daily_limit else ''}\n\n📬 Your physical card will be delivered to your registered address within 7 business days. You can start using it for online transactions immediately!",
            "card": card_data,
            "application": new_application,
            "process_complete": True
        }
        
    except Exception as e:
        return {"status": "error", "message": f"Database error: {str(e)}"}
def get_comprehensive_account_data(user_id: str) -> Dict[str, Any]:
    """Get comprehensive account information including all user data"""
    try:
        user = db.get_user(user_id)
        if not user:
            return {"status": "error", "message": "User not found"}
        
        # Get all account components
        cards = db.get_user_cards(user_id)
        loans = db.get_user_loans(user_id)
        transactions = db.get_user_transactions(user_id, limit=5)
        card_applications = db.get_user_card_applications(user_id)
        
        # Format cards information
        active_cards = [card for card in cards if card["status"] == "active"]
        blocked_cards = [card for card in cards if card["status"] == "blocked"]
        credit_cards = [card for card in cards if card["type"] == "credit"]
        debit_cards = [card for card in cards if card["type"] == "debit"]
        
        # Calculate credit utilization
        total_credit_limit = sum([card["limit_amount"] or 0 for card in credit_cards])
        total_available_credit = sum([card["available_credit"] or 0 for card in credit_cards])
        credit_utilization = 0 if total_credit_limit == 0 else ((total_credit_limit - total_available_credit) / total_credit_limit * 100)
        
        # Format cards display
        cards_text = []
        for card in cards:
            status_icon = "🟢" if card["status"] == "active" else "🔴"
            card_line = f"{status_icon} **{card['brand']} {card['type'].title()}** ending in {card['last_four']} - {card['status'].title()}"
            if card["type"] == "credit" and card["limit_amount"]:
                card_line += f"\n    Credit Limit: ${card['limit_amount']:,.2f} | Available: ${card['available_credit'] or 0:,.2f}"
            elif card["type"] == "debit" and card["daily_limit"]:
                card_line += f"\n    Daily Limit: ${card['daily_limit']:,.2f}"
            cards_text.append(card_line)
        
        # Format loans information
        loans_text = []
        for loan in loans:
            status_icon = "✅" if loan["status"] == "approved" else ("⏳" if loan["status"] == "in_review" else "📋")
            loan_line = f"{status_icon} **{loan['application_id']}**: ${loan['amount']:,.2f} for {loan['purpose']}"
            loan_line += f"\n    Status: {loan['status'].title()}"
            if loan.get('interest_rate'):
                loan_line += f" | Rate: {loan['interest_rate']}%"
            if loan.get('monthly_payment'):
                loan_line += f" | Monthly: ${loan['monthly_payment']:,.2f}"
            elif loan.get('estimated_monthly_payment'):
                loan_line += f" | Est. Monthly: ${loan['estimated_monthly_payment']:,.2f}"
            loans_text.append(loan_line)
        
        # Format recent transactions
        transactions_text = []
        for txn in transactions:
            amount_display = f"${abs(txn['amount']):,.2f}"
            type_icon = "💰" if txn['amount'] > 0 else "💸"
            transactions_text.append(f"{type_icon} {txn['date']} - {txn['description']}: {amount_display}")
        
        # Format card applications
        applications_text = []
        for app in card_applications:
            app_line = f"📋 **{app['application_id']}**: {app['brand']} {app['type'].title()} Card"
            app_line += f"\n    Applied: {app['applied_date']} | Status: {app['status'].title()}"
            if app.get('expected_delivery'):
                app_line += f" | Expected: {app['expected_delivery']}"
            applications_text.append(app_line)
        
        # Build comprehensive response
        response_text = f"""🏦 **Complete Account Details for {user['name']}**

👤 **Personal Information:**
• Account Number: {user['account_number']}
• Account Type: {user['account_type']}
• Email: {user['email']}
• Phone: {user['phone']}

💰 **Account Balance:**
• Current Balance: ${user['balance']:,.2f}
• Available Balance: ${user['available_balance']:,.2f}
• Pending Transactions: ${user['pending_transactions']:,.2f}

💳 **Cards Overview** ({len(cards)} total):
• Active Cards: {len(active_cards)}
• Blocked Cards: {len(blocked_cards)}
• Credit Cards: {len(credit_cards)}
• Debit Cards: {len(debit_cards)}

**Your Cards:**
{chr(10).join(cards_text) if cards_text else "No cards found"}

💰 **Credit Summary:**
• Total Credit Limit: ${total_credit_limit:,.2f}
• Available Credit: ${total_available_credit:,.2f}
• Credit Utilization: {credit_utilization:.1f}%

🏠 **Loans & Applications** ({len(loans)} total):
{chr(10).join(loans_text) if loans_text else "No loan applications found"}

💸 **Recent Transactions** (Last 5):
{chr(10).join(transactions_text) if transactions_text else "No recent transactions found"}

📋 **Card Applications** ({len(card_applications)} total):
{chr(10).join(applications_text) if applications_text else "No card applications found"}

📊 **Account Health:**
• Account Status: Active ✅
• Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
• Profile Completeness: 100%

📞 **Need Help?**
• Online Banking: Available 24/7
• Customer Service: 1-800-BANK-HELP
• Emergency Card Block: 1-800-CARD-BLOCK"""
        
        return {
            "status": "success",
            "message": response_text,
            "account_summary": {
                "user": user,
                "cards_count": len(cards),
                "active_cards": len(active_cards),
                "loans_count": len(loans),
                "applications_count": len(card_applications),
                "credit_utilization": f"{credit_utilization:.1f}%",
                "account_health": "Excellent"
            }
        }
        
    except Exception as e:
        return {"status": "error", "message": f"Database error: {str(e)}"}

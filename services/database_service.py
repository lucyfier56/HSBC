import sqlite3
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
import os

class DatabaseService:
    def __init__(self, db_path: str = 'banking_agent.db'):
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Initialize SQLite database with all required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                account_number TEXT,
                account_type TEXT,
                balance REAL DEFAULT 0.0,
                available_balance REAL DEFAULT 0.0,
                pending_transactions REAL DEFAULT 0.0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Cards table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cards (
                card_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                type TEXT NOT NULL,
                card_number TEXT,
                last_four TEXT,
                status TEXT DEFAULT 'active',
                limit_amount REAL,
                available_credit REAL,
                brand TEXT,
                expiry TEXT,
                annual_fee REAL DEFAULT 0.0,
                daily_limit REAL,
                blocked_date DATETIME,
                blocked_reason TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Transactions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                date TEXT,
                description TEXT,
                amount REAL,
                category TEXT,
                card_used TEXT,
                status TEXT DEFAULT 'completed',
                location TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Loan applications table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS loan_applications (
                application_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                amount REAL NOT NULL,
                purpose TEXT,
                annual_income REAL,
                status TEXT DEFAULT 'pending',
                interest_rate REAL,
                term_months INTEGER,
                monthly_payment REAL,
                estimated_monthly_payment REAL,
                debt_to_income_ratio REAL,
                applied_date TEXT,
                approved_date TEXT,
                created_date TEXT,
                next_step TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Card applications table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS card_applications (
                application_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                type TEXT NOT NULL,
                brand TEXT,
                status TEXT DEFAULT 'pending',
                applied_date TEXT,
                expected_delivery TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Session state table (existing)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS session_state (
                session_id TEXT PRIMARY KEY,
                state_data TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Conversation history table (existing)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                user_message TEXT NOT NULL,
                ai_response TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                topics TEXT,
                urgency_level TEXT DEFAULT 'normal'
            )
        ''')
        
        conn.commit()
        conn.close()
        
        # Initialize with John Doe's data if not exists
        self._initialize_sample_data()

    def _initialize_sample_data(self):
        """Initialize database with John Doe's sample data"""
        if not self.get_user('user123'):
            self._insert_sample_data()

    def _insert_sample_data(self):
        """Insert John Doe's sample data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Insert user
        cursor.execute('''
            INSERT INTO users (user_id, name, email, phone, account_number, account_type, balance, available_balance, pending_transactions)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', ('user123', 'John Doe', 'john.doe@email.com', '+1-555-0123', 'ACC-2025-001', 
              'Premium Checking', 28750.50, 28750.50, 125.75))
        
        # Insert cards
        cards_data = [
            ('card_001', 'user123', 'credit', '****-****-****-1234', '1234', 'active', 
             15000.00, 12500.00, 'Visa Platinum', '12/2028', 95.00, None, None, None),
            ('card_002', 'user123', 'debit', '****-****-****-5678', '5678', 'active', 
             None, None, 'Mastercard', '08/2027', 0.00, 2500.00, None, None),
            ('card_003', 'user123', 'credit', '****-****-****-9012', '9012', 'active', 
             25000.00, 18750.00, 'American Express Gold', '06/2029', 250.00, None, None, None),
            ('card_004', 'user123', 'debit', '****-****-****-3456', '3456', 'active', 
             None, None, 'Visa', '03/2028', 0.00, 5000.00, None, None),
            ('card_005', 'user123', 'credit', '****-****-****-7890', '7890', 'blocked', 
             10000.00, 8500.00, 'Visa Classic', '11/2026', 0.00, None, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'Lost card - replaced')
        ]
        
        for card in cards_data:
            cursor.execute('''
                INSERT INTO cards (card_id, user_id, type, card_number, last_four, status, 
                                 limit_amount, available_credit, brand, expiry, annual_fee, 
                                 daily_limit, blocked_date, blocked_reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', card)
        
        # Insert sample transactions
        transactions_data = [
            ('TXN001', 'user123', '2025-07-27', 'Starbucks Coffee', -8.45, 'Food & Dining', '****1234', 'completed', None),
            ('TXN002', 'user123', '2025-07-26', 'Amazon Purchase', -156.99, 'Shopping', '****9012', 'completed', None),
            ('TXN003', 'user123', '2025-07-25', 'Salary Deposit - TechCorp Inc', 4500.00, 'Income', None, 'completed', None),
            ('TXN004', 'user123', '2025-07-24', 'Shell Gas Station', -65.20, 'Transportation', '****5678', 'completed', None),
            ('TXN005', 'user123', '2025-07-23', 'Whole Foods Market', -234.67, 'Groceries', '****3456', 'completed', None),
            ('TXN006', 'user123', '2025-07-22', 'Netflix Subscription', -15.99, 'Entertainment', '****1234', 'completed', None),
            ('TXN007', 'user123', '2025-07-21', 'ATM Withdrawal', -200.00, 'Cash Withdrawal', None, 'completed', 'Main Street ATM'),
            ('TXN008', 'user123', '2025-07-20', 'Electric Bill Payment', -148.50, 'Utilities', None, 'completed', None)
        ]
        
        for txn in transactions_data:
            cursor.execute('''
                INSERT INTO transactions (id, user_id, date, description, amount, category, card_used, status, location)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', txn)
        
        # Insert sample loan application
        cursor.execute('''
            INSERT INTO loan_applications (application_id, user_id, amount, purpose, status, 
                                         interest_rate, term_months, monthly_payment, applied_date, approved_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', ('LOAN001', 'user123', 25000.00, 'Home Renovation', 'approved', 
              5.2, 60, 471.78, '2025-06-15', '2025-06-22'))
        
        conn.commit()
        conn.close()

    # User operations
    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user data"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        return dict(result) if result else None

    def update_user_balance(self, user_id: str, new_balance: float, available_balance: float = None):
        """Update user account balance"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if available_balance is None:
            available_balance = new_balance
        
        cursor.execute('''
            UPDATE users SET balance = ?, available_balance = ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
        ''', (new_balance, available_balance, user_id))
        
        conn.commit()
        conn.close()

    # Card operations
    def get_user_cards(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all cards for a user"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM cards WHERE user_id = ? ORDER BY created_at', (user_id,))
        results = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in results]

    def block_card(self, card_id: str) -> bool:
        """Block a card"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE cards SET status = 'blocked', 
                           blocked_date = CURRENT_TIMESTAMP,
                           blocked_reason = 'Customer request',
                           updated_at = CURRENT_TIMESTAMP
            WHERE card_id = ?
        ''', (card_id,))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return success

    def update_card_limit(self, card_id: str, new_limit: float, new_available_credit: float) -> bool:
        """Update card credit limit"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE cards SET limit_amount = ?, available_credit = ?, updated_at = CURRENT_TIMESTAMP
            WHERE card_id = ?
        ''', (new_limit, new_available_credit, card_id))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return success

    def get_card(self, card_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific card"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM cards WHERE card_id = ?', (card_id,))
        result = cursor.fetchone()
        conn.close()
        
        return dict(result) if result else None

    # Transaction operations
    def get_user_transactions(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get user transactions"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM transactions WHERE user_id = ? 
            ORDER BY date DESC, created_at DESC LIMIT ?
        ''', (user_id, limit))
        
        results = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in results]

    def add_transaction(self, user_id: str, transaction_data: Dict[str, Any]) -> str:
        """Add a new transaction"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        transaction_id = transaction_data.get('id', f"TXN{datetime.now().strftime('%Y%m%d%H%M%S')}")
        
        cursor.execute('''
            INSERT INTO transactions (id, user_id, date, description, amount, category, card_used, status, location)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            transaction_id, user_id, transaction_data.get('date'),
            transaction_data.get('description'), transaction_data.get('amount'),
            transaction_data.get('category'), transaction_data.get('card_used'),
            transaction_data.get('status', 'completed'), transaction_data.get('location')
        ))
        
        conn.commit()
        conn.close()
        
        return transaction_id

    # Loan operations
    def get_user_loans(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all loan applications for a user"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM loan_applications WHERE user_id = ? ORDER BY created_at DESC', (user_id,))
        results = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in results]

    def add_loan_application(self, user_id: str, loan_data: Dict[str, Any]) -> str:
        """Add a new loan application"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        application_id = loan_data['application_id']
        
        cursor.execute('''
            INSERT INTO loan_applications (
                application_id, user_id, amount, purpose, annual_income, status,
                interest_rate, term_months, estimated_monthly_payment, debt_to_income_ratio,
                created_date, next_step
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            application_id, user_id, loan_data.get('amount'),
            loan_data.get('purpose'), loan_data.get('annual_income'),
            loan_data.get('status', 'in_review'), loan_data.get('interest_rate'),
            loan_data.get('term_months'), loan_data.get('estimated_monthly_payment'),
            loan_data.get('debt_to_income_ratio'), loan_data.get('created_date'),
            loan_data.get('next_step')
        ))
        
        conn.commit()
        conn.close()
        
        return application_id

    def update_loan_status(self, application_id: str, status: str, approved_date: str = None) -> bool:
        """Update loan application status"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if approved_date:
            cursor.execute('''
                UPDATE loan_applications SET status = ?, approved_date = ?, updated_at = CURRENT_TIMESTAMP
                WHERE application_id = ?
            ''', (status, approved_date, application_id))
        else:
            cursor.execute('''
                UPDATE loan_applications SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE application_id = ?
            ''', (status, application_id))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return success

    # Card application operations
    def add_card_application(self, user_id: str, card_app_data: Dict[str, Any]) -> str:
        """Add a new card application"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        application_id = card_app_data['application_id']
        
        cursor.execute('''
            INSERT INTO card_applications (application_id, user_id, type, brand, status, applied_date, expected_delivery)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            application_id, user_id, card_app_data.get('type'),
            card_app_data.get('brand'), card_app_data.get('status', 'approved'),
            card_app_data.get('applied_date'), card_app_data.get('expected_delivery')
        ))
        
        conn.commit()
        conn.close()
        
        return application_id

    def get_user_card_applications(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all card applications for a user"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM card_applications WHERE user_id = ? ORDER BY created_at DESC', (user_id,))
        results = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in results]
    def add_actual_card(self, user_id: str, card_data: Dict[str, Any]) -> str:
        """Add an actual card to the cards table (not just application)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        card_id = card_data['card_id']
        
        cursor.execute('''
            INSERT INTO cards (
                card_id, user_id, type, card_number, last_four, status,
                limit_amount, available_credit, brand, expiry, annual_fee, daily_limit
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            card_id, user_id, card_data.get('type'),
            card_data.get('card_number'), card_data.get('last_four'),
            card_data.get('status', 'active'), card_data.get('limit_amount'),
            card_data.get('available_credit'), card_data.get('brand'),
            card_data.get('expiry'), card_data.get('annual_fee', 0.0),
            card_data.get('daily_limit')
        ))
        
        conn.commit()
        conn.close()
        
        return card_id

    def generate_card_number(self, card_type: str, brand: str) -> Dict[str, str]:
        """Generate a random card number based on type and brand"""
        import random
        
        # BIN (Bank Identification Number) ranges for different brands
        bin_ranges = {
            'visa': ['4'],
            'mastercard': ['5'],
            'rupay': ['6']
        }
        
        # Get appropriate BIN
        bin_start = bin_ranges.get(brand.lower(), ['4'])[0]
        
        # Generate 15 more digits (total 16)
        remaining_digits = ''.join([str(random.randint(0, 9)) for _ in range(15)])
        full_number = bin_start + remaining_digits
        
        # Format as masked number
        masked_number = f"****-****-****-{full_number[-4:]}"
        last_four = full_number[-4:]
        
        return {
            'full_number': full_number,
            'masked_number': masked_number,
            'last_four': last_four
        }


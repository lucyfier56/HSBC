# 🏦 Conversational Banking Agent

A sophisticated AI-powered banking assistant that provides natural language interactions for loan applications, card management, account inquiries, and transaction processing with advanced context switching and multi-step workflow support.

## 🚀 Features

### Core Banking Operations
- **💰 Account Management**: Balance inquiries, comprehensive account details, transaction history
- **💳 Card Services**: Block/unblock cards, apply for new cards, modify credit limits
- **🏠 Loan Applications**: Multi-step loan application process with context switching
- **📊 Account Analytics**: Credit utilization tracking, spending categorization

### Advanced Conversational AI
- **🧠 Context Switching**: Seamlessly switch between tasks while preserving progress
- **🔄 Multi-Step Processes**: Handle complex workflows with state persistence
- **🛡️ Fallback Mechanisms**: Graceful degradation when LLM services fail
- **💾 Database Persistence**: All actions saved to SQLite database in real-time

### Smart Features
- **📈 Progress Tracking**: Resume interrupted processes where you left off
- **🎯 Intent Detection**: Intelligent routing to appropriate banking services
- **⚡ Real-time Updates**: Instant database updates for all banking operations
- **🔍 Selection Interfaces**: User-friendly option selection for complex operations

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Presentation Layer                     │
│  FastAPI Web Server + HTML Chat Interface + REST APIs       │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│               Conversation Orchestration Layer              │
│   ConversationalAgent + Context Manager + State Manager     │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    Business Logic Layer                     │
│   Banking APIs + Multi-Step Handlers + Tool Executor        │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    Data Persistence Layer                   │
│     SQLite Database + Session Management + History          │
└─────────────────────────────────────────────────────────────┘
```

└─────────────────────────────────────────────────────────────┘


## 🛠️ Tech Stack

- **Backend**: Python 3.8+, FastAPI
- **AI/LLM**: Groq API integration with fallback mechanisms
- **Database**: SQLite with comprehensive schema
- **Frontend**: HTML/CSS/JavaScript chat interface
- **State Management**: Custom session and context managers

## 📋 Prerequisites

- Python 3.8 or higher
- Groq API key (optional - system works with fallbacks)
- pip package manager

## 🚀 Quick Start

### 1. Clone Repository
```
git clone 
cd conversational-banking-agent
```

### 2. Install Dependencies
```
pip install -r requirements.txt
```

### 3. Environment Setup
Create a `.env` file in the root directory:
```
GROQ_API_KEY=your_groq_api_key_here
DATABASE_URL=sqlite:///banking_agent.db
```


### 4. Run the Application
```
python run.py
```
### 5. Access the Interface
Open your browser and navigate to: `http://localhost:8000`

## 💬 Usage Examples

### Loan Application
User: "apply for loan"
Agent: "Step 1: Loan Amount - How much would you like to borrow?"
User: "15000"
Agent: "Step 2: Loan Purpose - What will you use this loan for?"
User: "home renovation"
Agent: "Step 3: Annual Income - What is your yearly gross income?"
User: "75000"
Agent: "✅ Application submitted successfully! ID: LOAN004..."


### Card Management


User: "card management"
Agent: "What would you like to do with your cards today?"
User: [Selects "Apply for New Card"]
Agent: "What type of card would you like to apply for?"
User: [Selects "Credit Card"]
Agent: "Which Credit card brand would you prefer?"
User: [Selects "Visa"]
Agent: "🎉 Congratulations! Your Visa credit card has been approved!"

### Context Switching

User: "apply for loan"
Agent: "Step 1: Loan Amount..."
User: "5000"
Agent: "Step 2: Loan Purpose..."
User: "block card" [Context Switch]
Agent: [Shows card selection]
User: [Selects card to block]
Agent: "✅ Card blocked successfully!"
User: "continue loan" [Resume Previous Process]
Agent: "Continuing with your $5,000 loan application. Step 2: Purpose..."

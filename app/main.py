from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from app.schemas import UserRequest, ChatResponse
from core.agent import ConversationalAgent
from services.database_service import DatabaseService

app = FastAPI(title="Conversational Banking Agent")

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database tables on startup"""
    db_service = DatabaseService()
    print("✅ Database initialized successfully!")
    print("📊 Sample data loaded for user: user123 (John Doe)")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = ConversationalAgent()

@app.get("/")
async def serve_frontend():
    """Serve the frontend HTML file"""
    return FileResponse("frontend.html")

@app.post("/chat", response_model=ChatResponse)
async def handle_chat(request: UserRequest):
    """
    Main endpoint to handle user messages.
    """
    user_id = request.user_id
    session_id = request.session_id
    message = request.message

    if not all([user_id, session_id, message]):
        raise HTTPException(status_code=400, detail="Missing required fields.")

    try:
        # The agent handles the entire conversational turn
        response_data = await agent.process_turn(user_id, session_id, message)
        return response_data
    except Exception as e:
        print(f"Error processing request: {str(e)}")  # For debugging
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "database": "connected"}

@app.get("/user/{user_id}/data")
async def get_user_data(user_id: str):
    """Get complete user data from database (for debugging)"""
    try:
        db_service = DatabaseService()
        user = db_service.get_user(user_id)
        cards = db_service.get_user_cards(user_id)
        loans = db_service.get_user_loans(user_id)
        transactions = db_service.get_user_transactions(user_id, limit=10)
        
        return {
            "user": user,
            "cards": cards,
            "loans": loans,
            "recent_transactions": transactions
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

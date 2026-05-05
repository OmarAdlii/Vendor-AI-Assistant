from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from typing import Optional
import uvicorn
import uuid
import os

from app.config import get_settings
from app.models.schemas import ChatMessage, ChatResponse, KnowledgeBaseQuery
from app.websocket_manager import manager
from agent.ai_agent import ai_agent
from agent.memory import conversation_memory
from mcp_server.database import db_manager
from rag.vector_store import vector_store
from mcp_server.tools.rag_tools import RAGTools

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    print(" Starting AI Chatbot Server...")
    
    # Connect to main database (vmbe) for MCP tools
    await db_manager.connect()
    print(" Main database (vmbe) connected")
    
    # Connect to chat database (chatAi) for conversation memory
    await conversation_memory.connect()
    await conversation_memory.initialize_tables()
    print(" Chat database (chatAi) connected")
    
    print(f" Server running on {settings.host}:{settings.port}")
    
    yield
    
    # Shutdown
    print(" Shutting down server...")
    await db_manager.disconnect()
    await conversation_memory.disconnect()
    print(" Cleanup complete")

app = FastAPI(
    title="Vendor AI Assistant",
    description="AI-powered chatbot with MCP, RAG, and database integration",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# Root endpoint - serve chat interface
@app.get("/")
async def root():
    """Serve the chat interface"""
    static_path = "static/chat.html"
    if os.path.exists(static_path):
        return FileResponse(static_path)
    return {"message": "AI Chatbot API is running. Visit /docs for API documentation."}


# ================== WebSocket Endpoint ==================

@app.websocket("/ws/{vendor_id}")
async def websocket_endpoint(websocket: WebSocket, vendor_id: str):
    """WebSocket endpoint for real-time chat"""
    session_id = str(uuid.uuid4())
    await manager.connect(websocket, session_id, vendor_id)
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_json()
            message = data.get("message", "")
            stream = data.get("stream", False)
            
            if not message:
                await manager.send_error("Empty message received", session_id)
                continue
            
            # Process with AI agent
            if stream:
                # Streaming response
                async for chunk in ai_agent.process_message(
                    message=message,
                    vendor_id=vendor_id,
                    session_id=session_id,
                    stream=True
                ):
                    if chunk.get("type") == "chunk":
                        await manager.send_stream_chunk(chunk["content"], session_id)
                    elif chunk.get("type") == "done":
                        await manager.send_to_session({
                            "type": "complete",
                            "session_id": session_id
                        }, session_id)
            else:
                # Non-streaming response
                result = await ai_agent.process_message(
                    message=message,
                    vendor_id=vendor_id,
                    session_id=session_id,
                    stream=False
                )
                
                await manager.send_to_session({
                    "type": "response",
                    "response": result["response"],
                    "tool_calls": result.get("tool_calls", []),
                    "tokens": result.get("tokens"),
                    "steps": result.get("steps", []),
                    "session_id": session_id
                }, session_id)
    
    except WebSocketDisconnect:
        manager.disconnect(session_id, vendor_id)
        print(f"Client {session_id} disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")
        await manager.send_error(str(e), session_id)
        manager.disconnect(session_id, vendor_id)

# ================== REST API Endpoints ==================

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(chat_message: ChatMessage):
    """REST API endpoint for chat (non-WebSocket)"""
    try:
        session_id = chat_message.session_id or str(uuid.uuid4())
        
        result = await ai_agent.process_message(
            message=chat_message.message,
            vendor_id=chat_message.vendor_id,
            session_id=session_id,
            stream=False
        )
        
        return ChatResponse(
            response=result["response"],
            session_id=session_id,
            tool_calls=result.get("tool_calls")
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload-document")
async def upload_document(file: UploadFile = File(...)):
    """Upload document to knowledge base"""
    try:
        content = await file.read()
        
        result = await RAGTools.add_documents_to_kb(
            file_content=content,
            content_type=file.content_type
        )
        
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/search-knowledge")
async def search_knowledge(query: KnowledgeBaseQuery):
    """Search knowledge base"""
    try:
        results = await RAGTools.search_knowledge_base(
            query=query.query,
            top_k=query.top_k,
            threshold=query.threshold
        )
        
        return {
            "success": True,
            "results": results,
            "count": len(results)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "active_connections": manager.get_total_connections(),
        "database": "connected" if db_manager.pool else "disconnected"
    }

@app.delete("/api/conversation/{session_id}")
async def clear_conversation(session_id: str):
    """Clear conversation history"""
    try:
        success = await conversation_memory.clear_history(session_id)
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/conversation/{session_id}")
async def get_conversation(session_id: str, limit: int = 20):
    """Get conversation history"""
    try:
        history = await conversation_memory.get_history(session_id, limit)
        return {
            "success": True,
            "history": history,
            "count": len(history)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/conversation/{session_id}/full")
async def get_full_conversation(
    session_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Get full conversation history for analysis """
    try:
        from datetime import datetime
        
        start = datetime.fromisoformat(start_date) if start_date else None
        end = datetime.fromisoformat(end_date) if end_date else None
        
        history = await conversation_memory.get_all_history(session_id, start, end)
        stats = await conversation_memory.get_session_stats(session_id)
        
        return {
            "success": True,
            "session_id": session_id,
            "history": history,
            "total_messages": len(history),
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/conversation/search")
async def search_conversations(
    session_id: Optional[str] = None,
    search_text: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100
):
    """Search conversation history for analysis"""
    try:
        from datetime import datetime
        
        start = datetime.fromisoformat(start_date) if start_date else None
        end = datetime.fromisoformat(end_date) if end_date else None
        
        results = await conversation_memory.search_history(
            session_id=session_id,
            search_text=search_text,
            start_date=start,
            end_date=end,
            limit=limit
        )
        
        return {
            "success": True,
            "results": results,
            "count": len(results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/conversation/{session_id}/stats")
async def get_session_statistics(session_id: str):
    """Get statistics for a conversation session"""
    try:
        stats = await conversation_memory.get_session_stats(session_id)
        return {
            "success": True,
            "session_id": session_id,
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/conversation/archive")
async def archive_old_conversations(days_old: int = 90):
    """Archive conversations older than specified days"""
    try:
        count = await conversation_memory.archive_old_sessions(days_old)
        return {
            "success": True,
            "archived_count": count,
            "message": f"Archived {count} old conversations"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ================== Main Entry Point ==================

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info"
    )
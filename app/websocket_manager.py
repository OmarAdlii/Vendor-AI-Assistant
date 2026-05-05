from typing import Dict, Set
from fastapi import WebSocket
import json
from datetime import datetime
from utils.json_utils import make_serializable

class ConnectionManager:
    """Manage WebSocket connections"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.vendor_connections: Dict[str, Set[str]] = {}  # vendor_id -> set of session_ids
    
    async def connect(self, websocket: WebSocket, session_id: str, vendor_id: str):
        """Accept and register new WebSocket connection"""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        
        # Track vendor connections
        if vendor_id not in self.vendor_connections:
            self.vendor_connections[vendor_id] = set()
        self.vendor_connections[vendor_id].add(session_id)
        
        # Send welcome message
        await self.send_personal_message(
            {
                "type": "connected",
                "message": "Connected to AI Assistant",
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            },
            websocket
        )
    
    def disconnect(self, session_id: str, vendor_id: str):
        """Remove WebSocket connection"""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        
        if vendor_id in self.vendor_connections:
            self.vendor_connections[vendor_id].discard(session_id)
            if not self.vendor_connections[vendor_id]:
                del self.vendor_connections[vendor_id]
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send message to specific WebSocket"""
        # Ensure message is JSON-serializable (convert Decimal, datetime, etc.)
        await websocket.send_text(json.dumps(make_serializable(message)))
    
    async def send_to_session(self, message: dict, session_id: str):
        """Send message to specific session"""
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_text(json.dumps(make_serializable(message)))
    
    async def broadcast_to_vendor(self, message: dict, vendor_id: str):
        """Broadcast message to all sessions of a vendor"""
        if vendor_id in self.vendor_connections:
            for session_id in self.vendor_connections[vendor_id]:
                await self.send_to_session(message, session_id)
    
    async def send_stream_chunk(self, chunk: str, session_id: str):
        """Send streaming response chunk"""
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_text(json.dumps(make_serializable({
                "type": "stream",
                "content": chunk,
                "timestamp": datetime.now().isoformat()
            })))
    
    async def send_error(self, error: str, session_id: str):
        """Send error message"""
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_text(json.dumps(make_serializable({
                "type": "error",
                "message": error,
                "timestamp": datetime.now().isoformat()
            })))
    
    def get_active_sessions(self, vendor_id: str) -> Set[str]:
        """Get all active sessions for a vendor"""
        return self.vendor_connections.get(vendor_id, set())
    
    def get_total_connections(self) -> int:
        """Get total number of active connections"""
        return len(self.active_connections)

# Singleton instance
manager = ConnectionManager()
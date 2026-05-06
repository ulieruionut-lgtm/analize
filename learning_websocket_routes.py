"""
FastAPI endpoints for real-time learning monitoring.
Add this to backend/main.py
"""
from fastapi import WebSocket, WebSocketDisconnect
from typing import Set
import json
import asyncio

# WebSocket connection manager
class LearningWebSocketManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        
        for connection in disconnected:
            self.disconnect(connection)


# Global manager instance
learning_ws_manager = LearningWebSocketManager()


# Add these routes to your FastAPI app in main.py

"""
@app.websocket("/ws/learning")
async def websocket_learning_endpoint(websocket: WebSocket):
    '''WebSocket endpoint for real-time learning events.'''
    await learning_ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection open, receive any messages
            data = await websocket.receive_text()
            if data == "stats":
                # Client requesting stats
                from backend.learning_events import get_event_bus
                bus = get_event_bus()
                stats = bus.get_statistics()
                await websocket.send_json({"type": "stats", "data": stats})
    except WebSocketDisconnect:
        learning_ws_manager.disconnect(websocket)


@app.get("/api/learning/events")
def get_learning_events(limit: int = 50):
    '''Get recent learning events via REST.'''
    from backend.learning_events import get_event_bus
    bus = get_event_bus()
    return {"events": bus.get_recent_events(limit)}


@app.get("/api/learning/stats")
def get_learning_stats():
    '''Get learning statistics via REST.'''
    from backend.learning_events import get_event_bus
    bus = get_event_bus()
    return bus.get_statistics()
"""

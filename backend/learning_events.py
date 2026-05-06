"""
Real-time learning event system.
Broadcasts what the LLM learning system learns.
"""
import asyncio
import json
from datetime import datetime
from typing import Callable, Dict, Any, List, Optional
from collections import deque
import threading
from queue import Queue

# Global event system
_event_lock = threading.Lock()
_event_queue: Queue = Queue(maxsize=1000)
_websocket_clients: List[Callable] = []


class LearningEvent:
    """Single learning event."""
    
    def __init__(
        self,
        event_type: str,  # 'alias_learned', 'mapping_success', 'llm_call', 'error'
        analysis_name: str,
        mapped_to: Optional[str] = None,
        score: Optional[float] = None,
        laborator_id: Optional[int] = None,
        error: Optional[str] = None,
        details: Optional[Dict] = None,
    ):
        self.event_type = event_type
        self.analysis_name = analysis_name
        self.mapped_to = mapped_to
        self.score = score
        self.laborator_id = laborator_id
        self.error = error
        self.details = details or {}
        self.timestamp = datetime.now()
        self.id = f"{event_type}_{int(self.timestamp.timestamp() * 1000000)}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON."""
        return {
            "id": self.id,
            "type": self.event_type,
            "analysis_name": self.analysis_name,
            "mapped_to": self.mapped_to,
            "score": self.score,
            "laborator_id": self.laborator_id,
            "error": self.error,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
        }


class LearningEventBus:
    """Central event bus for learning events."""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.events: deque = deque(maxlen=500)  # Keep last 500 events
        self.subscribers: List[Callable] = []
        self.lock = threading.Lock()
    
    def emit(self, event: LearningEvent):
        """Emit a learning event."""
        with self.lock:
            self.events.append(event)
            
            # Notify all subscribers
            for callback in self.subscribers:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        # For async callbacks
                        asyncio.create_task(callback(event))
                    else:
                        # For sync callbacks
                        callback(event)
                except Exception as e:
                    print(f"[EVENT-BUS] Error notifying subscriber: {e}")
            
            # Broadcast via WebSocket if available
            try:
                # Try to import and broadcast via WebSocket
                import asyncio as _asyncio
                from backend.main import learning_ws_manager
                
                stats = self.get_statistics()
                message = {
                    "type": "learning_event",
                    "event": event.to_dict(),
                    "stats": stats,
                }
                
                # Schedule the broadcast
                _asyncio.create_task(learning_ws_manager.broadcast(message))
            except Exception:
                # WebSocket not available or not initialized yet - ignore
                pass
    
    def subscribe(self, callback: Callable):
        """Subscribe to learning events."""
        with self.lock:
            self.subscribers.append(callback)
    
    def unsubscribe(self, callback: Callable):
        """Unsubscribe from learning events."""
        with self.lock:
            if callback in self.subscribers:
                self.subscribers.remove(callback)
    
    def get_recent_events(self, limit: int = 50) -> List[Dict]:
        """Get recent events as dicts."""
        with self.lock:
            events = list(self.events)[-limit:]
            return [e.to_dict() for e in events]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get learning statistics."""
        with self.lock:
            if not self.events:
                return {
                    "total_events": 0,
                    "aliases_learned": 0,
                    "errors": 0,
                    "success_rate": 0,
                }
            
            total = len(self.events)
            aliases_learned = sum(1 for e in self.events if e.event_type == "alias_learned")
            errors = sum(1 for e in self.events if e.event_type == "error")
            llm_calls = sum(1 for e in self.events if e.event_type == "llm_call")
            
            success_rate = (aliases_learned / llm_calls * 100) if llm_calls > 0 else 0
            
            return {
                "total_events": total,
                "aliases_learned": aliases_learned,
                "errors": errors,
                "llm_calls": llm_calls,
                "success_rate": round(success_rate, 1),
                "recent_events": [e.to_dict() for e in list(self.events)[-10:]],
            }


def emit_learning_event(
    event_type: str,
    analysis_name: str,
    mapped_to: Optional[str] = None,
    score: Optional[float] = None,
    laborator_id: Optional[int] = None,
    error: Optional[str] = None,
    details: Optional[Dict] = None,
):
    """Emit a learning event to the bus."""
    event = LearningEvent(
        event_type=event_type,
        analysis_name=analysis_name,
        mapped_to=mapped_to,
        score=score,
        laborator_id=laborator_id,
        error=error,
        details=details,
    )
    bus = LearningEventBus()
    bus.emit(event)
    
    # Also print for logs
    if event_type == "alias_learned":
        print(f"[LLM-LEARN] ✅ {analysis_name} → {mapped_to} ({score}%)", flush=True)
    elif event_type == "error":
        print(f"[LLM-LEARN-ERROR] {analysis_name}: {error}", flush=True)
    elif event_type == "llm_call":
        print(f"[LLM-CALL] Analyzing {analysis_name}...", flush=True)


# Backward compatibility
def get_event_bus() -> LearningEventBus:
    """Get the global event bus."""
    return LearningEventBus()

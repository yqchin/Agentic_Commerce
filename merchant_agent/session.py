from typing import Optional

_current_session_id: Optional[str] = None

def set_session_id(session_id: str) -> None:
    """Set the current session ID for tools to access"""
    global _current_session_id
    _current_session_id = session_id

def get_session_id() -> str:
    """Get the current session ID"""
    return _current_session_id or "default_session"

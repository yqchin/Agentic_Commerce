"""
Configuration for Merchant Agent Package
Handles all settings needed to initialize and run the agent
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MerchantAgentConfig:
    """
    Configuration for initializing a Merchant Agent.
    
    This class holds all the settings needed to run a merchant agent,
    making it easy for merchants to configure and pass settings.
    """
    
    # ========== Required Settings ==========
    api_key: str
    """Google GenAI API key - get from https://aistudio.google.com"""
    
    # ========== Optional Settings with Defaults ==========
    model: str = "gemini-2.0-flash-exp"
    """LLM model to use for the agent"""
    
    app_name: str = "merchant_app"
    """Application name for session management"""
    
    user_id: str = "merchant_user"
    """User identifier for session tracking"""
    
    session_id: Optional[str] = None
    """Session ID - if None, one will be generated automatically"""
    
    log_level: str = "INFO"
    """Logging level: DEBUG, INFO, WARNING, ERROR"""
    
    # ========== Advanced Settings ==========
    session_timeout: int = 3600
    """Session timeout in seconds (default: 1 hour)"""
    
    enable_debug: bool = False
    """Enable debug logging for troubleshooting"""
    
    custom_instruction: Optional[str] = None
    """Custom system instruction for the agent (overrides default)"""
    
    def validate(self) -> bool:
        """Validate configuration has required fields"""
        if not self.api_key:
            raise ValueError("api_key is required")
        if not self.app_name:
            raise ValueError("app_name is required")
        if not self.user_id:
            raise ValueError("user_id is required")
        if not self.model:
            raise ValueError("model is required")
        return True
    
    def to_dict(self) -> dict:
        """Convert config to dictionary"""
        return {
            "api_key": self.api_key,
            "model": self.model,
            "app_name": self.app_name,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "log_level": self.log_level,
            "session_timeout": self.session_timeout,
            "enable_debug": self.enable_debug,
            "custom_instruction": self.custom_instruction,
        }

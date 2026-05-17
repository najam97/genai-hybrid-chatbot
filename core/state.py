"""
Multi-turn conversation state management for the Hybrid Chatbot.
Maintains conversation history and context across multiple turns.
"""

from typing import List, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json


@dataclass
class Message:
    """Represents a single message in the conversation."""
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert message to dictionary."""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


class ConversationState:
    """
    Manages multi-turn conversation context and history.
    Enables the chatbot to maintain state across multiple interactions.
    """
    
    def __init__(self, max_history: int = 20):
        """
        Initialize conversation state.
        
        Args:
            max_history: Maximum number of messages to retain in history (default: 20)
        """
        self.max_history = max_history
        self.messages: List[Message] = []
        self.context_variables: Dict = {}
        self.turn_count: int = 0
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None) -> None:
        """
        Add a message to the conversation history.
        
        Args:
            role: 'user' or 'assistant'
            content: Message content
            metadata: Optional metadata (e.g., routing decision, execution time)
        """
        message = Message(
            role=role,
            content=content,
            metadata=metadata or {}
        )
        self.messages.append(message)
        
        # Trim history if it exceeds max_history
        if len(self.messages) > self.max_history:
            self.messages = self.messages[-self.max_history:]
        
        if role == "user":
            self.turn_count += 1
    
    def get_user_messages(self) -> List[str]:
        """Get all user messages in order."""
        return [msg.content for msg in self.messages if msg.role == "user"]
    
    def get_assistant_messages(self) -> List[str]:
        """Get all assistant messages in order."""
        return [msg.content for msg in self.messages if msg.role == "assistant"]
    
    def get_conversation_history(self, include_metadata: bool = False) -> List[Dict]:
        """
        Get conversation history in OpenAI API format.
        
        Args:
            include_metadata: Whether to include metadata in output
            
        Returns:
            List of message dictionaries compatible with OpenAI API
        """
        if include_metadata:
            return [msg.to_dict() for msg in self.messages]
        else:
            return [{"role": msg.role, "content": msg.content} for msg in self.messages]
    
    def get_last_user_message(self) -> Optional[str]:
        """Get the most recent user message."""
        for msg in reversed(self.messages):
            if msg.role == "user":
                return msg.content
        return None
    
    def get_last_assistant_message(self) -> Optional[str]:
        """Get the most recent assistant message."""
        for msg in reversed(self.messages):
            if msg.role == "assistant":
                return msg.content
        return None
    
    def set_context_variable(self, key: str, value: any) -> None:
        """Set a context variable for use across conversation turns."""
        self.context_variables[key] = value
    
    def get_context_variable(self, key: str, default: any = None) -> any:
        """Get a context variable."""
        return self.context_variables.get(key, default)
    
    def clear_history(self) -> None:
        """Clear all conversation history."""
        self.messages = []
        self.turn_count = 0
        self.context_variables = {}
    
    def to_json(self) -> str:
        """Serialize conversation state to JSON."""
        return json.dumps({
            "messages": [msg.to_dict() for msg in self.messages],
            "context_variables": self.context_variables,
            "turn_count": self.turn_count
        }, default=str)
    
    def __len__(self) -> int:
        """Return number of messages in history."""
        return len(self.messages)
    
    def __str__(self) -> str:
        """String representation of conversation state."""
        return f"ConversationState(messages={len(self.messages)}, turns={self.turn_count})"

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class AgentState(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    AWAITING_APPROVAL = "awaiting_approval"
    ERROR = "error"

class EventType(str, Enum):
    # Server -> Client
    STATE_UPDATE = "STATE_UPDATE"
    AUDIO_METRICS = "AUDIO_METRICS"
    TRANSCRIPT = "TRANSCRIPT"
    SAFETY_APPROVAL_REQUEST = "SAFETY_APPROVAL_REQUEST"
    DIFF_PREVIEW = "DIFF_PREVIEW"
    OBSIDIAN_UPDATE = "OBSIDIAN_UPDATE"
    SYSTEM_METRICS = "SYSTEM_METRICS"
    NOTIFICATION = "NOTIFICATION"

    # Client -> Server
    USER_INPUT = "USER_INPUT"
    SAFETY_DECISION = "SAFETY_DECISION"
    DEEP_WORK_TOGGLE = "DEEP_WORK_TOGGLE"
    DIFF_DECISION = "DIFF_DECISION"
    REQUEST_SYNC = "REQUEST_SYNC"

class WSEvent(BaseModel):
    event: EventType
    data: Dict[str, Any] = Field(default_factory=dict)

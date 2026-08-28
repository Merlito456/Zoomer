from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from enum import Enum

class ParticipantRole(str, Enum):
    HOST = "host"
    CO_HOST = "co_host"
    PARTICIPANT = "participant"

class ParticipantStatus(str, Enum):
    ACTIVE = "active"
    AWAY = "away"
    INACTIVE = "inactive"

class Participant(BaseModel):
    id: str
    room_id: str
    name: str
    email: Optional[str] = None
    company: str
    position: str
    role: ParticipantRole
    status: ParticipantStatus = ParticipantStatus.ACTIVE
    joined_at: datetime
    left_at: Optional[datetime] = None
    is_muted: bool = False
    is_video_off: bool = True
    is_screen_sharing: bool = False
    is_hand_raised: bool = False
    avatar_color: str = "#0066FF"

class RoomSettings(BaseModel):
    allow_chat: bool = True
    allow_screen_share: bool = True
    allow_recording: bool = True
    allow_polls: bool = True
    allow_breakout_rooms: bool = True
    require_host_approval: bool = False
    waiting_room_enabled: bool = False
    auto_mute_on_join: bool = True
    host_only_presentation: bool = False
    max_participants: int = 100

class Room(BaseModel):
    id: str
    name: str
    meeting_id: str
    host_id: str
    host_name: str
    host_email: Optional[str] = None
    created_at: datetime
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    is_active: bool = False
    is_recording: bool = False
    settings: RoomSettings = RoomSettings()
    participants: List[Participant] = []

class ChatMessage(BaseModel):
    id: str
    room_id: str
    participant_id: str
    participant_name: str
    participant_avatar: Optional[str] = None
    message: str
    created_at: datetime
    is_private: bool = False
    recipient_id: Optional[str] = None
    is_pinned: bool = False

class Poll(BaseModel):
    id: str
    room_id: str
    host_id: str
    question: str
    options: List[str]
    votes: List[dict] = []
    created_at: datetime
    is_active: bool = True
    is_anonymous: bool = True

class Recording(BaseModel):
    id: str
    room_id: str
    user_id: str
    file_url: str
    duration: int
    size: int
    created_at: datetime
    is_cloud: bool = False

class BreakoutRoom(BaseModel):
    id: str
    parent_room_id: str
    name: str
    participants: List[str]
    created_at: datetime
    is_active: bool = True

from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from enum import Enum

class UserRole(str, Enum):
    HOST = "host"
    PARTICIPANT = "participant"
    VIEWER = "viewer"

class User(BaseModel):
    id: str
    email: EmailStr
    username: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class Room(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    host_id: str
    meeting_id: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    is_active: bool = False
    is_recording: bool = False
    max_participants: int = 100
    created_at: datetime
    
class RoomParticipant(BaseModel):
    room_id: str
    user_id: str
    role: UserRole
    joined_at: datetime
    left_at: Optional[datetime] = None
    is_muted: bool = False
    is_video_off: bool = False
    is_screen_sharing: bool = False

class ChatMessage(BaseModel):
    id: str
    room_id: str
    user_id: str
    username: str
    message: str
    is_private: bool = False
    recipient_id: Optional[str] = None
    created_at: datetime

class Recording(BaseModel):
    id: str
    room_id: str
    user_id: str
    file_url: str
    duration: int
    size: int
    created_at: datetime

class MeetingSettings(BaseModel):
    allow_chat: bool = True
    allow_screen_share: bool = True
    allow_recording: bool = True
    require_host_approval: bool = False
    waiting_room_enabled: bool = False
    auto_mute_on_join: bool = True
    host_only_presentation: bool = False

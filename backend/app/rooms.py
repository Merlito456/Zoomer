from fastapi import APIRouter, HTTPException, Depends, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from typing import List, Dict, Optional
import json
import uuid
from datetime import datetime
import os

from .database import db
from .models import ParticipantRole, RoomSettings
from .livekit_service import LiveKitService

router = APIRouter()
livekit = LiveKitService()

# WebSocket connection manager for real-time updates
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, room_id: str, websocket: WebSocket):
        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = []
        self.active_connections[room_id].append(websocket)
    
    def disconnect(self, room_id: str, websocket: WebSocket):
        if room_id in self.active_connections:
            try:
                self.active_connections[room_id].remove(websocket)
            except ValueError:
                pass
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]
    
    async def broadcast(self, room_id: str, message: dict):
        if room_id in self.active_connections:
            for connection in self.active_connections[room_id]:
                try:
                    await connection.send_json(message)
                except:
                    pass

manager = ConnectionManager()

@router.post("/api/rooms/create")
async def create_room(request: Request):
    data = await request.json()
    name = data.get("name", "Meeting")
    host_name = data.get("host_name", "Host")
    host_email = data.get("host_email")
    host_id = str(uuid.uuid4())
    
    settings = data.get("settings", {})
    
    room = db.create_room(name, host_id, host_name, host_email, settings)
    
    # Add host as participant
    db.add_participant(
        room_id=room["id"],
        name=host_name,
        company=data.get("company", ""),
        position=data.get("position", ""),
        role=ParticipantRole.HOST,
        email=host_email
    )
    
    # Generate token for host
    token = livekit.generate_token(
        room_name=room["meeting_id"],
        identity=host_id,
        name=host_name,
        metadata={"role": "host", "email": host_email or ""}
    )
    
    return {
        "room": room,
        "token": token,
        "participant_id": host_id,
        "livekit_url": os.getenv("LIVEKIT_URL", "ws://localhost:7880").replace("ws://", "http://").replace("wss://", "https://")
    }

@router.post("/api/rooms/join/{meeting_id}")
async def join_room(request: Request, meeting_id: str):
    data = await request.json()
    
    room = db.get_room_by_meeting_id(meeting_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Check max participants
    participants = db.get_participants(room["id"])
    settings = json.loads(room.get("settings", "{}"))
    max_participants = settings.get("max_participants", 100)
    if len(participants) >= max_participants:
        raise HTTPException(status_code=400, detail="Room is full")
    
    # Add participant
    participant = db.add_participant(
        room_id=room["id"],
        name=data["name"],
        company=data.get("company", ""),
        position=data.get("position", ""),
        role=ParticipantRole.PARTICIPANT,
        email=data.get("email")
    )
    
    # Update room active status if not active
    if not room["is_active"]:
        db.update_room_status(room["id"], True)
    
    # Generate token
    token = livekit.generate_token(
        room_name=meeting_id,
        identity=participant["id"],
        name=data["name"],
        metadata={
            "role": "participant",
            "company": data.get("company", ""),
            "position": data.get("position", "")
        }
    )
    
    # Broadcast participant joined
    await manager.broadcast(room["id"], {
        "type": "participant_joined",
        "data": participant
    })
    
    return {
        "room": room,
        "token": token,
        "participant_id": participant["id"],
        "livekit_url": os.getenv("LIVEKIT_URL", "ws://localhost:7880").replace("ws://", "http://").replace("wss://", "https://")
    }

@router.post("/api/rooms/leave/{room_id}/{participant_id}")
async def leave_room(room_id: str, participant_id: str):
    participant = db.get_participant(participant_id)
    if participant:
        db.remove_participant(participant_id)
        
        # Broadcast participant left
        await manager.broadcast(room_id, {
            "type": "participant_left",
            "data": {"participant_id": participant_id}
        })
        
        # Check if host left (end meeting)
        room = db.get_room_by_id(room_id)
        if room and room["host_id"] == participant_id:
            db.update_room_status(room_id, False)
            await manager.broadcast(room_id, {
                "type": "meeting_ended",
                "data": {"message": "Host has left the meeting"}
            })
    
    return {"message": "Left successfully"}

@router.get("/api/rooms")
async def get_rooms():
    return db.get_all_rooms()

@router.get("/api/rooms/{meeting_id}")
async def get_room(meeting_id: str):
    room = db.get_room_by_meeting_id(meeting_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    participants = db.get_participants(room["id"])
    room["participants"] = participants
    room["settings"] = json.loads(room.get("settings", "{}"))
    return room

@router.get("/api/rooms/{meeting_id}/participants")
async def get_participants(meeting_id: str):
    room = db.get_room_by_meeting_id(meeting_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    return db.get_participants(room["id"])

@router.post("/api/rooms/{meeting_id}/mute/{participant_id}")
async def mute_participant(meeting_id: str, participant_id: str):
    db.update_participant(participant_id, is_muted=True)
    
    # Broadcast mute status
    room = db.get_room_by_meeting_id(meeting_id)
    if room:
        await manager.broadcast(room["id"], {
            "type": "participant_muted",
            "data": {"participant_id": participant_id}
        })
    
    return {"message": "Participant muted"}

@router.post("/api/rooms/{meeting_id}/unmute/{participant_id}")
async def unmute_participant(meeting_id: str, participant_id: str):
    db.update_participant(participant_id, is_muted=False)
    
    room = db.get_room_by_meeting_id(meeting_id)
    if room:
        await manager.broadcast(room["id"], {
            "type": "participant_unmuted",
            "data": {"participant_id": participant_id}
        })
    
    return {"message": "Participant unmuted"}

@router.post("/api/rooms/{meeting_id}/hand-raise/{participant_id}")
async def raise_hand(meeting_id: str, participant_id: str):
    participant = db.get_participant(participant_id)
    if participant:
        db.update_participant(participant_id, is_hand_raised=not participant.get("is_hand_raised", False))
        
        room = db.get_room_by_meeting_id(meeting_id)
        if room:
            await manager.broadcast(room["id"], {
                "type": "hand_raised",
                "data": {
                    "participant_id": participant_id,
                    "is_raised": not participant.get("is_hand_raised", False)
                }
            })
    
    return {"message": "Hand status toggled"}

@router.post("/api/rooms/{meeting_id}/record/start")
async def start_recording(meeting_id: str, request: Request):
    data = await request.json()
    participant_id = data.get("participant_id")
    
    room = db.get_room_by_meeting_id(meeting_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Check if user is host
    if room["host_id"] != participant_id:
        raise HTTPException(status_code=403, detail="Only host can start recording")
    
    db.update_room_status(room["id"], is_active=True, is_recording=True)
    
    await manager.broadcast(room["id"], {
        "type": "recording_started",
        "data": {"recording": True}
    })
    
    return {"message": "Recording started"}

@router.post("/api/rooms/{meeting_id}/record/stop")
async def stop_recording(meeting_id: str, request: Request):
    data = await request.json()
    participant_id = data.get("participant_id")
    
    room = db.get_room_by_meeting_id(meeting_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Check if user is host
    if room["host_id"] != participant_id:
        raise HTTPException(status_code=403, detail="Only host can stop recording")
    
    db.update_room_status(room["id"], is_active=True, is_recording=False)
    
    await manager.broadcast(room["id"], {
        "type": "recording_stopped",
        "data": {"recording": False}
    })
    
    return {"message": "Recording stopped"}

@router.post("/api/rooms/{meeting_id}/polls/create")
async def create_poll(meeting_id: str, request: Request):
    data = await request.json()
    host_id = data.get("host_id")
    question = data.get("question")
    options = data.get("options", [])
    is_anonymous = data.get("is_anonymous", True)
    
    room = db.get_room_by_meeting_id(meeting_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    poll = db.create_poll(room["id"], host_id, question, options, is_anonymous)
    
    await manager.broadcast(room["id"], {
        "type": "poll_created",
        "data": poll
    })
    
    return poll

@router.post("/api/rooms/{meeting_id}/polls/{poll_id}/vote")
async def vote_poll(meeting_id: str, poll_id: str, request: Request):
    data = await request.json()
    participant_id = data.get("participant_id")
    option_index = data.get("option_index")
    
    room = db.get_room_by_meeting_id(meeting_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    db.vote_poll(poll_id, option_index, participant_id)
    
    poll = db.get_poll(poll_id)
    await manager.broadcast(room["id"], {
        "type": "poll_updated",
        "data": poll
    })
    
    return {"message": "Vote recorded"}

# WebSocket for real-time updates and chat
@router.websocket("/ws/{meeting_id}")
async def websocket_endpoint(websocket: WebSocket, meeting_id: str):
    # Get participant info from query params
    participant_id = websocket.query_params.get("participant_id")
    if not participant_id:
        await websocket.close(code=4001)
        return
    
    room = db.get_room_by_meeting_id(meeting_id)
    if not room:
        await websocket.close(code=4002)
        return
    
    participant = db.get_participant(participant_id)
    if not participant:
        await websocket.close(code=4003)
        return
    
    await manager.connect(room["id"], websocket)
    
    try:
        # Send initial data
        participants = db.get_participants(room["id"])
        await websocket.send_json({
            "type": "initial",
            "data": {
                "room": room,
                "participants": participants,
                "messages": db.get_chat_messages(room["id"])
            }
        })
        
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            msg_type = message_data.get("type")
            
            if msg_type == "chat":
                # Save and broadcast chat message
                msg = db.save_chat_message(
                    room_id=room["id"],
                    participant_id=participant_id,
                    participant_name=participant["name"],
                    message=message_data.get("message", "")
                )
                await manager.broadcast(room["id"], {
                    "type": "chat",
                    "data": msg
                })
            
            elif msg_type == "status_update":
                # Update participant status
                status = message_data.get("status")
                db.update_participant(participant_id, status=status)
                await manager.broadcast(room["id"], {
                    "type": "status_update",
                    "data": {
                        "participant_id": participant_id,
                        "status": status
                    }
                })
    
    except WebSocketDisconnect:
        manager.disconnect(room["id"], websocket)

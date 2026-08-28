import os
import json
from livekit import api
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict

class LiveKitService:
    def __init__(self):
        self.api_key = os.getenv("LIVEKIT_API_KEY", "devkey")
        self.api_secret = os.getenv("LIVEKIT_API_SECRET", "secret")
        self.url = os.getenv("LIVEKIT_URL", "ws://localhost:7880")
        
        self.client = api.LiveKitAPI(
            self.url,
            api_key=self.api_key,
            api_secret=self.api_secret
        )
    
    def generate_token(
        self,
        room_name: str,
        identity: str,
        name: str = None,
        metadata: dict = None
    ) -> str:
        token = (
            jwt.AccessToken(self.api_key, self.api_secret)
            .with_identity(identity)
            .with_name(name or identity)
            .with_grants(
                jwt.VideoGrants(
                    room_join=True,
                    room=room_name,
                    can_publish=True,
                    can_subscribe=True,
                    can_publish_data=True,
                    can_update_metadata=True,
                )
            )
        )
        
        if metadata:
            token.with_metadata(json.dumps(metadata))
        
        return token.to_jwt()
    
    async def list_participants(self, room_name: str) -> list:
        try:
            result = await self.client.room.list_participants(
                api.ListParticipantsRequest(room=room_name)
            )
            return result.participants
        except Exception as e:
            print(f"Error listing participants: {e}")
            return []
    
    async def remove_participant(self, room_name: str, identity: str):
        try:
            await self.client.room.remove_participant(
                api.RoomParticipantIdentity(
                    room=room_name,
                    identity=identity
                )
            )
        except Exception as e:
            print(f"Error removing participant: {e}")
    
    async def mute_participant(self, room_name: str, identity: str, mute: bool = True):
        try:
            await self.client.room.mute_participant(
                api.RoomMuteParticipantRequest(
                    room=room_name,
                    identity=identity,
                    mute=mute
                )
            )
        except Exception as e:
            print(f"Error muting participant: {e}")
    
    async def update_participant_metadata(self, room_name: str, identity: str, metadata: dict):
        try:
            await self.client.room.update_participant_metadata(
                api.RoomUpdateParticipantMetadataRequest(
                    room=room_name,
                    identity=identity,
                    metadata=json.dumps(metadata)
                )
            )
        except Exception as e:
            print(f"Error updating participant metadata: {e}")

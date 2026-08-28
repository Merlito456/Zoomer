import sqlite3
import json
from datetime import datetime
from typing import List, Optional, Dict
import uuid
from contextlib import contextmanager

class Database:
    def __init__(self, db_path="zoom.db"):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Rooms table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rooms (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                meeting_id TEXT UNIQUE NOT NULL,
                host_id TEXT NOT NULL,
                host_name TEXT NOT NULL,
                host_email TEXT,
                created_at TEXT NOT NULL,
                start_time TEXT,
                end_time TEXT,
                is_active INTEGER DEFAULT 0,
                is_recording INTEGER DEFAULT 0,
                settings TEXT DEFAULT '{}'
            )
        ''')
        
        # Participants table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS participants (
                id TEXT PRIMARY KEY,
                room_id TEXT NOT NULL,
                name TEXT NOT NULL,
                email TEXT,
                company TEXT NOT NULL,
                position TEXT NOT NULL,
                role TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                joined_at TEXT NOT NULL,
                left_at TEXT,
                is_muted INTEGER DEFAULT 0,
                is_video_off INTEGER DEFAULT 1,
                is_screen_sharing INTEGER DEFAULT 0,
                is_hand_raised INTEGER DEFAULT 0,
                avatar_color TEXT DEFAULT '#0066FF',
                FOREIGN KEY (room_id) REFERENCES rooms (id)
            )
        ''')
        
        # Chat messages table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_messages (
                id TEXT PRIMARY KEY,
                room_id TEXT NOT NULL,
                participant_id TEXT NOT NULL,
                participant_name TEXT NOT NULL,
                participant_avatar TEXT,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL,
                is_private INTEGER DEFAULT 0,
                recipient_id TEXT,
                is_pinned INTEGER DEFAULT 0,
                FOREIGN KEY (room_id) REFERENCES rooms (id)
            )
        ''')
        
        # Polls table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS polls (
                id TEXT PRIMARY KEY,
                room_id TEXT NOT NULL,
                host_id TEXT NOT NULL,
                question TEXT NOT NULL,
                options TEXT NOT NULL,
                votes TEXT DEFAULT '[]',
                created_at TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                is_anonymous INTEGER DEFAULT 1,
                FOREIGN KEY (room_id) REFERENCES rooms (id)
            )
        ''')
        
        # Recordings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recordings (
                id TEXT PRIMARY KEY,
                room_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                file_url TEXT NOT NULL,
                duration INTEGER DEFAULT 0,
                size INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                is_cloud INTEGER DEFAULT 0,
                FOREIGN KEY (room_id) REFERENCES rooms (id)
            )
        ''')
        
        # Breakout rooms table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS breakout_rooms (
                id TEXT PRIMARY KEY,
                parent_room_id TEXT NOT NULL,
                name TEXT NOT NULL,
                participants TEXT DEFAULT '[]',
                created_at TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                FOREIGN KEY (parent_room_id) REFERENCES rooms (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    @contextmanager
    def get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def create_room(self, name: str, host_id: str, host_name: str, host_email: str = None, settings: dict = None) -> dict:
        room_id = str(uuid.uuid4())
        meeting_id = f"{uuid.uuid4().hex[:8].upper()}"
        
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO rooms (id, name, meeting_id, host_id, host_name, host_email, created_at, is_active, settings)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)
            ''', (room_id, name, meeting_id, host_id, host_name, host_email, datetime.utcnow().isoformat(), json.dumps(settings or {})))
            conn.commit()
        
        return self.get_room_by_meeting_id(meeting_id)
    
    def get_room_by_meeting_id(self, meeting_id: str) -> Optional[dict]:
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM rooms WHERE meeting_id = ?', (meeting_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None
    
    def get_room_by_id(self, room_id: str) -> Optional[dict]:
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM rooms WHERE id = ?', (room_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None
    
    def get_all_rooms(self) -> List[dict]:
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM rooms ORDER BY created_at DESC')
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def add_participant(self, room_id: str, name: str, company: str, position: str, role: str, email: str = None) -> dict:
        participant_id = str(uuid.uuid4())
        avatar_color = self._get_avatar_color(name)
        
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO participants (id, room_id, name, email, company, position, role, joined_at, avatar_color)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (participant_id, room_id, name, email, company, position, role, datetime.utcnow().isoformat(), avatar_color))
            conn.commit()
        
        return self.get_participant(participant_id)
    
    def get_participant(self, participant_id: str) -> Optional[dict]:
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM participants WHERE id = ?', (participant_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None
    
    def get_participants(self, room_id: str) -> List[dict]:
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM participants 
                WHERE room_id = ? AND left_at IS NULL
                ORDER BY joined_at
            ''', (room_id,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def update_participant(self, participant_id: str, **kwargs):
        with self.get_conn() as conn:
            cursor = conn.cursor()
            updates = []
            values = []
            for key, value in kwargs.items():
                if key in ['is_muted', 'is_video_off', 'is_screen_sharing', 'is_hand_raised', 'status']:
                    updates.append(f"{key} = ?")
                    values.append(1 if value else 0 if isinstance(value, bool) else value)
            if updates:
                values.append(participant_id)
                cursor.execute(f'UPDATE participants SET {", ".join(updates)} WHERE id = ?', values)
                conn.commit()
    
    def remove_participant(self, participant_id: str):
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE participants SET left_at = ? WHERE id = ?', 
                         (datetime.utcnow().isoformat(), participant_id))
            conn.commit()
    
    def save_chat_message(self, room_id: str, participant_id: str, participant_name: str, message: str) -> dict:
        msg_id = str(uuid.uuid4())
        
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO chat_messages (id, room_id, participant_id, participant_name, message, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (msg_id, room_id, participant_id, participant_name, message, datetime.utcnow().isoformat()))
            conn.commit()
        
        return self.get_chat_message(msg_id)
    
    def get_chat_message(self, message_id: str) -> Optional[dict]:
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM chat_messages WHERE id = ?', (message_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None
    
    def get_chat_messages(self, room_id: str, limit: int = 50) -> List[dict]:
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM chat_messages 
                WHERE room_id = ? 
                ORDER BY created_at DESC LIMIT ?
            ''', (room_id, limit))
            rows = cursor.fetchall()
            return [dict(row) for row in reversed(rows)]
    
    def create_poll(self, room_id: str, host_id: str, question: str, options: List[str], is_anonymous: bool = True) -> dict:
        poll_id = str(uuid.uuid4())
        
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO polls (id, room_id, host_id, question, options, votes, created_at, is_anonymous)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (poll_id, room_id, host_id, question, json.dumps(options), '[]', datetime.utcnow().isoformat(), 1 if is_anonymous else 0))
            conn.commit()
        
        return self.get_poll(poll_id)
    
    def get_poll(self, poll_id: str) -> Optional[dict]:
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM polls WHERE id = ?', (poll_id,))
            row = cursor.fetchone()
            if row:
                result = dict(row)
                result['options'] = json.loads(result['options'])
                result['votes'] = json.loads(result['votes'])
                return result
        return None
    
    def get_room_polls(self, room_id: str) -> List[dict]:
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM polls WHERE room_id = ? ORDER BY created_at DESC', (room_id,))
            rows = cursor.fetchall()
            polls = []
            for row in rows:
                poll = dict(row)
                poll['options'] = json.loads(poll['options'])
                poll['votes'] = json.loads(poll['votes'])
                polls.append(poll)
            return polls
    
    def vote_poll(self, poll_id: str, option_index: int, participant_id: str):
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT votes FROM polls WHERE id = ?', (poll_id,))
            row = cursor.fetchone()
            if row:
                votes = json.loads(row[0])
                votes.append({
                    'option': option_index,
                    'participant_id': participant_id,
                    'timestamp': datetime.utcnow().isoformat()
                })
                cursor.execute('UPDATE polls SET votes = ? WHERE id = ?', (json.dumps(votes), poll_id))
                conn.commit()
    
    def update_room_status(self, room_id: str, is_active: bool, is_recording: bool = None):
        with self.get_conn() as conn:
            cursor = conn.cursor()
            updates = []
            values = []
            
            if is_active is not None:
                updates.append("is_active = ?")
                values.append(1 if is_active else 0)
                if is_active:
                    updates.append("start_time = ?")
                    values.append(datetime.utcnow().isoformat())
                else:
                    updates.append("end_time = ?")
                    values.append(datetime.utcnow().isoformat())
            
            if is_recording is not None:
                updates.append("is_recording = ?")
                values.append(1 if is_recording else 0)
            
            if updates:
                values.append(room_id)
                cursor.execute(f'UPDATE rooms SET {", ".join(updates)} WHERE id = ?', values)
                conn.commit()
    
    def save_recording(self, room_id: str, user_id: str, file_url: str, duration: int = 0, size: int = 0) -> dict:
        recording_id = str(uuid.uuid4())
        
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO recordings (id, room_id, user_id, file_url, duration, size, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (recording_id, room_id, user_id, file_url, duration, size, datetime.utcnow().isoformat()))
            conn.commit()
        
        return self.get_recording(recording_id)
    
    def get_recording(self, recording_id: str) -> Optional[dict]:
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM recordings WHERE id = ?', (recording_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None
    
    def get_room_recordings(self, room_id: str) -> List[dict]:
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM recordings WHERE room_id = ? ORDER BY created_at DESC', (room_id,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def create_breakout_room(self, parent_room_id: str, name: str, participants: List[str]) -> dict:
        breakout_id = str(uuid.uuid4())
        
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO breakout_rooms (id, parent_room_id, name, participants, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (breakout_id, parent_room_id, name, json.dumps(participants), datetime.utcnow().isoformat()))
            conn.commit()
        
        return self.get_breakout_room(breakout_id)
    
    def get_breakout_room(self, breakout_id: str) -> Optional[dict]:
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM breakout_rooms WHERE id = ?', (breakout_id,))
            row = cursor.fetchone()
            if row:
                result = dict(row)
                result['participants'] = json.loads(result['participants'])
                return result
        return None
    
    def _get_avatar_color(self, name: str) -> str:
        colors = [
            '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7',
            '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9',
            '#F8C471', '#82E0AA', '#F1948A', '#85929E', '#73C6B6'
        ]
        index = sum(ord(c) for c in name) % len(colors)
        return colors[index]

db = Database()

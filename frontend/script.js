// ============================================================
// ZOOM CLONE PRO - Complete Frontend JavaScript
// ============================================================

// ===== State =====
const state = {
    currentView: 'dashboard',
    currentRoom: null,
    currentMeetingId: null,
    participantId: null,
    isHost: false,
    isMuted: false,
    isVideoOff: true,
    isScreenSharing: false,
    isRecording: false,
    isChatOpen: false,
    isParticipantsOpen: false,
    participants: [],
    messages: [],
    room: null,
    ws: null,
    livekitRoom: null,
    localTrack: null,
    pendingMeetingId: null,
};

// ===== DOM References =====
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const DOM = {
    // Navigation
    navNewMeeting: $('#navNewMeeting'),
    navJoinMeeting: $('#navJoinMeeting'),
    
    // Views
    dashboardView: $('#dashboardView'),
    meetingView: $('#meetingView'),
    roomsList: $('#roomsList'),
    
    // Dashboard
    createMeetingBtn: $('#createMeetingBtn'),
    totalMeetings: $('#totalMeetings'),
    activeParticipants: $('#activeParticipants'),
    totalRecordings: $('#totalRecordings'),
    
    // Meeting
    meetingContainer: $('#meetingContainer'),
    videoContainer: $('#videoContainer'),
    meetingTitle: $('#meetingTitle'),
    participantCount: $('#participantCount'),
    recordingStatus: $('#recordingStatus'),
    
    // Controls
    toggleAudio: $('#toggleAudio'),
    toggleVideo: $('#toggleVideo'),
    toggleScreenShare: $('#toggleScreenShare'),
    toggleChat: $('#toggleChat'),
    toggleParticipants: $('#toggleParticipants'),
    recordBtn: $('#recordBtn'),
    handRaiseBtn: $('#handRaiseBtn'),
    leaveMeetingBtn: $('#leaveMeetingBtn'),
    
    // Chat
    chatPanel: $('#chatPanel'),
    chatMessages: $('#chatMessages'),
    chatInput: $('#chatInput'),
    sendChatBtn: $('#sendChatBtn'),
    closeChatBtn: $('#closeChatBtn'),
    
    // Participants
    participantsPanel: $('#participantsPanel'),
    participantsList: $('#participantsList'),
    closeParticipantsBtn: $('#closeParticipantsBtn'),
    
    // Modals
    joinModal: $('#joinModal'),
    createModal: $('#createModal'),
    participantModal: $('#participantModal'),
    joinMeetingId: $('#joinMeetingId'),
    joinMeetingSubmit: $('#joinMeetingSubmit'),
    roomName: $('#roomName'),
    hostName: $('#hostName'),
    hostCompany: $('#hostCompany'),
    hostPosition: $('#hostPosition'),
    createRoomSubmit: $('#createRoomSubmit'),
    participantName: $('#participantName'),
    participantCompany: $('#participantCompany'),
    participantPosition: $('#participantPosition'),
    participantSubmit: $('#participantSubmit'),
    closeJoinModal: $('#closeJoinModal'),
    closeCreateModal: $('#closeCreateModal'),
};

// ===== Toast System =====
function showToast(title, message, type = 'info', duration = 4000) {
    const container = document.querySelector('.toast-container') || (() => {
        const div = document.createElement('div');
        div.className = 'toast-container';
        document.body.appendChild(div);
        return div;
    })();
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <div class="toast-title">${title}</div>
        <div class="toast-message">${message}</div>
    `;
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

// ===== Modal Helpers =====
function openModal(modal) {
    modal.classList.add('show');
    modal.style.display = 'flex';
}

function closeModal(modal) {
    modal.classList.remove('show');
    modal.style.display = 'none';
}

function closeAllModals() {
    $$('.modal.show').forEach(m => {
        m.classList.remove('show');
        m.style.display = 'none';
    });
}

// ===== API Calls =====
const API = {
    async createRoom(data) {
        const res = await fetch('/api/rooms/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (!res.ok) throw new Error('Failed to create room');
        return res.json();
    },
    
    async joinRoom(meetingId, data) {
        const res = await fetch(`/api/rooms/join/${meetingId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (!res.ok) throw new Error('Failed to join room');
        return res.json();
    },
    
    async leaveRoom(roomId, participantId) {
        const res = await fetch(`/api/rooms/leave/${roomId}/${participantId}`, {
            method: 'POST'
        });
        return res.json();
    },
    
    async getRooms() {
        const res = await fetch('/api/rooms');
        if (!res.ok) throw new Error('Failed to fetch rooms');
        return res.json();
    },
    
    async getRoom(meetingId) {
        const res = await fetch(`/api/rooms/${meetingId}`);
        if (!res.ok) throw new Error('Failed to fetch room');
        return res.json();
    },
    
    async getStats() {
        const res = await fetch('/api/stats');
        if (!res.ok) throw new Error('Failed to fetch stats');
        return res.json();
    },
    
    async toggleMute(meetingId, participantId) {
        const res = await fetch(`/api/rooms/${meetingId}/mute/${participantId}`, {
            method: 'POST'
        });
        return res.json();
    },
    
    async toggleUnmute(meetingId, participantId) {
        const res = await fetch(`/api/rooms/${meetingId}/unmute/${participantId}`, {
            method: 'POST'
        });
        return res.json();
    },
    
    async raiseHand(meetingId, participantId) {
        const res = await fetch(`/api/rooms/${meetingId}/hand-raise/${participantId}`, {
            method: 'POST'
        });
        return res.json();
    },
    
    async startRecording(meetingId, participantId) {
        const res = await fetch(`/api/rooms/${meetingId}/record/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ participant_id: participantId })
        });
        return res.json();
    },
    
    async stopRecording(meetingId, participantId) {
        const res = await fetch(`/api/rooms/${meetingId}/record/stop`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ participant_id: participantId })
        });
        return res.json();
    }
};

// ===== LiveKit Integration =====
const LiveKit = {
    async connect(meetingId, token, url) {
        try {
            const room = new LivekitClient.Room();
            
            room.on('participantConnected', (participant) => {
                console.log('Participant connected:', participant.identity);
                updateParticipantsList();
            });
            
            room.on('participantDisconnected', (participant) => {
                console.log('Participant disconnected:', participant.identity);
                updateParticipantsList();
            });
            
            room.on('trackSubscribed', (track, publication, participant) => {
                if (track.kind === 'video' && track.mediaStream) {
                    const container = getVideoContainer(participant.identity);
                    if (container) {
                        const video = document.createElement('video');
                        video.srcObject = track.mediaStream;
                        video.autoplay = true;
                        video.playsInline = true;
                        container.appendChild(video);
                    }
                }
            });
            
            room.on('trackUnsubscribed', (track, publication, participant) => {
                if (track.kind === 'video' && track.mediaStream) {
                    const container = getVideoContainer(participant.identity);
                    if (container) {
                        container.innerHTML = '';
                        container.appendChild(createParticipantLabel(participant.identity));
                    }
                }
            });
            
            await room.connect(url, token);
            state.livekitRoom = room;
            
            // Publish local tracks
            await room.localParticipant.setMicrophoneEnabled(!state.isMuted);
            await room.localParticipant.setCameraEnabled(!state.isVideoOff);
            
            return room;
        } catch (error) {
            console.error('LiveKit connection error:', error);
            showToast('Connection Error', error.message, 'error');
            throw error;
        }
    },
    
    async disconnect() {
        if (state.livekitRoom) {
            state.livekitRoom.disconnect();
            state.livekitRoom = null;
        }
    }
};

// ===== Video Grid Helpers =====
function getVideoContainer(identity) {
    const grid = document.querySelector('.video-grid');
    if (!grid) return null;
    let container = grid.querySelector(`[data-participant="${identity}"]`);
    if (!container) {
        container = document.createElement('div');
        container.className = 'video-participant';
        container.dataset.participant = identity;
        grid.appendChild(container);
    }
    return container;
}

function createParticipantLabel(name) {
    const label = document.createElement('div');
    label.className = 'participant-label';
    label.textContent = name;
    return label;
}

function renderVideoGrid() {
    const container = DOM.videoContainer;
    container.innerHTML = `
        <div class="video-grid" id="videoGrid"></div>
    `;
    
    // Add local participant
    if (state.participantId) {
        const grid = document.getElementById('videoGrid');
        const div = document.createElement('div');
        div.className = 'video-participant';
        div.dataset.participant = state.participantId;
        div.style.background = '#2A2A3A';
        
        const avatar = document.createElement('div');
        avatar.className = 'participant-avatar';
        const name = state.room?.host_name || 'You';
        avatar.textContent = name.charAt(0).toUpperCase();
        avatar.style.background = getAvatarColor(name);
        div.appendChild(avatar);
        
        const label = document.createElement('div');
        label.className = 'participant-label';
        label.textContent = `${name} (You)`;
        div.appendChild(label);
        
        grid.appendChild(div);
    }
}

function getAvatarColor(name) {
    const colors = ['#0066FF', '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#F7DC6F'];
    const index = name.split('').reduce((acc, c) => acc + c.charCodeAt(0), 0) % colors.length;
    return colors[index];
}

// ===== WebSocket Connection =====
function connectWebSocket(meetingId, participantId) {
    const ws = new WebSocket(`ws://${window.location.host}/ws/${meetingId}?participant_id=${participantId}`);
    
    ws.onopen = () => {
        console.log('WebSocket connected');
        state.ws = ws;
    };
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
    };
    
    ws.onclose = () => {
        console.log('WebSocket disconnected');
        state.ws = null;
    };
    
    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        showToast('Connection Error', 'Lost connection to server', 'error');
    };
}

function handleWebSocketMessage(data) {
    switch (data.type) {
        case 'initial':
            state.room = data.data.room;
            state.participants = data.data.participants;
            state.messages = data.data.messages || [];
            updateUI();
            renderMessages();
            break;
            
        case 'chat':
            state.messages.push(data.data);
            renderMessages();
            break;
            
        case 'participant_joined':
            state.participants.push(data.data);
            updateUI();
            break;
            
        case 'participant_left':
            state.participants = state.participants.filter(p => p.id !== data.data.participant_id);
            updateUI();
            break;
            
        case 'participant_muted':
            const p = state.participants.find(p => p.id === data.data.participant_id);
            if (p) p.is_muted = true;
            updateUI();
            break;
            
        case 'participant_unmuted':
            const p2 = state.participants.find(p => p.id === data.data.participant_id);
            if (p2) p2.is_muted = false;
            updateUI();
            break;
            
        case 'hand_raised':
            const p3 = state.participants.find(p => p.id === data.data.participant_id);
            if (p3) p3.is_hand_raised = data.data.is_raised;
            updateUI();
            break;
            
        case 'recording_started':
            state.isRecording = true;
            DOM.recordingStatus.className = 'recording-dot active';
            showToast('Recording', 'Meeting recording has started', 'info');
            break;
            
        case 'recording_stopped':
            state.isRecording = false;
            DOM.recordingStatus.className = 'recording-dot';
            showToast('Recording', 'Recording has stopped', 'info');
            break;
            
        case 'meeting_ended':
            showToast('Meeting Ended', 'Host has ended the meeting', 'warning');
            leaveMeeting();
            break;
    }
}

// ===== UI Updates =====
function updateUI() {
    // Update participant count
    const count = state.participants.length;
    DOM.participantCount.textContent = `${count} participant${count !== 1 ? 's' : ''}`;
    
    // Update meeting title
    if (state.room) {
        DOM.meetingTitle.textContent = state.room.name || 'Meeting';
    }
    
    // Update participants list
    renderParticipantsList();
    
    // Update audio button
    DOM.toggleAudio.className = `control-btn${state.isMuted ? ' muted' : ''}`;
    DOM.toggleAudio.querySelector('.material-icons').textContent = state.isMuted ? 'mic_off' : 'mic';
    DOM.toggleAudio.querySelector('.control-label').textContent = state.isMuted ? 'Unmute' : 'Mute';
    
    // Update video button
    DOM.toggleVideo.className = `control-btn${state.isVideoOff ? '' : ' active'}`;
    DOM.toggleVideo.querySelector('.material-icons').textContent = state.isVideoOff ? 'videocam_off' : 'videocam';
}

function renderMessages() {
    const container = DOM.chatMessages;
    container.innerHTML = '';
    
    state.messages.forEach(msg => {
        const div = document.createElement('div');
        div.className = `chat-message${msg.participant_id === state.participantId ? ' self' : ''}`;
        
        const avatar = document.createElement('div');
        avatar.className = 'msg-avatar';
        avatar.textContent = msg.participant_name.charAt(0).toUpperCase();
        avatar.style.background = getAvatarColor(msg.participant_name);
        
        const content = document.createElement('div');
        content.className = 'msg-content';
        content.innerHTML = `
            <div class="msg-name">${msg.participant_name}</div>
            <div class="msg-text">${escapeHtml(msg.message)}</div>
            <div class="msg-time">${new Date(msg.created_at).toLocaleTimeString()}</div>
        `;
        
        div.appendChild(avatar);
        div.appendChild(content);
        container.appendChild(div);
    });
    
    container.scrollTop = container.scrollHeight;
}

function renderParticipantsList() {
    const container = DOM.participantsList;
    container.innerHTML = '';
    
    state.participants.forEach(p => {
        const div = document.createElement('div');
        div.className = 'participant-item';
        
        const avatar = document.createElement('div');
        avatar.className = 'p-avatar';
        avatar.textContent = p.name.charAt(0).toUpperCase();
        avatar.style.background = p.avatar_color || getAvatarColor(p.name);
        
        const info = document.createElement('div');
        info.className = 'p-info';
        info.innerHTML = `
            <div class="p-name">${p.name} ${p.role === 'host' ? '👑' : ''}</div>
            <div class="p-company">${p.company} • ${p.position}</div>
        `;
        
        const status = document.createElement('div');
        status.className = `p-status ${p.role}`;
        status.textContent = p.role === 'host' ? 'Host' : 'Participant';
        
        if (p.is_muted) {
            const muteIcon = document.createElement('span');
            muteIcon.textContent = ' 🔇';
            muteIcon.style.fontSize = '0.8rem';
            info.querySelector('.p-name').appendChild(muteIcon);
        }
        
        if (p.is_hand_raised) {
            const handIcon = document.createElement('span');
            handIcon.textContent = ' ✋';
            handIcon.style.fontSize = '0.8rem';
            info.querySelector('.p-name').appendChild(handIcon);
        }
        
        div.appendChild(avatar);
        div.appendChild(info);
        div.appendChild(status);
        container.appendChild(div);
    });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ===== Dashboard =====
async function loadDashboard() {
    try {
        const [rooms, stats] = await Promise.all([
            API.getRooms(),
            API.getStats()
        ]);
        
        renderRooms(rooms);
        DOM.totalMeetings.textContent = stats.total_rooms || 0;
        DOM.activeParticipants.textContent = stats.total_participants || 0;
    } catch (error) {
        console.error('Error loading dashboard:', error);
        showToast('Error', 'Failed to load dashboard', 'error');
    }
}

function renderRooms(rooms) {
    const container = DOM.roomsList;
    container.innerHTML = '';
    
    if (!rooms || rooms.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <span class="material-icons" style="font-size: 48px; color: #C4C9D4;">meeting_room</span>
                <h3>No meetings yet</h3>
                <p>Create your first meeting to get started</p>
            </div>
        `;
        return;
    }
    
    rooms.forEach(room => {
        const card = document.createElement('div');
        card.className = 'room-card';
        card.innerHTML = `
            <div class="room-header">
                <div>
                    <div class="room-name">${room.name}</div>
                    <div class="meeting-id">ID: ${room.meeting_id}</div>
                </div>
                <span class="status-dot ${room.is_active ? 'active' : 'inactive'}"></span>
            </div>
            <div class="room-meta">
                Host: ${room.host_name}
            </div>
            <div class="room-status">
                <span class="participant-count">
                    <span class="material-icons" style="font-size: 16px;">people</span>
                    ${room.participant_count || 0} participants
                </span>
            </div>
            <div class="room-actions">
                <button class="btn-sm btn-join" data-meeting-id="${room.meeting_id}">Join</button>
                <button class="btn-sm btn-copy" data-meeting-id="${room.meeting_id}">Copy ID</button>
            </div>
        `;
        
        card.querySelector('.btn-join').addEventListener('click', (e) => {
            e.stopPropagation();
            joinMeeting(room.meeting_id);
        });
        
        card.querySelector('.btn-copy').addEventListener('click', (e) => {
            e.stopPropagation();
            navigator.clipboard.writeText(room.meeting_id).then(() => {
                showToast('Copied!', 'Meeting ID copied to clipboard', 'success');
            });
        });
        
        card.addEventListener('click', () => {
            joinMeeting(room.meeting_id);
        });
        
        container.appendChild(card);
    });
}

// ===== Meeting Functions =====
async function joinMeeting(meetingId) {
    state.pendingMeetingId = meetingId;
    openModal(DOM.participantModal);
}

async function createMeeting() {
    const name = DOM.roomName.value.trim() || 'Quick Meeting';
    const hostName = DOM.hostName.value.trim();
    const company = DOM.hostCompany.value.trim();
    const position = DOM.hostPosition.value.trim();
    
    if (!hostName) {
        showToast('Error', 'Please enter your name', 'error');
        return;
    }
    
    try {
        const result = await API.createRoom({
            name,
            host_name: hostName,
            company: company || 'Unknown',
            position: position || 'Guest',
        });
        
        closeModal(DOM.createModal);
        await enterMeeting(result, true);
    } catch (error) {
        showToast('Error', error.message, 'error');
    }
}

async function enterMeeting(data, isHost = false) {
    state.currentRoom = data.room;
    state.currentMeetingId = data.room.meeting_id;
    state.participantId = data.participant_id;
    state.isHost = isHost;
    
    // Switch view
    DOM.dashboardView.style.display = 'none';
    DOM.dashboardView.classList.remove('active');
    DOM.meetingView.style.display = 'block';
    DOM.meetingView.classList.add('active');
    
    // Render video grid
    renderVideoGrid();
    
    // Connect to LiveKit
    try {
        await LiveKit.connect(
            data.room.meeting_id,
            data.token,
            data.livekit_url
        );
    } catch (error) {
        showToast('Connection Error', 'Failed to connect to media server', 'error');
        return;
    }
    
    // Connect WebSocket
    connectWebSocket(data.room.meeting_id, data.participant_id);
    
    // Update UI
    state.room = data.room;
    updateUI();
    
    showToast('Connected', `Joined ${data.room.name}`, 'success');
}

async function leaveMeeting() {
    if (state.ws) {
        state.ws.close();
        state.ws = null;
    }
    
    await LiveKit.disconnect();
    
    if (state.currentRoom && state.participantId) {
        await API.leaveRoom(state.currentRoom.id, state.participantId);
    }
    
    // Reset state
    state.currentRoom = null;
    state.currentMeetingId = null;
    state.participantId = null;
    state.isHost = false;
    state.isMuted = false;
    state.isVideoOff = true;
    state.isRecording = false;
    state.participants = [];
    state.messages = [];
    
    // Switch view
    DOM.meetingView.style.display = 'none';
    DOM.meetingView.classList.remove('active');
    DOM.dashboardView.style.display = 'block';
    DOM.dashboardView.classList.add('active');
    
    // Reset controls
    DOM.chatPanel.style.display = 'none';
    DOM.participantsPanel.style.display = 'none';
    DOM.recordingStatus.className = 'recording-dot';
    
    loadDashboard();
    showToast('Left', 'You have left the meeting', 'info');
}

// ===== Control Handlers =====
async function toggleAudio() {
    state.isMuted = !state.isMuted;
    
    if (state.livekitRoom) {
        await state.livekitRoom.localParticipant.setMicrophoneEnabled(!state.isMuted);
    }
    
    updateUI();
}

async function toggleVideo() {
    state.isVideoOff = !state.isVideoOff;
    
    if (state.livekitRoom) {
        await state.livekitRoom.localParticipant.setCameraEnabled(!state.isVideoOff);
    }
    
    updateUI();
}

async function toggleScreenShare() {
    if (!state.livekitRoom) return;
    
    state.isScreenSharing = !state.isScreenSharing;
    
    try {
        if (state.isScreenSharing) {
            const tracks = await navigator.mediaDevices.getDisplayMedia({
                video: true,
                audio: false
            });
            await state.livekitRoom.localParticipant.publishTrack(tracks.getVideoTracks()[0]);
            showToast('Screen Share', 'Screen sharing started', 'success');
        } else {
            // Stop screen sharing
            const publications = state.livekitRoom.localParticipant.videoTrackPublications;
            for (const pub of publications) {
                if (pub.track && pub.track.kind === 'video' && pub.track.mediaStream) {
                    await state.livekitRoom.localParticipant.unpublishTrack(pub.track);
                    pub.track.stop();
                }
            }
            showToast('Screen Share', 'Screen sharing stopped', 'info');
        }
    } catch (error) {
        state.isScreenSharing = false;
        showToast('Screen Share Error', error.message, 'error');
    }
    
    updateUI();
}

function toggleChat() {
    state.isChatOpen = !state.isChatOpen;
    DOM.chatPanel.style.display = state.isChatOpen ? 'flex' : 'none';
    if (state.isChatOpen) {
        DOM.chatInput.focus();
    }
}

function toggleParticipants() {
    state.isParticipantsOpen = !state.isParticipantsOpen;
    DOM.participantsPanel.style.display = state.isParticipantsOpen ? 'flex' : 'none';
}

async function toggleRecording() {
    if (!state.isHost) {
        showToast('Permission Denied', 'Only the host can record', 'warning');
        return;
    }
    
    state.isRecording = !state.isRecording;
    
    try {
        if (state.isRecording) {
            await API.startRecording(state.currentMeetingId, state.participantId);
            DOM.recordingStatus.className = 'recording-dot active';
            showToast('Recording', 'Recording started', 'info');
        } else {
            await API.stopRecording(state.currentMeetingId, state.participantId);
            DOM.recordingStatus.className = 'recording-dot';
            showToast('Recording', 'Recording stopped', 'info');
        }
    } catch (error) {
        state.isRecording = !state.isRecording;
        showToast('Recording Error', error.message, 'error');
    }
}

async function raiseHand() {
    if (state.currentMeetingId && state.participantId) {
        await API.raiseHand(state.currentMeetingId, state.participantId);
    }
}

function sendChat() {
    const text = DOM.chatInput.value.trim();
    if (!text || !state.ws) return;
    
    state.ws.send(JSON.stringify({
        type: 'chat',
        message: text
    }));
    
    DOM.chatInput.value = '';
}

// ===== Event Listeners =====
// Navigation
DOM.navNewMeeting.addEventListener('click', () => openModal(DOM.createModal));
DOM.navJoinMeeting.addEventListener('click', () => openModal(DOM.joinModal));

// Dashboard
DOM.createMeetingBtn.addEventListener('click', () => openModal(DOM.createModal));

// Modals
DOM.closeJoinModal.addEventListener('click', () => closeModal(DOM.joinModal));
DOM.closeCreateModal.addEventListener('click', () => closeModal(DOM.createModal));

DOM.joinMeetingSubmit.addEventListener('click', async () => {
    const meetingId = DOM.joinMeetingId.value.trim().toUpperCase();
    if (!meetingId) {
        showToast('Error', 'Please enter a meeting ID', 'error');
        return;
    }
    closeModal(DOM.joinModal);
    joinMeeting(meetingId);
});

DOM.createRoomSubmit.addEventListener('click', createMeeting);

DOM.participantSubmit.addEventListener('click', async () => {
    const name = DOM.participantName.value.trim();
    const company = DOM.participantCompany.value.trim();
    const position = DOM.participantPosition.value.trim();
    
    if (!name) {
        showToast('Error', 'Please enter your name', 'error');
        return;
    }
    
    try {
        const result = await API.joinRoom(state.pendingMeetingId, {
            name,
            company: company || 'Unknown',
            position: position || 'Guest'
        });
        closeModal(DOM.participantModal);
        await enterMeeting(result, false);
    } catch (error) {
        showToast('Error', error.message, 'error');
    }
});

// Enter key handlers
DOM.joinMeetingId.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') DOM.joinMeetingSubmit.click();
});

DOM.participantName.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') DOM.participantSubmit.click();
});

DOM.participantCompany.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') DOM.participantSubmit.click();
});

DOM.participantPosition.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') DOM.participantSubmit.click();
});

DOM.roomName.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') DOM.createRoomSubmit.click();
});

DOM.hostName.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') DOM.createRoomSubmit.click();
});

// Meeting controls
DOM.toggleAudio.addEventListener('click', toggleAudio);
DOM.toggleVideo.addEventListener('click', toggleVideo);
DOM.toggleScreenShare.addEventListener('click', toggleScreenShare);
DOM.toggleChat.addEventListener('click', toggleChat);
DOM.toggleParticipants.addEventListener('click', toggleParticipants);
DOM.recordBtn.addEventListener('click', toggleRecording);
DOM.handRaiseBtn.addEventListener('click', raiseHand);
DOM.leaveMeetingBtn.addEventListener('click', leaveMeeting);

// Chat
DOM.sendChatBtn.addEventListener('click', sendChat);
DOM.chatInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendChat();
});
DOM.closeChatBtn.addEventListener('click', toggleChat);
DOM.closeParticipantsBtn.addEventListener('click', toggleParticipants);

// Close modals on outside click
$$('.modal').forEach(modal => {
    modal.addEventListener('click', (e) => {
        if (e.target === modal) closeModal(modal);
    });
});

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    // Alt+M: Toggle mute
    if (e.altKey && e.key === 'm') {
        e.preventDefault();
        toggleAudio();
    }
    // Alt+V: Toggle video
    if (e.altKey && e.key === 'v') {
        e.preventDefault();
        toggleVideo();
    }
    // Alt+C: Toggle chat
    if (e.altKey && e.key === 'c') {
        e.preventDefault();
        toggleChat();
    }
    // Escape: Close panels
    if (e.key === 'Escape') {
        if (state.isChatOpen) toggleChat();
        if (state.isParticipantsOpen) toggleParticipants();
        closeAllModals();
    }
});

// ===== Initialize =====
loadDashboard();

// Refresh dashboard every 30 seconds
setInterval(loadDashboard, 30000);

// Show welcome toast
setTimeout(() => {
    showToast('Welcome to Zoom Clone Pro!', 'Create or join a meeting to get started', 'success');
}, 500);

console.log('🚀 Zoom Clone Pro initialized');
console.log('📹 Server: http://localhost:8000');
console.log('🔑 LiveKit: ws://localhost:7880');
console.log('📋 Keyboard shortcuts: Alt+M (mute), Alt+V (video), Alt+C (chat)');

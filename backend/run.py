import uvicorn
import subprocess
import time
import os
import sys

def run_livekit():
    """Start LiveKit server in background"""
    print("Starting LiveKit Server...")
    
    # Check if livekit-server is in PATH
    try:
        subprocess.Popen(
            ["livekit-server", "--config", "livekit.yaml"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        )
        time.sleep(3)
        print("✅ LiveKit Server started")
        return True
    except FileNotFoundError:
        print("⚠️  LiveKit Server not found. Please download from: https://github.com/livekit/livekit/releases")
        return False

def run_backend():
    """Start FastAPI backend"""
    print("Starting Zoom Clone Backend...")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

if __name__ == "__main__":
    print("🚀 Starting Zoom Clone Pro...")
    print("=" * 50)
    
    # Start LiveKit
    livekit_started = run_livekit()
    
    # Start backend
    run_backend()

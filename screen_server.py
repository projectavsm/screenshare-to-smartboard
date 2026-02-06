import os
import cv2
import numpy as np
import pyautogui  # NEW: Allows Python to control keyboard/mouse
from mss import mss
from flask import Flask, Response, render_template, request, session, redirect, url_for
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-key-123-replace-this")

# --- GLOBAL STATE ---
# Track if we are in "Privacy/Blackout" mode
is_blackout = False

@app.route('/', methods=['GET', 'POST'])
def index():
    """Handles PIN login and shows the main stream page."""
    correct_pin = os.getenv("SCREEN_PIN", "1234")
    
    if request.method == 'POST':
        user_pin = request.form.get('pin')
        if user_pin == correct_pin:
            session['authorized'] = True
            return redirect(url_for('index'))
        return render_template('login.html', error="Incorrect PIN.")
    
    if session.get('authorized'):
        return render_template('stream.html')
        
    return render_template('login.html')

@app.route('/command/<action>')
def handle_command(action):
    """
    NEW: Receives commands from the Smart Board sidebar.
    Uses pyautogui to simulate physical key presses on your laptop.
    """
    global is_blackout
    
    if not session.get('authorized'):
        return {"status": "unauthorized"}, 401

    if action == 'next':
        pyautogui.press('right')  # Move slide forward
    elif action == 'prev':
        pyautogui.press('left')   # Move slide backward
    elif action == 'blackout':
        is_blackout = not is_blackout  # Toggle Privacy Mode
    elif action == 'space':
        pyautogui.press('space')  # Play/Pause video
        
    return {"status": "success", "blackout": is_blackout}

def generate_frames():
    """
    Captures screen and encodes as WebP.
    Includes logic to show a black screen when Privacy Mode is active.
    """
    with mss() as sct:
        monitor = sct.monitors[1]
        
        while True:
            if is_blackout:
                # 1. CREATE PRIVACY SCREEN: Solid black image
                frame = np.zeros((720, 1280, 3), dtype=np.uint8)
                cv2.putText(frame, "PRIVACY MODE ACTIVE", (420, 360), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                
                # Encode at very low quality/size since it's just a black frame
                ret, buffer = cv2.imencode('.webp', frame, [int(cv2.IMWRITE_WEBP_QUALITY), 10])
            else:
                # 2. NORMAL CAPTURE: 60 FPS Optimized
                img = np.array(sct.grab(monitor))
                frame = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                
                # Encode as WebP (Better compression than JPEG)
                encode_param = [int(cv2.IMWRITE_WEBP_QUALITY), 70]
                ret, buffer = cv2.imencode('.webp', frame, encode_param)
            
            if not ret:
                continue
            
            # 3. STREAM DATA
            yield (b'--frame\r\n'
                   b'Content-Type: image/webp\r\n\r\n' + buffer.tobytes() + b'\r\n')

@app.route('/video_feed')
def video_feed():
    """Endpoint for the <img> tag in stream.html."""
    if not session.get('authorized'):
        return "Unauthorized", 401
        
    return Response(
        generate_frames(), 
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == "__main__":
    # Note: threaded=True is crucial for handling video + commands simultaneously
    app.run(host='0.0.0.0', port=5000, threaded=True)
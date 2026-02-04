import os
import cv2
import numpy as np
from mss import mss
from flask import Flask, Response, render_template, request, session, redirect, url_for
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-key-123")
CORRECT_PIN = os.getenv("SCREEN_PIN", "1234")

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if request.form.get('pin') == CORRECT_PIN:
            session['authorized'] = True
            return redirect(url_for('index'))
        return render_template('login.html', error="Incorrect PIN")
    
    if session.get('authorized'):
        return render_template('stream.html')
    return render_template('login.html')

def generate_frames():
    # Use a 'with' statement so mss closes properly on every stop/refresh
    with mss() as sct:
        # monitor[1] is usually the primary display
        monitor = sct.monitors[1]
        
        while True:
            # Capture
            img = np.array(sct.grab(monitor))
            # Convert BGRA to BGR
            frame = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            # Resize for smooth streaming over tunnel
            frame = cv2.resize(frame, (1280, 720))
            
            # Encode to JPEG
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if not ret: continue
            
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

@app.route('/video_feed')
def video_feed():
    if not session.get('authorized'):
        return "Unauthorized", 401
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, threaded=True)
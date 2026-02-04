import cv2
import numpy as np
import os
from flask import Flask, Response, render_template_string, request, session, redirect, url_for
from mss import mss
from dotenv import load_dotenv

# Load security settings from .env file
load_dotenv()

app = Flask(__name__)

# --- CONFIGURATION ---
# The Secret Key encrypts the browser cookie so the PIN cannot be bypassed
app.secret_key = os.getenv("FLASK_SECRET_KEY", "change-this-to-something-random")
CORRECT_PIN = os.getenv("SCREEN_PIN", "1234")
sct = mss()

# --- HTML TEMPLATES ---
# Simple CSS-in-HTML for the login and player pages
LOGIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Secure Screen Share</title>
    <style>
        body { font-family: -apple-system, sans-serif; background: #0f172a; color: #f8fafc; 
               display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .card { background: #1e293b; padding: 2.5rem; border-radius: 1rem; box-shadow: 0 10px 25px rgba(0,0,0,0.3); text-align: center; width: 320px; }
        h2 { margin-bottom: 1.5rem; font-weight: 500; }
        input { font-size: 1.5rem; width: 100%; padding: 12px; border: 1px solid #334155; 
                border-radius: 0.5rem; background: #0f172a; color: white; margin-bottom: 1rem; box-sizing: border-box; text-align: center; }
        button { width: 100%; padding: 12px; background: #3b82f6; color: white; border: none; border-radius: 0.5rem; font-size: 1rem; cursor: pointer; transition: 0.2s; }
        button:hover { background: #2563eb; }
        .error { color: #f87171; margin-top: 1rem; font-size: 0.9rem; }
    </style>
</head>
<body>
    <div class="card">
        <h2>Enter Access PIN</h2>
        <form method="POST">
            <input type="password" name="pin" placeholder="••••" maxlength="4" autofocus autocomplete="off">
            <button type="submit">Unlock Stream</button>
        </form>
        {% if error %}<p class="error">{{ error }}</p>{% endif %}
    </div>
</body>
</html>
"""

STREAM_HTML = """
<!DOCTYPE html>
<html>
<body style="margin:0; background:black; display:flex; align-items:center; justify-content:center; overflow:hidden;">
    <img src="{{ url_for('video_feed') }}" style="width:100vw; height:100vh; object-fit: contain;">
</body>
</html>
"""

# --- LOGIC ROUTES ---

@app.route('/', methods=['GET', 'POST'])
def index():
    """Handles the login page and session check."""
    if request.method == 'POST':
        if request.form.get('pin') == CORRECT_PIN:
            session['authorized'] = True # Set the cookie
            return redirect(url_for('index'))
        else:
            return render_template_string(LOGIN_HTML, error="Incorrect PIN. Please try again.")

    # Show stream if authorized, else show login
    if session.get('authorized'):
        return render_template_string(STREAM_HTML)
    return render_template_string(LOGIN_HTML)

@app.route('/video_feed')
def video_feed():
    """The route that actually streams the screen frames."""
    # Check if the browser has the authorization cookie
    if not session.get('authorized'):
        return "Unauthorized Access", 401
        
    def generate_frames():
        try:
            # Try index 0 (All monitors) if 1 is failing
            monitor = sct.monitors[0] 
            print(f"DEBUG: Attempting to capture monitor: {monitor}")
            
            while True:
                sct_img = sct.grab(monitor)
                if sct_img is None:
                    print("DEBUG: Grab failed")
                    break

                # Convert to numpy array
                img = np.array(sct_img)
                
                # Convert color (mss grabs BGRA, we need BGR)
                frame = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                
                # Resize
                frame = cv2.resize(frame, (1280, 720))
                
                # Encode
                ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                if not ret:
                    continue
                    
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        except Exception as e:
            print(f"❌ SERVER ERROR: {e}") # This will print to your terminal

    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, threaded=True)
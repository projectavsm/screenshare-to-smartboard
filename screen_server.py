import os
import cv2
import numpy as np
from mss import mss
from flask import Flask, Response, render_template, request, session, redirect, url_for
from dotenv import load_dotenv

# Load any static variables from .env (like FLASK_SECRET_KEY)
load_dotenv()

app = Flask(__name__)

# Secret key is required to use 'session' (cookies)
# It's better to have a static key in .env so sessions don't expire on server restart
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-key-123-replace-this")

@app.route('/', methods=['GET', 'POST'])
def index():
    """
    Handles the Login page and the Stream page.
    The PIN is pulled from the environment variable set by run_and_mail.py.
    """
    # Dynamically grab the PIN passed from the controller script
    # Defaults to '1234' if the server is run manually without the controller
    correct_pin = os.getenv("SCREEN_PIN", "1234")
    
    if request.method == 'POST':
        user_pin = request.form.get('pin')
        if user_pin == correct_pin:
            session['authorized'] = True  # Set a cookie to remember the user
            return redirect(url_for('index'))
        return render_template('login.html', error="Incorrect PIN. Please check your email.")
    
    # If the user has a valid session cookie, show the stream
    if session.get('authorized'):
        return render_template('stream.html')
        
    # Otherwise, show the login/PIN entry page
    return render_template('login.html')

def generate_frames():
    """
    Optimized for 60 FPS using WebP encoding and reduced latency.
    """
    with mss() as sct:
        # Select the primary monitor
        monitor = sct.monitors[1]
        
        while True:
            # 1. Capture screen
            img = np.array(sct.grab(monitor))
            
            # 2. Convert color (BGRA to BGR)
            frame = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            
            # 3. Downscale slightly (Optional but recommended for 60FPS)
            # Even a drop to 1600px wide makes 60FPS much easier over a tunnel
            # frame = cv2.resize(frame, (1280, 720)) 

            # 4. SWAP JPEG FOR WEBP
            # WEBP_QUALITY: 60-80 is the sweet spot. 
            # Lower = Faster/Smoother. Higher = Sharper.
            encode_param = [int(cv2.IMWRITE_WEBP_QUALITY), 70]
            ret, buffer = cv2.imencode('.webp', frame, encode_param)
            
            if not ret:
                continue
            
            # 5. Yield as a stream
            # Note: We change the Content-Type to image/webp
            yield (b'--frame\r\n'
                   b'Content-Type: image/webp\r\n\r\n' + buffer.tobytes() + b'\r\n')

@app.route('/video_feed')
def video_feed():
    """
    The URL for the <img> tag in stream.html. 
    It streams the actual video data.
    """
    # Security check: Don't allow access to the video data unless authorized
    if not session.get('authorized'):
        return "Unauthorized access. Please login.", 401
        
    return Response(
        generate_frames(), 
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

@app.route('/logout')
def logout():
    """Clears the session so the user has to enter the PIN again."""
    session.clear()
    return redirect(url_for('index'))

if __name__ == "__main__":
    # host='0.0.0.0' makes the server accessible locally by the tunnel
    # threaded=True allows multiple connections (if you have two boards)
    app.run(host='0.0.0.0', port=5000, threaded=True)
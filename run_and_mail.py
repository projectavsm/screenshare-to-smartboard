import subprocess
import time
import sys
import re
import os
import random
import threading
import smtplib
import urllib.request
import tkinter as tk
from tkinter import simpledialog
from email.message import EmailMessage
from datetime import datetime
from dotenv import load_dotenv

# Third-party libraries
import qrcode
import pystray
import pyperclip
from PIL import Image
from url_utils import shorten_url

# Load environment variables
load_dotenv()

# --- CONFIGURATION ---
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
DEFAULT_RECIPIENT = os.getenv("RECIPIENT_EMAIL")

# --- GLOBAL STATE ---
public_url = "Initializing..."
otp_pin = "0000"
recipient = ""
server_proc = None
tunnel_proc = None

# --- UI & EMAIL FUNCTIONS ---

def get_recipient_email():
    """Opens a popup to ask for the recipient's email address."""
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True) # Force popup to the front
    user_input = simpledialog.askstring(
        "Recipient Email", 
        "Where should I send the Smart Board link?",
        initialvalue=DEFAULT_RECIPIENT
    )
    root.destroy()
    return user_input

def send_email_with_qr(url, qr_path, target_email, pin):
    """Sends the link, PIN, and QR code to the target email."""
    now = datetime.now().strftime("%I:%M %p")
    if not all([SENDER_EMAIL, SENDER_PASSWORD, target_email]):
        print("⚠️ Email credentials missing in .env!")
        return

    msg = EmailMessage()
    msg['Subject'] = f'📺 Smart Board Link - {now}'
    msg['From'] = SENDER_EMAIL
    msg['To'] = target_email
    msg.set_content(f"Link: {url}\nPIN: {pin}\n\nScan the attached QR code to start.")

    try:
        with open(qr_path, 'rb') as f:
            msg.add_attachment(f.read(), maintype='image', subtype='png', filename='qr.png')
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(SENDER_EMAIL, SENDER_PASSWORD)
            smtp.send_message(msg)
        print(f"✅ Email sent successfully to {target_email}!")
    except Exception as e:
        print(f"❌ Email Error: {e}")

# --- TRAY MENU ACTIONS ---

def copy_to_clipboard():
    """Right-click action: Copy details to Windows clipboard."""
    pyperclip.copy(f"Link: {public_url} | PIN: {otp_pin}")
    print("📋 Copied to clipboard!")

def resend_email_action():
    """Right-click action: Trigger a fresh email."""
    if public_url and recipient:
        send_email_with_qr(public_url, "current_qr.png", recipient, otp_pin)

def quit_app(icon):
    """Right-click action: Kill everything and exit."""
    print("🛑 Shutting down system...")
    if server_proc: server_proc.terminate()
    if tunnel_proc: tunnel_proc.terminate()
    icon.stop()
    os._exit(0)

# --- CORE LOGIC ---

def ensure_cloudflared():
    if not os.path.exists("cloudflared.exe"):
        print("📥 Downloading cloudflared...")
        url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
        urllib.request.urlretrieve(url, "cloudflared.exe")

def run_logic():
    global public_url, otp_pin, recipient, server_proc, tunnel_proc
    
    recipient = get_recipient_email()
    if not recipient:
        print("🚫 Cancelled.")
        return

    ensure_cloudflared()
    otp_pin = str(random.randint(1000, 9999))
    
    server_env = os.environ.copy()
    server_env["SCREEN_PIN"] = otp_pin
    server_proc = subprocess.Popen([sys.executable, "screen_server.py"], env=server_env)
    
    tunnel_cmd = ["./cloudflared.exe", "tunnel", "--url", "http://localhost:5000"]
    tunnel_proc = subprocess.Popen(
        tunnel_cmd, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.STDOUT, 
        text=True, 
        bufsize=1
    )

    for line in iter(tunnel_proc.stdout.readline, ''):
        if ".trycloudflare.com" in line:
            match = re.search(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", line)
            if match:
                long_url = match.group(0)
                public_url = shorten_url(long_url)
                qr_img = qrcode.make(public_url)
                qr_img.save("current_qr.png")
                send_email_with_qr(public_url, "current_qr.png", recipient, otp_pin)
                break

def setup_tray():
    """Creates the System Tray icon and starts the background thread."""
    try:
        image = Image.open("icon.png")
    except Exception:
        image = Image.new('RGB', (64, 64), color=(0, 120, 215))
    
    # FIXED: Using pystray.MenuItem.SEPARATOR
    menu = pystray.Menu(
        pystray.MenuItem("Copy URL & PIN", copy_to_clipboard),
        pystray.MenuItem("Resend Email", resend_email_action),
        pystray.MenuItem("Exit & Stop Sharing", quit_app)
    )
    
    icon = pystray.Icon("SmartShare", image, "Smart Board Share", menu)
    
    logic_thread = threading.Thread(target=run_logic, daemon=True)
    logic_thread.start()
    
    icon.run()

if __name__ == "__main__":
    setup_tray()
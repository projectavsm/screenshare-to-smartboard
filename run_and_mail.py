import subprocess
import time
import sys
import re
import os
import smtplib
import qrcode
import urllib.request
import random
import tkinter as tk
from tkinter import simpledialog
from email.message import EmailMessage
from datetime import datetime
from dotenv import load_dotenv

# Load variables from the .env file
load_dotenv()

# --- CONFIGURATION FROM .ENV ---
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
DEFAULT_RECIPIENT = os.getenv("RECIPIENT_EMAIL")

def get_recipient_email():
    """Opens a Windows dialog box to ask for the recipient's email address."""
    root = tk.Tk()
    root.withdraw()  # Hide the main Tkinter window
    
    user_input = simpledialog.askstring(
        "Recipient Email", 
        "Where should I send the Smart Board link?",
        initialvalue=DEFAULT_RECIPIENT
    )
    
    root.destroy()
    return user_input

def ensure_cloudflared():
    """Checks if cloudflared.exe exists; if not, downloads it automatically."""
    if not os.path.exists("cloudflared.exe"):
        print("📥 cloudflared.exe not found. Downloading it now...")
        url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
        try:
            urllib.request.urlretrieve(url, "cloudflared.exe")
            print("✅ Download complete!")
        except Exception as e:
            print(f"❌ Failed to download cloudflared: {e}")
            sys.exit(1)

def send_email_with_qr(url, qr_path, target_email, pin):
    """Constructs and sends the email containing the URL, the PIN, and the QR code."""
    now = datetime.now().strftime("%I:%M %p")
    print(f"📨 Sending email to {target_email}...")
    
    # Validation check
    if not all([SENDER_EMAIL, SENDER_PASSWORD, target_email]):
        print("⚠️ Error: Missing email credentials. Check your .env file.")
        return

    msg = EmailMessage()
    msg['Subject'] = f'📺 Smart Board Link - {now}'
    msg['From'] = SENDER_EMAIL
    msg['To'] = target_email
    
    # The message body includes the One-Time PIN
    msg.set_content(f"""
Screen share session started at {now}.

🔗 LINK: {url}
🔑 SECURITY PIN: {pin}

Scan the attached QR code to open the link on the Smart Board.
Enter the 4-digit PIN when prompted to start the stream.
    """)

    try:
        # Attach the QR code image
        with open(qr_path, 'rb') as f:
            msg.add_attachment(
                f.read(), 
                maintype='image', 
                subtype='png', 
                filename=f'qr_{now.replace(":", "")}.png'
            )
        
        # Connect to Gmail SMTP server
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(SENDER_EMAIL, SENDER_PASSWORD)
            smtp.send_message(msg)
        print(f"✅ SUCCESS: Email sent with PIN {pin}!")
    except Exception as e:
        print(f"❌ SMTP Error: {e}")

def start_app():
    # 1. Ask for the recipient email via Popup
    recipient = get_recipient_email()
    if not recipient:
        print("🚫 No email provided. Script cancelled.")
        return

    # 2. Ensure cloudflared is ready to go
    ensure_cloudflared()

    # 3. Generate a random 4-digit One-Time PIN (OTP)
    otp_pin = str(random.randint(1000, 9999))
    print(f"🔐 Security: Generated PIN for this session: {otp_pin}")

    # 4. Launch Screen Server (passing the PIN as an environment variable)
    print("🚀 Step 1: Launching Screen Server...")
    server_env = os.environ.copy()
    server_env["SCREEN_PIN"] = otp_pin  # Pass PIN to the subprocess
    
    server_proc = subprocess.Popen([sys.executable, "screen_server.py"], env=server_env)
    time.sleep(2)  # Give the server a moment to boot

    # 5. Start the Cloudflare Tunnel
    print("🌐 Step 2: Opening Secure Tunnel...")
    tunnel_cmd = ["./cloudflared.exe", "tunnel", "--url", "http://localhost:5000"]
    tunnel_proc = subprocess.Popen(
        tunnel_cmd, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.STDOUT, 
        text=True, 
        bufsize=1
    )

    public_url = None
    try:
        # Read tunnel output line-by-line to find the public URL
        for line in iter(tunnel_proc.stdout.readline, ''):
            if ".trycloudflare.com" in line:
                url_match = re.search(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", line)
                if url_match:
                    public_url = url_match.group(0)
                    print(f"\n✅ LIVE AT: {public_url}")
                    print(f"🔑 ACCESS CODE: {otp_pin}")
                    
                    # 6. Generate QR Image
                    qr_img = qrcode.make(public_url)
                    qr_file = "current_qr.png"
                    qr_img.save(qr_file)
                    
                    # 7. Send the Email with the URL and the generated PIN
                    send_email_with_qr(public_url, qr_file, recipient, otp_pin)
                    
                    # Optional: Print QR to terminal for local testing
                    qr_terminal = qrcode.QRCode(box_size=1)
                    qr_terminal.add_data(public_url)
                    qr_terminal.print_ascii()
                    break 

        print("\n🔥 System running. Keep this window open.")
        print("Press Ctrl+C to shut down all processes.")
        
        # Keep the script alive while the tunnel is running
        tunnel_proc.wait()

    except KeyboardInterrupt:
        print("\n🛑 Shutting down safely...")
        server_proc.terminate()
        tunnel_proc.terminate()
        print("👋 Goodbye!")

if __name__ == "__main__":
    start_app()
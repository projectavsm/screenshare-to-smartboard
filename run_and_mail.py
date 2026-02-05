import subprocess, time, sys, re, os, smtplib, qrcode, urllib.request
from email.message import EmailMessage
from datetime import datetime
from dotenv import load_dotenv
import tkinter as tk
from tkinter import simpledialog

load_dotenv()

# Get default credentials from .env
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
DEFAULT_RECIPIENT = os.getenv("RECIPIENT_EMAIL")

def get_recipient_email():
    """Opens a popup dialog to ask for the recipient's email."""
    root = tk.Tk()
    root.withdraw()  # Hide the main tiny tkinter window
    
    # Ask for input
    user_input = simpledialog.askstring(
        "Recipient Email", 
        "Enter the Smart Board or Recipient Email:",
        initialvalue=DEFAULT_RECIPIENT
    )
    
    root.destroy()
    return user_input

def ensure_cloudflared():
    if not os.path.exists("cloudflared.exe"):
        print("📥 cloudflared.exe not found. Downloading...")
        url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
        try:
            urllib.request.urlretrieve(url, "cloudflared.exe")
            print("✅ Download complete!")
        except Exception as e:
            print(f"❌ Download failed: {e}")
            sys.exit(1)

def send_email_with_qr(url, qr_path, target_email):
    now = datetime.now().strftime("%I:%M %p")
    print(f"📨 Attempting to send email to {target_email}...")
    
    if not all([SENDER_EMAIL, SENDER_PASSWORD, target_email]):
        print("⚠️ Error: Email credentials or recipient missing.")
        return

    msg = EmailMessage()
    msg['Subject'] = f'📺 Smart Board Link - {now}'
    msg['From'] = SENDER_EMAIL
    msg['To'] = target_email
    msg.set_content(f"Screen share is live!\n\nLink: {url}")

    try:
        with open(qr_path, 'rb') as f:
            msg.add_attachment(f.read(), maintype='image', subtype='png', filename='qr_code.png')
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(SENDER_EMAIL, SENDER_PASSWORD)
            smtp.send_message(msg)
        print(f"✅ SUCCESS: Email sent to {target_email}!")
    except Exception as e:
        print(f"❌ SMTP Error: {e}")

def start_app():
    # 1. Ask for email first
    recipient = get_recipient_email()
    if not recipient:
        print("🚫 No email provided. Cancelling startup.")
        return

    # 2. Check for cloudflared
    ensure_cloudflared()

    # 3. Start Server
    print("🚀 Step 1: Launching Screen Server...")
    server_proc = subprocess.Popen([sys.executable, "screen_server.py"])
    time.sleep(2)

    # 4. Start Tunnel
    print("🌐 Step 2: Opening Secure Tunnel...")
    tunnel_cmd = ["./cloudflared.exe", "tunnel", "--url", "http://localhost:5000"]
    tunnel_proc = subprocess.Popen(tunnel_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)

    try:
        for line in iter(tunnel_proc.stdout.readline, ''):
            if ".trycloudflare.com" in line:
                url_match = re.search(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", line)
                if url_match:
                    public_url = url_match.group(0)
                    print(f"\n✅ LIVE AT: {public_url}")
                    
                    qr_img = qrcode.make(public_url)
                    qr_file = "current_qr.png"
                    qr_img.save(qr_file)
                    
                    qr_terminal = qrcode.QRCode(box_size=1)
                    qr_terminal.add_data(public_url)
                    qr_terminal.print_ascii()

                    # Send to the email from the dialog box
                    send_email_with_qr(public_url, qr_file, recipient)
                    break 

        print("\n🔥 System running. Press Ctrl+C to stop.")
        tunnel_proc.wait()

    except KeyboardInterrupt:
        server_proc.terminate()
        tunnel_proc.terminate()
        print("👋 Stopped.")

if __name__ == "__main__":
    start_app()
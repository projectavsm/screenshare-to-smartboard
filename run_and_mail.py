import subprocess, time, sys, re, os, smtplib, qrcode, urllib.request
from email.message import EmailMessage
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Get credentials from .env
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")

def ensure_cloudflared():
    """Checks if cloudflared.exe exists, downloads it if missing."""
    if not os.path.exists("cloudflared.exe"):
        print("📥 cloudflared.exe not found. Downloading it now...")
        url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
        try:
            urllib.request.urlretrieve(url, "cloudflared.exe")
            print("✅ Download complete!")
        except Exception as e:
            print(f"❌ Failed to download cloudflared: {e}")
            sys.exit(1) # Stop the script if we can't get the tool

def send_email_with_qr(url, qr_path):
    now = datetime.now().strftime("%I:%M %p")
    print(f"📨 Attempting to send email to {RECIPIENT_EMAIL}...")
    
    if not all([SENDER_EMAIL, SENDER_PASSWORD, RECIPIENT_EMAIL]):
        print("⚠️ Error: Email credentials missing in .env")
        return

    msg = EmailMessage()
    msg['Subject'] = f'📺 Smart Board Link - {now}'
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECIPIENT_EMAIL
    msg.set_content(f"Screen share is live!\n\nStarted at: {now}\nLink: {url}")

    try:
        with open(qr_path, 'rb') as f:
            msg.add_attachment(
                f.read(), 
                maintype='image', 
                subtype='png', 
                filename=f'qr_{now.replace(":", "")}.png'
            )
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(SENDER_EMAIL, SENDER_PASSWORD)
            smtp.send_message(msg)
        print(f"✅ SUCCESS: Email sent at {now}!")
    except Exception as e:
        print(f"❌ SMTP Error: {e}")

def start_app():
    # --- NEW: Check for cloudflared before starting ---
    ensure_cloudflared()

    # 1. Start Server
    print("🚀 Step 1: Launching Screen Server...")
    server_proc = subprocess.Popen([sys.executable, "screen_server.py"])
    time.sleep(2)

    # 2. Start Tunnel
    print("🌐 Step 2: Opening Secure Tunnel...")
    tunnel_cmd = ["./cloudflared.exe", "tunnel", "--url", "http://localhost:5000"]
    tunnel_proc = subprocess.Popen(tunnel_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)

    public_url = None
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

                    send_email_with_qr(public_url, qr_file)
                    break 

        print("\n🔥 System running. Keep this window open to maintain the stream.")
        print("Press Ctrl+C to stop everything.")
        tunnel_proc.wait()

    except KeyboardInterrupt:
        print("\n🛑 Shutting down processes...")
        server_proc.terminate()
        tunnel_proc.terminate()
        print("👋 Goodbye!")

if __name__ == "__main__":
    start_app()
import subprocess
import time
import sys
import re
import os
import smtplib
import qrcode
from email.message import EmailMessage
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")

def send_email_with_qr(url, qr_path):
    """Sends an email with the public URL and the QR code attached."""
    if not all([SENDER_EMAIL, SENDER_PASSWORD, RECIPIENT_EMAIL]):
        print("⚠️ Warning: Email credentials missing in .env. Skipping email...")
        return

    msg = EmailMessage()
    msg['Subject'] = '📺 Your Smart Board Screen Share is Ready'
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECIPIENT_EMAIL
    msg.set_content(f"The screen share is live!\n\nLink: {url}\n\nScan the attached QR code to connect instantly.")

    try:
        # Attach the QR Image
        with open(qr_path, 'rb') as f:
            msg.add_attachment(f.read(), maintype='image', subtype='png', filename='qr_code.png')
        
        # Connect and send via Gmail SMTP
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(SENDER_EMAIL, SENDER_PASSWORD)
            smtp.send_message(msg)
        print("📧 Success: Link and QR Code emailed to Smart Board.")
    except Exception as e:
        print(f"❌ Email error: {e}")

def start_app():
    """Main process controller."""
    # 1. Start the Flask Server
    print("🚀 Step 1: Launching Screen Capture Server...")
    server_proc = subprocess.Popen([sys.executable, "screen_server.py"], 
                                   stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

    time.sleep(2) # Give it a moment to bind to port 5000

    # 2. Start the Cloudflare Tunnel
    print("🌐 Step 2: Opening Secure Tunnel to the Internet...")
    # Change 'cloudflared.exe' to 'cloudflared' if on Mac/Linux
    tunnel_cmd = ["./cloudflared.exe", "tunnel", "--url", "http://localhost:5000"]
    tunnel_proc = subprocess.Popen(tunnel_cmd, stdout=subprocess.PIPE, 
                                   stderr=subprocess.STDOUT, text=True, encoding='utf-8')

    try:
        # 3. Monitor tunnel logs for the public URL
        print("🔎 Searching for live URL...")
        for line in tunnel_proc.stdout:
            if ".trycloudflare.com" in line:
                url_match = re.search(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", line)
                if url_match:
                    public_url = url_match.group(0)
                    print(f"\n✅ SYSTEM ONLINE: {public_url}\n")
                    
                    # 4. Generate & Show QR Code in Terminal
                    qr = qrcode.QRCode()
                    qr.add_data(public_url)
                    print("🤳 SCAN ME WITH PHONE OR SMART BOARD:")
                    qr.print_ascii() 
                    
                    # 5. Save QR and Email it
                    qr_img = qr.make_image(fill_color="black", back_color="white")
                    qr_file = "current_qr.png"
                    qr_img.save(qr_file)
                    send_email_with_qr(public_url, qr_file)
                    
                    print("\n🔥 Stream is running. Press Ctrl+C to disconnect.")
                    break
        tunnel_proc.wait()
    except KeyboardInterrupt:
        # 6. Cleanup on exit
        print("\n🛑 Shutting down server and closing tunnel...")
        server_proc.terminate()
        tunnel_proc.terminate()
        if os.path.exists("current_qr.png"): os.remove("current_qr.png")
        print("👋 Goodbye.")

if __name__ == "__main__":
    start_app()
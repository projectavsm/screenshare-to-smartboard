import subprocess, time, sys, re, os, smtplib, qrcode
from email.message import EmailMessage
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Get credentials from .env
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")

def send_email_with_qr(url, qr_path):
    # Create a timestamp for the subject line
    now = datetime.now().strftime("%I:%M %p")
    print(f"📨 Attempting to send email to {RECIPIENT_EMAIL}...")
    
    if not all([SENDER_EMAIL, SENDER_PASSWORD, RECIPIENT_EMAIL]):
        print("⚠️ Error: Email credentials missing in .env")
        return

    msg = EmailMessage()
    msg['Subject'] = f'📺 Smart Board Link - {now}'
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECIPIENT_EMAIL
    
    # Simple HTML body for a nicer look on the Smart Board
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
    # 1. Start Server
    print("🚀 Step 1: Launching Screen Server...")
    server_proc = subprocess.Popen([sys.executable, "screen_server.py"])
    time.sleep(2)

    # 2. Start Tunnel
    print("🌐 Step 2: Opening Secure Tunnel...")
    tunnel_cmd = ["./cloudflared.exe", "tunnel", "--url", "http://localhost:5000"]
    # We use bufsize=1 and universal_newlines=True (via text=True) for real-time reading
    tunnel_proc = subprocess.Popen(tunnel_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)

    public_url = None
    try:
        # Loop through output lines as they arrive
        for line in iter(tunnel_proc.stdout.readline, ''):
            # Useful for debugging: print(line.strip()) 
            if ".trycloudflare.com" in line:
                url_match = re.search(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", line)
                if url_match:
                    public_url = url_match.group(0)
                    print(f"\n✅ LIVE AT: {public_url}")
                    
                    # Generate QR Image
                    qr_img = qrcode.make(public_url)
                    qr_file = "current_qr.png"
                    qr_img.save(qr_file)
                    
                    # Print ASCII QR to terminal
                    qr_terminal = qrcode.QRCode(box_size=1)
                    qr_terminal.add_data(public_url)
                    qr_terminal.print_ascii()

                    # 3. Send the Email
                    send_email_with_qr(public_url, qr_file)
                    break # Exit the loop once the URL is found and email is sent

        print("\n🔥 System running. Keep this window open to maintain the stream.")
        print("Press Ctrl+C to stop everything.")
        
        # Keep the script alive so the tunnel doesn't close
        tunnel_proc.wait()

    except KeyboardInterrupt:
        print("\n🛑 Shutting down processes...")
        server_proc.terminate()
        tunnel_proc.terminate()
        print("👋 Goodbye!")

if __name__ == "__main__":
    start_app()
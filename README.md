# 📺 Secure Screen Share to Smart Board

A lightweight, secure Python application that streams your laptop screen to any device (Smart Board, Phone, Tablet) via a secure Cloudflare tunnel. Features a PIN-protected web interface and automatic QR code generation/emailing.

## ✨ Features

- **Zero Configuration Tunnel**: Uses Cloudflare (via cloudflared) to bypass firewalls and port forwarding
- **Security First**: Protected by a customizable 4-digit PIN and Flask session encryption
- **Automated Workflow**: One script launches the server, opens the tunnel, generates a QR code, and emails the link
- **Low Latency**: Optimized MJPEG streaming via OpenCV and MSS

## 🚀 Getting Started

### Prerequisites

- Python 3.8 or higher
- A Gmail account (if using the auto-email feature)
- The `cloudflared.exe` binary in the project root

### Installation

```bash
git clone https://github.com/projectavsm/screenshare-to-smartboard.git
cd screenshare-to-smartboard

# Create and activate virtual environment
python -m venv venv
source venv/Scripts/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install flask opencv-python numpy mss python-dotenv qrcode pillow
```

### Environment Setup (.env)

Create a `.env` file in the root directory:

```env
# Security
SCREEN_PIN=1234
FLASK_SECRET_KEY=your_random_secret_string

# Email (For Smart Board auto-link)
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=your-app-password
RECIPIENT_EMAIL=smartboard-email@example.com
```

> **Note**: If using Gmail, use an App Password, not your regular password.

## 🛠️ Project Structure

```
├── templates/
│   ├── login.html       # Secure PIN entry page
│   └── stream.html      # MJPEG video player
├── screen_server.py     # Flask backend & screen capture logic
├── run_and_mail.py      # Master controller (Tunnel + QR + Email)
├── .env                 # Private credentials (DO NOT GIT PUSH)
└── cloudflared.exe      # Cloudflare binary
```

## 📖 Usage

```bash
python run_and_mail.py

to run it purely in the background

pythonw run_and_mail.py 
```

1. **Server Starts**: Flask launches on `localhost:5000`
2. **Tunnel Opens**: A public `.trycloudflare.com` URL is generated
3. **QR Generated**: A QR code appears in your terminal and is saved as `current_qr.png`
4. **Email Sent**: The link and QR are sent to your recipient
5. **Connect**: Scan the QR on the Smart Board, enter your PIN, and start sharing!

## 🛡️ Troubleshooting

| Issue | Solution |
|-------|----------|
| Black Screen | Ensure the terminal/IDE has "Screen Recording" permissions in Windows/macOS |
| 500 Error | Check the monitor index in `screen_server.py` |
| Tunnel Fails | Ensure `cloudflared.exe` is in the root folder and not blocked by firewall |

## 📄 License

Distributed under the MIT License. See LICENSE for more information.

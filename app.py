import os
import asyncio
from flask import Flask, render_template_string, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = "vivek_panel_secret_key"
app.config['UPLOAD_FOLDER'] = 'uploads'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

temp_storage = {}

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Vivek Panel</title>
    <style>
        body { font-family: Arial, sans-serif; background: #0f172a; color: #f8fafc; text-align: center; padding: 30px; }
        .card { background: #1e293b; padding: 25px; border-radius: 12px; display: inline-block; box-shadow: 0 4px 20px rgba(0,0,0,0.6); width: 380px; text-align: left; }
        h1 { color: #38bdf8; text-align: center; margin-bottom: 5px; font-size: 22px; }
        p { color: #94a3b8; text-align: center; margin-bottom: 15px; font-size: 13px; }
        label { font-size: 13px; color: #cbd5e1; display: block; margin-top: 10px; }
        input[type="text"], input[type="password"], input[type="file"], select { width: 100%; padding: 9px; margin-top: 5px; margin-bottom: 12px; border-radius: 6px; border: 1px solid #475569; background: #0f172a; color: white; box-sizing: border-box; }
        .btn { width: 100%; padding: 11px; font-size: 14px; font-weight: bold; color: white; background: #0284c7; border: none; border-radius: 6px; cursor: pointer; transition: 0.2s; }
        .btn:hover { background: #0ea5e9; }
        .btn-danger { background: #dc2626; margin-top: 10px; }
        .btn-danger:hover { background: #ef4444; }
        .error-box { background: rgba(239, 68, 68, 0.1); border: 1px solid #ef4444; padding: 10px; border-radius: 6px; margin-bottom: 15px; }
        .error { color: #f87171; font-size: 12px; text-align: center; word-break: break-all; }
        .success { color: #4ade80; font-size: 13px; text-align: center; margin-bottom: 10px; }
    </style>
</head>
<body>
    <div class="card">
        <h1>Vivek Panel</h1>
        <p>Telegram Userbot & Audio Control</p>
        
        {% if error %}
            <div class="error-box">
                <div class="error">❌ {{ error }}</div>
            </div>
            <a href="/logout" class="btn btn-danger" style="display: block; text-align: center; text-decoration: none; margin-bottom: 15px;">🔄 Try Again / Reset</a>
        {% endif %}

        {% if msg %}
            <div class="success">{{ msg }}</div>
        {% endif %}

        {% if not error %}
            {% if step == 'credentials' %}
                <form method="POST" action="/save-credentials">
                    <label>API ID:</label>
                    <input type="text" name="api_id" placeholder="30357864" required>
                    
                    <label>API Hash:</label>
                    <input type="text" name="api_hash" placeholder="8d8a1027816b1724b0b420480ea06a6f" required>
                    
                    <label>Phone Number:</label>
                    <input type="text" name="phone" placeholder="+919876543210" required>
                    
                    <button type="submit" class="btn">Send OTP</button>
                </form>
            {% elif step == 'otp' %}
                <form method="POST" action="/verify-otp">
                    <label>Enter Telegram OTP:</label>
                    <input type="text" name="otp" placeholder="12345" required>
                    <button type="submit" class="btn">Verify OTP</button>
                </form>
                <a href="/logout" class="btn btn-danger" style="display: block; text-align: center; text-decoration: none; margin-top: 10px;">Cancel / Start Over</a>
            {% elif step == 'password' %}
                <form method="POST" action="/verify-password">
                    <label>2FA Password:</label>
                    <input type="password" name="password" placeholder="Enter 2FA password" required>
                    <button type="submit" class="btn">Login</button>
                </form>
                <a href="/logout" class="btn btn-danger" style="display: block; text-align: center; text-decoration: none; margin-top: 10px;">Cancel / Start Over</a>
            {% elif step == 'dashboard' %}
                <form method="POST" action="/upload-audio" enctype="multipart/form-data">
                    <label>Upload Audio File (.mp3):</label>
                    <input type="file" name="audio" accept=".mp3" required>
                    
                    <label>Playback Mode:</label>
                    <select name="loop_mode">
                        <option value="single">Single Play (No Loop)</option>
                        <option value="loop">Infinite Loop</option>
                    </select>
                    
                    <button type="submit" class="btn">Upload & Save Settings</button>
                </form>
                <a href="/logout" class="btn btn-danger" style="display: block; text-align: center; text-decoration: none;">Logout</a>
            {% endif %}
        {% endif %}
    </div>
</body>
</html>
"""

@app.route("/")
def index():
    if session.get("logged_in"):
        return render_template_string(HTML_TEMPLATE, step="dashboard", msg=session.get("msg"))
    elif session.get("waiting_for_password"):
        return render_template_string(HTML_TEMPLATE, step="password")
    elif session.get("waiting_for_otp"):
        return render_template_string(HTML_TEMPLATE, step="otp")
    else:
        return render_template_string(HTML_TEMPLATE, step="credentials", error=session.get("error"))

@app.route("/save-credentials", methods=["POST"])
def save_credentials():
    session.pop("error", None)
    try:
        api_id = int(request.form.get("api_id").strip())
        api_hash = request.form.get("api_hash").strip()
        phone = request.form.get("phone").strip()
        
        session["api_id"] = api_id
        session["api_hash"] = api_hash
        session["phone"] = phone

        async def _send():
            from pyrogram import Client
            client = Client(f"session_{phone.replace('+', '')}", api_id=api_id, api_hash=api_hash, in_memory=True)
            await client.connect()
            sent_code = await client.send_code(phone)
            return sent_code

        sent_code = loop.run_until_complete(_send())
        session["phone_code_hash"] = sent_code.phone_code_hash
        session["waiting_for_otp"] = True
    except Exception as e:
        session["error"] = str(e)
    return redirect(url_for("index"))

@app.route("/verify-otp", methods=["POST"])
def verify_otp():
    session.pop("error", None)
    otp = request.form.get("otp").strip().replace(" ", "")
    phone = session.get("phone")
    phone_code_hash = session.get("phone_code_hash")
    api_id = session.get("api_id")
    api_hash = session.get("api_hash")
    
    async def _verify():
        from pyrogram import Client
        from pyrogram.errors import SessionPasswordNeeded
        client = Client(f"session_{phone.replace('+', '')}", api_id=api_id, api_hash=api_hash, in_memory=True)
        await client.connect()
        try:
            await client.sign_in(phone, phone_code_hash, otp)
            session["logged_in"] = True
            session.pop("waiting_for_otp", None)
            await client.disconnect()
        except SessionPasswordNeeded:
            session.pop("waiting_for_otp", None)
            session["waiting_for_password"] = True
            temp_storage["client"] = client

    try:
        loop.run_until_complete(_verify())
    except Exception as e:
        session["error"] = str(e)
    return redirect(url_for("index"))

@app.route("/verify-password", methods=["POST"])
def verify_password():
    session.pop("error", None)
    password = request.form.get("password")
    client = temp_storage.get("client")
    
    async def _password():
        await client.check_password(password)
        session["logged_in"] = True
        session.pop("waiting_for_password", None)
        await client.disconnect()

    try:
        loop.run_until_complete(_password())
    except Exception as e:
        session["error"] = str(e)
    return redirect(url_for("index"))

@app.route("/upload-audio", methods=["POST"])
def upload_audio():
    if 'audio' not in request.files:
        session["msg"] = "Koi file select nahi ki!"
        return redirect(url_for("index"))
    
    file = request.files['audio']
    loop_mode = request.form.get("loop_mode")
    
    if file.filename == '':
        session["msg"] = "File ka naam khali hai!"
        return redirect(url_for("index"))
    
    if file:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], "audio.mp3")
        file.save(filepath)
        session["msg"] = f"✅ Audio successfully upload ho gayi! Mode: {loop_mode.upper()}"
    
    return redirect(url_for("index"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

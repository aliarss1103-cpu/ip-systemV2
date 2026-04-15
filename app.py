from flask import Flask, request
import sqlite3
from datetime import datetime, timedelta
import requests

app = Flask(__name__)

# DB oluştur
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
            saat TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# IP bilgisi çek
def ip_bilgi(ip):
    try:
        r = requests.get(f"http://ip-api.com/json/{ip}?fields=status,country,city,isp")
        data = r.json()
        if data["status"] == "success":
            return data["country"], data["city"], data["isp"]
    except:
        pass
    return "Bilinmiyor", "Bilinmiyor", "Bilinmiyor"

# IP kaydet (30 dk kontrol var)
def ekle(ip):
    now = datetime.now()
    conn = sqlite3.connect("data.db")
    c = conn.cursor()

    # son kayıt kontrol
    c.execute("SELECT tarih, saat FROM logs WHERE ip=? ORDER BY id DESC LIMIT 1", (ip,))
    last = c.fetchone()

    if last:
        last_time = datetime.strptime(last[0] + " " + last[1], "%Y-%m-%d %H:%M:%S")
        if now - last_time < timedelta(minutes=30):
            conn.close()
            return  # 30 dk dolmadıysa ekleme

    ulke, sehir, isp = ip_bilgi(ip)

    c.execute(
        "INSERT INTO logs (ip, ulke, sehir, isp, tarih, saat) VALUES (?, ?, ?, ?, ?, ?)",
        (ip, ulke, sehir, isp, now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S"))
    )
    conn.commit()
    conn.close()

# Liste çek
def getir():
    conn = sqlite3.connect("data.db")
    c = conn.cursor()
    c.execute("SELECT ip, ulke, sehir, isp, tarih, saat FROM logs ORDER BY id DESC")
    data = c.fetchall()
    conn.close()
    return data

# 404 SAYFA
@app.route("/")
def home():
    return """
    <html>
    <body style="background:black;color:white;text-align:center;font-family:Arial;padding-top:100px;">
        <h1>ERROR 404</h1>
        <p>Page Not Found</p>
        <p style="font-size:12px;color:gray;">
            The page you are looking for might have been removed,<br>
            had its name changed, or is temporarily unavailable.
        </p>
    </body>
    </html>
    """, 404

# ADMIN PANEL
@app.route("/rexa/1103")
def admin():
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    ip = ip.split(",")[0].strip()

    ekle(ip)
    data = getir()

    html = """
    <html>
    <head>
        <meta http-equiv="refresh" content="5">
        <title>ADMIN PANEL</title>
        <style>
            body { background:#0a0a0a; color:#00ff00; font-family:monospace; padding:20px; }
            .box { border-bottom:1px solid #222; padding:10px; }
        </style>
    </head>
    <body>
        <h2>IP LOGS</h2>
    """

    for ip, ulke, sehir, isp, tarih, saat in data:
        html += f"""
        <div class="box">
            IP: {ip} <br>
            Ülke: {ulke} | Şehir: {sehir} <br>
            ISP: {isp} <br>
            Tarih: {tarih} {saat}
        </div>
        """

    html += "</body></html>"
    return html

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
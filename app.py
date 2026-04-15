from flask import Flask, request
import sqlite3
import requests
import os
from datetime import datetime, timedelta

app = Flask(__name__)

DB = "data.db"
WEBHOOK = os.getenv("DISCORD_WEBHOOK")


# ---------------- DATABASE ----------------
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip TEXT,
            country TEXT,
            city TEXT,
            isp TEXT,
            time TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()


# ---------------- GEO IP ----------------
def geo(ip):
    try:
        r = requests.get(f"http://ip-api.com/json/{ip}", timeout=3).json()
        return r.get("country","?"), r.get("city","?"), r.get("isp","?")
    except:
        return "?", "?", "?"


# ---------------- WEBHOOK ----------------
def send(msg):
    if WEBHOOK:
        try:
            requests.post(WEBHOOK, json={"content": msg}, timeout=3)
        except:
            pass


# ---------------- COOLDOWN (30 DK) ----------------
def blocked(ip):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT time FROM logs WHERE ip=? ORDER BY id DESC LIMIT 1", (ip,))
    row = c.fetchone()
    conn.close()

    if not row:
        return False

    last = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
    return datetime.now() - last < timedelta(minutes=30)


# ---------------- INSERT LOG ----------------
def log(ip, country, city, isp):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("INSERT INTO logs (ip,country,city,isp,time) VALUES (?,?,?,?,?)",
              (ip, country, city, isp, now))
    conn.commit()
    conn.close()

    send(f"📡 IP: {ip} | {country} - {city} | {isp} | {now}")


# ---------------- 404 PAGE ----------------
@app.route("/")
def home():
    return """
    <body style="background:black;color:white;text-align:center;font-family:monospace;padding-top:120px;">
        <h1 style="font-size:70px;">404</h1>
        <h3>PAGE NOT FOUND</h3>
        <p style="color:gray;">The page you are looking for does not exist.</p>
        <p style="color:gray;">Check the URL and try again.</p>
    </body>
    """, 404


# ---------------- ADMIN PANEL ----------------
@app.route("/rexa/1103")
def admin():

    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    ip = ip.split(",")[0].strip()

    if blocked(ip):
        return "<h1 style='color:red'>WAIT 30 MINUTES</h1>"

    country, city, isp = geo(ip)
    log(ip, country, city, isp)

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT ip,country,city,isp,time FROM logs ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()

    html = ""
    for r in rows:
        html += f"<div>{r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]}</div><hr>"

    return f"""
    <html>
    <body style="background:#0d0d0d;color:#00ff00;font-family:monospace;padding:20px;">
        <h2>ADMIN PANEL</h2>
        <meta http-equiv="refresh" content="5">
        {html}
    </body>
    </html>
    """


# ---------------- RUN ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

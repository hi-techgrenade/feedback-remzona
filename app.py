from datetime import datetime
from urllib.parse import quote_plus
import time
import re
import os

import requests
from flask import Flask, jsonify, request, send_from_directory

app = Flask(__name__, static_folder=".", static_url_path="")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
CHAT_ID = os.getenv("CHAT_ID", "").strip()

if not BOT_TOKEN or not CHAT_ID:
    raise RuntimeError("Set BOT_TOKEN and CHAT_ID environment variables")

MAX_MESSAGE_LENGTH = 1500

last_message = None
last_time = 0


def is_mobile_request(user_agent: str) -> bool:
    if not user_agent:
        return False

    ua = user_agent.lower()
    mobile_markers = (
        "android",
        "iphone",
        "ipad",
        "ipod",
        "mobile",
        "windows phone",
        "opera mini",
        "blackberry",
    )

    return any(marker in ua for marker in mobile_markers)


def send_telegram(text: str):

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    requests.post(
        url,
        json={
            "chat_id": CHAT_ID,
            "text": text
        },
        timeout=10
    )


@app.route("/")
def index():
    if not is_mobile_request(request.headers.get("User-Agent", "")):
        qr_data = quote_plus(request.url)
        qr_src = f"https://api.qrserver.com/v1/create-qr-code/?size=320x320&data={qr_data}"
        return (
            (
                "<!doctype html>"
                "<html lang='ru'><head><meta charset='utf-8'>"
                "<meta name='viewport' content='width=device-width,initial-scale=1'>"
                "<title>Откройте с телефона</title>"
                "<style>"
                "body{margin:0;min-height:100vh;display:grid;place-items:center;"
                "font-family:Arial,sans-serif;background:#f2f6ff;color:#102048;padding:20px}"
                ".card{max-width:420px;width:100%;background:#fff;border-radius:20px;padding:24px;"
                "text-align:center;box-shadow:0 20px 40px rgba(16,32,72,.12)}"
                ".logo{width:220px;max-width:90%;margin:0 auto 14px;display:block}"
                "h1{margin:0 0 8px;font-size:28px}.muted{margin:0 0 16px;color:#5b6785}"
                ".qr{width:220px;height:220px;max-width:100%;border-radius:12px;"
                "border:1px solid #dbe6ff}.small{margin-top:12px;color:#6e7892;font-size:14px}"
                "</style></head><body><div class='card'>"
                "<img class='logo' src='/logo.jpg' alt='РемЗОНА'>"
                "<h1>Зайдите с телефона</h1>"
                "<p class='muted'>Наведите камеру на QR-код и откройте страницу на смартфоне.</p>"
                f"<img class='qr' src='{qr_src}' alt='QR-код для открытия сайта'>"
                "<div class='small'>Если QR не сканируется, попробуйте открыть эту ссылку в браузере телефона вручную.</div>"
                "</div></body></html>"
            ),
            200,
            {"Content-Type": "text/html; charset=utf-8"},
        )

    return send_from_directory(".", "index.html")


@app.route("/logo.jpg")
def logo():
    return send_from_directory(".", "logo.jpg")


@app.route("/favicon.ico")
def favicon():
    return "", 204


@app.route("/feedback", methods=["POST"])
def feedback():

    global last_message
    global last_time

    data = request.get_json(force=True)

    name = (data.get("name") or "").strip()
    phone = (data.get("phone") or "").strip()
    message = (data.get("message") or "").strip()
    honey = (data.get("company") or "").strip()  # honeypot

    # honeypot защита
    if honey:
        return jsonify({"ok": False})

    if not message:
        return jsonify({"ok": False})

    if len(message) > MAX_MESSAGE_LENGTH:
        return jsonify({"ok": False})

    # блок ссылок
    if "http://" in message or "https://" in message:
        return jsonify({"ok": False})

    # телефон обязателен: минимум 10 цифр
    if not phone:
        return jsonify({"ok": False})
    if not re.fullmatch(r"[0-9+()\-\s]{10,25}", phone):
        return jsonify({"ok": False})
    digits_only = re.sub(r"\D", "", phone)
    if len(digits_only) < 10:
        return jsonify({"ok": False})

    # защита от спама одинаковыми сообщениями
    if message == last_message:
        return jsonify({"ok": False})

    # минимальная пауза между отправками
    if time.time() - last_time < 2:
        return jsonify({"ok": False})

    last_message = message
    last_time = time.time()

    now = datetime.now().strftime("%d.%m %H:%M")

    text = (
        "🛠 Новая обратная связь\n\n"
        f"🕒 {now}\n"
        f"👤 {name or 'Не указано'}\n"
        f"📞 {phone}\n\n"
        f"{message}"
    )

    send_telegram(text)

    return jsonify({"ok": True})


@app.route("/track", methods=["POST"])
def track():

    data = request.get_json(force=True)

    platform = (data.get("platform") or "").strip()

    if not platform:
        return jsonify({"ok": True})

    now = datetime.now().strftime("%d.%m %H:%M")

    text = f"⭐ Переход на отзыв\n{platform}\n🕒 {now}"

    send_telegram(text)

    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)

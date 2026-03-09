from datetime import datetime
import time

import requests
from flask import Flask, jsonify, request, send_from_directory

app = Flask(__name__, static_folder=".", static_url_path="")

BOT_TOKEN = "8512904617:AAEG2wyXs5bMGAQ-bJ9t1fa-ZLoPwGzS6ow"
CHAT_ID = "7493805659"

MAX_MESSAGE_LENGTH = 1500

last_message = None
last_time = 0


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
        f"📞 {phone or 'Не указан'}\n\n"
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
    app.run(host="0.0.0.0", port=5000, debug=True)
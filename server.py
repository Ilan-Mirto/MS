import os
from datetime import datetime, timezone

from flask import Flask, render_template, request
from flask_socketio import SocketIO


socketio = SocketIO(async_mode="threading")


@socketio.on("connect")
def handle_connect(_auth=None):
    print(f"Client connecté : {request.sid}")


@socketio.on("disconnect")
def handle_disconnect(_reason=None):
    print(f"Client déconnecté : {request.sid}")


@socketio.on("send_message")
def handle_send_message(data):
    if not isinstance(data, dict):
        return

    name = data.get("name")
    text = data.get("text")
    if not isinstance(name, str) or not isinstance(text, str):
        return

    name = " ".join(name.split())[:24] or "Anonyme"
    text = text.strip()[:500]
    if not text:
        return

    socketio.emit(
        "chat_message",
        {
            "name": name,
            "text": text,
            "sender_id": request.sid,
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        },
    )

@socketio.on("send_image")
def handle_send_image(data):
    if not isinstance(data, dict):
        return

    name = data.get("name")
    image_url = data.get("image_url")
    if not isinstance(name, str) or not isinstance(image_url, str):
        return

    name = " ".join(name.split())[:24] or "Anonyme"
    image_url = image_url.strip()[:500]
    if not image_url:
        return

    socketio.emit(
        "chat_image",
        {
            "name": name,
            "image_url": image_url,
            "sender_id": request.sid,
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        },
    )


def create_app():
    app = Flask(__name__)

    @app.get("/")
    def index():
        return render_template("index.html")

    socketio.init_app(app)
    return app


app = create_app()


if __name__ == "__main__":
    socketio.run(
        app,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "5000")),
        allow_unsafe_werkzeug=True,
    )
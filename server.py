import os
import sqlite3
from datetime import datetime, timezone

from flask import Flask, current_app, request
from flask_socketio import SocketIO
from views import load_messages, views as views_blueprint


socketio = SocketIO(async_mode="threading")


def initialize_database(app):
    database_path = app.config["DATABASE"]
    os.makedirs(os.path.dirname(os.path.abspath(database_path)), exist_ok=True)

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL,
                name TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )"""
        )


def save_message(kind, name, content, timestamp):
    connection = sqlite3.connect(current_app.config["DATABASE"])
    try:
        connection.execute( 
            "INSERT INTO messages (kind, name, content, timestamp) VALUES (?, ?,?, ?)",
            (kind, name, content, timestamp),
        )
        connection.commit()
    finally:
        connection.close()


@socketio.on("connect")
def handle_connect(_auth=None):
    print(f"Client connecté : {request.sid}")
    socketio.emit("chat_history", load_messages(), to=request.sid)


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

    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    save_message("text", name, text, timestamp)
    socketio.emit(
        "chat_message",
        {
            "name": name,
            "text": text,
            "sender_id": request.sid,
            "timestamp": timestamp,
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

    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    save_message("image", name, image_url, timestamp)
    socketio.emit(
        "chat_image",
        {
            "name": name,
            "image_url": image_url,
            "sender_id": request.sid,
            "timestamp": timestamp,
        },
    )


def create_app(test_config=None):
    app = Flask(__name__)
    app.config["DATABASE"] = os.environ.get(
        "CHAT_DATABASE", os.path.join(app.instance_path, "chat.db")
    )
    if test_config:
        app.config.update(test_config)

    initialize_database(app)

    app.register_blueprint(views_blueprint)
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
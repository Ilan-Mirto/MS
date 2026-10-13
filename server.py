import os
import secrets
import sqlite3
from datetime import datetime, timezone

from flask import Flask, current_app, request, session
from flask_socketio import SocketIO
from views import load_messages, views as views_blueprint


socketio = SocketIO(async_mode="threading")


def initialize_database(app):
    database_path = app.config["DATABASE"]
    os.makedirs(os.path.dirname(os.path.abspath(database_path)), exist_ok=True)

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                first_name_key TEXT NOT NULL,
                last_name_key TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                UNIQUE (first_name_key, last_name_key)
            )"""
        )
        user_columns = {
            column[1] for column in connection.execute("PRAGMA table_info(users)")
        }
        added_name_keys = False
        if "first_name_key" not in user_columns:
            connection.execute("ALTER TABLE users ADD COLUMN first_name_key TEXT")
            added_name_keys = True
        if "last_name_key" not in user_columns:
            connection.execute("ALTER TABLE users ADD COLUMN last_name_key TEXT")
            added_name_keys = True
        if added_name_keys:
            users = connection.execute(
                "SELECT id, first_name, last_name FROM users"
            ).fetchall()
            for user_id, first_name, last_name in users:
                connection.execute(
                    "UPDATE users SET first_name_key = ?, last_name_key = ? "
                    "WHERE id = ?",
                    (first_name.casefold(), last_name.casefold(), user_id),
                )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_users_name_key "
                "ON users (first_name_key, last_name_key)"
            )
        connection.execute(
            """CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL,
                name TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                user_id INTEGER REFERENCES users(id)
            )"""
        )
        message_columns = {
            column[1] for column in connection.execute("PRAGMA table_info(messages)")
        }
        if "user_id" not in message_columns:
            connection.execute("ALTER TABLE messages ADD COLUMN user_id INTEGER")


def save_message(kind, user_id, name, content, timestamp):
    connection = sqlite3.connect(current_app.config["DATABASE"])
    try:
        cursor = connection.execute(
            "INSERT INTO messages (kind, name, content, timestamp, user_id) "
            "VALUES (?, ?, ?, ?, ?)",
            (kind, name, content, timestamp, user_id),
        )
        connection.commit()
        return cursor.lastrowid
    finally:
        connection.close()


def authenticated_user():
    user_id = session.get("user_id")
    user_name = session.get("user_name")
    if not isinstance(user_id, int) or not isinstance(user_name, str):
        return None
    return {"id": user_id, "name": user_name}


@socketio.on("connect")
def handle_connect(_auth=None):
    user = authenticated_user()
    if user is None:
        return False

    print(f"Client connecté : {user['name']} ({request.sid})")
    socketio.emit("chat_history", load_messages(), to=request.sid)
    socketio.emit(
        "system_message",
        {
            "text": f"{user['name']} vient de rejoindre le salon.",
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        },
        skip_sid=request.sid,
    )


@socketio.on("disconnect")
def handle_disconnect(_reason=None):
    print(f"Client déconnecté : {request.sid}")


@socketio.on("send_message")
def handle_send_message(data):
    user = authenticated_user()
    if user is None or not isinstance(data, dict):
        return

    text = data.get("text")
    if not isinstance(text, str):
        return

    text = text.strip()[:500]
    if not text:
        return

    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    message_id = save_message("text", user["id"], user["name"], text, timestamp)
    socketio.emit(
        "chat_message",
        {
            "id": message_id,
            "user_id": user["id"],
            "name": user["name"],
            "text": text,
            "timestamp": timestamp,
        },
    )


@socketio.on("send_image")
def handle_send_image(data):
    user = authenticated_user()
    if user is None or not isinstance(data, dict):
        return

    image_url = data.get("image_url")
    if not isinstance(image_url, str):
        return

    image_url = image_url.strip()[:500]
    if not image_url:
        return

    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    message_id = save_message("image", user["id"], user["name"], image_url, timestamp)
    socketio.emit(
        "chat_image",
        {
            "id": message_id,
            "user_id": user["id"],
            "name": user["name"],
            "image_url": image_url,
            "timestamp": timestamp,
        },
    )


def create_app(test_config=None):
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("CHAT_SECRET_KEY") or secrets.token_hex(32)
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
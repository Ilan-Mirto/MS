import os
import secrets
from datetime import datetime, timezone

from flask import Flask, request, session
from flask_socketio import SocketIO
from sqlalchemy import inspect, text
from models import Message, USER_NAME_INDEX, User, db
from views import load_messages, views as views_blueprint


socketio = SocketIO(async_mode="threading")


def initialize_database():
    db.create_all()

    with db.engine.begin() as connection:
        user_columns = {
            column["name"] for column in inspect(connection).get_columns("users")
        }
        added_name_keys = False
        if "first_name_key" not in user_columns:
            connection.execute(text("ALTER TABLE users ADD COLUMN first_name_key TEXT"))
            added_name_keys = True
        if "last_name_key" not in user_columns:
            connection.execute(text("ALTER TABLE users ADD COLUMN last_name_key TEXT"))
            added_name_keys = True
        if added_name_keys:
            users = connection.execute(
                text("SELECT id, first_name, last_name FROM users")
            ).mappings()
            for user in users:
                connection.execute(
                    text(
                        "UPDATE users SET first_name_key = :first_name_key, "
                        "last_name_key = :last_name_key WHERE id = :user_id"
                    ),
                    {
                        "first_name_key": user["first_name"].casefold(),
                        "last_name_key": user["last_name"].casefold(),
                        "user_id": user["id"],
                    },
                )

        message_columns = {
            column["name"] for column in inspect(connection).get_columns("messages")
        }
        if "user_id" not in message_columns:
            connection.execute(text("ALTER TABLE messages ADD COLUMN user_id INTEGER"))

    USER_NAME_INDEX.create(bind=db.engine, checkfirst=True)


def save_message(kind, user_id, name, content, timestamp):
    message = Message(
        kind=kind,
        user_id=user_id,
        name=name,
        content=content,
        timestamp=timestamp,
    )
    db.session.add(message)
    db.session.commit()
    return message.id


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
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    if test_config:
        app.config.update(test_config)

    if not test_config or "SQLALCHEMY_DATABASE_URI" not in test_config:
        database_setting = app.config["DATABASE"]
        if "://" in database_setting:
            app.config["SQLALCHEMY_DATABASE_URI"] = database_setting
        else:
            database_path = os.path.abspath(database_setting)
            os.makedirs(os.path.dirname(database_path), exist_ok=True)
            app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{database_path}"

    db.init_app(app)
    with app.app_context():
        initialize_database()

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
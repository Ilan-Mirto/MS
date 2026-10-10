import os

from flask import Flask, render_template, request
from flask_socketio import SocketIO


socketio = SocketIO(async_mode="threading")


@socketio.on("connect")
def handle_connect(_auth=None):
    print(f"Client connecté : {request.sid}")


@socketio.on("disconnect")
def handle_disconnect(_reason=None):
    print(f"Client déconnecté : {request.sid}")


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
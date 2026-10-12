import sqlite3

from flask import Blueprint, current_app, render_template


views = Blueprint("views", __name__)


def load_messages():
	connection = sqlite3.connect(current_app.config["DATABASE"])
	try:
		rows = connection.execute(
			"SELECT kind, name, content, timestamp FROM messages ORDER BY id"
		).fetchall()
	finally:
		connection.close()

	messages = []
	for kind, name, content, timestamp in rows:
		content_key = "text" if kind == "text" else "image_url"
		messages.append(
			{
				"type": kind,
				"name": name,
				content_key: content,
				"timestamp": timestamp,
			}
		)
	return messages


@views.get("/")
def index():
	return render_template("index.html")


@views.get("/messages")
def message_history():
	return render_template("messages.html", messages=load_messages())

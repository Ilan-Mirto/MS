import hmac
import secrets
import sqlite3

from flask import (
	Blueprint,
	current_app,
	flash,
	redirect,
	render_template,
	request,
	session,
	url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash


views = Blueprint("views", __name__)
INDEX_ENDPOINT = "views.index"


def load_messages():
	connection = sqlite3.connect(current_app.config["DATABASE"])
	try:
		rows = connection.execute(
			"SELECT kind, name, content, timestamp, user_id FROM messages ORDER BY id"
		).fetchall()
	finally:
		connection.close()

	messages = []
	for kind, name, content, timestamp, user_id in rows:
		content_key = "text" if kind == "text" else "image_url"
		messages.append(
			{
				"type": kind,
				"name": name,
				"user_id": user_id,
				content_key: content,
				"timestamp": timestamp,
			}
		)
	return messages


def csrf_token():
	token = session.get("csrf_token")
	if token is None:
		token = secrets.token_urlsafe(32)
		session["csrf_token"] = token
	return token


def valid_csrf_token():
	stored_token = session.get("csrf_token", "")
	submitted_token = request.form.get("csrf_token", "")
	return bool(stored_token) and hmac.compare_digest(stored_token, submitted_token)


def authenticate_or_create(first_name, last_name, password):
	first_name_key = first_name.casefold()
	last_name_key = last_name.casefold()
	connection = sqlite3.connect(current_app.config["DATABASE"])
	try:
		users = connection.execute(
			"SELECT id, first_name, last_name, password_hash FROM users "
			"WHERE first_name_key = ? AND last_name_key = ?",
			(first_name_key, last_name_key),
		).fetchall()
		for user in users:
			if check_password_hash(user[3], password):
				return user[0], user[1], user[2]
		if users:
			return None

		password_hash = generate_password_hash(password)
		try:
			cursor = connection.execute(
				"INSERT INTO users "
				"(first_name, last_name, first_name_key, last_name_key, password_hash) "
				"VALUES (?, ?, ?, ?, ?)",
				(first_name, last_name, first_name_key, last_name_key, password_hash),
			)
			connection.commit()
			return cursor.lastrowid, first_name, last_name
		except sqlite3.IntegrityError:
			connection.rollback()
			users = connection.execute(
				"SELECT id, first_name, last_name, password_hash FROM users "
				"WHERE first_name_key = ? AND last_name_key = ?",
				(first_name_key, last_name_key),
			).fetchall()
			for user in users:
				if check_password_hash(user[3], password):
					return user[0], user[1], user[2]
			return None
	finally:
		connection.close()


@views.route("/", methods=["GET", "POST"])
def index():
	if request.method == "POST":
		if not valid_csrf_token():
			flash("Formulaire expiré. Réessaie.", "error")
			return redirect(url_for(INDEX_ENDPOINT))

		first_name = " ".join(request.form.get("first_name", "").split())[:40]
		last_name = " ".join(request.form.get("last_name", "").split())[:40]
		password = request.form.get("password", "")
		if not first_name or not last_name or len(password) < 8 or len(password) > 128:
			flash("Renseigne ton nom, ton prénom et un mot de passe de 8 caractères minimum.", "error")
			return redirect(url_for(INDEX_ENDPOINT))

		user = authenticate_or_create(first_name, last_name, password)
		if user is None:
			flash("Nom, prénom ou mot de passe incorrect.", "error")
			return redirect(url_for(INDEX_ENDPOINT))

		session.clear()
		session["user_id"] = user[0]
		session["user_name"] = f"{user[1]} {user[2]}"
		csrf_token()
		return redirect(url_for(INDEX_ENDPOINT))

	if isinstance(session.get("user_id"), int) and isinstance(session.get("user_name"), str):
		return render_template(
			"index.html",
			user={"id": session["user_id"], "full_name": session["user_name"]},
			csrf_token=csrf_token(),
		)
	return render_template("login.html", csrf_token=csrf_token())


@views.post("/logout")
def logout():
	if not valid_csrf_token():
		flash("Formulaire expiré. Réessaie.", "error")
		return redirect(url_for(INDEX_ENDPOINT))
	session.clear()
	return redirect(url_for(INDEX_ENDPOINT))


@views.get("/messages")
def message_history():
	if not isinstance(session.get("user_id"), int):
		return redirect(url_for(INDEX_ENDPOINT))
	return render_template("messages.html", messages=load_messages())

import hmac
import secrets

from flask import (
	Blueprint,
	flash,
	redirect,
	render_template,
	request,
	session,
	url_for,
)
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash
from models import Message, User, db


views = Blueprint("views", __name__)
INDEX_ENDPOINT = "views.index"


def load_messages():
	messages = []
	for message in Message.query.order_by(Message.id).all():
		content_key = "text" if message.kind == "text" else "image_url"
		messages.append(
			{
				"type": message.kind,
				"name": message.name,
				"user_id": message.user_id,
				content_key: message.content,
				"timestamp": message.timestamp,
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
	users = User.query.filter_by(
		first_name_key=first_name_key, last_name_key=last_name_key
	).all()
	for user in users:
		if check_password_hash(user.password_hash, password):
			return user.id, user.first_name, user.last_name
	if users:
		return None

	user = User(
		first_name=first_name,
		last_name=last_name,
		first_name_key=first_name_key,
		last_name_key=last_name_key,
		password_hash=generate_password_hash(password),
	)
	db.session.add(user)
	try:
		db.session.commit()
		return user.id, user.first_name, user.last_name
	except IntegrityError:
		db.session.rollback()
		users = User.query.filter_by(
			first_name_key=first_name_key, last_name_key=last_name_key
		).all()
		for existing_user in users:
			if check_password_hash(existing_user.password_hash, password):
				return existing_user.id, existing_user.first_name, existing_user.last_name
		return None


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

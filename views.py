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
from models import Message, Party, PartyBan, PartyMembership, User, db, Game
from datetime import datetime, timezone


views = Blueprint("views", __name__)
INDEX_ENDPOINT = "views.index"
GAMES_ENDPOINT = "views.games"
CREATE_PARTY_ENDPOINT = "views.create_party"
PARTY_VIEW_ENDPOINT = "views.view_party"
FORM_EXPIRED_MESSAGE = "Formulaire expiré. Réessaie."


def redirect_to_party(party_id):
	return redirect(url_for(PARTY_VIEW_ENDPOINT, party_id=party_id))


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
			flash(FORM_EXPIRED_MESSAGE, "error")
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
		flash(FORM_EXPIRED_MESSAGE, "error")
		return redirect(url_for(INDEX_ENDPOINT))
	session.clear()
	return redirect(url_for(INDEX_ENDPOINT))


@views.get("/messages")
def message_history():
	if not isinstance(session.get("user_id"), int):
		return redirect(url_for(INDEX_ENDPOINT))
	return render_template(
		"messages.html", messages=load_messages(), csrf_token=csrf_token()
	)


@views.get("/games")
def games():
	if not isinstance(session.get("user_id"), int):
		return redirect(url_for(INDEX_ENDPOINT))

	games = Game.query.order_by(Game.id).all()
	party_cards = []
	for party in Party.query.order_by(Party.id.desc()).all():
		game = db.session.get(Game, party.game_id)
		if game is not None:
			party_cards.append(
				{
					"party": party,
					"game": game,
					"member_count": PartyMembership.query.filter_by(party_id=party.id).count(),
				}
			)

	session_is_hosting = Party.query.filter_by(host_id=session["user_id"]).first() is not None

	return render_template(
		"games.html",
		games=games,
		party_cards=party_cards,
		session_is_hosting=session_is_hosting,
		csrf_token=csrf_token()
	)


@views.post("/party/<int:party_id>/join")
def join_party(party_id):
	if not isinstance(session.get("user_id"), int):
		return redirect(url_for(INDEX_ENDPOINT))
	party = Party.query.get_or_404(party_id)
	user_id = session["user_id"]
	if not valid_csrf_token():
		flash(FORM_EXPIRED_MESSAGE, "error")
		return redirect_to_party(party.id)
	if PartyBan.query.filter_by(user_id=user_id, party_id=party.id).first() is not None:
		flash("Tu ne peux plus rejoindre cette partie.", "error")
		return redirect_to_party(party.id)
	if Party.query.filter_by(host_id=user_id).first() is not None:
		flash("Un hôte ne peut pas rejoindre une autre partie.", "error")
		return redirect_to_party(party.id)
	if party.is_started:
		flash("Cette partie a déjà commencé.", "error")
		return redirect_to_party(party.id)
	existing_membership = PartyMembership.query.filter_by(user_id=user_id).first()
	if existing_membership is not None:
		if existing_membership.party_id == party.id:
			return redirect_to_party(party.id)
		flash("Tu fais déjà partie d’une autre partie.", "error")
		return redirect_to_party(party.id)
	party_password = request.form.get("party_password", "")
	if party.password_hash and not check_password_hash(party.password_hash, party_password):
		flash("Mot de passe incorrect.", "error")
		return redirect_to_party(party.id)
	game = Game.query.get_or_404(party.game_id)
	member_count = PartyMembership.query.filter_by(party_id=party.id).count()
	if member_count >= game.nb_players_max:
		flash("Cette partie est complète.", "error")
		return redirect_to_party(party.id)
	db.session.add(
		PartyMembership(
			user_id=user_id,
			party_id=party.id,
			connected_at=datetime.now(timezone.utc).isoformat(),
		)
	)
	db.session.commit()
	flash("Tu as rejoint la partie.", "success")
	return redirect_to_party(party.id)


@views.post("/party/<int:party_id>/leave")
def leave_party(party_id):
	if not isinstance(session.get("user_id"), int):
		return redirect(url_for(INDEX_ENDPOINT))
	party = Party.query.get_or_404(party_id)
	user_id = session["user_id"]
	if not valid_csrf_token():
		flash(FORM_EXPIRED_MESSAGE, "error")
		return redirect_to_party(party.id)
	if party.host_id == user_id:
		flash("L’hôte ne peut pas quitter sa partie.", "error")
		return redirect_to_party(party.id)

	membership = PartyMembership.query.filter_by(
		user_id=user_id, party_id=party.id
	).first()
	if membership is None:
		flash("Tu ne fais pas partie de cette partie.", "error")
		return redirect_to_party(party.id)

	db.session.delete(membership)
	db.session.commit()
	flash("Tu as quitté la partie.", "success")
	return redirect(url_for(GAMES_ENDPOINT))


@views.post("/party/<int:party_id>/kick/<int:user_id>")
def kick_party_member(party_id, user_id):
	if not isinstance(session.get("user_id"), int):
		return redirect(url_for(INDEX_ENDPOINT))
	party = Party.query.get_or_404(party_id)
	if not valid_csrf_token():
		flash(FORM_EXPIRED_MESSAGE, "error")
		return redirect_to_party(party.id)
	if party.host_id != session["user_id"]:
		flash("Seul l’hôte peut exclure un joueur.", "error")
		return redirect_to_party(party.id)
	if party.is_started:
		flash("Les joueurs ne peuvent plus être exclus après le lancement.", "error")
		return redirect_to_party(party.id)
	if user_id == party.host_id:
		flash("L’hôte ne peut pas être exclu de sa partie.", "error")
		return redirect_to_party(party.id)
	membership = PartyMembership.query.filter_by(user_id=user_id, party_id=party.id).first()
	if membership is None:
		flash("Ce joueur ne fait pas partie du salon.", "error")
		return redirect_to_party(party.id)
	db.session.delete(membership)
	if PartyBan.query.filter_by(user_id=user_id, party_id=party.id).first() is None:
		db.session.add(PartyBan(user_id=user_id, party_id=party.id))
	db.session.commit()
	flash("Le joueur a été exclu de la partie.", "success")
	return redirect_to_party(party.id)


@views.post("/party/<int:party_id>/start")
def start_party(party_id):
	if not isinstance(session.get("user_id"), int):
		return redirect(url_for(INDEX_ENDPOINT))
	party = Party.query.get_or_404(party_id)
	if not valid_csrf_token():
		flash(FORM_EXPIRED_MESSAGE, "error")
		return redirect_to_party(party.id)
	if party.host_id != session["user_id"]:
		flash("Seul l’hôte peut lancer la partie.", "error")
		return redirect_to_party(party.id)
	if party.is_started:
		flash("Cette partie a déjà commencé.", "error")
		return redirect_to_party(party.id)
	game = Game.query.get_or_404(party.game_id)
	member_count = PartyMembership.query.filter_by(party_id=party.id).count()
	if member_count < game.nb_players_min:
		flash(f"Il faut au moins {game.nb_players_min} joueurs pour lancer la partie.", "error")
		return redirect_to_party(party.id)
	party.is_started = True
	db.session.commit()
	flash("La partie est lancée.", "success")
	return redirect_to_party(party.id)


@views.post("/party/<int:party_id>/delete")
def delete_party(party_id):
	if not isinstance(session.get("user_id"), int):
		return redirect(url_for(INDEX_ENDPOINT))
	party = Party.query.get_or_404(party_id)
	if not valid_csrf_token():
		flash(FORM_EXPIRED_MESSAGE, "error")
		return redirect_to_party(party.id)
	if party.host_id != session["user_id"]:
		flash("Seul l’hôte peut supprimer cette partie.", "error")
		return redirect_to_party(party.id)

	PartyMembership.query.filter_by(party_id=party.id).delete()
	PartyBan.query.filter_by(party_id=party.id).delete()
	db.session.delete(party)
	db.session.commit()
	flash("La partie a été supprimée.", "success")
	return redirect(url_for(GAMES_ENDPOINT))


@views.route("/create-party", methods=["GET", "POST"])
def create_party():
	if not isinstance(session.get("user_id"), int):
		return redirect(url_for(INDEX_ENDPOINT))

	if Party.query.filter_by(host_id=session["user_id"]).first() is not None:
		flash("Vous hébergez déjà une partie.", "error")
		return redirect(url_for(GAMES_ENDPOINT))
	if PartyMembership.query.filter_by(user_id=session["user_id"]).first() is not None:
		flash("Tu dois quitter ta partie actuelle avant d’en créer une.", "error")
		return redirect(url_for(GAMES_ENDPOINT))

	host_id = session.get("user_id")
	game_id = request.args.get("game_id", type=int)
	game = db.session.get(Game, game_id) if game_id else None
	if game is None:
		flash("Jeu invalide.", "error")
		return redirect(url_for(GAMES_ENDPOINT))

	creator_name = session.get("user_name", "")
	if request.method == "POST":
		if not valid_csrf_token():
			flash(FORM_EXPIRED_MESSAGE, "error")
			return redirect(url_for(CREATE_PARTY_ENDPOINT, game_id=game_id))
		party_name = request.form.get("party_name", "").strip()[:100]
		party_password = request.form.get("party_password", "")
		if not party_name:
			flash("Nom de la partie requis.", "error")
			return redirect(url_for(CREATE_PARTY_ENDPOINT, game_id=game_id))
		if len(party_password) > 128:
			flash("Le mot de passe ne peut pas dépasser 128 caractères.", "error")
			return redirect(url_for(CREATE_PARTY_ENDPOINT, game_id=game_id))

		new_party = Party(
			name=party_name,
			game_id=game_id,
			created_at=datetime.now(timezone.utc).isoformat(),
			host_id=host_id,
			password_hash=generate_password_hash(party_password) if party_password else None,
			is_started=False,
		)
		db.session.add(new_party)
		db.session.flush()
		db.session.add(
			PartyMembership(
				user_id=host_id,
				party_id=new_party.id,
				connected_at=datetime.now(timezone.utc).isoformat(),
			)
		)
		db.session.commit()
		flash("Partie créée avec succès.", "success")
		return redirect_to_party(new_party.id)

	return render_template("create_party.html", game_id=game_id, creator_name=creator_name, csrf_token=csrf_token())


@views.route("/party/<int:party_id>")
def view_party(party_id):
	if not isinstance(session.get("user_id"), int):
		return redirect(url_for(INDEX_ENDPOINT))

	party = Party.query.get_or_404(party_id)
	game = Game.query.get_or_404(party.game_id)
	user_id = session["user_id"]
	session_is_hosting = party.host_id == user_id
	members = (
		User.query.join(PartyMembership, User.id == PartyMembership.user_id)
		.filter(PartyMembership.party_id == party.id)
		.order_by(User.first_name, User.last_name)
		.all()
	)
	is_member = PartyMembership.query.filter_by(user_id=user_id, party_id=party.id).first() is not None
	is_banned = PartyBan.query.filter_by(user_id=user_id, party_id=party.id).first() is not None
	return render_template(
		"party.html",
		party=party,
		game=game,
		members=members,
		member_count=len(members),
		is_member=is_member,
		is_banned=is_banned,
		can_start=session_is_hosting and len(members) >= game.nb_players_min and not party.is_started,
		session_is_hosting=session_is_hosting,
		csrf_token=csrf_token()
	)

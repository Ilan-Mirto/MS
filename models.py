from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(40), nullable=False)
    last_name = db.Column(db.String(40), nullable=False)
    first_name_key = db.Column(db.String(40), nullable=False)
    last_name_key = db.Column(db.String(40), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    wins = db.Column(db.Integer, nullable=False, default=0)

    __table_args__ = (
        db.UniqueConstraint(
            "first_name_key", "last_name_key", name="uq_users_name_key"
        ),
        db.Index("idx_users_name_key", "first_name_key", "last_name_key"),
    )


USER_NAME_INDEX = next(index for index in User.__table__.indexes if index.name == "idx_users_name_key")


class Message(db.Model):
    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)
    kind = db.Column(db.String(20), nullable=False)
    name = db.Column(db.String(81), nullable=False)
    content = db.Column(db.String(500), nullable=False)
    timestamp = db.Column(db.String(40), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)


# ? Classe de jeu

class Party(db.Model):
    __tablename__ = "parties"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    game_id = db.Column(db.Integer, db.ForeignKey("games.id"), nullable=False)
    created_at = db.Column(db.String(40), nullable=False)

class isConnected(db.Model):
    __tablename__ = "is_connected"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    party_id = db.Column(db.Integer, db.ForeignKey("parties.id"), nullable=False)
    connected_at = db.Column(db.String(40), nullable=False)

class Game(db.Model):
    __tablename__ = "games"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    imgUrl = db.Column(db.String(500), nullable=True)

class Card(db.Model):
    __tablename__ = "cards"

    id = db.Column(db.Integer, primary_key=True)
    symbole = db.Column(db.String(5), nullable=False)
    symbole_color = db.Column(db.String(20), nullable=False)
    bg_color = db.Column(db.String(20), nullable=False)
    game_id = db.Column(db.Integer, db.ForeignKey("games.id"), nullable=False)
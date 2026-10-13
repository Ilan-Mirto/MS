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

    __table_args__ = (
        db.UniqueConstraint(
            "first_name_key", "last_name_key", name="uq_users_name_key"
        ),
        db.Index("idx_users_name_key", "first_name_key", "last_name_key"),
    )


USER_NAME_INDEX = next(
    index for index in User.__table__.indexes if index.name == "idx_users_name_key"
)


class Message(db.Model):
    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)
    kind = db.Column(db.String(20), nullable=False)
    name = db.Column(db.String(81), nullable=False)
    content = db.Column(db.String(500), nullable=False)
    timestamp = db.Column(db.String(40), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
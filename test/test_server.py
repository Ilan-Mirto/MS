import os
import sqlite3
import tempfile
import unittest

from server import create_app, socketio
from werkzeug.security import check_password_hash, generate_password_hash
from models import Game, Party, PartyBan, PartyMembership, db


class ServerTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = os.path.join(self.temp_dir.name, "chat.db")
        self.app = create_app(
            {
                "TESTING": True,
                "DATABASE": self.database_path,
            }
        )
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def authenticate(self, client, first_name, last_name, password):
        client.get("/")
        with client.session_transaction() as browser_session:
            csrf_token = browser_session["csrf_token"]
        return client.post(
            "/",
            data={
                "csrf_token": csrf_token,
                "first_name": first_name,
                "last_name": last_name,
                "password": password,
            },
        )

    def test_creates_party_and_renders_its_page(self):
        self.authenticate(self.client, "Alice", "Martin", "motdepasse-a")
        with self.client.session_transaction() as browser_session:
            csrf_token = browser_session["csrf_token"]

        response = self.client.post(
            "/create-party?game_id=1",
            data={"csrf_token": csrf_token, "party_name": "Table de test"},
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Table de test", response.data)

    def test_create_party_form_prefills_the_creator_name(self):
        self.authenticate(self.client, "Alice", "Martin", "motdepasse-a")

        response = self.client.get("/create-party?game_id=1")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'value="Partie de Alice Martin"', response.data)

    def test_user_can_join_only_one_party_and_hosts_cannot_join(self):
        self.authenticate(self.client, "Alice", "Martin", "motdepasse-a")
        with self.client.session_transaction() as browser_session:
            host_csrf = browser_session["csrf_token"]
        self.client.post(
            "/create-party?game_id=1",
            data={"csrf_token": host_csrf, "party_name": "Partie Alice"},
        )
        with self.app.app_context():
            first_party_id = Party.query.one().id

        second_host = self.app.test_client()
        self.authenticate(second_host, "Bob", "Durand", "motdepasse-b")
        with second_host.session_transaction() as browser_session:
            second_host_csrf = browser_session["csrf_token"]
        second_host.post(
            "/create-party?game_id=1",
            data={"csrf_token": second_host_csrf, "party_name": "Partie Bob"},
        )
        with self.app.app_context():
            second_party_id = Party.query.order_by(Party.id.desc()).first().id

        player = self.app.test_client()
        self.authenticate(player, "Camille", "Noel", "motdepasse-c")
        with player.session_transaction() as browser_session:
            player_csrf = browser_session["csrf_token"]
            player_id = browser_session["user_id"]
        player.post(
            f"/party/{first_party_id}/join",
            data={"csrf_token": player_csrf},
        )

        second_join = player.post(
            f"/party/{second_party_id}/join",
            data={"csrf_token": player_csrf},
            follow_redirects=True,
        )
        self.assertIn("Tu fais déjà partie d’une autre partie.".encode(), second_join.data)

        host_join = self.client.post(
            f"/party/{second_party_id}/join",
            data={"csrf_token": host_csrf},
            follow_redirects=True,
        )
        self.assertIn("Un hôte ne peut pas rejoindre une autre partie.".encode(), host_join.data)

        create_another = player.get("/create-party?game_id=1", follow_redirects=True)
        self.assertIn("Tu dois quitter ta partie actuelle".encode(), create_another.data)
        with self.app.app_context():
            self.assertEqual(
                PartyMembership.query.filter_by(user_id=player_id).count(), 1
            )

    def test_party_password_and_maximum_capacity_are_enforced(self):
        self.authenticate(self.client, "Alice", "Martin", "motdepasse-a")
        with self.client.session_transaction() as browser_session:
            csrf_token = browser_session["csrf_token"]
        self.client.post(
            "/create-party?game_id=1",
            data={
                "csrf_token": csrf_token,
                "party_name": "Partie privée",
                "party_password": "secret",
            },
        )
        with self.app.app_context():
            party = Party.query.one()
            party_id = party.id
            game = db.session.get(Game, party.game_id)
            game.nb_players_max = 2
            self.assertTrue(check_password_hash(party.password_hash, "secret"))
            self.assertNotEqual(party.password_hash, "secret")
            db.session.commit()
            self.assertEqual(
                PartyMembership.query.filter_by(party_id=party_id).count(), 1
            )

        second_client = self.app.test_client()
        self.authenticate(second_client, "Bob", "Durand", "motdepasse-b")
        with second_client.session_transaction() as browser_session:
            second_csrf = browser_session["csrf_token"]
            second_user_id = browser_session["user_id"]
        wrong_password = second_client.post(
            f"/party/{party_id}/join",
            data={"csrf_token": second_csrf, "party_password": "wrong"},
            follow_redirects=True,
        )
        self.assertIn(b"Mot de passe incorrect", wrong_password.data)

        joined = second_client.post(
            f"/party/{party_id}/join",
            data={"csrf_token": second_csrf, "party_password": "secret"},
            follow_redirects=True,
        )
        self.assertIn(b"Tu as rejoint la partie", joined.data)

        third_client = self.app.test_client()
        self.authenticate(third_client, "Camille", "Noel", "motdepasse-c")
        with third_client.session_transaction() as browser_session:
            third_csrf = browser_session["csrf_token"]
        full_party = third_client.post(
            f"/party/{party_id}/join",
            data={"csrf_token": third_csrf, "party_password": "secret"},
            follow_redirects=True,
        )
        self.assertIn(b"Cette partie est compl\xc3\xa8te", full_party.data)
        with self.app.app_context():
            self.assertEqual(
                PartyMembership.query.filter_by(party_id=party_id).count(), 2
            )

    def test_host_can_kick_and_ban_a_party_member(self):
        self.authenticate(self.client, "Alice", "Martin", "motdepasse-a")
        with self.client.session_transaction() as browser_session:
            host_csrf = browser_session["csrf_token"]
        self.client.post(
            "/create-party?game_id=1",
            data={"csrf_token": host_csrf, "party_name": "Salon"},
        )
        with self.app.app_context():
            party_id = Party.query.one().id

        guest = self.app.test_client()
        self.authenticate(guest, "Bob", "Durand", "motdepasse-b")
        with guest.session_transaction() as browser_session:
            guest_csrf = browser_session["csrf_token"]
            guest_id = browser_session["user_id"]
        guest.post(
            f"/party/{party_id}/join",
            data={"csrf_token": guest_csrf},
        )

        kicked = self.client.post(
            f"/party/{party_id}/kick/{guest_id}",
            data={"csrf_token": host_csrf},
            follow_redirects=True,
        )
        self.assertIn(b"exclu de la partie", kicked.data)
        blocked = guest.post(
            f"/party/{party_id}/join",
            data={"csrf_token": guest_csrf},
            follow_redirects=True,
        )
        self.assertIn(b"Tu ne peux plus rejoindre", blocked.data)
        with self.app.app_context():
            self.assertEqual(
                PartyMembership.query.filter_by(user_id=guest_id, party_id=party_id).count(),
                0,
            )
            self.assertEqual(
                PartyBan.query.filter_by(user_id=guest_id, party_id=party_id).count(),
                1,
            )

    def test_only_host_can_start_after_minimum_players_join(self):
        self.authenticate(self.client, "Alice", "Martin", "motdepasse-a")
        with self.client.session_transaction() as browser_session:
            host_csrf = browser_session["csrf_token"]
        self.client.post(
            "/create-party?game_id=1",
            data={"csrf_token": host_csrf, "party_name": "Salon"},
        )
        with self.app.app_context():
            party_id = Party.query.one().id

        too_early = self.client.post(
            f"/party/{party_id}/start",
            data={"csrf_token": host_csrf},
            follow_redirects=True,
        )
        self.assertIn(b"Il faut au moins 2 joueurs", too_early.data)

        guest = self.app.test_client()
        self.authenticate(guest, "Bob", "Durand", "motdepasse-b")
        with guest.session_transaction() as browser_session:
            guest_csrf = browser_session["csrf_token"]
        guest.post(
            f"/party/{party_id}/join",
            data={"csrf_token": guest_csrf},
        )
        not_host = guest.post(
            f"/party/{party_id}/start",
            data={"csrf_token": guest_csrf},
            follow_redirects=True,
        )
        self.assertIn(b"Seul l\xe2\x80\x99h\xc3\xb4te peut lancer", not_host.data)

        started = self.client.post(
            f"/party/{party_id}/start",
            data={"csrf_token": host_csrf},
            follow_redirects=True,
        )
        self.assertIn(b"La partie est lanc\xc3\xa9e", started.data)
        with self.app.app_context():
            self.assertTrue(db.session.get(Party, party_id).is_started)

    def test_serves_page_and_accepts_socket_io_connection(self):
        first_browser = self.app.test_client()
        self.authenticate(first_browser, "Alice", "Martin", "motdepasse-a")
        response = first_browser.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Salon g\xc3\xa9n\xc3\xa9ral", response.data)
        self.assertIn(b"/static/css/chat.css", response.data)
        self.assertIn(b"/static/js/chat.js", response.data)
        self.assertIn(b'href="/messages"', response.data)
        with first_browser.session_transaction() as browser_session:
            first_user_id = browser_session["user_id"]

        second_browser = self.app.test_client()
        self.authenticate(second_browser, "Bob", "Durand", "motdepasse-b")
        first_client = socketio.test_client(
            self.app, flask_test_client=first_browser
        )
        self.assertTrue(first_client.is_connected())
        self.assertEqual(first_client.get_received()[0]["name"], "chat_history")
        second_client = socketio.test_client(
            self.app, flask_test_client=second_browser
        )
        self.assertTrue(second_client.is_connected())
        self.assertEqual(second_client.get_received()[0]["name"], "chat_history")

        connection_notice = first_client.get_received()
        self.assertEqual(connection_notice[0]["name"], "system_message")
        self.assertEqual(
            connection_notice[0]["args"][0]["text"],
            "Bob Durand vient de rejoindre le salon.",
        )

        first_client.emit(
            "send_message", {"name": "Usurpateur", "text": "Bonjour !"}
        )
        first_client.emit(
            "send_image",
            {"image_url": "https://example.com/photo.jpg"},
        )
        first_messages = first_client.get_received()
        second_messages = second_client.get_received()

        self.assertEqual(first_messages[0]["name"], "chat_message")
        self.assertEqual(first_messages[0]["args"][0]["name"], "Alice Martin")
        self.assertEqual(
            first_messages[0]["args"][0]["user_id"],
            first_user_id,
        )
        self.assertEqual(first_messages[0]["args"][0]["text"], "Bonjour !")
        self.assertEqual(second_messages[0]["name"], "chat_message")
        self.assertEqual(second_messages[0]["args"][0]["text"], "Bonjour !")
        self.assertEqual(first_messages[1]["name"], "chat_image")
        self.assertEqual(
            second_messages[1]["args"][0]["image_url"],
            "https://example.com/photo.jpg",
        )

        first_client.disconnect()
        second_client.disconnect()

        restarted_app = create_app(
            {"TESTING": True, "DATABASE": self.database_path}
        )
        restarted_browser = restarted_app.test_client()
        self.authenticate(restarted_browser, "Alice", "Martin", "motdepasse-a")
        restarted_client = socketio.test_client(
            restarted_app, flask_test_client=restarted_browser
        )
        history_events = restarted_client.get_received()
        self.assertEqual(history_events[0]["name"], "chat_history")
        history = history_events[0]["args"][0]
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["text"], "Bonjour !")
        self.assertEqual(history[0]["name"], "Alice Martin")
        self.assertEqual(
            history[1]["image_url"], "https://example.com/photo.jpg"
        )
        restarted_client.disconnect()

    def test_creates_account_and_requires_its_password_on_reconnect(self):
        first_client = self.app.test_client()
        response = self.authenticate(
            first_client, "Élodie", "Martin", "mon-secret-123"
        )
        self.assertEqual(response.status_code, 302)
        with first_client.session_transaction() as browser_session:
            first_user_id = browser_session["user_id"]

        second_client = self.app.test_client()
        self.authenticate(second_client, "élodie", "martin", "mauvais-secret")
        with second_client.session_transaction() as browser_session:
            self.assertNotIn("user_id", browser_session)

        self.authenticate(second_client, "élodie", "martin", "mon-secret-123")
        with second_client.session_transaction() as browser_session:
            self.assertEqual(browser_session["user_id"], first_user_id)
            self.assertEqual(browser_session["user_name"], "Élodie Martin")

    def test_logout_requires_csrf_protected_post(self):
        self.authenticate(self.client, "Alice", "Martin", "motdepasse-a")
        with self.client.session_transaction() as browser_session:
            csrf_token = browser_session["csrf_token"]

        self.assertEqual(self.client.get("/logout").status_code, 405)
        response = self.client.post(
            "/logout", data={"csrf_token": csrf_token}
        )
        self.assertEqual(response.status_code, 302)
        with self.client.session_transaction() as browser_session:
            self.assertNotIn("user_id", browser_session)

    def test_migrates_legacy_schema_without_losing_account_or_history(self):
        legacy_database = os.path.join(self.temp_dir.name, "legacy.db")
        with sqlite3.connect(legacy_database) as connection:
            connection.execute(
                """CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    first_name TEXT NOT NULL COLLATE NOCASE,
                    last_name TEXT NOT NULL COLLATE NOCASE,
                    password_hash TEXT NOT NULL,
                    UNIQUE (first_name, last_name)
                )"""
            )
            connection.execute(
                """CREATE TABLE messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kind TEXT NOT NULL,
                    name TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )"""
            )
            connection.execute(
                "INSERT INTO users (first_name, last_name, password_hash) "
                "VALUES (?, ?, ?)",
                ("Élodie", "Martin", generate_password_hash("motdepasse-a")),
            )
            connection.execute(
                "INSERT INTO messages (kind, name, content, timestamp) "
                "VALUES (?, ?, ?, ?)",
                ("text", "Élodie Martin", "Ancien message", "2026-01-01T10:00:00+00:00"),
            )

        migrated_app = create_app(
            {"TESTING": True, "DATABASE": legacy_database}
        )
        browser = migrated_app.test_client()
        self.authenticate(browser, "élodie", "martin", "motdepasse-a")
        with browser.session_transaction() as browser_session:
            self.assertEqual(browser_session["user_id"], 1)
        with sqlite3.connect(legacy_database) as connection:
            self.assertEqual(
                connection.execute("SELECT wins FROM users WHERE id = 1").fetchone(),
                (0,),
            )

        socket_client = socketio.test_client(
            migrated_app, flask_test_client=browser
        )
        history = socket_client.get_received()[0]["args"][0]
        self.assertEqual(history[0]["text"], "Ancien message")
        self.assertEqual(history[0]["name"], "Élodie Martin")
        socket_client.disconnect()

    def test_clears_legacy_parties_on_startup(self):
        legacy_database = os.path.join(self.temp_dir.name, "legacy_parties.db")
        with sqlite3.connect(legacy_database) as connection:
            connection.execute(
                """CREATE TABLE parties (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    game_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                )"""
            )
            connection.execute(
                "INSERT INTO parties (name, game_id, created_at) VALUES (?, ?, ?)",
                ("Ancienne partie", 1, "2026-01-01T10:00:00"),
            )

        migrated_app = create_app(
            {"TESTING": True, "DATABASE": legacy_database}
        )
        browser = migrated_app.test_client()
        self.authenticate(browser, "Alice", "Martin", "motdepasse-a")

        response = browser.get("/games")

        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b"Ancienne partie", response.data)
        with sqlite3.connect(legacy_database) as connection:
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM parties").fetchone()[0], 0
            )
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM is_connected").fetchone()[0],
                0,
            )
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM party_bans").fetchone()[0],
                0,
            )
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM games").fetchone()[0], 1
            )

    def test_clears_parties_memberships_and_bans_on_restart(self):
        self.authenticate(self.client, "Alice", "Martin", "motdepasse-a")
        with self.client.session_transaction() as browser_session:
            host_csrf = browser_session["csrf_token"]
        self.client.post(
            "/create-party?game_id=1",
            data={"csrf_token": host_csrf, "party_name": "Salon temporaire"},
        )
        with self.app.app_context():
            party_id = Party.query.one().id

        guest = self.app.test_client()
        self.authenticate(guest, "Bob", "Durand", "motdepasse-b")
        with guest.session_transaction() as browser_session:
            guest_csrf = browser_session["csrf_token"]
            guest_id = browser_session["user_id"]
        guest.post(
            f"/party/{party_id}/join",
            data={"csrf_token": guest_csrf},
        )
        self.client.post(
            f"/party/{party_id}/kick/{guest_id}",
            data={"csrf_token": host_csrf},
        )

        create_app({"TESTING": True, "DATABASE": self.database_path})

        with sqlite3.connect(self.database_path) as connection:
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM parties").fetchone()[0], 0
            )
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM is_connected").fetchone()[0],
                0,
            )
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM party_bans").fetchone()[0],
                0,
            )

    def test_rejects_socket_connections_without_an_authenticated_session(self):
        unauthenticated_client = socketio.test_client(
            self.app, flask_test_client=self.client
        )
        self.assertFalse(unauthenticated_client.is_connected())

    def test_serves_chat_assets(self):
        stylesheet = self.client.get("/static/css/chat.css")
        script = self.client.get("/static/js/chat.js")

        self.assertEqual(stylesheet.status_code, 200)
        self.assertIn(b".chat {", stylesheet.data)
        self.assertEqual(script.status_code, 200)
        self.assertIn(b"socket.on('chat_history'", script.data)
        self.assertIn(b"socket.on('system_message'", script.data)
        stylesheet.close()
        script.close()

    def test_notifies_connected_clients_when_a_user_connects(self):
        first_browser = self.app.test_client()
        second_browser = self.app.test_client()
        self.authenticate(first_browser, "Alice", "Martin", "motdepasse-a")
        self.authenticate(second_browser, "Bob", "Durand", "motdepasse-b")
        first_client = socketio.test_client(
            self.app, flask_test_client=first_browser
        )
        first_client.get_received()
        second_client = socketio.test_client(
            self.app, flask_test_client=second_browser
        )

        received = first_client.get_received()
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0]["name"], "system_message")
        self.assertEqual(
            received[0]["args"][0]["text"],
            "Bob Durand vient de rejoindre le salon.",
        )
        first_client.disconnect()
        second_client.disconnect()

    def test_message_history_route_displays_saved_messages(self):
        self.authenticate(self.client, "Alice", "Martin", "motdepasse-a")
        socket_client = socketio.test_client(
            self.app, flask_test_client=self.client
        )
        socket_client.emit(
            "send_message", {"text": "Message archivé"}
        )
        socket_client.emit(
            "send_image",
            {"image_url": "https://example.com/photo.jpg"},
        )

        response = self.client.get("/messages")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Message archiv\xc3\xa9", response.data)
        self.assertIn(b"https://example.com/photo.jpg", response.data)
        socket_client.disconnect()


if __name__ == "__main__":
    unittest.main()
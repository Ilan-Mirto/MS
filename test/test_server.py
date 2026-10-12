import os
import tempfile
import unittest

from server import create_app, socketio


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

    def test_serves_page_and_accepts_socket_io_connection(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Salon g\xc3\xa9n\xc3\xa9ral", response.data)
        self.assertIn(b"/static/css/chat.css", response.data)
        self.assertIn(b"/static/js/chat.js", response.data)

        first_client = socketio.test_client(self.app, flask_test_client=self.client)
        second_client = socketio.test_client(self.app, flask_test_client=self.client)
        self.assertTrue(first_client.is_connected())
        self.assertTrue(second_client.is_connected())
        first_client.get_received()
        second_client.get_received()

        first_client.emit("send_message", {"name": "Alice", "text": "Bonjour !"})
        first_client.emit(
            "send_image",
            {"name": "Alice", "image_url": "https://example.com/photo.jpg"},
        )
        first_messages = first_client.get_received()
        second_messages = second_client.get_received()

        self.assertEqual(first_messages[0]["name"], "chat_message")
        self.assertEqual(first_messages[0]["args"][0]["name"], "Alice")
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
        restarted_client = socketio.test_client(
            restarted_app, flask_test_client=restarted_app.test_client()
        )
        history_events = restarted_client.get_received()
        self.assertEqual(history_events[0]["name"], "chat_history")
        history = history_events[0]["args"][0]
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["text"], "Bonjour !")
        self.assertEqual(
            history[1]["image_url"], "https://example.com/photo.jpg"
        )
        restarted_client.disconnect()

    def test_serves_chat_assets(self):
        stylesheet = self.client.get("/static/css/chat.css")
        script = self.client.get("/static/js/chat.js")

        self.assertEqual(stylesheet.status_code, 200)
        self.assertIn(b".chat {", stylesheet.data)
        self.assertEqual(script.status_code, 200)
        self.assertIn(b"socket.on('chat_message'", script.data)
        stylesheet.close()
        script.close()


if __name__ == "__main__":
    unittest.main()
import unittest

from server import app, socketio


class ServerTest(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def test_serves_page_and_accepts_socket_io_connection(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Socket.IO avec Flask", response.data)

        socket_client = socketio.test_client(self.app, flask_test_client=self.client)
        self.assertTrue(socket_client.is_connected())
        socket_client.disconnect()


if __name__ == "__main__":
    unittest.main()
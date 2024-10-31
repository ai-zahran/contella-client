from unittest import TestCase
from fastapi.testclient import TestClient

from src.app import app


class TestApp(TestCase):
    def test_validate_email(self):
        client = TestClient(app)

        # Try valid case.
        payload = {"email": "hello.world@gmail.com"}
        response = client.post("/validate-email", headers={}, data=payload, files=[])
        response_json = response.json()

        self.assertIn("isValid", response_json)
        self.assertIn("email", response_json)
        self.assertEqual(True, response_json["isValid"])
        self.assertEqual("hello.world@gmail.com", response_json["email"])

        # Try invalid case.
        payload = {'email': 'hello.world@gmail'}
        response = client.post("/validate-email", headers={}, data=payload, files=[])
        response_json = response.json()

        self.assertIn("isValid", response_json)
        self.assertIn("email", response_json)
        self.assertEqual(False, response_json["isValid"])
        self.assertIsNone(response_json["email"])

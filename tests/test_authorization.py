import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from routers.authorization import has_permission


class AuthorizationTests(unittest.TestCase):
    def test_permission_is_resolved_from_role_mapping(self):
        request = SimpleNamespace(session={"role": 2})
        connection = MagicMock()
        cursor = connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = (True,)

        with patch("authorization.get_connection", return_value=connection):
            self.assertTrue(has_permission(request, "quan_ly_phong"))

        cursor.execute.assert_called_once()
        self.assertEqual(cursor.execute.call_args.args[1], (2, "quan_ly_phong"))
        connection.close.assert_called_once()

    def test_missing_role_does_not_query_database(self):
        request = SimpleNamespace(session={})

        with patch("authorization.get_connection") as connect:
            self.assertFalse(has_permission(request, "quan_ly_phong"))

        connect.assert_not_called()

    def test_unassigned_permission_is_denied(self):
        request = SimpleNamespace(session={"role": 0})
        connection = MagicMock()
        cursor = connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = (False,)

        with patch("authorization.get_connection", return_value=connection):
            self.assertFalse(has_permission(request, "quan_ly_phong"))

        connection.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from psycopg2.errors import ForeignKeyViolation
from routers.admin import delete_room


class RoomDeleteTests(unittest.TestCase):
    def execute_delete(self, answers, failure=None):
        connection = MagicMock()
        cursor = connection.cursor.return_value
        cursor.fetchone.side_effect = answers
        cursor.rowcount = 1
        if failure:
            def execute(sql, params):
                if "DELETE FROM MAY_TINH" in sql:
                    raise failure
            cursor.execute.side_effect = execute
        request = SimpleNamespace(session={"role": 2})
        with (
            patch("routers.admin.has_permission", return_value=True),
            patch("routers.admin.get_connection", return_value=connection),
        ):
            response = delete_room(request, 102)
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], "/admin/room")
        cursor.close.assert_called_once()
        connection.close.assert_called_once()
        return request, connection, cursor

    def test_other_roles_cannot_delete(self):
        request = SimpleNamespace(session={"role": 1})
        with (
            patch("routers.admin.has_permission", return_value=False) as permission,
            patch("routers.admin.get_connection") as connect,
        ):
            response = delete_room(request, 102)
        permission.assert_called_once_with(request, "quan_ly_phong")
        connect.assert_not_called()
        self.assertEqual(response.headers["location"], "/login")

    def test_missing_room_is_reported_as_error(self):
        request, connection, cursor = self.execute_delete([None])
        self.assertIn("không tồn tại", request.session["error"])
        connection.commit.assert_not_called()
        connection.rollback.assert_called_once()

    def test_reports_and_schedules_are_preserved(self):
        request, connection, cursor = self.execute_delete([(102,), (7,), (32,)])
        self.assertIn("7 báo cáo", request.session["error"])
        self.assertIn("32 buổi", request.session["error"])
        self.assertFalse(any("DELETE" in call.args[0] for call in cursor.execute.call_args_list))
        connection.commit.assert_not_called()

    def test_schedule_alone_also_prevents_dangling_room_reference(self):
        request, connection, cursor = self.execute_delete([(102,), (0,), (2,)])
        self.assertIn("2 buổi", request.session["error"])
        self.assertFalse(any("DELETE" in call.args[0] for call in cursor.execute.call_args_list))
        connection.commit.assert_not_called()

    def test_unreferenced_room_deletes_machines_then_room(self):
        request, connection, cursor = self.execute_delete([(102,), (0,), (0,)])
        queries = [call.args[0] for call in cursor.execute.call_args_list]
        report_query = next(query for query in queries if "BAO_CAO_TINH_TRANG" in query)
        self.assertIn("TINH_TRANG_MAY_TINH", report_query)
        self.assertIn("ttm.MaBaoCao = bc.MaBaoCao", report_query)
        self.assertIn("ttm.MaMayTinh", report_query)
        self.assertNotIn("bc.MaMayTinh", report_query)
        self.assertIn("COUNT(DISTINCT bc.MaBaoCao)", report_query)
        self.assertTrue(any("FROM LICH_THUC_HANH" in query for query in queries))
        self.assertFalse(any("YEU_CAU_THU" in query for query in queries))
        deletes = [call.args[0] for call in cursor.execute.call_args_list if "DELETE" in call.args[0]]
        self.assertEqual(len(deletes), 2)
        self.assertIn("MAY_TINH", deletes[0])
        self.assertIn("PHONG", deletes[1])
        connection.commit.assert_called_once()
        connection.rollback.assert_not_called()
        self.assertIn("Xóa phòng thành công", request.session["success"])

    def test_foreign_key_race_is_reported_without_server_error(self):
        request, connection, cursor = self.execute_delete(
            [(102,), (0,), (0,)], ForeignKeyViolation("referenced room")
        )
        self.assertIn("đang được dữ liệu khác sử dụng", request.session["error"])
        connection.rollback.assert_called_once()
        connection.commit.assert_not_called()


if __name__ == "__main__":
    unittest.main()

import unittest
from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from routers.teacher import add_required, delete_program


class TeacherRequiredTests(unittest.TestCase):
    def setUp(self):
        self.request = SimpleNamespace(
            session={"accountId": 42},
        )
        self.connection = MagicMock()
        self.cursor = self.connection.cursor.return_value

    def test_add_practice_request_creates_each_weekday_and_week(self):
        start = date.today() + timedelta(days=7)
        end = start + timedelta(days=7)
        self.cursor.fetchone.side_effect = [(1,), (1,), (1,), (22,)]
        self.cursor.fetchall.side_effect = [
            [(117, start, start + timedelta(days=6)), (118, end, end + timedelta(days=6))],
            [(117,), (118,)],
        ]

        with (
            patch("routers.teacher.has_permission", return_value=True),
            patch("routers.teacher.get_user_by_id", return_value=(7,)),
            patch("routers.teacher.get_connection", return_value=self.connection),
        ):
            response = add_required(
                self.request,
                required_course_id=19,
                required_semester_id=4,
                required_group_id=2,
                required_lesson=1,
                required_type="thuc_hanh",
                required_week_start_id=117,
                required_week_end_id=118,
                required_week_day=[3, 5],
                required_note="  Lập trình  ",
            )

        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], "/teacher/required")
        self.assertEqual(len(self.cursor.executemany.call_args.args[1]), 4)
        self.assertEqual(
            self.cursor.executemany.call_args.args[1][0],
            (22, "thuc_hanh", 117, 3, 1, None, "Lập trình"),
        )
        class_insert = next(
            call
            for call in self.cursor.execute.call_args_list
            if "INSERT INTO LOP_HOC_PHAN" in call.args[0]
        )
        self.assertEqual(class_insert.args[1], (19, 4, 7, 2))
        class_insert_index = next(
            index
            for index, call in enumerate(self.cursor.mock_calls)
            if call[0] == "execute" and "INSERT INTO LOP_HOC_PHAN" in call.args[0]
        )
        schedule_insert_index = next(
            index
            for index, call in enumerate(self.cursor.mock_calls)
            if call[0] == "executemany"
        )
        self.assertEqual(
            self.cursor.executemany.call_args.args[1][0][0],
            22,
        )
        self.assertLess(class_insert_index, schedule_insert_index)
        self.connection.commit.assert_called_once()
        self.assertEqual(self.request.session["success"], "Thêm yêu cầu thành công!")

    def test_add_other_request_creates_a_date_specific_row(self):
        practice_day = date.today() + timedelta(days=5)
        self.cursor.fetchone.side_effect = [(1,), (1,), (1,), (117, 3), (22,)]

        with (
            patch("routers.teacher.has_permission", return_value=True),
            patch("routers.teacher.get_user_by_id", return_value=(7,)),
            patch("routers.teacher.get_connection", return_value=self.connection),
        ):
            response = add_required(
                self.request,
                required_course_id=19,
                required_semester_id=4,
                required_group_id=2,
                required_lesson=1,
                required_type="khac",
                required_practice_day=practice_day,
                required_note=None,
            )

        self.assertEqual(response.status_code, 303)
        self.assertEqual(
            self.cursor.executemany.call_args.args[1],
            [(22, "khac", 117, 3, 1, practice_day, None)],
        )
        class_insert = next(
            call
            for call in self.cursor.execute.call_args_list
            if "INSERT INTO LOP_HOC_PHAN" in call.args[0]
        )
        self.assertEqual(class_insert.args[1], (19, 4, 7, 2))
        self.connection.commit.assert_called_once()

    def test_add_rejects_class_not_owned_by_teacher(self):
        self.cursor.fetchone.return_value = None

        with (
            patch("routers.teacher.has_permission", return_value=True),
            patch("routers.teacher.get_user_by_id", return_value=(7,)),
            patch("routers.teacher.get_connection", return_value=self.connection),
        ):
            response = add_required(
                self.request,
                required_course_id=19,
                required_semester_id=4,
                required_group_id=2,
                required_lesson=1,
                required_type="thuc_hanh",
                required_week_start_id=None,
                required_week_end_id=None,
                required_week_day=[],
                required_practice_day=None,
                required_note=None,
            )

        self.assertEqual(response.status_code, 303)
        self.cursor.executemany.assert_not_called()
        self.connection.rollback.assert_called_once()
        self.assertIn("Học phần không thuộc", self.request.session["error"])

    def test_delete_uses_current_schema_and_is_scoped_to_teacher(self):
        self.cursor.rowcount = 4

        with (
            patch("routers.teacher.has_permission", return_value=True),
            patch("routers.teacher.get_user_by_id", return_value=(7,)),
            patch("routers.teacher.get_connection", return_value=self.connection),
        ):
            response = delete_program(self.request, 117)

        query = self.cursor.execute.call_args.args[0]
        self.assertIn("DELETE FROM LICH_THUC_HANH", query)
        self.assertIn("lhp.MaGiangVien = %s", query)
        self.assertIn("lth.MaTrangThai = 0", query)
        self.assertEqual(self.cursor.execute.call_args.args[1], (117, 7))
        self.connection.commit.assert_called_once()
        self.assertEqual(self.request.session["success"], "Xóa yêu cầu thành công!")


if __name__ == "__main__":
    unittest.main()

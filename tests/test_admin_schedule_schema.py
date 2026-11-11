import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from routers.admin import accept_required, refuse_required, save_calendar_schedule


class AdminScheduleSchemaTests(unittest.TestCase):
    def setUp(self):
        self.request = SimpleNamespace(session={"accountId": 10})
        self.connection = MagicMock()
        self.cursor = self.connection.cursor.return_value

    def test_accept_updates_all_rows_in_current_request_group(self):
        self.cursor.fetchall.return_value = [(31,), (32,), (33,)]

        with (
            patch("routers.admin.has_permission", return_value=True),
            patch("routers.admin.get_connection", return_value=self.connection),
        ):
            result = accept_required(31, self.request)

        query = self.cursor.execute.call_args.args[0]
        self.assertIn("UPDATE LICH_THUC_HANH lth", query)
        self.assertIn("MaTrangThai = 0", query)
        self.assertIn("GhiChu IS NOT DISTINCT FROM", query)
        self.assertEqual(self.cursor.execute.call_args.args[1], (31,))
        self.assertTrue(result["success"])
        self.connection.commit.assert_called_once()

    def test_refuse_updates_request_group_and_reason(self):
        self.cursor.fetchall.return_value = [(31,), (32,)]

        with (
            patch("routers.admin.has_permission", return_value=True),
            patch("routers.admin.get_connection", return_value=self.connection),
        ):
            result = refuse_required(31, self.request, reason="Không phù hợp")

        query = self.cursor.execute.call_args.args[0]
        self.assertIn("UPDATE LICH_THUC_HANH lth", query)
        self.assertIn("LyDo = %s", query)
        self.assertEqual(
            self.cursor.execute.call_args.args[1],
            (31, "Không phù hợp"),
        )
        self.assertTrue(result["success"])
        self.connection.commit.assert_called_once()

    def test_accept_returns_conflict_when_request_is_not_pending(self):
        self.cursor.fetchall.return_value = []

        with (
            patch("routers.admin.has_permission", return_value=True),
            patch("routers.admin.get_connection", return_value=self.connection),
        ):
            result = accept_required(31, self.request)

        self.assertEqual(result.status_code, 409)
        self.connection.rollback.assert_called_once()
        self.connection.commit.assert_not_called()

    def test_calendar_rejects_non_boolean_placement_flags(self):
        with (
            patch("routers.admin.has_permission", return_value=True),
            patch("routers.admin.get_connection") as get_connection,
        ):
            result = save_calendar_schedule(
                self.request,
                {
                    "schedules": [
                        {
                            "requiredId": 31,
                            "roomId": 101,
                            "day": 0,
                            "weekId": 117,
                            "currentWeekOnly": "true",
                            "existingSchedule": False,
                        }
                    ],
                    "removedDays": [],
                    "removedDayWeeks": [],
                },
            )

        self.assertEqual(result.status_code, 400)
        get_connection.assert_not_called()

    def test_calendar_removal_unassigns_current_schedule_rows(self):
        self.cursor.fetchone.return_value = (
            7,
            "thuc_hanh",
            1,
            date(2026, 11, 1),
            None,
            None,
            2,
            101,
        )
        self.cursor.fetchall.side_effect = [
            [(31, 117)],
            [(31, 10)],
            [(31,)],
            [(31, 10)],
        ]

        with (
            patch("routers.admin.has_permission", return_value=True),
            patch("routers.admin.get_connection", return_value=self.connection),
        ):
            result = save_calendar_schedule(
                self.request,
                {
                    "schedules": [],
                    "removedDays": ["31:1"],
                    "removedDayWeeks": [],
                },
            )

        update_queries = [
            call.args[0]
            for call in self.cursor.execute.call_args_list
            if "UPDATE LICH_THUC_HANH" in call.args[0]
        ]
        self.assertTrue(update_queries)
        self.assertIn("MaPhong = NULL", update_queries[0])
        self.assertIn("MaTrangThai = 1", update_queries[0])
        self.assertTrue(result["success"])
        self.connection.commit.assert_called_once()

    def test_calendar_keeps_existing_schedule_in_its_original_week(self):
        self.cursor.fetchone.return_value = (
            7,
            "thuc_hanh",
            1,
            date(2026, 11, 1),
            None,
            None,
            2,
            2,
            117,
            201,
            10,
            20,
            101,
        )

        with (
            patch("routers.admin.has_permission", return_value=True),
            patch("routers.admin.get_connection", return_value=self.connection),
        ):
            result = save_calendar_schedule(
                self.request,
                {
                    "schedules": [
                        {
                            "requiredId": 31,
                            "roomId": 102,
                            "day": 0,
                            "weekId": 118,
                            "currentWeekOnly": True,
                            "existingSchedule": True,
                        }
                    ],
                    "removedDays": [],
                    "removedDayWeeks": [],
                },
            )

        self.assertEqual(result.status_code, 400)
        self.connection.rollback.assert_called_once()
        self.connection.commit.assert_not_called()


if __name__ == "__main__":
    unittest.main()

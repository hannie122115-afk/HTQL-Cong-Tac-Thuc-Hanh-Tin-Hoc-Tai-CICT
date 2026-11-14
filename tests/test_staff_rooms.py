import sqlite3
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import HTTPException
from routers.staff import (
    get_staff_rooms, save_status_report, show_staff_room_detail,
    create_staff_status_report,
)


class StaffRoomQueryTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.addCleanup(self.db.close)
        self.db.executescript("""
            CREATE TABLE PHONG (MaPhong, TenPhong, TinhTrangPhong, MaNguoiQuanLy);
            CREATE TABLE MAY_TINH (MaMayTinh, TinhTrangMay, MaPhong);
            CREATE TABLE NGUOI_DUNG (MaNguoiDung, MaTaiKhoan, MaVaiTro);
            CREATE TABLE BAO_CAO_TINH_TRANG (
                MaBaoCao INTEGER PRIMARY KEY, TinhTrangCuThe, MaNguoiDung, MaPhong
            );
            CREATE TABLE TINH_TRANG_MAY_TINH (MaBaoCao, MaMayTinh, DienGiai,
                PRIMARY KEY (MaBaoCao, MaMayTinh));
            INSERT INTO PHONG VALUES
                (1, 'A101', 1, 10), (2, 'A102', 0, 20),
                (3, 'A103', 1, NULL), (4, 'A104', -1, 10);
            INSERT INTO MAY_TINH VALUES ('PC01', 1, 1), ('PC02', 0, 1), ('PC03', 1, 2);
            INSERT INTO NGUOI_DUNG VALUES (10, 100, 0), (20, 200, 0), (30, 300, 2), (40, 400, 2);
        """)
        self.connection = MagicMock()
        self.connection.commit.side_effect = self.db.commit
        self.connection.rollback.side_effect = self.db.rollback
        self.cursor = self.connection.cursor.return_value
        self.cursor.execute.side_effect = self.execute
        self.connect = patch("routers.staff.get_connection", return_value=self.connection)
        self.connect.start()
        self.addCleanup(self.connect.stop)
        notification_patch = patch("routers.staff.insert_notification")
        self.notifications = notification_patch.start()
        self.addCleanup(notification_patch.stop)

    def execute(self, query, params=()):
        result = self.db.execute(query.replace("%s", "?"), params)
        self.cursor.rowcount = result.rowcount
        self.cursor.fetchone.side_effect = result.fetchone
        self.cursor.fetchall.side_effect = result.fetchall

    def test_assigned_rooms_include_empty_room_without_any_schedule(self):
        self.assertEqual(get_staff_rooms(10), [(1, 'A101', 2, 1), (4, 'A104', 0, -1)])
        self.assertEqual(get_staff_rooms(99), [])

    def test_room_report_uses_new_author_and_notifies_actual_admin_accounts(self):
        save_status_report(10, 1, None, 'Room issue')
        self.assertEqual(self.db.execute(
            'SELECT TinhTrangCuThe, MaNguoiDung, MaPhong FROM BAO_CAO_TINH_TRANG'
        ).fetchone(), ('Room issue', 10, 1))
        self.assertEqual([c.args[1] for c in self.notifications.call_args_list], [300, 400])
        self.connection.commit.assert_called_once()

    def test_machine_report_preserves_machine_id_in_content(self):
        save_status_report(10, 1, 'PC02', 'Broken')
        content = self.db.execute('SELECT TinhTrangCuThe FROM BAO_CAO_TINH_TRANG').fetchone()[0]
        self.assertIn('PC02', content)
        self.assertTrue(content.endswith('\nBroken'))

    def test_multiple_machines_share_one_report_and_remove_duplicates(self):
        save_status_report(10, 1, ['PC01', 'PC02', 'PC01'], 'Same issue')
        rows = self.db.execute('SELECT TinhTrangCuThe FROM BAO_CAO_TINH_TRANG').fetchall()
        self.assertEqual(len(rows), 1)
        self.assertIn('PC01, PC02', rows[0][0])
        self.assertTrue(rows[0][0].endswith('\nSame issue'))
        self.assertEqual(self.notifications.call_count, 2)

    def test_mixed_valid_and_foreign_machines_rejects_entire_report(self):
        with self.assertRaises(HTTPException):
            save_status_report(10, 1, ['PC01', 'PC03'], 'Issue')
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM BAO_CAO_TINH_TRANG').fetchone()[0], 0)
        self.connection.commit.assert_not_called()
        self.notifications.assert_not_called()

    def test_bulk_status_updates_only_selected_machines_and_saves_snapshot(self):
        save_status_report(10, 1, ['PC01', 'PC02'], 'Maintenance', new_status=3)
        self.assertEqual(self.db.execute('SELECT MaMayTinh, TinhTrangMay FROM MAY_TINH ORDER BY MaMayTinh').fetchall(),
                         [('PC01', 3), ('PC02', 3), ('PC03', 1)])
        content = self.db.execute('SELECT TinhTrangCuThe FROM BAO_CAO_TINH_TRANG').fetchone()[0]
        self.assertIn('Maintenance', content)
        self.assertIn('PC01, PC02', content)
        self.assertEqual(self.db.execute('SELECT MaMayTinh, DienGiai FROM TINH_TRANG_MAY_TINH ORDER BY MaMayTinh').fetchall(),
                         [('PC01', 'Maintenance'), ('PC02', 'Maintenance')])

    def test_individual_mode_saves_each_description_and_each_status(self):
        details = [
            {'computer_id': 'PC01', 'description': 'Keyboard broken', 'status': 0},
            {'computer_id': 'PC02', 'description': 'Cleaning', 'status': 3},
        ]
        save_status_report(10, 1, ['PC01', 'PC02'], '', machine_details=details)
        self.assertEqual(self.db.execute('SELECT MaMayTinh, DienGiai FROM TINH_TRANG_MAY_TINH ORDER BY MaMayTinh').fetchall(),
                         [('PC01', 'Keyboard broken'), ('PC02', 'Cleaning')])
        self.assertEqual(self.db.execute('SELECT MaMayTinh, TinhTrangMay FROM MAY_TINH ORDER BY MaMayTinh').fetchall(),
                         [('PC01', 0), ('PC02', 3), ('PC03', 1)])
        self.assertEqual(self.db.execute('SELECT COUNT(DISTINCT MaBaoCao) FROM TINH_TRANG_MAY_TINH').fetchone()[0], 1)

    def test_individual_mode_rejects_missing_extra_or_invalid_details(self):
        valid = {'computer_id': 'PC01', 'description': 'Issue', 'status': 0}
        for details in [[], [valid, valid], [{**valid, 'computer_id': 'PC03'}],
                        [{**valid, 'description': ' '}], [{**valid, 'status': 8}],
                        [{**valid, 'status': True}], {'PC01': valid}]:
            with self.subTest(details=details), self.assertRaises(HTTPException):
                save_status_report(10, 1, ['PC01'], '', machine_details=details)
        self.connection.commit.assert_not_called()

    def test_room_report_updates_room_without_machine_details(self):
        save_status_report(10, 1, [], 'Room maintenance', new_room_status=0)
        self.assertEqual(self.db.execute('SELECT TinhTrangPhong FROM PHONG WHERE MaPhong=1').fetchone()[0], 0)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM BAO_CAO_TINH_TRANG').fetchone()[0], 1)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM TINH_TRANG_MAY_TINH').fetchone()[0], 0)

    def test_room_status_rolls_back_when_notification_fails(self):
        self.notifications.side_effect = RuntimeError('failed')
        with self.assertRaises(RuntimeError):
            save_status_report(10, 1, [], 'Room issue', new_room_status=-1)
        self.assertEqual(self.db.execute('SELECT TinhTrangPhong FROM PHONG WHERE MaPhong=1').fetchone()[0], 1)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM BAO_CAO_TINH_TRANG').fetchone()[0], 0)

    def test_notification_failure_rolls_back_status_and_report(self):
        self.notifications.side_effect = RuntimeError('Notification failed')
        with self.assertRaises(RuntimeError):
            save_status_report(10, 1, ['PC01', 'PC02'], 'Issue', new_status=2)
        self.assertEqual(self.db.execute('SELECT TinhTrangMay FROM MAY_TINH WHERE MaPhong=1 ORDER BY MaMayTinh').fetchall(), [(1,), (0,)])
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM BAO_CAO_TINH_TRANG').fetchone()[0], 0)

        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM TINH_TRANG_MAY_TINH').fetchone()[0], 0)

    def test_invalid_bulk_status_is_rejected_before_saving(self):
        for machine_ids, status in [(['PC01'], 9), ([], 1)]:
            with self.assertRaises(HTTPException) as error:
                save_status_report(10, 1, machine_ids, 'Issue', new_status=status)
            self.assertEqual(error.exception.status_code, 422)
        self.connection.commit.assert_not_called()

    def test_foreign_machine_prevents_all_status_changes(self):
        with self.assertRaises(HTTPException):
            save_status_report(10, 1, ['PC01', 'PC03'], 'Issue', new_status=0)
        self.assertEqual(self.db.execute("SELECT TinhTrangMay FROM MAY_TINH WHERE MaMayTinh='PC01'").fetchone()[0], 1)

    def test_foreign_unassigned_and_wrong_machine_reports_are_rejected(self):
        for room_id, machine in [(2, None), (3, None), (1, 'PC03'), (1, 'missing')]:
            with self.subTest(room=room_id, machine=machine), self.assertRaises(HTTPException) as error:
                save_status_report(10, room_id, machine, 'Issue')
            self.assertEqual(error.exception.status_code, 403)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM BAO_CAO_TINH_TRANG').fetchone()[0], 0)
        self.notifications.assert_not_called()
        self.connection.commit.assert_not_called()
        self.assertEqual(self.connection.rollback.call_count, 4)

    def test_reassigned_room_cannot_be_reported_by_previous_staff(self):
        self.db.execute('UPDATE PHONG SET MaNguoiQuanLy=20 WHERE MaPhong=1')
        with self.assertRaises(HTTPException):
            save_status_report(10, 1, None, 'Issue')


class StaffRoomRouteTests(unittest.TestCase):
    def setUp(self):
        self.request = SimpleNamespace(session={'accountId': 100}, query_params={})
        self.connection = MagicMock()
        self.cursor = self.connection.cursor.return_value
        for patcher in (
            patch('routers.staff.get_connection', return_value=self.connection),
            patch('routers.staff.get_user_by_id', return_value=(10, 'Staff')),
            patch('routers.staff.has_permission', return_value=True),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_detail_rejects_unassigned_room_before_loading_machines(self):
        self.cursor.fetchone.return_value = None
        with self.assertRaises(HTTPException) as error:
            show_staff_room_detail(self.request, 2, keyword='', page=1)
        self.assertEqual(error.exception.status_code, 404)
        self.assertEqual(self.cursor.execute.call_args.args[1], (2, 10))
        self.cursor.execute.assert_called_once()
        self.connection.close.assert_called_once()

    def test_detail_paginates_and_clamps_page_to_available_results(self):
        self.cursor.fetchone.side_effect = [(1, 'A101', None, None, 1), (12,)]
        self.cursor.fetchall.return_value = [('PC11', 1), ('PC12', 0)]
        with patch('routers.staff.templates.TemplateResponse') as template:
            show_staff_room_detail(self.request, 1, keyword=' PC ', page=99)
        context = template.call_args.kwargs['context']
        self.assertEqual((context['page'], context['per_page'], context['amount']), (2, 10, 12))
        self.assertEqual(self.cursor.execute.call_args_list[-2].args[1], (1, '%PC%', 10, 10))
        self.assertEqual(self.cursor.execute.call_args.args[1], (1,))
        self.assertIn('report_computers', context)

    def test_report_redirects_to_detail_without_week_parameter(self):
        with patch('routers.staff.save_status_report') as save:
            response = create_staff_status_report(self.request, 1, ' Broken ', 'PC01', new_status=1)
        save.assert_called_once_with(10, 1, ['PC01'], 'Broken', new_status=1)
        self.assertEqual(response.headers['location'], '/staff/room/1?success=1')

    def test_empty_or_overlong_report_is_rejected_before_saving(self):
        with patch('routers.staff.save_status_report') as save:
            for content in ['  ', 'x' * 2001]:
                with self.assertRaises(HTTPException) as error:
                    create_staff_status_report(self.request, 1, content, None)
                self.assertEqual(error.exception.status_code, 422)
        save.assert_not_called()

    def test_machine_report_requires_selection_and_normalizes_multiple_ids(self):
        with patch('routers.staff.save_status_report') as save:
            with self.assertRaises(HTTPException) as error:
                create_staff_status_report(self.request, 1, 'Issue', None, [], 'computers')
            self.assertEqual(error.exception.status_code, 422)
            save.assert_not_called()
            response = create_staff_status_report(
                self.request, 1, 'Issue', None, [' PC01 ', 'PC02', 'PC01'], 'computers', 1
            )
        save.assert_called_once_with(10, 1, ['PC01', 'PC02'], 'Issue', new_status=1)
        self.assertEqual(response.headers['location'], '/staff/room/1?success=1')

    def test_route_passes_bulk_status_to_transaction(self):
        with patch('routers.staff.save_status_report') as save:
            create_staff_status_report(self.request, 1, 'Issue', None, ['PC01', 'PC02'], 'computers', 0)
        save.assert_called_once_with(10, 1, ['PC01', 'PC02'], 'Issue', new_status=0)

    def test_route_parses_individual_details_without_shared_description(self):
        import json
        details = [{'computer_id': 'PC01', 'description': 'Issue', 'status': 0}]
        with patch('routers.staff.save_status_report') as save:
            response = create_staff_status_report(
                self.request, 1, '', None, ['PC01'], 'computers',
                report_mode='individual', machine_details_json=json.dumps(details)
            )
        save.assert_called_once_with(10, 1, ['PC01'], '', machine_details=details)
        self.assertEqual(response.status_code, 303)

    def test_route_passes_room_status_and_rejects_missing_common_machine_status(self):
        with patch('routers.staff.save_status_report') as save:
            create_staff_status_report(self.request, 1, 'Room issue', None, new_room_status=-1)
            save.assert_called_once_with(10, 1, [], 'Room issue', new_status=None, new_room_status=-1)
            with self.assertRaises(HTTPException):
                create_staff_status_report(self.request, 1, 'Issue', None, ['PC01'], 'computers')


if __name__ == '__main__':
    unittest.main()

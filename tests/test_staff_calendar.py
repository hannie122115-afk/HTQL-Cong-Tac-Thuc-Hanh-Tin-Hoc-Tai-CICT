import sqlite3
import unittest
from unittest.mock import MagicMock, patch

from routers.staff import get_staff_assignments, get_user_by_id


class StaffCalendarTests(unittest.TestCase):
    def setUp(self):
        # Chạy chính câu SQL của ứng dụng trên dữ liệu cô lập, không sửa DB thật.
        self.db = sqlite3.connect(":memory:")
        self.addCleanup(self.db.close)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            CREATE TABLE NGUOI_DUNG (
                MaNguoiDung, TenNguoiDung, SoDienThoai, Email,
                GioiTinh, NgaySinh, MaTaiKhoan, MaVaiTro
            );
            CREATE TABLE TAI_KHOAN_DANG_NHAP (MaTaiKhoan, AnhDaiDien);
            CREATE TABLE PHONG (MaPhong, TenPhong, MaNguoiQuanLy);
            CREATE TABLE TUAN_HOC (MaTuanHoc, MaHocKy);
            CREATE TABLE LICH_THUC_HANH (
                MaPhong, MaTuanHoc, MaThu, MaBuoi, MaTrangThai
            );
            INSERT INTO NGUOI_DUNG VALUES
                (10, 'Can bo A', '', '', 0, NULL, 100, 0),
                (20, 'Giang vien B', '', '', 0, NULL, 200, 1);
            INSERT INTO TAI_KHOAN_DANG_NHAP VALUES (100, 'a.png'), (200, 'b.png');
            INSERT INTO PHONG VALUES
                (1, 'A101', 10), (2, 'A102', 20),
                (3, 'A103', NULL), (4, 'A104', 10);
            INSERT INTO TUAN_HOC VALUES (11, 1), (12, 1), (21, 2);
            INSERT INTO LICH_THUC_HANH VALUES
                (1, 11, 2, 1, 2), (2, 11, 2, 1, 2),
                (3, 11, 2, 1, 2), (4, 12, 3, 2, 2),
                (1, 11, 3, 1, 0), (1, 11, 4, 1, 1),
                (1, 11, 5, 1, 3), (1, 21, 2, 1, 2),
                (NULL, 11, 2, 1, 2);
        """)
        self.connection = MagicMock()
        self.cursor = self.connection.cursor.return_value
        self.cursor.execute.side_effect = self.execute
        self.sql_result = None
        self.connect_patch = patch(
            "routers.staff.get_connection", return_value=self.connection
        )
        self.connect_patch.start()
        self.addCleanup(self.connect_patch.stop)

    def execute(self, query, params):
        self.sql_result = self.db.execute(query.replace("%s", "?"), params)
        self.cursor.fetchall.side_effect = lambda: [dict(row) for row in self.sql_result]
        self.cursor.fetchone.side_effect = lambda: self.sql_result.fetchone()

    def test_only_assigned_rooms_and_finalized_schedules_in_selected_semester(self):
        self.assertEqual(get_staff_assignments(10, 1), [
            {"MaPhong": 1, "TenPhong": "A101", "Thu": 2,
             "MaTuanHoc": 11, "BuoiThucHanh": 1},
            {"MaPhong": 4, "TenPhong": "A104", "Thu": 3,
             "MaTuanHoc": 12, "BuoiThucHanh": 2},
        ])
        self.cursor.close.assert_called_once()
        self.connection.close.assert_called_once()

    def test_no_assigned_rooms_returns_empty_calendar(self):
        self.assertEqual(get_staff_assignments(30, 1), [])

    def test_reassignment_removes_old_staff_access(self):
        self.db.execute("UPDATE PHONG SET MaNguoiQuanLy = 20 WHERE MaPhong = 1")
        self.assertEqual([row["MaPhong"] for row in get_staff_assignments(10, 1)], [4])
        self.assertEqual([row["MaPhong"] for row in get_staff_assignments(20, 1)], [1, 2])

    def test_unassigning_room_removes_its_schedule(self):
        self.db.execute("UPDATE PHONG SET MaNguoiQuanLy = NULL WHERE MaPhong = 1")
        self.assertEqual([row["MaPhong"] for row in get_staff_assignments(10, 1)], [4])

    def test_account_resolves_to_assigned_staff_id_and_preserves_template_columns(self):
        user = get_user_by_id(100)
        self.assertEqual((user[0], user[1], user[7], user[8]),
                         (10, "Can bo A", "a.png", 0))

    def test_non_staff_or_missing_account_is_not_resolved(self):
        self.assertIsNone(get_user_by_id(200))
        self.assertIsNone(get_user_by_id(999))


if __name__ == "__main__":
    unittest.main()

import sqlite3
import unittest
from datetime import date
from unittest.mock import MagicMock, patch

from routers.teacher import get_scheduled_requests_for_teacher


class TeacherCalendarTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:", detect_types=sqlite3.PARSE_DECLTYPES)
        self.db.row_factory = sqlite3.Row
        self.addCleanup(self.db.close)
        self.db.executescript("""
            CREATE TABLE HOC_PHAN (MaHocPhan, TenHocPhan);
            CREATE TABLE NHOM (MaNhom, TenNhom);
            CREATE TABLE LOP_HOC_PHAN (MaLopHocPhan, MaGiangVien, MaHocKy, MaHocPhan, MaNhom);
            CREATE TABLE TUAN_HOC (MaTuanHoc, MaHocKy, NgayBatDau);
            CREATE TABLE LICH_THUC_HANH (
                MaLichThucHanh, MaLopHocPhan, MaTuanHoc, MaThu, MaBuoi,
                MaPhong, MaTrangThai, NgayThucHanh DATE
            );
            INSERT INTO HOC_PHAN VALUES (1, 'Course');
            INSERT INTO NHOM VALUES (1, '01');
            INSERT INTO LOP_HOC_PHAN VALUES (1, 10, 1, 1, 1), (2, 20, 1, 1, 1), (3, 10, 2, 1, 1);
            INSERT INTO TUAN_HOC VALUES (99, 1, '2026-11-02'), (11, 1, '2026-11-09'), (21, 2, '2027-01-04');
            INSERT INTO LICH_THUC_HANH VALUES
                (1, 1, 99, 2, 1, 101, 2, NULL),
                (2, 1, 11, 4, 2, 102, 2, '2026-11-11'),
                (3, 2, 99, 2, 1, 101, 2, NULL),
                (4, 3, 21, 2, 1, 101, 2, NULL),
                (5, 1, 99, 3, 1, 101, 0, NULL),
                (6, 1, 99, 4, 1, 101, 1, NULL),
                (7, 1, 99, 5, 1, 101, 3, NULL),
                (8, 1, 99, 6, 1, NULL, 2, NULL),
                (9, 1, 21, 2, 1, 101, 2, NULL);
        """)
        self.connection = MagicMock()
        self.cursor = self.connection.cursor.return_value
        def execute(query, params):
            result = self.db.execute(query.replace('%s', '?'), params)
            self.cursor.fetchall.return_value = [dict(row) for row in result]
        self.cursor.execute.side_effect = execute
        patcher = patch('routers.teacher.get_connection', return_value=self.connection)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_only_own_finalized_placements_in_matching_semester(self):
        rows = get_scheduled_requests_for_teacher(10, 1)
        self.assertEqual([row['MaYeuCau'] for row in rows], [1, 2])
        self.assertEqual([row['MaTuanHoc'] for row in rows], [99, 11])
        self.assertEqual([row['MaPhong'] for row in rows], [101, 102])
        self.assertEqual(rows[1]['NgayThucHanh'], '2026-11-11')
        self.assertEqual(rows[1]['NhomHocPhan'], '01')
        self.cursor.close.assert_called_once()
        self.connection.close.assert_called_once()

    def test_other_teacher_and_semester_are_separate(self):
        self.assertEqual([row['MaYeuCau'] for row in get_scheduled_requests_for_teacher(20, 1)], [3])
        self.assertEqual([row['MaYeuCau'] for row in get_scheduled_requests_for_teacher(10, 2)], [4])
        self.assertEqual(get_scheduled_requests_for_teacher(999, 1), [])

    def test_database_error_still_closes_connection(self):
        self.cursor.execute.side_effect = RuntimeError('query failed')
        with self.assertRaises(RuntimeError):
            get_scheduled_requests_for_teacher(10, 1)
        self.cursor.close.assert_called_once()
        self.connection.close.assert_called_once()

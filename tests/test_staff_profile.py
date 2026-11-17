import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from routers.staff import update_staff_information, change_staff_password
from password_service import password_hash, verify_password


class StaffProfileTests(unittest.TestCase):
    def setUp(self):
        self.request = SimpleNamespace(session={
            'accountId': 100, 'role': 0, 'staff_user_csrf': 'token',
        })
        self.conn = MagicMock()
        self.cursor = self.conn.cursor.return_value
        self.cursor.rowcount = 1
        for patcher in (
            patch('routers.staff.has_permission', return_value=True),
            patch('routers.staff.get_connection', return_value=self.conn),
            patch('routers.staff.get_staff_profile', return_value={'MaNguoiDung': 10}),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def information(self, **overrides):
        values = dict(name='Staff A', phone='0901234567', gender='0',
                      birthday='1990-05-15', csrf_token='token')
        values.update(overrides)
        return update_staff_information(self.request, **values)

    def password(self, **overrides):
        values = dict(current_password='OldPass1!', new_password='NewPass2!',
                      confirm_password='NewPass2!', csrf_token='token')
        values.update(overrides)
        return change_staff_password(self.request, **values)

    def test_information_commits_only_own_staff_profile(self):
        response = self.information()
        query, params = self.cursor.execute.call_args.args
        self.assertIn('WHERE MaTaiKhoan=%s AND MaVaiTro=0', query)
        self.assertNotIn('MatKhau', query)
        self.assertEqual(params, ('Staff A', '0901234567', 0, date(1990, 5, 15), 100))
        self.conn.commit.assert_called_once()
        self.assertEqual(response.status_code, 303)
        self.assertTrue(self.request.session['staff_user_notice']['success'])

    def test_empty_or_invalid_information_does_not_write(self):
        for overrides in [dict(name='  '), dict(phone=''), dict(gender=''),
                          dict(birthday=''), dict(phone='abc'), dict(gender='2'),
                          dict(birthday='2099-01-01')]:
            with self.subTest(overrides=overrides):
                self.information(**overrides)
                self.assertFalse(self.request.session['staff_user_notice']['success'])
        self.cursor.execute.assert_not_called()
        self.conn.commit.assert_not_called()

    def test_password_supports_legacy_and_hashed_current_password(self):
        for stored in ['OldPass1!', password_hash.hash('OldPass1!')]:
            with self.subTest(hashed=stored.startswith('$')):
                self.cursor.reset_mock()
                self.conn.commit.reset_mock()
                self.cursor.fetchone.return_value = (stored,)
                response = self.password()
                query, params = self.cursor.execute.call_args.args
                self.assertIn('UPDATE TAI_KHOAN_DANG_NHAP', query)
                self.assertEqual(params[1], 100)
                self.assertNotEqual(params[0], 'NewPass2!')
                self.assertTrue(verify_password('NewPass2!', params[0]))
                self.conn.commit.assert_called_once()
                self.assertEqual(response.status_code, 303)

    def test_wrong_current_password_does_not_update(self):
        self.cursor.fetchone.return_value = ('WrongPass1!',)
        self.password()
        self.assertEqual(self.cursor.execute.call_count, 1)
        self.conn.commit.assert_not_called()
        self.assertFalse(self.request.session['staff_user_notice']['success'])

    def test_missing_or_invalid_passwords_do_not_access_database(self):
        for overrides in [dict(current_password=''), dict(new_password=''),
                          dict(confirm_password=''), dict(confirm_password='Mismatch1!'),
                          dict(new_password='weak', confirm_password='weak')]:
            with self.subTest(overrides=overrides):
                self.password(**overrides)
                self.assertFalse(self.request.session['staff_user_notice']['success'])
        self.cursor.execute.assert_not_called()

    def test_csrf_and_role_protect_both_updates(self):
        for operation in [self.information, self.password]:
            with self.assertRaises(HTTPException):
                operation(csrf_token='wrong')
        self.request.session['role'] = 1
        self.assertEqual(self.information().headers['location'], '/login')
        self.assertEqual(self.password().headers['location'], '/login')
        self.cursor.execute.assert_not_called()

    def test_error_notice_identifies_field_to_focus(self):
        for overrides, field in [(dict(phone='abc'), 'phone'),
                                 (dict(name='x' * 101), 'name'),
                                 (dict(gender='2'), 'gender'),
                                 (dict(birthday='2099-01-01'), 'birthday'),
                                 (dict(phone=' '), 'phone')]:
            with self.subTest(field=field):
                self.information(**overrides)
                self.assertEqual(self.request.session['staff_user_notice']['field'], field)
        self.password(confirm_password='Mismatch1!')
        self.assertEqual(self.request.session['staff_user_notice']['field'], 'confirm_password')
        self.password(new_password='weak', confirm_password='weak')
        self.assertEqual(self.request.session['staff_user_notice']['field'], 'new_password')
        self.cursor.fetchone.return_value = ('WrongPass1!',)
        self.password()
        self.assertEqual(self.request.session['staff_user_notice']['field'], 'current_password')

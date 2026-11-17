import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from starlette.requests import Request

from routers.teacher import (
    update_teacher_information, change_teacher_password, show_user_teacher as show_teacher_user,
    get_teacher_profile,
)
from password_service import verify_password, password_hash


class TeacherUserTests(unittest.TestCase):
    def setUp(self):
        self.request = SimpleNamespace(session={
            'accountId': 100, 'role': 1, 'teacher_user_csrf': 'test-token',
        })
        self.conn = MagicMock()
        self.cursor = self.conn.cursor.return_value
        self.cursor.rowcount = 1
        self.profile = dict(TenNguoiDung='Original Teacher', SoDienThoai='0909999999',
                            Email='a@ctu.edu.vn', MaHocVi=2, MaHocHam=1,
                            GioiTinh=0, NgaySinh=date(1990, 5, 15))
        for patcher in (
            patch('routers.teacher.has_permission', return_value=True),
            patch('routers.teacher.get_connection', return_value=self.conn),
            patch('routers.teacher.get_teacher_profile', return_value=self.profile),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def update_information(self, **overrides):
        values = dict(name='Teacher A', phone='0901234567', gender='0', birthday='1990-05-15',
                      degree_id=2, title_id=1, csrf_token='test-token')
        values.update(overrides)
        return update_teacher_information(self.request, **values)

    def change_password(self, **overrides):
        values = dict(current_password='OldPass1!', new_password='NewPass2!',
                      confirm_password='NewPass2!', csrf_token='test-token')
        values.update(overrides)
        return change_teacher_password(self.request, **values)

    def test_information_form_only_updates_own_profile_not_password(self):
        self.cursor.fetchone.return_value = (1,)
        response = self.update_information()
        query, params = self.cursor.execute.call_args.args
        self.assertIn('UPDATE NGUOI_DUNG', query)
        self.assertIn('MaTaiKhoan=%s AND MaVaiTro=1', query)
        self.assertNotIn('MatKhau', query)
        self.assertNotIn('Email=', query)
        self.assertEqual(params[-1], 100)
        self.assertEqual(response.headers['location'], '/teacher/profile#profile-information')
        self.conn.commit.assert_called_once()

    def test_information_errors_do_not_update_database_or_password(self):
        for overrides in [dict(name='x' * 101), dict(phone='abc'),
                          dict(birthday='2099-12-31'), dict(gender='2')]:
            with self.subTest(overrides=overrides):
                self.update_information(**overrides)
                self.assertFalse(self.request.session['teacher_user_notice']['success'])
        self.cursor.execute.assert_not_called()

    def test_empty_fields_are_rejected_without_restoring_old_values(self):
        for field, value in [('name', '  '), ('phone', ' '), ('degree_id', None),
                             ('title_id', None), ('birthday', ''), ('gender', '')]:
            with self.subTest(field=field):
                self.update_information(**{field: value})
                notice = self.request.session['teacher_user_notice']
                self.assertFalse(notice['success'])
                self.assertEqual(notice['values'][field], None if value is None else '')
        self.cursor.execute.assert_not_called()
        self.conn.commit.assert_not_called()

    def test_zero_gender_is_a_valid_value(self):
        self.cursor.fetchone.return_value = (1,)
        self.update_information(gender='0')
        self.assertEqual(self.cursor.execute.call_args.args[1][4], 0)
        self.conn.commit.assert_called_once()

    def test_invalid_degree_or_title_is_rejected(self):
        self.cursor.fetchone.return_value = None
        self.update_information(degree_id=999)
        self.conn.commit.assert_not_called()
        self.assertTrue(all('UPDATE' not in c.args[0] for c in self.cursor.execute.call_args_list))

    def test_password_form_hashes_new_password_without_updating_profile(self):
        self.cursor.fetchone.return_value = ('OldPass1!',)
        response = self.change_password()
        query, params = self.cursor.execute.call_args.args
        self.assertIn('UPDATE TAI_KHOAN_DANG_NHAP', query)
        self.assertNotIn('TenNguoiDung', query)
        self.assertEqual(params[1], 100)
        self.assertNotEqual(params[0], 'NewPass2!')
        self.assertTrue(verify_password('NewPass2!', params[0]))
        self.assertEqual(response.headers['location'], '/teacher/profile#password-section')
        self.conn.commit.assert_called_once()
        self.assertIsNone(self.request.session['teacher_user_notice']['values'])

    def test_wrong_current_password_and_mismatch_do_not_write(self):
        self.cursor.fetchone.return_value = ('Different1!',)
        self.change_password()
        self.conn.commit.assert_not_called()
        self.assertEqual(self.cursor.execute.call_count, 1)
        self.cursor.reset_mock()
        self.change_password(confirm_password='WrongConfirm2!')
        self.cursor.execute.assert_not_called()

    def test_csrf_failure_prevents_any_database_access(self):
        with self.assertRaises(HTTPException) as error:
            self.update_information(csrf_token='wrong')
        self.assertEqual(error.exception.status_code, 403)
        self.cursor.execute.assert_not_called()

    def test_other_roles_cannot_update_teacher_profile(self):
        self.request.session['role'] = 0
        self.assertEqual(self.update_information().headers['location'], '/login')
        self.assertEqual(self.change_password().headers['location'], '/login')
        self.cursor.execute.assert_not_called()

    def test_missing_profile_redirects_to_login(self):
        with patch('routers.teacher.get_teacher_profile', return_value=None):
            response = show_teacher_user(self.request)
        self.assertEqual(response.headers['location'], '/login')

    def test_profile_route_renders_current_html_with_all_form_context(self):
        profile = dict(TenNguoiDung='Teacher A', SoDienThoai='0901234567', Email='a@ctu.edu.vn',
                       GioiTinh=0, NgaySinh=date(1990, 5, 15), MaHocVi=2, MaHocHam=1,
                       TenHocVi='Doctor', TenHocHam='Associate professor', AnhDaiDien=None,
                       HocHamHocVi='PGS. TS.')
        self.cursor.fetchall.side_effect = [[(2, 'Master')], [(1, 'Lecturer')]]
        request = Request({'type': 'http', 'session': self.request.session})
        with patch('routers.teacher.get_teacher_profile', return_value=profile), \
             patch('routers.teacher.get_unread_notification_types', return_value=set()):
            response = show_teacher_user(request)
        self.assertEqual(response.status_code, 200)
        for key in ('profile', 'values', 'degrees', 'titles', 'notice', 'csrf_token', 'today'):
            self.assertIn(key, response.context)
        html = response.body.decode()
        self.assertIn('action="/teacher/profile/information"', html)
        self.assertIn('action="/teacher/profile/password"', html)
        self.assertIn('Teacher A', html)
        self.assertEqual(response.context['profile']['HocHamHocVi'], 'PGS. TS.')
        self.assertEqual(response.context['values']['name'], 'Teacher A')
        self.assertEqual(response.context['values']['phone'], '0901234567')
        self.assertEqual(response.context['values']['gender'], 0)
        self.assertEqual(response.context['values']['birthday'], '1990-05-15')
        from html.parser import HTMLParser
        class InputParser(HTMLParser):
            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if tag == 'input' and attrs.get('id') == 'email':
                    self.email = attrs
        parser = InputParser()
        parser.feed(html)
        self.assertIn('readonly', parser.email)
        self.assertEqual(parser.email['value'], 'a@ctu.edu.vn')
        self.assertEqual(html.count('<form'), 2)

    def test_profile_aliases_and_academic_abbreviations_match_template(self):
        self.cursor.fetchone.return_value = {'VietTatHocHam': 'PGS', 'VietTatHocVi': 'TS.'}
        profile = get_teacher_profile(100)
        self.assertEqual(profile['HocHamHocVi'], 'PGS. TS.')
        self.assertIn('AS "TenNguoiDung"', self.cursor.execute.call_args.args[0])
        self.assertEqual(self.cursor.execute.call_args.args[1], (100,))

    def test_profile_routes_are_registered_once_in_teacher_router(self):
        from routers.teacher import router
        for path, method in [('/teacher/profile', 'GET'),
                             ('/teacher/profile/information', 'POST'), ('/teacher/profile/password', 'POST')]:
            routes = [r for r in router.routes if r.path == path and method in r.methods]
            self.assertEqual(len(routes), 1)

    def test_login_password_verifier_accepts_legacy_and_hashed_passwords(self):
        self.assertTrue(verify_password('Legacy1!', 'Legacy1!'))
        self.assertFalse(verify_password('Wrong1!', 'Legacy1!'))
        hashed = password_hash.hash('NewPass2!')
        self.assertTrue(verify_password('NewPass2!', hashed))
        self.assertFalse(verify_password('Wrong2!', hashed))

    def test_login_route_accepts_password_hash_after_change(self):
        from routers.auth import login
        self.cursor.fetchone.return_value = (100, 'teacher-a', password_hash.hash('NewPass2!'), 1, '', 1)
        with patch('routers.auth.get_connection', return_value=self.conn):
            response = login(self.request, 'teacher-a', 'NewPass2!')
        self.assertEqual(response.headers['location'], '/teacher')
        self.assertEqual(self.request.session['accountId'], 100)


if __name__ == '__main__':
    unittest.main()

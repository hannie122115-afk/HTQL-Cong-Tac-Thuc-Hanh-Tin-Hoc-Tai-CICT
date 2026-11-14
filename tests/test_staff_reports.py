import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from starlette.requests import Request

from routers.staff import show_staff_reports, templates


class StaffReportsTests(unittest.TestCase):
    def setUp(self):
        self.request = SimpleNamespace(session={'accountId': 100}, query_params={'staff_id': '20'})
        self.conn = MagicMock()
        self.cursor = self.conn.cursor.return_value
        self.cursor.fetchall.return_value = [
            (7, 1, 'A101', 'Staff A', 'PC01, PC02',
             '[Máy tính PC01, PC02]\nIssue', None, date(2026, 11, 14)),
        ]

    def test_filter_uses_staff_id_from_session_account_and_selected_date(self):
        with patch('routers.staff.has_permission', return_value=True), \
             patch('routers.staff.get_user_by_id', return_value=(10, 'Staff A')) as user, \
             patch('routers.staff.get_connection', return_value=self.conn), \
             patch('routers.staff.templates.TemplateResponse') as template:
            show_staff_reports(self.request, date(2026, 11, 14))
        user.assert_called_once_with(100)
        query, params = self.cursor.execute.call_args.args
        self.assertIn('bc.MaNguoiDung = %s', query)
        self.assertEqual(params, (date(2026, 11, 14), 10))
        context = template.call_args.kwargs['context']
        self.assertEqual(context['reports'][0][5], 'Issue')
        self.assertEqual(context['user'], (10, 'Staff A'))
        self.conn.close.assert_called_once()

    def test_missing_staff_redirects_without_loading_reports(self):
        with patch('routers.staff.has_permission', return_value=True), \
             patch('routers.staff.get_user_by_id', return_value=None), \
             patch('routers.staff.get_connection') as connect:
            response = show_staff_reports(self.request, date(2026, 11, 14))
        self.assertEqual(response.headers['location'], '/login')
        connect.assert_not_called()

    def test_missing_permission_redirects_without_resolving_staff(self):
        with patch('routers.staff.has_permission', return_value=False), \
             patch('routers.staff.get_user_by_id') as user:
            response = show_staff_reports(self.request, date(2026, 11, 14))
        self.assertEqual(response.status_code, 303)
        user.assert_not_called()

    def test_template_has_seven_columns_and_staff_only_links(self):
        request = Request({'type': 'http', 'session': {'role': 0}})
        html = templates.env.get_template('staff/report.html').render(
            request=request, user=(10, 'Staff A', None, None, None, None, None, ''),
            reports=self.cursor.fetchall.return_value, created_date=date(2026, 11, 14),
        )
        self.assertIn('action="/staff/report"', html)
        self.assertIn('/static/js/staff/report.js', html)
        self.assertIn('PC01, PC02', html)
        self.assertNotIn('href="/admin', html)
        self.assertNotIn('data-read=', html)
        self.assertEqual(html.count('<th>'), 7)


if __name__ == '__main__':
    unittest.main()

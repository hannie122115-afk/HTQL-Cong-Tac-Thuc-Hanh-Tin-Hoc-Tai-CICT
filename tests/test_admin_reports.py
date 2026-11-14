import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from starlette.requests import Request

from routers.admin import router, show_admin_reports, templates


class AdminReportTests(unittest.TestCase):
    def test_report_status_mutation_route_is_removed(self):
        self.assertFalse(any(route.path == '/admin/report/{report_id}/status' for route in router.routes))

    def test_detail_template_contains_no_update_controls(self):
        request = Request({'type': 'http', 'session': {'role': 2}})
        html = templates.env.get_template('admin/report.html').render(
            request=request, user=(1, 'Admin'), avt='', reports=[],
            created_date=date(2026, 11, 14),
        )
        self.assertNotIn('name="status"', html)
        self.assertNotIn('report-status-form', html)
        self.assertNotIn('type="submit"', html)
        self.assertNotIn('Cập nhật', html)

    def test_new_schema_report_exposes_multiple_machines_for_read_only_view(self):
        conn = MagicMock()
        cursor = conn.cursor.return_value
        cursor.fetchall.return_value = [
            (7, 1, 'A101', 'Staff', None, '[Máy tính PC01, PC02]\nIssue', None, False),
            (8, 1, 'A101', 'Staff', 'PC03', '[Máy tính PC03]\r\nAnother issue', None, True),
            (9, 1, 'A101', 'Staff', None, 'Room issue', None, True),
        ]
        request = SimpleNamespace(session={'accountId': 300})
        with patch('routers.admin.has_permission', return_value=True), \
             patch('routers.admin.get_connection', return_value=conn), \
             patch('routers.admin.get_user_by_id', return_value=(1, 'Admin')), \
             patch('routers.admin.templates.TemplateResponse') as template:
            show_admin_reports(request, date(2026, 11, 14))
        self.assertEqual(template.call_args.kwargs['context']['reports'][0][4], 'PC01, PC02')
        reports = template.call_args.kwargs['context']['reports']
        self.assertEqual([row[5] for row in reports], ['Issue', 'Another issue', 'Room issue'])
        self.assertIsNone(reports[2][4])
        query = cursor.execute.call_args.args[0]
        self.assertIn('bc.MaNguoiDung', query)
        self.assertNotIn('bc.MaMayTinh', query)
        self.assertNotIn('CAN_BO', query)


if __name__ == '__main__':
    unittest.main()

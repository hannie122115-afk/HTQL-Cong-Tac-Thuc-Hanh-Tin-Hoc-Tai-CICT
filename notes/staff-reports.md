# Trang xem báo cáo của cán bộ

- `routers/staff.py` / `show_staff_reports`: kiểm tra quyền xem của cán bộ, lấy cán bộ từ tài khoản trong session rồi lọc `BAO_CAO_TINH_TRANG.MaNguoiDung = user[0]`. Không dùng `accountId` làm mã người dùng và không nhận mã cán bộ từ query string. Lọc ngày giống trang admin; không lọc theo người hiện quản lý phòng để cán bộ vẫn xem được báo cáo mình từng gửi sau khi phân công thay đổi.
- `templates/staff/report.html`: bảng bảy cột, bộ lọc ngày và popup chi tiết tương tự admin; dùng chung CSS báo cáo admin và date picker. Chỉ có thao tác xem/đóng. Báo cáo máy hiện mã máy, báo cáo phòng ẩn mã máy. Dòng `[Máy tính ...]` được tách khỏi nội dung ở máy chủ.
- `static/js/staff/report.js`: mở popup, điền chi tiết, đóng bằng nút/nhấn nền/Escape. Không gọi API admin hoặc thay đổi trạng thái đã đọc của admin.
- Trang staff không dùng trạng thái đã xem/chưa xem: bỏ cột `DaXem` khỏi truy vấn và không thêm `is-viewed` khi mở chi tiết, nên nút giữ nguyên màu sau khi xem.
- Sửa liên kết Xem báo cáo trong các template staff thành `/staff/report` để không bị ghép sai đường dẫn khi đang ở chi tiết phòng.

Kiểm tra: hai cán bộ gửi báo cáo cùng phòng/cùng ngày; mỗi người đăng nhập chỉ thấy báo cáo chính mình. Đổi ngày để kiểm tra lọc; thử thêm `staff_id` hay `accountId` vào URL không được xem báo cáo người khác. Mở lần lượt báo cáo máy và báo cáo phòng để kiểm tra hiện/ẩn mã máy và nội dung. Tài khoản không có hồ sơ cán bộ bị chuyển về đăng nhập.

Test: `venv/Scripts/python.exe -m unittest discover -s tests -p test_staff_reports.py`.

# Trang hồ sơ giảng viên

## Điều chỉnh theo khung trang hiện tại

`user.html` giữ header, menu tài khoản, breadcrumb và các file giao diện dùng chung như trang giảng viên hiện có. Chỉ vùng nội dung được thay bằng thẻ hồ sơ bên trái và hai form bên phải theo ảnh. `user.css` giới hạn selector trong `.teacher-user-page`, không ghi đè header/menu/body chung. Thay asset `required.css`/`required.js` và popup xóa yêu cầu còn sót từ trang mẫu bằng tài nguyên hồ sơ phù hợp. Dữ liệu header lấy từ `profile` để khớp context router hiện tại.

- `templates/teacher/user.html`, `static/js/teacher/user.js`, `static/css/teacher/user.css`: bố cục theo hình tham chiếu, thông tin tóm tắt bên trái, thông tin cá nhân và mật khẩu bên phải. Có bố cục điện thoại, nhãn trường, nút hiện/ẩn mật khẩu và thông báo riêng.
- Hai form độc lập: `/teacher/user/information` chỉ lưu họ tên, điện thoại, email, học hàm, học vị, ngày sinh, giới tính; `/teacher/user/password` chỉ đổi mật khẩu. Mỗi form có nút Đặt lại và nút lưu riêng. Lưu thông tin không yêu cầu nhập mật khẩu; đổi mật khẩu không gửi trường hồ sơ.
- `routers/teacher.py` / phần **HO SO CA NHAN**: xử lý các route trực tiếp trên router giảng viên, không import `teacher_user.py`. `show_user_teacher(request)` mở `/teacher/user` và `/teacher/profile`; truyền đủ `profile`, `values`, `degrees`, `titles`, `notice`, `csrf_token`, `today` và thông báo lịch cho HTML hiện tại. Hai route POST cập nhật thông tin và mật khẩu vẫn tách riêng.
- DB không có cột địa chỉ, nên giao diện dùng email, ngày sinh và giới tính thay cho địa chỉ. Ảnh đại diện hiện tại được hiển thị nếu có; trang này chưa thay đổi ảnh đại diện.
- `password_service.py` và `routers/auth.py`: kiểm tra mật khẩu băm và mật khẩu cũ. Mật khẩu mới được băm bằng pwdlib; không lưu mật khẩu mới dạng rõ. Chính sách mật khẩu giống trang thiết lập mật khẩu: tối thiểu 8 ký tự, có chữ hoa/thường, số, ký tự đặc biệt (tối đa 128 ký tự).
- Các liên kết hồ sơ giảng viên trỏ tới `/teacher/user`.

Kiểm tra: mở `/teacher/user`, lưu thông tin khi ba ô mật khẩu trống; thay mật khẩu khi thông tin hồ sơ chưa lưu; đặt lại từng form; nhập sai mật khẩu hiện tại/xác nhận; thử bằng tài khoản khác vai trò; kiểm tra bố cục trên màn hình nhỏ. Mật khẩu không được đưa vào session thông báo hoặc HTML trả về.

Test: `venv/Scripts/python.exe -m unittest discover -s tests -p test_teacher_user.py`.

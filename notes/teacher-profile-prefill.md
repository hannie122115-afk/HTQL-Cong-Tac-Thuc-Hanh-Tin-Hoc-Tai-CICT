# Sửa hiển thị hồ sơ và khóa email

## Giữ giá trị cũ khi ô nhập bị xóa rỗng

- `get_teacher_form_values(profile)` tạo dữ liệu điền form. GET và POST đều dùng hàm này để ánh xạ tên cột sang tên input.
- POST đọc hồ sơ mới nhất từ DB, tạo `values` từ hồ sơ rồi chỉ ghi đè các trường thực sự được nhập. Ô trống, chỉ có khoảng trắng hoặc không gửi sẽ giữ giá trị cũ. Giá trị `0` (nữ hoặc không có học hàm/học vị) vẫn được coi là lựa chọn mới hợp lệ.
- Các tham số form có mặc định rỗng/None để FastAPI không chặn bằng 422 trước khi thực hiện việc giữ dữ liệu cũ. JS cũng khôi phục ô rỗng từ dữ liệu ban đầu trước khi gửi; phía máy chủ không phụ thuộc JS.
- Với quy tắc này, xóa trắng ngày sinh/giới tính/điện thoại không xóa dữ liệu trong DB; trường chưa từng có thông tin vẫn giữ trạng thái chưa có. Email tiếp tục chỉ đọc.

- `get_teacher_profile` trong `routers/teacher.py`: alias được đặt trong dấu ngoặc kép để PostgreSQL trả đúng `TenNguoiDung`, `SoDienThoai`, `AnhDaiDien`... như HTML đang dùng. Lấy thêm `TenVietTat` từ `HOC_HAM` và `HOC_VI`, tạo chuỗi `HocHamHocVi` như `PGS. TS.`; không có học hàm thì chỉ hiện học vị nếu có.
- `show_user_teacher`: ánh xạ rõ từng trường từ profile sang `values` tương ứng tên input; giữ giới tính 0 và định dạng ngày sinh `YYYY-MM-DD`. Sau POST thành công, chuyển về `/teacher/profile` và đọc dữ liệu mới từ DB cho cả form, tên trong menu và thẻ bên trái. Khi nhập sai, chỉ giữ các trường được phép chỉnh sửa; email luôn lấy lại từ DB.
- `update_teacher_information`: không nhận email và không cập nhật cột `Email`. Dù sửa request thủ công để gửi email khác, email trong DB vẫn giữ nguyên.
- `templates/teacher/profile.html`: email `readonly`; dưới ảnh là tên, tiếp theo học hàm/học vị viết tắt. JS không chỉnh sửa ô email. Thêm CSS cho dòng học hàm/học vị và email chỉ đọc.

Kiểm tra: mở hồ sơ đã có dữ liệu, kiểm tra tên/điện thoại/học hàm/học vị/ngày sinh/giới tính được điền sẵn. Đổi thông tin và lưu; form và thẻ trái hiển thị giá trị vừa lưu. Email không thể sửa trên giao diện; thử gửi email giả trong POST vẫn không đổi DB. Khi nhập lỗi số điện thoại, thông tin vừa nhập được giữ để sửa và email vẫn là email DB.

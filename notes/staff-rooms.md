# Cập nhật room và room-detail theo DB mới

Luồng báo cáo mới nhất: xem [staff-report-modes.md](staff-report-modes.md) — cập nhật phòng, nhập chung hoặc riêng từng máy và ghi bảng `TINH_TRANG_MAY_TINH`.

Các vị trí chính có chú thích `NOTE` để dễ đối chiếu.

- `routers/staff.py` / `get_staff_rooms`: lấy phòng theo `PHONG.MaNguoiQuanLy`, đếm máy bằng `LEFT JOIN MAY_TINH`. Phòng chưa có máy, chưa có lịch hoặc ngoài học kỳ vẫn hiển thị nếu được phân công.
- `show_staff_rooms` và `templates/staff/room.html`: bỏ bộ lọc tuần, tham số tuần trên liên kết và form báo cáo; cập nhật thông báo khi chưa có phòng được phân công.
- `show_staff_room_detail`: kiểm tra mã phòng và mã cán bộ trong cùng truy vấn. Truy cập phòng khác trả 404. Tìm theo mã máy, phân trang 10 máy/trang, điều chỉnh trang khi vượt số trang hiện có.
- `templates/staff/room-detail.html`: bỏ tham số tuần, bỏ form chỉnh sửa thông tin phòng không có route xử lý; hiển thị thông tin chỉ đọc. Sửa thông báo tìm kiếm rỗng, tổng số máy bằng 0 và mã hóa từ khóa trong liên kết phân trang.
- `save_status_report`: lưu `TinhTrangCuThe`, `MaNguoiDung`, `MaPhong`; `NgayGui` dùng mặc định của DB. DB mới không có `MaMayTinh`, nên báo cáo từng máy được lưu dạng `[Máy tính <mã>]` rồi xuống dòng nội dung. Máy phải thuộc phòng và phòng phải được phân công cho cán bộ hiện tại. Không đủ quyền trả 403; lỗi được rollback. Thông báo gửi tới các tài khoản quản trị có vai trò 2.
- `create_staff_status_report`: không yêu cầu tuần; kiểm tra nội dung 1–2000 ký tự; báo cáo máy thành công quay lại chi tiết phòng, báo cáo phòng quay lại danh sách.

## Kiểm tra

### Báo cáo nhiều máy cùng lúc

- `room-detail.html`: thay các nút báo cáo từng dòng bằng nút **Báo cáo tình trạng chung**. Hộp báo cáo có checkbox từng máy, chọn tất cả và số máy đã chọn. Nút bị khóa khi phòng chưa có máy.
- `show_staff_room_detail`: cấp danh sách tất cả máy trong phòng cho hộp chọn, không phụ thuộc trang hoặc từ khóa đang xem.
- `static/js/staff/room-detail.js` và CSS tương ứng: chọn nhiều máy, chọn tất cả, trạng thái chọn một phần; chặn gửi khi chưa chọn máy hoặc nội dung trống; hủy sẽ xóa lựa chọn và nội dung.
- `create_staff_status_report` nhận nhiều trường `computer_ids`, loại mã trùng và yêu cầu ít nhất một máy với `report_type=computers`.
- `save_status_report`: xác minh toàn bộ máy thuộc phòng trước khi lưu **một báo cáo** dạng `[Máy tính PC01, PC02]` rồi xuống dòng nội dung chung. Nếu có một máy sai, từ chối toàn bộ; không tạo báo cáo hay thông báo một phần. Báo cáo phòng tại trang danh sách vẫn hoạt động như trước.
- Kiểm tra: mở nút chung, chọn hai máy rồi nhập nội dung; thử chọn tất cả/bỏ một máy, gửi khi chưa chọn, hủy rồi mở lại. Thử trên trang 2 hoặc khi đang tìm kiếm để kiểm tra vẫn chọn được mọi máy của phòng.
- Test JavaScript: `node --test tests/staff-room-report.test.cjs`.

1. Phân công phòng A cho cán bộ A, phòng B cho cán bộ B. Đăng nhập A: `/staff/room` chỉ hiển thị phòng A, kể cả chưa xếp lịch hoặc chưa có máy.
2. Mở chi tiết A không cần `week_id`; kiểm tra tên, cấu hình và tình trạng. Thử mở trực tiếp mã phòng B: nhận 404.
3. Tìm mã máy có/không tồn tại. Với phòng hơn 10 máy, kiểm tra chuyển trang và giữ từ khóa; không có máy phải hiển thị 0–0.
4. Gửi báo cáo phòng và báo cáo máy: kiểm tra `BAO_CAO_TINH_TRANG.MaNguoiDung`, `MaPhong`, nội dung và ngày gửi. Báo cáo máy có mã máy ở đầu nội dung.
5. Thử gửi mã máy thuộc phòng khác hoặc gửi sau khi phòng đã được chuyển sang cán bộ khác: nhận 403, không lưu báo cáo/thông báo.

Chạy tự động: `venv/Scripts/python.exe -m unittest discover -s tests -p test_staff_*.py -v`.

## Cập nhật trạng thái hàng loạt và admin chỉ xem

- CSS bảng máy tại `static/css/staff/room-detail.css`: bảng rộng 100%, ba cột bằng nhau, căn giữa. Đổi phiên bản CSS trong template để tải bản mới.
- Hộp báo cáo chi tiết phòng có trường `new_status`: giữ nguyên hoặc chọn Hư hỏng / Đang hoạt động / Đang sửa chữa / Đang bảo trì. Khi gửi, trạng thái mới áp dụng cho tất cả máy đã chọn.
- `save_status_report` kiểm tra trạng thái và máy, lưu báo cáo và cập nhật máy trong cùng một giao dịch. Có lỗi sẽ rollback cả báo cáo, trạng thái và thông báo. Nội dung báo cáo lưu cả trạng thái đã áp dụng để admin xem lại.
- Trang `/admin/report` đọc `NGUOI_DUNG` và báo cáo theo DB mới; chi tiết hiển thị danh sách máy, nội dung, người gửi. Bỏ form/nút cập nhật, JavaScript cập nhật và route POST `/admin/report/{report_id}/status`. Admin vẫn có thể đánh dấu đã đọc.
- Kiểm tra: chọn hai máy, chọn trạng thái mới, nhập nội dung và gửi; xác nhận hai máy đổi trạng thái, máy không chọn giữ nguyên. Mở báo cáo admin: chỉ xem và đóng, không có thao tác cập nhật. Chọn Giữ nguyên trạng thái để gửi nội dung mà không đổi trạng thái máy.

Kết quả xác minh: kiểm tra độ rộng và căn giữa ba cột bằng Chrome; kiểm tra giao dịch cập nhật nhiều máy/báo cáo/thông báo trên bảng tạm PostgreSQL rồi rollback; các test staff và admin reports đạt. Toàn bộ bộ test còn lỗi ngoài phần thay đổi: 3 test authorization tham chiếu sai đường dẫn module `authorization`, và 3 test teacher required không khớp hành vi/dữ liệu hiện tại. Không sửa các phần này trong yêu cầu báo cáo.

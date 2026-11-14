# Báo cáo phòng và báo cáo máy: hai chế độ nhập

## Chỗ sửa

- `templates/staff/room.html`: báo cáo phòng có thể chọn `new_room_status`: giữ nguyên, ngừng hoạt động, bảo trì hoặc đang hoạt động.
- `templates/staff/room-detail.html`, JS và CSS tương ứng: báo cáo máy chọn **Tình trạng chung** hoặc **Tình trạng cụ thể từng máy**. Chung nhập một diễn giải và một trạng thái; cụ thể hiện diễn giải và trạng thái riêng cho từng máy đã chọn. Bỏ chọn máy thì dữ liệu máy đó không được gửi. Đổi chế độ không xóa nội dung đang nhập; hủy báo cáo sẽ xóa toàn bộ.
- `routers/staff.py` / `create_staff_status_report`: nhận chế độ nhập, trạng thái phòng và JSON từng máy; kiểm tra dữ liệu. Với chế độ cụ thể, bắt buộc đủ đúng các máy đã chọn, mỗi máy một diễn giải 1–2000 ký tự và trạng thái 0/1/2/3.
- `save_status_report`: tạo một dòng `BAO_CAO_TINH_TRANG`, rồi một dòng `TINH_TRANG_MAY_TINH(MaBaoCao, MaMayTinh, DienGiai)` cho mỗi máy. Chế độ chung sao chép nguyên diễn giải vào từng dòng; cụ thể lưu từng diễn giải riêng. Cập nhật `MAY_TINH.TinhTrangMay` theo trạng thái chung hoặc từng máy. Báo cáo phòng cập nhật `PHONG.TinhTrangPhong` nếu được chọn. Tất cả thao tác và thông báo trong cùng giao dịch, lỗi sẽ rollback.
- `routers/admin.py`: danh sách máy của báo cáo lấy từ `TINH_TRANG_MAY_TINH`; vẫn đọc báo cáo cũ chưa có dòng con. Admin tiếp tục chỉ xem, không cập nhật trạng thái.
- Chi tiết admin: chỉ hiện mục mã máy cho báo cáo máy tính. CSS riêng bảo đảm thuộc tính `hidden` không bị `display:flex` của popup ghi đè. Dòng đầu `[Máy tính ...]` được tách khỏi nội dung hiển thị; dữ liệu lưu trong DB giữ nguyên.

## Kiểm tra nhanh

1. Báo cáo phòng → chọn Bảo trì, nhập nội dung, gửi. Kiểm tra trạng thái phòng và báo cáo được lưu cùng lúc, không tạo dòng tình trạng máy.
2. Báo cáo máy → chọn hai máy → Tình trạng chung → nhập một nội dung và chọn một trạng thái → gửi. Có một báo cáo, hai dòng tình trạng máy có `DienGiai` giống hệt nội dung nhập, cả hai máy đổi cùng trạng thái.
3. Chọn hai máy → Tình trạng cụ thể từng máy → nhập nội dung và trạng thái khác nhau → gửi. Kiểm tra từng dòng diễn giải và trạng thái máy đúng dữ liệu riêng.
4. Thử để trống diễn giải/trạng thái một máy; gửi thiếu máy, trùng máy hoặc máy ngoài phòng qua API. Yêu cầu bị từ chối, không lưu một phần.
5. Đổi chế độ, bỏ/chọn lại một máy, chọn tất cả và hủy báo cáo. Kiểm tra dữ liệu ẩn không được gửi và hủy sẽ reset cả chế độ lẫn các ô nhập.
6. Mở báo cáo admin: danh sách máy, nội dung chung hoặc từng máy hiển thị đầy đủ; không có nút cập nhật.

Chạy test: `venv/Scripts/python.exe -m unittest discover -s tests -p test_staff_*.py` và `venv/Scripts/python.exe -m unittest discover -s tests -p test_admin_reports.py`.

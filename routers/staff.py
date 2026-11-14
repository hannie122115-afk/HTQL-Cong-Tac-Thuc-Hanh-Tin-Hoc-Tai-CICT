import re

from fastapi import APIRouter, Request, Form, Query, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from routers.authorization import has_permission
from psycopg2.extras import RealDictCursor
from datetime import date
from datetime import datetime, timedelta
from database import get_connection
from notification_service import (
    NOTIFICATION_TYPE_SCHEDULE,
    NOTIFICATION_TYPE_STATUS_REPORT,
    get_unread_notification_types,
    insert_notification,
    mark_notifications_read,
)
from typing import Annotated, List, Optional
import json

templates = Jinja2Templates(directory="templates")
router = APIRouter()


def get_user_by_id(accountId):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
            SELECT nd.MaNguoiDung, nd.TenNguoiDung, nd.SoDienThoai,
                   nd.Email, nd.GioiTinh, nd.NgaySinh, nd.MaTaiKhoan
                , tk.AnhDaiDien
                , nd.MaVaiTro
            FROM NGUOI_DUNG nd
            JOIN TAI_KHOAN_DANG_NHAP tk ON tk.MaTaiKhoan = nd.MaTaiKhoan
            WHERE tk.MaTaiKhoan = %s
              AND nd.MaVaiTro = 0
        """,
        (accountId,),
    )
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user


def get_semester_current():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
            SELECT MaHocKy, TenHocKy, NamHoc
            FROM HOC_KY
            WHERE CURRENT_DATE BETWEEN NgayBatDau AND NgayKetThuc
            LIMIT 1
        """)
    semester = cursor.fetchone()
    cursor.close()
    conn.close()
    return semester


def get_weeks_by_semester(semester_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
            SELECT MaTuanHoc, TenTuanHoc, NgayBatDau, NgayKetThuc
            FROM TUAN_HOC
            WHERE MaHocKy = %s
            ORDER BY NgayBatDau
        """,
        (semester_id,),
    )
    weeks = cursor.fetchall()
    cursor.close()
    conn.close()

    return [
        {
            "id": week[0],
            "name": week[1],
            "start": week[2].strftime("%Y-%m-%d"),
            "end": week[3].strftime("%Y-%m-%d"),
        }
        for week in weeks
    ]


def get_staff_assignments(staff_id, semester_id):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute(
        """
            SELECT
                lth.MaPhong AS "MaPhong",
                p.TenPhong AS "TenPhong",
                lth.MaThu AS "Thu",
                lth.MaTuanHoc AS "MaTuanHoc",
                lth.MaBuoi AS "BuoiThucHanh"
            FROM LICH_THUC_HANH lth
            JOIN TUAN_HOC th ON th.MaTuanHoc = lth.MaTuanHoc
            JOIN PHONG p ON p.MaPhong = lth.MaPhong
            WHERE p.MaNguoiQuanLy = %s
              AND th.MaHocKy = %s
              AND lth.MaTrangThai = 2
            ORDER BY lth.MaTuanHoc, lth.MaThu, lth.MaBuoi, p.TenPhong
        """,
        (staff_id, semester_id),
    )
    assignments = cursor.fetchall()
    cursor.close()
    conn.close()
    return assignments


# ================trang chu ===========================
@router.get("/staff")
@router.get("/staff/index.html")
def show_admin(request: Request):
    if not has_permission(request, "xem_trang_chu_can_bo"):
        return RedirectResponse(url="/login", status_code=303)

    user = get_user_by_id(request.session.get("accountId"))
    avt = request.session.get("avt")
    unread_notifications = get_unread_notification_types(
        request.session.get("accountId")
    )

    return templates.TemplateResponse(
        request=request,
        name="staff/index.html",
        context={
            "user": user,
            "avt": avt,
            "has_unread_schedule": NOTIFICATION_TYPE_SCHEDULE in unread_notifications,
        },
    )


@router.get("/staff/room")
def show_staff_rooms(request: Request):
    if not has_permission(request, "xem_phong_duoc_phan_cong"):
        return RedirectResponse(url="/login", status_code=303)

    user = get_user_by_id(request.session.get("accountId"))
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    rooms = get_staff_rooms(user[0])

    return templates.TemplateResponse(
        request=request,
        name="staff/room.html",
        context={
            "user": user,
            "avt": request.session.get("avt"),
            "rooms": rooms,
            "success": request.query_params.get("success") == "1",
        },
    )


# ============= PHONG THUC HANH ===================


def get_staff_rooms(staff_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
            SELECT
                p.MaPhong,
                p.TenPhong,
                COUNT(DISTINCT mt.MaMayTinh) AS SoLuongMay,
                p.TinhTrangPhong
            FROM PHONG p
            LEFT JOIN MAY_TINH mt ON mt.MaPhong = p.MaPhong
            WHERE p.MaNguoiQuanLy = %s
            GROUP BY p.MaPhong, p.TenPhong, p.TinhTrangPhong
            ORDER BY p.TenPhong
        """,
        (staff_id,),
    )
    rooms = cursor.fetchall()
    cursor.close()
    conn.close()
    return rooms


@router.get("/staff/room/{room_id}")
def show_staff_room_detail(
    request: Request,
    room_id: int,
    keyword: str = Query(default=""),
    page: int = Query(default=1, ge=1),
):
    if not has_permission(request, "xem_phong_duoc_phan_cong"):
        return RedirectResponse(url="/login", status_code=303)

    user = get_user_by_id(request.session.get("accountId"))
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
            SELECT
                p.MaPhong,
                p.TenPhong,
                CASE
                    WHEN ch.MaCauHinh IS NULL THEN NULL
                    ELSE CONCAT('CPU ', ch.Cpu, ', RAM ', ch.Ram, ', Ổ cứng ', ch.OCung)
                END,
                p.MaCauHinh,
                p.TinhTrangPhong
            FROM PHONG p
            LEFT JOIN CAU_HINH ch ON ch.MaCauHinh = p.MaCauHinh
            -- NOTE: Chặn truy cập trực tiếp phòng không được phân công.
            WHERE p.MaPhong = %s AND p.MaNguoiQuanLy = %s
        """,
        (room_id, user[0]),
    )
    room = cursor.fetchone()
    if room is None:
        cursor.close()
        conn.close()
        raise HTTPException(
            status_code=404, detail="Không tìm thấy phòng được phân công."
        )

    keyword = keyword.strip()
    per_page = 10
    cursor.execute(
        "SELECT COUNT(*) FROM MAY_TINH WHERE MaPhong = %s AND MaMayTinh ILIKE %s",
        (room_id, f"%{keyword}%"),
    )
    amount = cursor.fetchone()[0]
    page = min(page, max(1, (amount + per_page - 1) // per_page))
    cursor.execute(
        """
            SELECT MaMayTinh, TinhTrangMay
            FROM MAY_TINH
            WHERE MaPhong = %s
              AND MaMayTinh::TEXT ILIKE %s
            ORDER BY MaMayTinh
            LIMIT %s OFFSET %s
        """,
        (room_id, f"%{keyword}%", per_page, (page - 1) * per_page),
    )
    computers = cursor.fetchall()
    cursor.execute(
        "SELECT MaMayTinh FROM MAY_TINH WHERE MaPhong = %s ORDER BY MaMayTinh",
        (room_id,),
    )
    report_computers = cursor.fetchall()
    cursor.close()
    conn.close()

    return templates.TemplateResponse(
        request=request,
        name="staff/room-detail.html",
        context={
            "user": user,
            "avt": request.session.get("avt"),
            "room": room,
            "computers": computers,
            "report_computers": report_computers,
            "keyword": keyword,
            "page": page,
            "per_page": per_page,
            "amount": amount,
            "success": request.query_params.get("success") == "1",
        },
    )


# =============== BAO CAO TINH TRANG ==================


def save_status_report(
    staff_id,
    room_id,
    computer_ids,
    current_status,
    new_status=None,
    machine_details=None,
    new_room_status=None,
):
    if isinstance(computer_ids, str):
        computer_ids = [computer_ids]
    computer_ids = list(dict.fromkeys(computer_ids or []))
    statuses = {
        0: "Hư hỏng",
        1: "Đang hoạt động",
        2: "Đang sửa chữa",
        3: "Đang bảo trì",
    }
    if new_status is not None and (new_status not in statuses or not computer_ids):
        raise HTTPException(
            status_code=422,
            detail="Trạng thái máy tính hoặc danh sách máy không hợp lệ.",
        )
    if new_room_status is not None and (
        computer_ids or new_room_status not in (-1, 0, 1)
    ):
        raise HTTPException(status_code=422, detail="Trạng thái phòng không hợp lệ.")
    # NOTE: Mỗi máy phải có đúng một diễn giải và trạng thái khi nhập cụ thể.
    if machine_details is not None:
        if not isinstance(machine_details, list) or not computer_ids:
            raise HTTPException(
                status_code=422, detail="Danh sách tình trạng máy không hợp lệ."
            )
        normalized = []
        for item in machine_details:
            if (
                not isinstance(item, dict)
                or not isinstance(item.get("computer_id"), str)
                or not isinstance(item.get("description"), str)
                or type(item.get("status")) is not int
                or item["status"] not in statuses
                or not 1 <= len(item["description"].strip()) <= 2000
            ):
                raise HTTPException(
                    status_code=422,
                    detail="Vui lòng nhập diễn giải và trạng thái hợp lệ cho từng máy.",
                )
            normalized.append({**item, "description": item["description"].strip()})
        if len(normalized) != len(computer_ids) or {
            item["computer_id"] for item in normalized
        } != set(computer_ids):
            raise HTTPException(
                status_code=422, detail="Phải nhập đủ và đúng các máy đã chọn."
            )
        machine_details = normalized
        current_status = "\n\n".join(
            f"Máy {item['computer_id']} — {statuses[item['status']]}:\n{item['description']}"
            for item in machine_details
        )
    elif not 1 <= len(current_status.strip()) <= 2000:
        raise HTTPException(
            status_code=422, detail="Vui lòng nhập tình trạng từ 1 đến 2000 ký tự."
        )
    report_content = (
        f"[Máy tính {', '.join(computer_ids)}]\n{current_status}"
        if computer_ids
        else current_status
    )
    if new_status is not None:
        report_content += f"\n[Trạng thái đã cập nhật: {statuses[new_status]}]"
    if new_room_status is not None:
        room_statuses = {-1: "Ngừng hoạt động", 0: "Bảo trì", 1: "Đang hoạt động"}
        report_content += f"\n[Trạng thái phòng: {room_statuses[new_room_status]}]"
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if computer_ids:
            placeholders = ", ".join(["%s"] * len(computer_ids))
            cursor.execute(
                f"SELECT MaMayTinh FROM MAY_TINH WHERE MaPhong = %s "
                f"AND MaMayTinh IN ({placeholders})",
                (room_id, *computer_ids),
            )
            if {row[0] for row in cursor.fetchall()} != set(computer_ids):
                raise HTTPException(
                    status_code=403,
                    detail="Có máy tính không thuộc phòng được báo cáo.",
                )
        cursor.execute(
            """
                INSERT INTO Bao_cao_tinh_trang
                    (TinhTrangCuThe, MaNguoiDung, MaPhong)
                SELECT %s, %s, %s
                WHERE EXISTS (
                    SELECT 1
                    FROM PHONG p
                    WHERE p.MaNguoiQuanLy = %s
                      AND p.MaPhong = %s
                )
                RETURNING MaBaoCao
            """,
            (
                report_content,
                staff_id,
                room_id,
                staff_id,
                room_id,
            ),
        )
        report = cursor.fetchone()
        if report is None:
            raise HTTPException(
                status_code=403,
                detail="Bạn không được phân công phòng này hoặc máy tính không thuộc phòng.",
            )
        # NOTE: Lưu bảng con TINH_TRANG_MAY_TINH cho mọi máy trong báo cáo.
        # Chế độ chung sao chép nguyên diễn giải; chế độ cụ thể dùng từng dòng.
        entries = (
            machine_details
            if machine_details is not None
            else [
                {
                    "computer_id": machine_id,
                    "description": current_status,
                    "status": new_status,
                }
                for machine_id in computer_ids
            ]
        )
        for entry in entries:
            cursor.execute(
                "INSERT INTO TINH_TRANG_MAY_TINH (MaBaoCao, MaMayTinh, DienGiai) VALUES (%s, %s, %s)",
                (report[0], entry["computer_id"], entry["description"]),
            )
            if entry["status"] is not None:
                cursor.execute(
                    "UPDATE MAY_TINH SET TinhTrangMay = %s WHERE MaPhong = %s AND MaMayTinh = %s",
                    (entry["status"], room_id, entry["computer_id"]),
                )
                if cursor.rowcount != 1:
                    raise HTTPException(
                        status_code=409,
                        detail="Danh sách máy đã thay đổi. Vui lòng tải lại phòng.",
                    )

        if new_room_status is not None:
            cursor.execute(
                "UPDATE PHONG SET TinhTrangPhong = %s WHERE MaPhong = %s AND MaNguoiQuanLy = %s",
                (new_room_status, room_id, staff_id),
            )
            if cursor.rowcount != 1:
                raise HTTPException(
                    status_code=409,
                    detail="Phân công phòng đã thay đổi. Vui lòng tải lại trang.",
                )
        cursor.execute("SELECT DISTINCT MaTaiKhoan FROM NGUOI_DUNG WHERE MaVaiTro = 2")
        for (account_id,) in cursor.fetchall():
            insert_notification(
                cursor, account_id, NOTIFICATION_TYPE_STATUS_REPORT, report[0]
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


@router.post("/staff/room/report")
def create_staff_status_report(
    request: Request,
    room_id: int = Form(...),
    current_status: Annotated[str, Form()] = "",
    computer_id: Optional[str] = Form(default=None),
    computer_ids: Annotated[Optional[List[str]], Form()] = None,
    report_type: Annotated[str, Form()] = "room",
    new_status: Annotated[Optional[int], Form()] = None,
    report_mode: Annotated[str, Form()] = "common",
    machine_details_json: Annotated[Optional[str], Form()] = None,
    new_room_status: Annotated[Optional[int], Form()] = None,
):
    if not has_permission(request, "cap_nhat_tinh_trang"):
        return RedirectResponse(url="/login", status_code=303)

    user = get_user_by_id(request.session.get("accountId"))
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    current_status = current_status.strip()
    if report_mode not in ("common", "individual") or report_type not in (
        "room",
        "computers",
    ):
        raise HTTPException(status_code=422, detail="Loại báo cáo không hợp lệ.")
    if report_mode != "individual" and (
        not current_status or len(current_status) > 2000
    ):
        raise HTTPException(
            status_code=422, detail="Vui lòng nhập tình trạng từ 1 đến 2000 ký tự."
        )

    computer_id = (computer_id.strip() or None) if computer_id else None
    selected_ids = list(
        dict.fromkeys(value.strip() for value in (computer_ids or []) if value.strip())
    )
    if computer_id:
        selected_ids = list(dict.fromkeys([*selected_ids, computer_id]))
    if report_type == "computers" and not selected_ids:
        raise HTTPException(
            status_code=422, detail="Vui lòng chọn ít nhất một máy tính."
        )
    if selected_ids and report_mode == "common" and new_status is None:
        raise HTTPException(
            status_code=422, detail="Vui lòng chọn trạng thái cho các máy."
        )
    if report_mode == "individual":
        if report_type != "computers" or new_room_status is not None:
            raise HTTPException(
                status_code=422, detail="Chế độ cụ thể chỉ dùng cho máy tính."
            )
        try:
            details = json.loads(machine_details_json or "")
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=422, detail="Danh sách tình trạng máy không hợp lệ."
            )
        if not isinstance(details, list):
            raise HTTPException(
                status_code=422, detail="Danh sách tình trạng máy không hợp lệ."
            )
        save_status_report(user[0], room_id, selected_ids, "", machine_details=details)
    elif new_room_status is not None:
        save_status_report(
            user[0],
            room_id,
            selected_ids,
            current_status,
            new_status=new_status,
            new_room_status=new_room_status,
        )
    elif new_status is None:
        if report_type == "computers":
            raise HTTPException(
                status_code=422, detail="Vui lòng chọn trạng thái cho các máy."
            )
        save_status_report(user[0], room_id, selected_ids, current_status)
    else:
        save_status_report(
            user[0], room_id, selected_ids, current_status, new_status=new_status
        )
    target = f"/staff/room/{room_id}" if selected_ids else "/staff/room"
    return RedirectResponse(url=f"{target}?success=1", status_code=303)


# ================== XEM BAO CAO TINH TRANG ================


@router.get("/staff/report")
def show_staff_reports(
    request: Request,
    created_date: Optional[date] = Query(default=None),
):
    if not has_permission(request, "xem_phong_duoc_phan_cong"):
        return RedirectResponse(url="/login", status_code=303)

    # NOTE: MaTaiKhoan và MaNguoiDung khác nhau; chỉ lọc theo cán bộ trong session.
    user = get_user_by_id(request.session.get("accountId"))
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    selected_date = created_date or date.today()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
                SELECT
                    bc.MaBaoCao,
                    p.MaPhong,
                    p.TenPhong,
                    nd.TenNguoiDung,
                    (SELECT STRING_AGG(ttm.MaMayTinh, ', ' ORDER BY ttm.MaMayTinh)
                     FROM TINH_TRANG_MAY_TINH ttm WHERE ttm.MaBaoCao = bc.MaBaoCao) AS DanhSachMay,
                    bc.TinhTrangCuThe,
                    NULL AS TinhTrangHienTai,
                    bc.NgayGui
                FROM Bao_cao_tinh_trang bc
                JOIN PHONG p ON p.MaPhong = bc.MaPhong
                JOIN NGUOI_DUNG nd ON nd.MaNguoiDung = bc.MaNguoiDung
                WHERE bc.NgayGui = %s
                AND bc.MaNguoiDung = %s
                ORDER BY bc.MaBaoCao DESC
            """,
            (
                selected_date,
                user[0],
            ),
        )
        reports = cursor.fetchall()
        reports = [list(report) for report in reports]
        for report in reports:
            header = re.match(r"^\[Máy tính ([^\r\n]*)\]\r?\n", report[5] or "")
            if header:
                if not report[4]:
                    report[4] = header.group(1)
                report[5] = report[5][header.end() :]
        cursor.close()
    finally:
        conn.close()

    return templates.TemplateResponse(
        request=request,
        name="staff/report.html",
        context={
            "user": user,
            "avt": request.session.get("avt"),
            "reports": reports,
            "created_date": selected_date,
            "success": request.session.pop("success", None),
        },
    )


# ================== XEM LICH PHAN CONG ================


@router.get("/staff/calendar")
def show_staff_calendar(request: Request):
    if not (
        has_permission(request, "xem_lich_duoc_phan_cong")
        and has_permission(request, "xem_thong_bao_ca_nhan_can_bo")
    ):
        return RedirectResponse(url="/login", status_code=303)

    user = get_user_by_id(request.session.get("accountId"))
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    mark_notifications_read(
        request.session.get("accountId"),
        NOTIFICATION_TYPE_SCHEDULE,
    )
    semester = get_semester_current()
    weeks = get_weeks_by_semester(semester[0]) if semester else []
    assignments = get_staff_assignments(user[0], semester[0]) if semester else []

    return templates.TemplateResponse(
        request=request,
        name="staff/calendar.html",
        context={
            "user": user,
            "avt": request.session.get("avt"),
            "semester": semester,
            "weeks": weeks,
            "all_scheduled": assignments,
        },
    )

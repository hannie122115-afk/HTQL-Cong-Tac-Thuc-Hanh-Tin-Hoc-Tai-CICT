from fastapi import APIRouter, Request, Form, Query, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from psycopg2.extras import RealDictCursor
from database import get_connection
from routers.authorization import has_permission
from notification_service import (
    NOTIFICATION_TYPE_SCHEDULE,
    get_unread_notification_types,
    mark_notifications_read,
)
from datetime import date, timedelta
from typing import List, Optional

templates = Jinja2Templates(directory="templates")
router = APIRouter()


def get_user_by_id(accountId):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
            SELECT nd.*
                , tk.AnhDaiDien
                , vt.TenVaiTro
            FROM NGUOI_DUNG nd
            JOIN TAI_KHOAN_DANG_NHAP tk ON tk.MaTaiKhoan = nd.MaTaiKhoan
            JOIN VAI_TRO vt ON vt.MaVaiTro = nd.MaVaiTro
            WHERE tk.MaTaiKhoan = %s
        """,
        (accountId,),
    )
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user


# ================trang chu ===========================
@router.get("/teacher")
@router.get("/teacher/index.html")
def show_admin(request: Request):
    if not has_permission(request, "xem_trang_chu_giang_vien"):
        return RedirectResponse(url="/login", status_code=303)

    user = get_user_by_id(request.session.get("accountId"))
    avt = request.session.get("avt")
    unread_notifications = get_unread_notification_types(
        request.session.get("accountId")
    )

    return templates.TemplateResponse(
        request=request,
        name="teacher/index.html",
        context={
            "user": user,
            "avt": avt,
            "has_unread_schedule": NOTIFICATION_TYPE_SCHEDULE in unread_notifications,
        },
    )


# ================== yeu cau sap lich ===================


def get_required(per_page, offset, keyword, teacherId, created_date, status):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    status_val = int(status) if status is not None and str(status).isdigit() else None
    date_val = created_date.strip() if created_date and created_date.strip() else None

    cursor.execute(
        """
            WITH filtered_schedule AS (
                SELECT
                    lth.MaLichThucHanh,
                    lth.MaLopHocPhan,
                    lth.LoaiYeuCau,
                    lth.MaBuoi,
                    lth.MaTrangThai,
                    lth.NgayYeuCau,
                    lth.NgayThucHanh,
                    lth.MaThu,
                    lth.MaTuanHoc,
                    lth.GhiChu,
                    lhp.MaHocPhan,
                    lhp.MaHocKy,
                    lhp.MaGiangVien,
                    lhp.SiSo,
                    hp.TenHocPhan,
                    nd.TenNguoiDung AS TenGiangVien,
                    hk.TenHocKy,
                    b.TenBuoi,
                    tt.TenTrangThai,
                    th.TenTuanHoc,
                    n.TenNhom
                FROM LICH_THUC_HANH lth
                JOIN LOP_HOC_PHAN lhp
                    ON lhp.MaLopHocPhan = lth.MaLopHocPhan
                JOIN HOC_PHAN hp ON hp.MaHocPhan = lhp.MaHocPhan
                JOIN NGUOI_DUNG nd ON nd.MaNguoiDung = lhp.MaGiangVien
                JOIN HOC_KY hk ON hk.MaHocKy = lhp.MaHocKy
                JOIN BUOI b ON b.MaBuoi = lth.MaBuoi
                JOIN TRANG_THAI tt ON tt.MaTrangThai = lth.MaTrangThai
                JOIN NHOM n ON n.MaNhom = lhp.MaNhom
                LEFT JOIN TUAN_HOC th ON th.MaTuanHoc = lth.MaTuanHoc
                WHERE lhp.MaGiangVien = %s
                  AND hp.TenHocPhan ILIKE %s
                  AND (%s IS NULL OR lth.NgayYeuCau = %s::date)
                  AND (%s IS NULL OR lth.MaTrangThai = %s)
            ),
            grouped_requests AS (
                SELECT
                    MIN(MaLichThucHanh) AS MaYeuCau,
                    MaLopHocPhan,
                    MaHocPhan,
                    MaHocKy,
                    TenHocKy,
                    SiSo,
                    TenHocPhan,
                    TenGiangVien,
                    LoaiYeuCau,
                    MaBuoi,
                    TenBuoi,
                    MaTrangThai,
                    TenTrangThai,
                    NgayYeuCau,
                    GhiChu,
                    CASE
                        WHEN LoaiYeuCau = 'khac' THEN NgayThucHanh
                        ELSE NULL
                    END AS NgayThucHanh,
                    STRING_AGG(
                        DISTINCT MaThu::text,
                        ', ' ORDER BY MaThu::text
                    ) FILTER (WHERE MaThu IS NOT NULL) AS DanhSachThu,
                    MIN(TenTuanHoc) AS TuanBatDau,
                    MAX(TenTuanHoc) AS TuanKetThuc
                FROM filtered_schedule
                GROUP BY
                    MaLopHocPhan,
                    MaHocPhan,
                    MaHocKy,
                    TenHocKy,
                    SiSo,
                    TenHocPhan,
                    TenGiangVien,
                    LoaiYeuCau,
                    MaBuoi,
                    TenBuoi,
                    MaTrangThai,
                    TenTrangThai,
                    NgayYeuCau,
                    GhiChu,
                    CASE
                        WHEN LoaiYeuCau = 'khac' THEN NgayThucHanh
                        ELSE NULL
                    END
            )
            SELECT
                gr.MaYeuCau AS "MaYeuCau",
                gr.MaHocPhan AS "MaHocPhan",
                gr.TenHocPhan AS "TenHocPhan",
                (
                    SELECT STRING_AGG(pm.TenPhanMem, ', ' ORDER BY pm.TenPhanMem)
                    FROM HOC_PHAN_PHAN_MEM hppm
                    JOIN PHAN_MEM pm ON pm.MaPhanMem = hppm.MaPhanMem
                    WHERE hppm.MaHocPhan = gr.MaHocPhan
                ) AS "TenPhanMem",
                gr.LoaiYeuCau AS "LoaiYeuCau",
                gr.MaBuoi AS "BuoiThucHanh",
                gr.TenBuoi AS "TenBuoi",
                gr.MaTrangThai AS "TrangThai",
                gr.TenTrangThai AS "TenTrangThai",
                gr.GhiChu AS "GhiChu",
                TO_CHAR(gr.NgayThucHanh, 'DD/MM/YYYY') AS "NgayThucHanh",
                gr.DanhSachThu AS "DanhSachThu",
                gr.TuanBatDau AS "TuanBatDau",
                gr.TuanKetThuc AS "TuanKetThuc",
                gr.TenHocKy AS "TenHocKy",
                TO_CHAR(gr.NgayYeuCau, 'DD/MM/YYYY') AS "NgayYeuCau",
                gr.TenGiangVien AS "TenGiangVien"
            FROM grouped_requests gr
            ORDER BY gr.NgayYeuCau DESC, gr.MaYeuCau DESC
            LIMIT %s OFFSET %s
        """,
        (
            teacherId,
            f"%{keyword}%",
            date_val,
            date_val,
            status_val,
            status_val,
            per_page,
            offset,
        ),
    )

    required = cursor.fetchall()

    cursor.close()
    conn.close()

    return required


def get_sum_required(keyword, userId, created_date, status):
    conn = get_connection()
    cursor = conn.cursor()

    status_val = int(status) if status is not None and str(status).isdigit() else None
    date_val = created_date.strip() if created_date and created_date.strip() else None

    cursor.execute(
        """
            SELECT COUNT(*)
            FROM (
                SELECT
                    lth.MaLopHocPhan,
                    lth.LoaiYeuCau,
                    lth.MaBuoi,
                    lth.MaTrangThai,
                    lth.NgayYeuCau,
                    lth.GhiChu,
                    CASE
                        WHEN lth.LoaiYeuCau = 'khac' THEN lth.NgayThucHanh
                        ELSE NULL
                    END AS NgayThucHanh
                FROM LICH_THUC_HANH lth
                JOIN LOP_HOC_PHAN lhp
                    ON lhp.MaLopHocPhan = lth.MaLopHocPhan
                JOIN HOC_PHAN hp ON hp.MaHocPhan = lhp.MaHocPhan
                WHERE lhp.MaGiangVien = %s
                  AND hp.TenHocPhan ILIKE %s
                  AND (%s IS NULL OR lth.NgayYeuCau = %s::date)
                  AND (%s IS NULL OR lth.MaTrangThai = %s)
                GROUP BY
                    lth.MaLopHocPhan,
                    lth.LoaiYeuCau,
                    lth.MaBuoi,
                    lth.MaTrangThai,
                    lth.NgayYeuCau,
                    lth.GhiChu,
                    CASE
                        WHEN lth.LoaiYeuCau = 'khac' THEN lth.NgayThucHanh
                        ELSE NULL
                    END
            ) grouped_requests
        """,
        (
            userId,
            f"%{keyword}%",
            date_val,
            date_val,
            status_val,
            status_val,
        ),
    )
    amount = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return amount


def get_semester_current():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
            SELECT MaHocKy, TenHocKy, NamHoc
            FROM HOC_KY
            WHERE CURRENT_DATE BETWEEN NgayBatDau AND NgayKetThuc
            LIMIT 1
        """,
    )
    semester = cursor.fetchone()
    cursor.close()
    conn.close()
    return semester


def get_all_semesters():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
                SELECT MaHocKy, TenHocKy, NamHoc, NgayBatDau, NgayKetThuc
                FROM HOC_KY
                ORDER BY NgayBatDau DESC
            """)
        return cursor.fetchall()
    finally:
        conn.close()


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
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    return [
        {
            "id": row[0],
            "name": row[1],
            "start": row[2].strftime("%Y-%m-%d"),
            "end": row[3].strftime("%Y-%m-%d"),
        }
        for row in rows
    ]


@router.get("/teacher/required")
def show_required_teacher(
    request: Request,
    page: int = 1,
    keyword: str = "",
    created_date: str = "",
    status: Optional[str] = Query(None),
):
    if not has_permission(request, "xem_yeu_cau_ca_nhan"):
        return RedirectResponse(url="/login", status_code=303)

    account_id = request.session.get("accountId")
    user = get_user_by_id(account_id)
    avt = request.session.get("avt")

    per_page = 10
    offset = (page - 1) * per_page

    status_int = int(status) if (status is not None and status != "") else None
    amount = get_sum_required(keyword, user[0], created_date, status_int)
    required = get_required(
        per_page, offset, keyword, user[0], created_date, status_int
    )
    semesters = get_all_semesters()
    current_semester = get_semester_current()
    selected_semester_id = (
        current_semester[0]
        if current_semester
        and any(semester[0] == current_semester[0] for semester in semesters)
        else semesters[0][0] if semesters else None
    )

    success = request.session.pop("success", None)
    error = request.session.pop("error", None)

    return templates.TemplateResponse(
        request=request,
        name="teacher/required.html",
        context={
            "user": user,
            "avt": avt,
            "required": required,
            "per_page": per_page,
            "page": page,
            "amount": amount,
            "keyword": keyword,
            "created_date": created_date,
            "status": status,
            "semesters": semesters,
            "selected_semester_id": selected_semester_id,
            "success": success,
            "error": error,
        },
    )


# ================== them yeu cau sap lich ===================


@router.get("/api/courses")
def search_courses(
    request: Request,
    keyword: str = Query(default="", min_length=1),
):
    if not has_permission(request, "gui_yeu_cau_xep_lich"):
        raise HTTPException(
            status_code=403,
            detail="Bạn không có quyền thực hiện thao tác này.",
        )

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
                SELECT MaHocPhan, TenHocPhan
                FROM HOC_PHAN 
                WHERE TenHocPhan ILIKE %s
                ORDER BY TenHocPhan
                LIMIT 10
            """,
            (f"%{keyword}%",),
        )
        rows = cur.fetchall()

        return [{"MaHocPhan": row[0], "TenHocPhan": row[1]} for row in rows]
    finally:
        conn.close()


@router.get("/api/course-groups")
def get_course_groups(
    request: Request,
):
    if not has_permission(request, "gui_yeu_cau_xep_lich"):
        raise HTTPException(
            status_code=403,
            detail="Bạn không có quyền thực hiện thao tác này.",
        )

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
                SELECT DISTINCT MaNhom, TenNhom
                FROM NHOM 
                ORDER BY TenNhom
            """,
        )
        return [{"MaNhom": row[0], "TenNhom": row[1]} for row in cur.fetchall()]

    finally:
        conn.close()


@router.get("/api/course-software")
def get_course_software(
    request: Request,
    course_id: int,
):
    if not has_permission(request, "gui_yeu_cau_xep_lich"):
        raise HTTPException(
            status_code=403,
            detail="Bạn không có quyền thực hiện thao tác này.",
        )

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
                SELECT DISTINCT pm.MaPhanMem, pm.TenPhanMem
                FROM HOC_PHAN_PHAN_MEM hppm
                JOIN PHAN_MEM pm ON pm.MaPhanMem = hppm.MaPhanMem
                WHERE MaHocPhan = %s
                ORDER BY pm.TenPhanMem
            """,
            (course_id,),
        )
        return [{"MaPhanMem": row[0], "TenPhanMem": row[1]} for row in cur.fetchall()]
    finally:
        conn.close()


@router.get("/api/weeks")
def search_weeks(
    request: Request,
    keyword: str = Query(default="", min_length=1),
    semester_id: int = Query(...),
):
    if not has_permission(request, "gui_yeu_cau_xep_lich"):
        raise HTTPException(
            status_code=403,
            detail="Bạn không có quyền thực hiện thao tác này.",
        )

    if not keyword.isdigit():
        return []

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT 
                th.MaTuanHoc
                ,th.TenTuanHoc
                ,TO_CHAR(th.NgayBatDau, 'DD/MM/YYYY') AS "NgayBatDau"
                ,TO_CHAR(th.NgayKetThuc, 'DD/MM/YYYY') AS "NgayKetThuc"
            FROM TUAN_HOC th
            WHERE th.MaHocKy = %s
              AND th.TenTuanHoc = %s
            ORDER BY th.TenTuanHoc
            LIMIT 10
        """,
            (semester_id, int(keyword)),
        )
        rows = cur.fetchall()

        return [
            {
                "MaTuanHoc": row[0],
                "TenTuanHoc": row[1],
                "NgayBatDau": row[2],
                "NgayKetThuc": row[3],
            }
            for row in rows
        ]
    finally:
        conn.close()


@router.post("/teacher/required")
def add_required(
    request: Request,
    required_course_id: int = Form(""),
    required_semester_id: int = Form(""),
    required_group_id: int = Form(""),
    required_lesson: int = Form(""),
    required_number_class: int = Form(""),
    required_type: str = Form("thuc_hanh"),
    required_week_start_id: Optional[int] = Form(None),
    required_week_end_id: Optional[int] = Form(None),
    required_practice_day: Optional[date] = Form(None),
    required_note: Optional[str] = Form(""),
    required_week_day: List[int] = Form([]),
):
    if not has_permission(request, "gui_yeu_cau_xep_lich"):
        return RedirectResponse(url="/login", status_code=303)

    user = get_user_by_id(request.session.get("accountId"))
    if user is None:
        request.session["error"] = "Không tìm thấy tài khoản giảng viên."
        return RedirectResponse(url="/teacher/required", status_code=303)

    conn = get_connection()
    cursor = None
    try:
        cursor = conn.cursor()

        def reject(message):
            conn.rollback()
            request.session["error"] = message
            return RedirectResponse(url="/teacher/required", status_code=303)

        if required_type not in {"thuc_hanh", "khac"}:
            return reject("Loại yêu cầu không hợp lệ.")

        cursor.execute(
            "SELECT 1 FROM NHOM WHERE MaNhom = %s",
            (required_group_id,),
        )
        if cursor.fetchone() is None:
            return reject("Nhóm học phần không hợp lệ.")

        cursor.execute(
            "SELECT 1 FROM BUOI WHERE MaBuoi = %s",
            (required_lesson,),
        )
        if cursor.fetchone() is None:
            return reject("Buổi thực hành không hợp lệ.")

        schedule_rows = []
        if required_type == "thuc_hanh":
            week_days = sorted(set(required_week_day))
            if (
                not week_days
                or required_week_start_id is None
                or required_week_end_id is None
            ):
                return reject("Vui lòng chọn thứ thực hành và khoảng tuần.")

            if any(day not in range(2, 9) for day in week_days):
                return reject("Thứ thực hành không hợp lệ.")

            cursor.execute(
                """
                    SELECT MaTuanHoc, NgayBatDau, NgayKetThuc
                    FROM TUAN_HOC
                    WHERE MaHocKy = %s
                      AND MaTuanHoc IN (%s, %s)
                    ORDER BY NgayBatDau
                """,
                (
                    required_semester_id,
                    required_week_start_id,
                    required_week_end_id,
                ),
            )
            selected_weeks = cursor.fetchall()
            if not selected_weeks:
                return reject("Tuần đã chọn không thuộc học kỳ.")

            week_by_id = {row[0]: row for row in selected_weeks}
            start_week = week_by_id.get(required_week_start_id)
            end_week = week_by_id.get(required_week_end_id)
            if start_week is None or end_week is None:
                return reject("Tuần đã chọn không thuộc học kỳ.")
            # if start_week[1] < date.today():
            #     return reject("Không thể gửi yêu cầu bắt đầu từ tuần đã qua.")
            if start_week[1] > end_week[1]:
                return reject("Tuần kết thúc phải sau hoặc bằng tuần bắt đầu.")

            cursor.execute(
                """
                    SELECT MaTuanHoc
                    FROM TUAN_HOC
                    WHERE MaHocKy = %s
                      AND NgayBatDau >= %s
                      AND NgayBatDau <= %s
                    ORDER BY NgayBatDau
                """,
                (required_semester_id, start_week[1], end_week[1]),
            )
            weeks = [row[0] for row in cursor.fetchall()]
            schedule_rows = [
                (
                    required_type,
                    week_id,
                    week_day,
                    required_lesson,
                    None,
                    required_note.strip() if required_note else None,
                )
                for week_id in weeks
                for week_day in week_days
            ]
        else:
            if required_practice_day is None:
                return reject("Vui lòng chọn ngày thực hành.")
            if required_practice_day < date.today() + timedelta(days=3):
                return reject("Ngày thực hành cần cách ngày hiện tại ít nhất 3 ngày.")

            cursor.execute(
                """
                    SELECT th.MaTuanHoc, thu.MaThu
                    FROM TUAN_HOC th
                    JOIN THU thu ON thu.MaThu = %s
                    WHERE th.MaHocKy = %s
                    AND (%s::date BETWEEN th.NgayBatDau AND th.NgayKetThuc)
                """,
                (
                    required_practice_day.isoweekday() + 1,
                    required_semester_id,
                    required_practice_day,
                ),
            )
            week_day = cursor.fetchone()
            if week_day is None:
                return reject("Ngày thực hành không nằm trong tuần của học kỳ đã chọn.")
            schedule_rows.append(
                (
                    required_type,
                    week_day[0],
                    week_day[1],
                    required_lesson,
                    required_practice_day,
                    required_note.strip() if required_note else None,
                )
            )

        cursor.execute(
            """
                INSERT INTO LOP_HOC_PHAN
                    (MaHocPhan, MaHocKy, MaGiangVien, MaNhom, SiSo)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING MaLopHocPhan
            """,
            (
                required_course_id,
                required_semester_id,
                user[0],
                required_group_id,
                required_number_class,
            ),
        )
        required_class_id = cursor.fetchone()[0]

        schedule_rows = [
            (required_class_id, *schedule_row) for schedule_row in schedule_rows
        ]
        cursor.executemany(
            """
                INSERT INTO LICH_THUC_HANH
                    (MaLopHocPhan, LoaiYeuCau, MaTuanHoc, MaThu, MaBuoi,
                     MaTrangThai, NgayThucHanh, GhiChu)
                VALUES (%s, %s, %s, %s, %s, 0, %s, %s)
            """,
            schedule_rows,
        )
        conn.commit()
        request.session["success"] = "Thêm yêu cầu thành công!"
    except Exception:
        conn.rollback()
        raise
    finally:
        if cursor is not None:
            cursor.close()
        conn.close()

    return RedirectResponse(
        url="required",
        status_code=303,
    )


# ================== xoa yeu cau sap lich ===================


@router.post("/teacher/required/{required_id}/delete")
def delete_program(
    request: Request,
    required_id: int,
):
    if not has_permission(request, "xoa_yeu_cau_ca_nhan"):
        return RedirectResponse(url="/login", status_code=303)
    user = get_user_by_id(request.session.get("accountId"))
    if user is None:
        request.session["error"] = "Không tìm thấy tài khoản giảng viên."
        return RedirectResponse(url="/teacher/required", status_code=303)

    conn = get_connection()
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
                WITH target AS (
                    SELECT
                        lth.MaLopHocPhan,
                        lth.LoaiYeuCau,
                        lth.MaBuoi,
                        lth.NgayYeuCau,
                        lth.NgayThucHanh,
                        lth.GhiChu
                    FROM LICH_THUC_HANH lth
                    JOIN LOP_HOC_PHAN lhp
                        ON lhp.MaLopHocPhan = lth.MaLopHocPhan
                    WHERE lth.MaLichThucHanh = %s
                      AND lhp.MaGiangVien = %s
                      AND lth.MaTrangThai = 0
                    FOR UPDATE OF lth
                )
                DELETE FROM LICH_THUC_HANH lth
                USING target t
                WHERE lth.MaLopHocPhan = t.MaLopHocPhan
                  AND lth.LoaiYeuCau = t.LoaiYeuCau
                  AND lth.MaBuoi = t.MaBuoi
                  AND lth.MaTrangThai = 0
                  AND lth.NgayYeuCau = t.NgayYeuCau
                  AND lth.GhiChu IS NOT DISTINCT FROM t.GhiChu
                  AND (
                      t.LoaiYeuCau = 'thuc_hanh'
                      OR lth.NgayThucHanh IS NOT DISTINCT FROM t.NgayThucHanh
                  )
            """,
            (required_id, user[0]),
        )

        if cursor.rowcount == 0:
            conn.rollback()
            request.session["error"] = (
                "Không tìm thấy yêu cầu đang chờ duyệt hoặc bạn không có quyền xóa."
            )
        else:
            conn.commit()
            request.session["success"] = "Xóa yêu cầu thành công!"

    except Exception:
        conn.rollback()
        raise

    finally:
        if cursor is not None:
            cursor.close()
        conn.close()

    return RedirectResponse(
        url="/teacher/required",
        status_code=303,
    )


# =========== hien lich da sap


def get_scheduled_requests_for_teacher(teacher_id, semester_id):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute(
        """
            SELECT
                yc.MaYeuCau AS "MaYeuCau",
                yct.MaPhong AS "MaPhong",
                yct.MaTuanHoc AS "MaTuanHoc",
                yc.BuoiThucHanh AS "BuoiThucHanh",
                (yc.NgayThucHanh IS NULL) AS "LaLichDinhKy",
                yc.MaTuanBatDau AS "MaTuanBatDau",
                yc.MaTuanKetThuc AS "MaTuanKetThuc",
                yc.SoLuongMay AS "SoLuongMay",
                yc.MaPhanMem AS "MaPhanMem",
                hp.TenHocPhan AS "TenHocPhan",
                yc.NhomHocPhan AS "NhomHocPhan",
                STRING_AGG(
                    DISTINCT yct.thu::text,
                    ',' ORDER BY yct.thu::text
                ) FILTER (
                    WHERE yct.NgayThucHanh IS NULL
                      AND yct.MaPhong IS NOT NULL
                ) AS "DanhSachThu",
                STRING_AGG(
                    DISTINCT TO_CHAR(yct.NgayThucHanh, 'YYYY-MM-DD'),
                    ',' ORDER BY TO_CHAR(yct.NgayThucHanh, 'YYYY-MM-DD')
                ) FILTER (
                    WHERE yct.NgayThucHanh BETWEEN hk.NgayBatDau AND hk.NgayKetThuc
                      AND yct.MaPhong IS NOT NULL
                ) AS "DanhSachNgay"
            FROM YEU_CAU_XEP_LICH yc
            JOIN HOC_PHAN hp ON hp.MaHocPhan = yc.MaHocPhan
            JOIN YEU_CAU_THU yct ON yct.MaYeuCau = yc.MaYeuCau
            LEFT JOIN TUAN_HOC tbd ON tbd.MaTuanHoc = yc.MaTuanBatDau
            LEFT JOIN TUAN_HOC tkt ON tkt.MaTuanHoc = yc.MaTuanKetThuc
            JOIN HOC_KY hk ON hk.MaHocKy = %s
            WHERE yc.MaGiangVien = %s
              AND yc.TrangThai = 2
              AND yct.MaPhong IS NOT NULL
              AND (
                    (
                        yc.NgayThucHanh IS NULL
                        AND tbd.NgayBatDau <= hk.NgayKetThuc
                        AND tkt.NgayKetThuc >= hk.NgayBatDau
                    )
                    OR (
                        yc.NgayThucHanh BETWEEN hk.NgayBatDau AND hk.NgayKetThuc
                    )
                    OR EXISTS (
                        SELECT 1
                        FROM YEU_CAU_THU yct_date
                        WHERE yct_date.MaYeuCau = yc.MaYeuCau
                          AND yct_date.MaPhong IS NOT NULL
                          AND yct_date.NgayThucHanh
                              BETWEEN hk.NgayBatDau AND hk.NgayKetThuc
                    )
              )
            GROUP BY
                yc.MaYeuCau,
                yct.MaPhong,
                yct.MaTuanHoc,
                yc.BuoiThucHanh,
                (yc.NgayThucHanh IS NULL),
                yc.MaTuanBatDau,
                yc.MaTuanKetThuc,
                yc.SoLuongMay,
                yc.MaPhanMem,
                yc.NhomHocPhan,
                hp.TenHocPhan
            ORDER BY yc.MaYeuCau
        """,
        (semester_id, teacher_id),
    )
    schedules = cursor.fetchall()
    cursor.close()
    conn.close()
    return schedules


def get_rooms_by_ids(room_ids=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
            SELECT
                p.MaPhong,
                p.TenPhong,
                p.TinhTrangPhong,
                COUNT(DISTINCT mt.MaMayTinh) AS TongSoMay,
                p.MaCauHinh,
                COALESCE(
                    ARRAY_AGG(DISTINCT cpm.MaPhanMem)
                    FILTER (WHERE cpm.MaPhanMem IS NOT NULL),
                    ARRAY[]::integer[]
                ) AS DanhSachPhanMem
            FROM PHONG p
            LEFT JOIN MAY_TINH mt ON mt.MaPhong = p.MaPhong
            LEFT JOIN CAU_HINH_PHAN_MEM cpm ON cpm.MaCauHinh = p.MaCauHinh
            WHERE (%s IS NULL OR p.MaPhong = ANY(%s))
            GROUP BY
                p.MaPhong,
                p.TenPhong,
                p.TinhTrangPhong,
                p.MaCauHinh
            ORDER BY p.TenPhong
        """,
        (room_ids, room_ids),
    )
    rooms = cursor.fetchall()
    cursor.close()
    conn.close()
    return rooms


@router.get("/teacher/calendar")
def show_teacher_calendar(request: Request):
    if not (
        has_permission(request, "xem_lich_giang_day_ca_nhan")
        and has_permission(request, "xem_thong_bao_ca_nhan_giang_vien")
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
    schedules = (
        get_scheduled_requests_for_teacher(user[0], semester[0]) if semester else []
    )
    all_room = get_rooms_by_ids()
    success = request.session.pop("success", None)

    return templates.TemplateResponse(
        request=request,
        name="teacher/calendar.html",
        context={
            "user": user,
            "avt": request.session.get("avt"),
            "semester": semester,
            "weeks": weeks,
            "all_scheduled": schedules,
            "all_room": all_room,
            "success": success,
        },
    )

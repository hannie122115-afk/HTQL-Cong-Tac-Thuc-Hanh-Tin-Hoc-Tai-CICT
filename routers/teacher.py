from fastapi import APIRouter, Request, Form, Query
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from psycopg2.extras import RealDictCursor
from database import get_connection
from datetime import date
from typing import List, Optional

templates = Jinja2Templates(directory="templates")
router = APIRouter()


def get_user_by_id(accountId):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
            SELECT gv.*
                , tk.AnhDaiDien
                , tk.VaiTro
            FROM GIANG_VIEN gv
            JOIN TAI_KHOAN_DANG_NHAP tk ON tk.MaTaiKhoan = gv.MaTaiKhoan
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
def show_admin(request: Request):
    role = request.session.get("role")

    if role != 1:
        return RedirectResponse(url="/login", status_code=303)

    user = get_user_by_id(request.session.get("accountId"))
    avt = request.session.get("avt")

    return templates.TemplateResponse(
        request=request,
        name="teacher/index.html",
        context={
            "user": user,
            "avt": avt,
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
            SELECT 
                yc.MaYeuCau AS "MaYeuCau"
                , TO_CHAR(yc.NgayYeuCau, 'DD/MM/YYYY') AS "NgayYeuCau"
                , yc.BuoiThucHanh AS "BuoiThucHanh"
                , yc.SoLuongMay AS "SoLuongMay"
                , yc.NhomHocPhan AS "NhomHocPhan"
                , yc.TrangThai AS "TrangThai"
                , yc.GhiChu AS "GhiChu"
                , TO_CHAR(yc.NgayThucHanh, 'DD/MM/YYYY') AS "NgayThucHanh"
                , STRING_AGG(
                    DISTINCT yct.thu::text,
                    ', ' ORDER BY yct.thu::text
                ) AS "DanhSachThu"
                , hp.TenHocPhan AS "TenHocPhan"
                , hp.MaHocPhan AS "MaHocPhan"
                , pm.TenPhanMem AS "TenPhanMem"
                , gv.TenGiangVien AS "TenGiangVien"
                , qtv.TenQuanTriVien AS "TenQuanTriVien"
                , tbd.TenTuanHoc AS "TuanBatDau"
                , tkt.TenTuanHoc AS "TuanKetThuc"
                , CASE 
                    WHEN yc.NgayThucHanh IS NOT NULL THEN 0 
                    ELSE 1
                END AS "LoaiYeuCau"
            FROM YEU_CAU_XEP_LICH yc
            JOIN HOC_PHAN hp ON hp.MaHocPhan = yc.MaHocPhan
            JOIN PHAN_MEM pm ON pm.MaPhanMem = yc.MaPhanMem
            JOIN GIANG_VIEN gv ON gv.MaGiangVien = yc.MaGiangVien
            LEFT JOIN QUAN_TRI_VIEN qtv ON qtv.MaQuanTriVien = yc.MaQuanTriVien
            LEFT JOIN TUAN_HOC tbd ON tbd.MaTuanHoc = yc.MaTuanBatDau
            LEFT JOIN TUAN_HOC tkt ON tkt.MaTuanHoc = yc.MaTuanKetThuc
            LEFT JOIN YEU_CAU_THU yct ON yct.MaYeuCau = yc.MaYeuCau
            WHERE 
                yc.MaGiangVien = %s
                AND hp.TenHocPhan ILIKE %s
                AND (%s IS NULL OR %s = '' OR yc.NgayYeuCau::date = %s::date)
                AND (%s IS NULL OR yc.TrangThai = %s)
            GROUP BY
                yc.MaYeuCau
                , yc.NgayYeuCau
                , yc.BuoiThucHanh
                , yc.SoLuongMay
                , yc.NhomHocPhan
                , yc.TrangThai
                , yc.GhiChu
                , yc.NgayThucHanh
                , hp.TenHocPhan
                , hp.MaHocPhan
                , pm.TenPhanMem
                , gv.TenGiangVien
                , qtv.TenQuanTriVien
                , tbd.TenTuanHoc
                , tkt.TenTuanHoc
            ORDER BY yc.NgayYeuCau DESC
            LIMIT %s OFFSET %s
        """,
        (
            teacherId,
            f"%{keyword}%",
            date_val,
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
            SELECT COUNT(DISTINCT yc.MaYeuCau)
            FROM YEU_CAU_XEP_LICH yc
            JOIN HOC_PHAN hp ON hp.MaHocPhan = yc.MaHocPhan
            WHERE yc.MaGiangVien = %s 
                AND hp.TenHocPhan ILIKE %s
                AND (%s IS NULL OR %s = '' OR yc.NgayYeuCau::date = %s::date)
                AND (%s IS NULL OR yc.TrangThai = %s)
        """,
        (
            userId,
            f"%{keyword}%",
            date_val,
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


def get_scheduled_requests_for_teacher(teacher_id, semester_id):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute(
        """
            SELECT
                yc.MaYeuCau AS "MaYeuCau",
                yct.MaPhong AS "MaPhong",
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
    if request.session.get("role") != 1:
        return RedirectResponse(url="/login", status_code=303)

    user = get_user_by_id(request.session.get("accountId"))
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    semester = get_semester_current()
    weeks = get_weeks_by_semester(semester[0]) if semester else []
    schedules = (
        get_scheduled_requests_for_teacher(user[0], semester[0])
        if semester
        else []
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


@router.get("/teacher/required")
def show_required_teacher(
    request: Request,
    page: int = 1,
    keyword: str = "",
    created_date: str = "",
    status: Optional[str] = Query(None),
):
    role = request.session.get("role")
    if role != 1:
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
    semester = get_semester_current()

    success = request.session.pop("success", None)

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
            "semester": semester,
            "success": success,
        },
    )


# ================== them yeu cau sap lich ===================


@router.get("/api/courses")
def search_courses(
    keyword: str = Query(default="", min_length=1),
):
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


@router.get("/api/programs")
def search_programs(
    keyword: str = Query(default="", min_length=1),
):

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT MaPhanMem, TenPhanMem
            FROM PHAN_MEM
            WHERE TenPhanMem ILIKE %s
            ORDER BY TenPhanMem
            LIMIT 10
        """,
            (f"%{keyword}%",),
        )
        rows = cur.fetchall()

        return [{"MaPhanMem": row[0], "TenPhanMem": row[1]} for row in rows]
    finally:
        conn.close()


@router.get("/api/weeks")
def search_weeks(
    keyword: str = Query(default="", min_length=1),
):

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
            JOIN HOC_KY hk ON hk.MaHocKy = th.MaHocKy
            WHERE th.TenTuanHoc = %s
            AND CURRENT_DATE BETWEEN hk.NgayBatDau AND hk.NgayKetThuc
            ORDER BY th.TenTuanHoc
            LIMIT 10
        """,
            (int(keyword),),
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
    required_program_id: int = Form(""),
    required_computer_amount: int = Form(""),
    required_group: Optional[str] = Form(None, max_length=100),
    required_lesson: int = Form(""),
    required_type: int = Form(1),
    required_week_start_id: Optional[int] = Form(None),
    required_week_end_id: Optional[int] = Form(None),
    required_practice_day: Optional[str] = Form(None),
    required_note: Optional[str] = Form(""),
    required_week_day: List[int] = Form([]),
):
    role = request.session.get("role")
    if role != 1:
        return RedirectResponse(url="/login", status_code=303)

    user = get_user_by_id(request.session.get("accountId"))
    conn = get_connection()
    cursor = conn.cursor()

    week_start = required_week_start_id if required_type == 1 else None
    week_end = required_week_end_id if required_type == 1 else None
    practice_day = (
        required_practice_day
        if (required_type == 0 and required_practice_day)
        else None
    )
    group_name = required_group.strip() if required_group else None

    cursor.execute(
        """
            INSERT INTO YEU_CAU_XEP_LICH
            (BuoiThucHanh
            , SoLuongMay
            , NhomHocPhan
            , GhiChu
            , MaPhanMem
            , MaHocPhan
            , MaGiangVien
            , MaTuanBatDau
            , MaTuanKetThuc
            , NgayThucHanh)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING MaYeuCau
        """,
        (
            required_lesson,
            required_computer_amount,
            group_name,
            required_note,
            required_program_id,
            required_course_id,
            user[0],
            week_start,
            week_end,
            practice_day,
        ),
    )

    required_id = cursor.fetchone()[0]

    if required_week_day:
        for rwd in required_week_day:
            cursor.execute(
                """
                    INSERT INTO YEU_CAU_THU (MaYeuCau, Thu)
                    VALUES (%s, %s)
                """,
                (
                    required_id,
                    rwd,
                ),
            )
    elif practice_day:
        practice_weekday = date.fromisoformat(practice_day).isoweekday() + 1
        cursor.execute(
            """
                INSERT INTO YEU_CAU_THU (MaYeuCau, Thu, NgayThucHanh)
                VALUES (%s, %s, %s)
            """,
            (
                required_id,
                practice_weekday,
                practice_day,
            ),
        )

    conn.commit()
    cursor.close()
    conn.close()

    request.session["success"] = "Thêm yêu cầu thành công!"

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
    role = request.session.get("role")
    if role != 1:
        return RedirectResponse(url="/login", status_code=303)
    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            DELETE FROM YEU_CAU_XEP_LICH
            WHERE MaYeuCau = %s
            """,
            (required_id,),
        )

        if cursor.rowcount == 0:
            conn.rollback()
            request.session["success"] = "Yêu cầu không tồn tại."
        else:
            conn.commit()
            request.session["success"] = "Xóa yêu cầu thành công!"

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()

    return RedirectResponse(
        url="/teacher/required",
        status_code=303,
    )

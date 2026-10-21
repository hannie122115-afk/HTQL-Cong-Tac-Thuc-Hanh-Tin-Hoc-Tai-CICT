from fastapi import APIRouter, Request, Form, Query
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from psycopg2.extras import RealDictCursor
from database import get_connection
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


# ==================yeu cau sap lich ===================


def get_required(per_page, offset, keyword, teacherId):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute(
        """
            SELECT 
                yc.MaYeuCau AS "MaYeuCau"
                , TO_CHAR(yc.NgayYeuCau, 'DD/MM/YYYY') AS "NgayYeuCau"
                , yc.BuoiThucHanh AS "BuoiThucHanh"
                , yc.SoLuongMay AS "SoLuongMay"
                , yc.TrangThai AS "TrangThai"
                , yc.GhiChu AS "GhiChu"
                , TO_CHAR(yc.NgayThucHanh, 'DD/MM/YYYY') AS "NgayThucHanh"
                , STRING_AGG(yct.thu::text, ', ' ORDER BY yct.thu) AS "DanhSachThu"
                , hp.TenHocPhan AS "TenHocPhan"
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
            GROUP BY
                yc.MaYeuCau
                , yc.NgayYeuCau
                , yc.BuoiThucHanh
                , yc.SoLuongMay
                , yc.TrangThai
                , yc.GhiChu
                , yc.NgayThucHanh
                , hp.TenHocPhan
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
            per_page,
            offset,
        ),
    )

    required = cursor.fetchall()

    cursor.close()
    conn.close()

    return required


def get_sum_required(keyword, userId):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
            SELECT COUNT(DISTINCT yc.MaYeuCau)
            FROM YEU_CAU_XEP_LICH yc
            JOIN HOC_PHAN hp ON hp.MaHocPhan = yc.MaHocPhan
            WHERE yc.MaGiangVien = %s AND hp.TenHocPhan ILIKE %s
        """,
        (userId, f"%{keyword}%"),
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


@router.get("/teacher/required")
def show_required_teacher(
    request: Request,
    page: int = 1,
    keyword: str = "",
):
    role = request.session.get("role")
    if role != 1:
        return RedirectResponse(url="/login", status_code=303)

    account_id = request.session.get("accountId")
    user = get_user_by_id(account_id)
    avt = request.session.get("avt")

    per_page = 10
    offset = (page - 1) * per_page

    amount = get_sum_required(keyword, user[0])
    required = get_required(per_page, offset, keyword, user[0])

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
            "semester": semester,
            "success": success,
        },
    )


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


def get_teacher_id(account_id: str = ""):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT MaGiangVien
        FROM GIANG_VIEN
        WHERE MaTaiKhoan = %s
    """,
        (account_id,),
    )
    teacher_id = cur.fetchone()[0]
    cur.close()
    conn.close()
    return teacher_id


@router.post("/teacher/required")
def add_required(
    request: Request,
    required_course_id: int = Form(""),
    required_program_id: int = Form(""),
    required_computer_amount: int = Form(""),
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

    teacher_id = get_teacher_id(request.session.get("accountId"))
    conn = get_connection()
    cursor = conn.cursor()

    week_start = required_week_start_id if required_type == 1 else None
    week_end = required_week_end_id if required_type == 1 else None
    practice_day = (
        required_practice_day
        if (required_type == 0 and required_practice_day)
        else None
    )

    cursor.execute(
        """
            INSERT INTO YEU_CAU_XEP_LICH
            (BuoiThucHanh
            , SoLuongMay
            , GhiChu
            , MaPhanMem
            , MaHocPhan
            , MaGiangVien
            , MaTuanBatDau
            , MaTuanKetThuc
            , NgayThucHanh)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING MaYeuCau
        """,
        (
            required_lesson,
            required_computer_amount,
            required_note,
            required_program_id,
            required_course_id,
            teacher_id,
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

    conn.commit()
    cursor.close()
    conn.close()

    request.session["success"] = "Thêm yêu cầu thành công!"

    return RedirectResponse(
        url="required",
        status_code=303,
    )

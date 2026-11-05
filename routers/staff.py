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
            SELECT cb.*
                , tk.AnhDaiDien
                , tk.VaiTro
            FROM CAN_BO cb
            JOIN TAI_KHOAN_DANG_NHAP tk ON tk.MaTaiKhoan = cb.MaTaiKhoan
            WHERE tk.MaTaiKhoan = %s
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
                yct.MaPhong AS "MaPhong",
                p.TenPhong AS "TenPhong",
                yct.Thu AS "Thu",
                yct.MaTuanHoc AS "MaTuanHoc",
                yc.BuoiThucHanh AS "BuoiThucHanh"
            FROM YEU_CAU_THU yct
            JOIN YEU_CAU_XEP_LICH yc ON yc.MaYeuCau = yct.MaYeuCau
            JOIN TUAN_HOC th ON th.MaTuanHoc = yct.MaTuanHoc
            JOIN PHONG p ON p.MaPhong = yct.MaPhong
            WHERE yct.MaCanBo = %s
              AND th.MaHocKy = %s
              AND yc.TrangThai = 2
              AND yct.MaPhong IS NOT NULL
            ORDER BY yct.MaTuanHoc, yct.Thu, yc.BuoiThucHanh, p.TenPhong
        """,
        (staff_id, semester_id),
    )
    assignments = cursor.fetchall()
    cursor.close()
    conn.close()
    return assignments


# ================trang chu ===========================
@router.get("/staff")
def show_admin(request: Request):
    role = request.session.get("role")

    if role != 0:
        return RedirectResponse(url="/login", status_code=303)

    user = get_user_by_id(request.session.get("accountId"))
    avt = request.session.get("avt")

    return templates.TemplateResponse(
        request=request,
        name="staff/index.html",
        context={
            "user": user,
            "avt": avt,
        },
    )


@router.get("/staff/calendar")
def show_staff_calendar(request: Request):
    if request.session.get("role") != 0:
        return RedirectResponse(url="/login", status_code=303)

    user = get_user_by_id(request.session.get("accountId"))
    if not user:
        return RedirectResponse(url="/login", status_code=303)

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

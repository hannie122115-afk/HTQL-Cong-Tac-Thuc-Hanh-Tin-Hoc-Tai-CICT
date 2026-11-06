from fastapi import APIRouter, Request, Form, Query, HTTPException
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

# =========== phong thuc hanh ============


def get_staff_rooms_for_week(staff_id, week_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
            SELECT
                p.MaPhong,
                p.TenPhong,
                COUNT(DISTINCT mt.MaMayTinh) AS SoLuongMay,
                p.TinhTrangPhong
            FROM YEU_CAU_THU yct
            JOIN YEU_CAU_XEP_LICH yc ON yc.MaYeuCau = yct.MaYeuCau
            JOIN PHONG p ON p.MaPhong = yct.MaPhong
            LEFT JOIN MAY_TINH mt ON mt.MaPhong = p.MaPhong
            WHERE yct.MaCanBo = %s
              AND yct.MaTuanHoc = %s
              AND yc.TrangThai = 2
              AND yct.MaPhong IS NOT NULL
            GROUP BY p.MaPhong, p.TenPhong, p.TinhTrangPhong
            ORDER BY p.TenPhong
        """,
        (staff_id, week_id),
    )
    rooms = cursor.fetchall()
    cursor.close()
    conn.close()
    return rooms


def save_status_report(staff_id, room_id, week_id, computer_id, current_status):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
                INSERT INTO Bao_cao_tinh_trang
                    (TinhTrangCuThe, MaCanBo, MaMayTinh, MaPhong)
                SELECT %s, %s, %s, %s
                WHERE EXISTS (
                    SELECT 1
                    FROM YEU_CAU_THU yct
                    JOIN YEU_CAU_XEP_LICH yc ON yc.MaYeuCau = yct.MaYeuCau
                    WHERE yct.MaCanBo = %s
                      AND yct.MaTuanHoc = %s
                      AND yct.MaPhong = %s
                      AND yc.TrangThai = 2
                )
                  AND (
                      %s IS NULL
                      OR EXISTS (
                          SELECT 1
                          FROM MAY_TINH mt
                          WHERE mt.MaMayTinh = %s
                            AND mt.MaPhong = %s
                      )
                  )
                RETURNING MaBaoCao
            """,
            (
                current_status,
                staff_id,
                computer_id,
                room_id,
                staff_id,
                week_id,
                room_id,
                computer_id,
                computer_id,
                room_id,
            ),
        )
        report = cursor.fetchone()
        if report is None:
            raise HTTPException(
                status_code=403,
                detail="Bạn không được phân công phòng hoặc máy tính này trong tuần đã chọn.",
            )
        conn.commit()
        cursor.close()
    finally:
        conn.close()


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


@router.get("/staff/room")
def show_staff_rooms(request: Request, week_id: Optional[int] = Query(default=None)):
    if request.session.get("role") != 0:
        return RedirectResponse(url="/login", status_code=303)

    user = get_user_by_id(request.session.get("accountId"))
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    semester = get_semester_current()
    weeks = get_weeks_by_semester(semester[0]) if semester else []
    selected_week = next(
        (week for week in weeks if week["id"] == week_id),
        next(
            (
                week
                for week in weeks
                if week["start"] <= date.today().isoformat() <= week["end"]
            ),
            weeks[0] if weeks else None,
        ),
    )
    rooms = (
        get_staff_rooms_for_week(user[0], selected_week["id"])
        if selected_week
        else []
    )

    return templates.TemplateResponse(
        request=request,
        name="staff/room.html",
        context={
            "user": user,
            "avt": request.session.get("avt"),
            "weeks": weeks,
            "selected_week": selected_week,
            "rooms": rooms,
            "success": request.query_params.get("success") == "1",
        },
    )


# ============= PHONG THUC HANH ===================


@router.get("/staff/room/{room_id}")
def show_staff_room_detail(
    request: Request,
    room_id: int,
    week_id: int = Query(...),
    keyword: str = Query(default=""),
):
    if request.session.get("role") != 0:
        return RedirectResponse(url="/login", status_code=303)

    user = get_user_by_id(request.session.get("accountId"))
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    rooms = get_staff_rooms_for_week(user[0], week_id)
    if not any(room[0] == room_id for room in rooms):
        raise HTTPException(status_code=404, detail="Không tìm thấy phòng được phân công.")

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
            WHERE p.MaPhong = %s
        """,
        (room_id,),
    )
    room = cursor.fetchone()
    cursor.execute(
        """
            SELECT MaCauHinh, Cpu
            FROM CAU_HINH
            ORDER BY MaCauHinh
        """
    )
    configs = cursor.fetchall()
    cursor.execute(
        """
            SELECT MaMayTinh, TinhTrangMay
            FROM MAY_TINH
            WHERE MaPhong = %s
              AND MaMayTinh::TEXT ILIKE %s
            ORDER BY MaMayTinh
        """,
        (room_id, f"%{keyword}%"),
    )
    computers = cursor.fetchall()
    cursor.close()
    conn.close()

    return templates.TemplateResponse(
        request=request,
        name="staff/room-detail.html",
        context={
            "user": user,
            "avt": request.session.get("avt"),
            "room": room,
            "configs": configs,
            "computers": computers,
            "keyword": keyword,
            "page": 1,
            "per_page": max(len(computers), 1),
            "amount": len(computers),
            "week_id": week_id,
            "success": request.query_params.get("success") == "1",
        },
    )


@router.post("/staff/room/report")
def create_staff_status_report(
    request: Request,
    room_id: int = Form(...),
    week_id: int = Form(...),
    current_status: str = Form(...),
    computer_id: Optional[str] = Form(default=None),
):
    if request.session.get("role") != 0:
        return RedirectResponse(url="/login", status_code=303)

    user = get_user_by_id(request.session.get("accountId"))
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    current_status = current_status.strip()
    if not current_status:
        raise HTTPException(status_code=422, detail="Vui lòng nhập tình trạng hiện tại.")

    computer_id = computer_id.strip() if computer_id else None
    save_status_report(user[0], room_id, week_id, computer_id, current_status)
    return RedirectResponse(url=f"/staff/room?week_id={week_id}&success=1", status_code=303,)


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

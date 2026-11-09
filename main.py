from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from database import get_connection
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from routers.auth import router as auth_router
from routers.admin import router as admin_router
from routers.staff import router as staff_router
from routers.teacher import router as teacher_router
from fastapi.staticfiles import StaticFiles
from psycopg2.extras import RealDictCursor

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
app.add_middleware(SessionMiddleware, secret_key="122115")
templates = Jinja2Templates(directory="templates")

app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(staff_router)
app.include_router(teacher_router)


@app.get("/")
@app.get("/index.html")
def home(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


# ================ LICH TOAN BO ===========


@app.get("/calendar")
def show_public_calendar(request: Request):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
            SELECT MaHocKy, TenHocKy, NamHoc
            FROM HOC_KY
            WHERE CURRENT_DATE BETWEEN NgayBatDau AND NgayKetThuc
            LIMIT 1
        """
    )
    semester = cursor.fetchone()

    weeks = []
    scheduled = []
    if semester:
        cursor.execute(
            """
                SELECT MaTuanHoc, TenTuanHoc, NgayBatDau, NgayKetThuc
                FROM TUAN_HOC
                WHERE MaHocKy = %s
                ORDER BY NgayBatDau
            """,
            (semester[0],),
        )
        weeks = [
            {
                "id": week[0],
                "name": week[1],
                "start": week[2].strftime("%Y-%m-%d"),
                "end": week[3].strftime("%Y-%m-%d"),
            }
            for week in cursor.fetchall()
        ]

        schedule_cursor = conn.cursor(cursor_factory=RealDictCursor)
        schedule_cursor.execute(
            """
                SELECT
                    yc.MaYeuCau AS "MaYeuCau",
                    yct.MaPhong AS "MaPhong",
                    yct.MaTuanHoc AS "MaTuanHoc",
                    yc.BuoiThucHanh AS "BuoiThucHanh",
                    (yc.NgayThucHanh IS NULL) AS "LaLichDinhKy",
                    yc.MaTuanBatDau AS "MaTuanBatDau",
                    yc.MaTuanKetThuc AS "MaTuanKetThuc",
                    hp.TenHocPhan AS "TenHocPhan",
                    yc.NhomHocPhan AS "NhomHocPhan",
                    gv.TenGiangVien AS "TenGiangVien",
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
                JOIN GIANG_VIEN gv ON gv.MaGiangVien = yc.MaGiangVien
                JOIN YEU_CAU_THU yct ON yct.MaYeuCau = yc.MaYeuCau
                LEFT JOIN TUAN_HOC tbd ON tbd.MaTuanHoc = yc.MaTuanBatDau
                LEFT JOIN TUAN_HOC tkt ON tkt.MaTuanHoc = yc.MaTuanKetThuc
                JOIN HOC_KY hk ON hk.MaHocKy = %s
                WHERE yc.TrangThai = 2
                  AND yct.MaPhong IS NOT NULL
                  AND (
                        (
                            yc.NgayThucHanh IS NULL
                            AND tbd.NgayBatDau <= hk.NgayKetThuc
                            AND tkt.NgayKetThuc >= hk.NgayBatDau
                        )
                        OR yc.NgayThucHanh BETWEEN hk.NgayBatDau AND hk.NgayKetThuc
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
                    yc.NhomHocPhan,
                    gv.TenGiangVien,
                    hp.TenHocPhan
                ORDER BY yc.MaYeuCau
            """,
            (semester[0],),
        )
        scheduled = schedule_cursor.fetchall()
        schedule_cursor.close()

    cursor.execute("SELECT MaPhong, TenPhong FROM PHONG ORDER BY TenPhong")
    rooms = cursor.fetchall()
    cursor.close()
    conn.close()

    sessions = [
        {"id": 1, "name": "Sáng", "icon": "fa-sun", "time": "07:00 - 11:00"},
        {"id": 2, "name": "Chiều", "icon": "fa-cloud-sun", "time": "13:30 - 17:00"},
        {"id": 3, "name": "Tối", "icon": "fa-moon", "time": "18:20 - 20:00"},
    ]
    for session in sessions:
        session["rooms"] = rooms

    return templates.TemplateResponse(
        request=request,
        name="calendar.html",
        context={
            "semester": semester,
            "weeks": weeks,
            "all_scheduled": scheduled,
            "calendar_sessions": sessions,
        },
    )

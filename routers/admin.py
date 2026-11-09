from fastapi import APIRouter, Request, Form, Query, Body, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse, RedirectResponse
from pwdlib import PasswordHash
from typing import List, Optional
from datetime import date
from datetime import datetime, timedelta
from psycopg2.extras import RealDictCursor
from psycopg2.errors import ForeignKeyViolation
import re, secrets, string, hashlib, os
from datetime import datetime, date, timedelta

from email_service import send_account_email
from database import get_connection
from notification_service import (
    NOTIFICATION_TYPE_SCHEDULE,
    NOTIFICATION_TYPE_SCHEDULE_REQUEST,
    NOTIFICATION_TYPE_STATUS_REPORT,
    get_unread_notification_types,
    get_schedule_notification_accounts,
    mark_notifications_read,
    notify_schedule_recipients,
    insert_notification,
)
from authorization import has_permission

router = APIRouter()

templates = Jinja2Templates(directory="templates")


# ====================================Trang chu========================


def get_user_by_id(accountId):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
            SELECT *
            FROM QUAN_TRI_VIEN
            WHERE MaTaiKhoan = %s
        """,
        (accountId,),
    )

    user = cursor.fetchone()

    cursor.close()
    conn.close()

    return user


@router.get("/admin")
@router.get("/admin/index.html")
def show_admin(request: Request):
    if not has_permission(request, "xem_trang_chu_quan_tri"):
        return RedirectResponse(url="/login", status_code=303)

    user = get_user_by_id(request.session.get("accountId"))
    avt = request.session.get("avt")
    unread_notifications = get_unread_notification_types(
        request.session.get("accountId")
    )

    return templates.TemplateResponse(
        request=request,
        name="admin/index.html",
        context={
            "user": user,
            "avt": avt,
            "has_unread_reports": NOTIFICATION_TYPE_STATUS_REPORT
            in unread_notifications,
            "has_unread_requests": NOTIFICATION_TYPE_SCHEDULE_REQUEST
            in unread_notifications,
        },
    )


# ====================================Cau hinh may========================
def get_config(per_page, offset, keyword):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
            SELECT *
            FROM CAU_HINH
            WHERE 
                Cpu ILIKE %s
                OR Ram ILIKE %s
                OR OCung ILIKE %s
            LIMIT %s OFFSET %s
        """,
        (
            f"%{keyword}%",
            f"%{keyword}%",
            f"%{keyword}%",
            per_page,
            offset,
        ),
    )

    configs = cursor.fetchall()

    cursor.close()
    conn.close()

    return configs


def get_sum_config(keyword):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
            SELECT COUNT(MaCauHinh)
            FROM CAU_HINH
            WHERE 
                Cpu ILIKE %s
                OR Ram ILIKE %s
                OR OCung ILIKE %s
        """,
        (
            f"%{keyword}%",
            f"%{keyword}%",
            f"%{keyword}%",
        ),
    )

    config = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    return config


def get_all_room():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
            SELECT *
            FROM PHONG
        """,
    )

    rooms = cursor.fetchall()

    cursor.close()
    conn.close()

    return rooms


@router.get("/admin/config")
def show_admin_config(
    request: Request,
    page: int = 1,
    keyword: str = "",
):
    if not has_permission(request, "quan_ly_cau_hinh"):
        return RedirectResponse(url="/login", status_code=303)

    user = get_user_by_id(request.session.get("accountId"))
    avt = request.session.get("avt")
    rooms = get_all_room()
    success = request.session.pop("success", None)

    per_page = 10  # moi bang hien 10 dong
    offset = (page - 1) * per_page
    configs = get_config(per_page, offset, keyword)
    amount = get_sum_config(keyword)

    return templates.TemplateResponse(
        request=request,
        name="admin/config.html",
        context={
            "configs": configs,
            "page": page,
            "user": user,
            "avt": avt,
            "amount": amount,
            "per_page": per_page,
            "keyword": keyword,
            "rooms": rooms,
            "success": success,
        },
    )


@router.post("/admin/config")
def add_config(
    request: Request,
    cpu: str = Form(""),
    ram: str = Form(""),
    hard_drive: str = Form(""),
    screen_card: str = Form(""),
    rooms: List[int] = Form([]),
    success: int = 1,
):
    if not has_permission(request, "quan_ly_cau_hinh"):
        return RedirectResponse(url="/login", status_code=303)
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
            INSERT INTO CAU_HINH
            (Cpu, Ram, OCung, CardManHinh)
            VALUES (%s, %s, %s, %s)
            RETURNING MaCauHinh
        """,
        (
            cpu,
            ram,
            hard_drive,
            screen_card,
        ),
    )

    configId = cursor.fetchone()[0]

    if rooms:
        for room in rooms:
            cursor.execute(
                """
                    UPDATE PHONG
                    SET MaCauHinh = %s
                    WHERE MaPhong = %s
                """,
                (
                    configId,
                    room,
                ),
            )

    conn.commit()
    cursor.close()
    conn.close()

    request.session["success"] = "Thêm cấu hình thành công!"

    return RedirectResponse(
        url="config",
        status_code=303,
    )


@router.post("/admin/config/{config_id}/delete")
def delete_config(
    request: Request,
    config_id: int,
):
    if not has_permission(request, "quan_ly_cau_hinh"):
        return RedirectResponse(url="/login", status_code=303)
    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            DELETE FROM CAU_HINH_PHAN_MEM
            WHERE MaCauHinh = %s
            """,
            (config_id,),
        )

        cursor.execute(
            """
            DELETE FROM CAU_HINH
            WHERE MaCauHinh = %s
            """,
            (config_id,),
        )

        if cursor.rowcount == 0:
            conn.rollback()
            request.session["success"] = "Cấu hình không tồn tại."
        else:
            conn.commit()
            request.session["success"] = "Xóa cấu hình thành công!"

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()

    return RedirectResponse(
        url="/admin/config",
        status_code=303,
    )


# ====================================Chi tiet cau hinh may========================


def get_program(keyword):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
            SELECT *
            FROM PHAN_MEM
            WHERE 
                TenPhanMem ILIKE %s
                OR NhaPhatHanh ILIKE %s
        """,
        (
            f"%{keyword}%",
            f"%{keyword}%",
        ),
    )

    programs = cursor.fetchall()

    cursor.close()
    conn.close()

    return programs


def get_sum_config_program(config_id, keyword):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
            SELECT COUNT(*)
            FROM CAU_HINH_PHAN_MEM chpm
            JOIN PHAN_MEM pm
                ON chpm.MaPhanMem = pm.MaPhanMem
            WHERE chpm.MaCauHinh = %s
            AND (
                pm.TenPhanMem ILIKE %s
                OR pm.NhaPhatHanh ILIKE %s
            )
        """,
        (
            config_id,
            f"%{keyword}%",
            f"%{keyword}%",
        ),
    )

    amount = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    return amount


def get_config_program(
    config_id,
    per_page,
    offset,
    keyword,
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
            SELECT pm.*
            FROM CAU_HINH_PHAN_MEM chpm
            JOIN PHAN_MEM pm
                ON chpm.MaPhanMem = pm.MaPhanMem
            WHERE chpm.MaCauHinh = %s
            AND (
                pm.TenPhanMem ILIKE %s
                OR pm.NhaPhatHanh ILIKE %s
            )
            ORDER BY pm.MaPhanMem
            LIMIT %s OFFSET %s
        """,
        (
            config_id,
            f"%{keyword}%",
            f"%{keyword}%",
            per_page,
            offset,
        ),
    )

    config_programs = cursor.fetchall()

    cursor.close()
    conn.close()

    return config_programs


@router.get("/admin/config/{config_id}")
def show_admin_config_detail(
    request: Request,
    config_id: int,
    keyword: str = "",
    page: int = 1,
):
    if not has_permission(request, "quan_ly_cau_hinh"):
        return RedirectResponse(url="/login", status_code=303)
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
            SELECT *
            FROM CAU_HINH
            WHERE MaCauHinh = %s
        """,
        (config_id,),
    )
    config = cursor.fetchone()

    cursor.execute(
        """
            SELECT MaPhong, TenPhong, MaCauHinh
            FROM PHONG
            WHERE 
                MaCauHinh = %s
                OR MaCauHinh IS NULL
            ORDER BY TenPhong
            """,
        (config_id,),
    )
    select_rooms = cursor.fetchall()

    cursor.execute(
        """
            SELECT MaPhong, TenPhong, MaCauHinh
            FROM PHONG
            ORDER BY TenPhong
        """,
    )
    rooms = cursor.fetchall()

    user = get_user_by_id(request.session.get("accountId"))
    avt = request.session.get("avt")

    success = request.session.pop("success", None)

    per_page = 5  # moi bang hien 5 dong
    offset = (page - 1) * per_page
    # table program full
    programs = get_program(keyword)
    # table config program
    config_programs = get_config_program(
        config_id,
        per_page,
        offset,
        keyword,
    )
    amount = get_sum_config_program(
        config_id,
        keyword,
    )
    selected_program_ids = [program[0] for program in config_programs]

    cursor.close()
    conn.close()

    return templates.TemplateResponse(
        request=request,
        name="admin/config-detail.html",
        context={
            "config": config,
            "user": user,
            "avt": avt,
            "rooms": rooms,
            "select_rooms": select_rooms,
            "success": success,
            "page": page,
            "amount": amount,
            "per_page": per_page,
            "keyword": keyword,
            "programs": programs,
            "config_programs": config_programs,
            "selected_program_ids": selected_program_ids,
        },
    )


@router.post("/admin/config/{config_id}")
def update_config(
    request: Request,
    config_id: int,
    cpu: str = Form(""),
    ram: str = Form(""),
    hard_drive: str = Form(""),
    screen_card: str = Form(""),
    rooms: List[int] = Form([]),
):
    if not has_permission(request, "quan_ly_cau_hinh"):
        return RedirectResponse(url="/login", status_code=303)
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE CAU_HINH
        SET Cpu = %s,
            Ram = %s,
            OCung = %s,
            CardManHinh = %s
        WHERE MaCauHinh = %s
        """,
        (
            cpu,
            ram,
            hard_drive,
            screen_card,
            config_id,
        ),
    )

    cursor.execute(
        """
        UPDATE PHONG
        SET MaCauHinh = NULL
        WHERE MaCauHinh = %s
        """,
        (config_id,),
    )

    if rooms:
        for room_id in rooms:
            cursor.execute(
                """
                UPDATE PHONG
                SET MaCauHinh = %s
                WHERE MaPhong = %s
                """,
                (
                    config_id,
                    room_id,
                ),
            )

    conn.commit()
    cursor.close()
    conn.close()

    request.session["success"] = "Cập nhật cấu hình thành công!"

    return RedirectResponse(
        url=f"/admin/config/{config_id}",
        status_code=303,
    )


@router.get("/admin/config/{config_id}/program/{program_id}/delete")
def delete_program_from_config(
    request: Request,
    config_id: int,
    program_id: int,
):
    if not has_permission(request, "quan_ly_cau_hinh"):
        return RedirectResponse(url="/login", status_code=303)
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
            DELETE FROM CAU_HINH_PHAN_MEM
            WHERE MaCauHinh = %s
            AND MaPhanMem = %s
        """,
        (
            config_id,
            program_id,
        ),
    )

    conn.commit()
    cursor.close()
    conn.close()

    request.session["success"] = "Đã xóa phần mềm tương thích với cấu hình!"

    return RedirectResponse(
        url=f"/admin/config/{config_id}",
        status_code=303,
    )


@router.post("/admin/config/{config_id}/program/save")
def save_config_program(
    request: Request,
    config_id: int,
    program_ids: list[int] = Form(default=[]),
):
    if not has_permission(request, "quan_ly_cau_hinh"):
        return RedirectResponse(url="/login", status_code=303)
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
            DELETE FROM CAU_HINH_PHAN_MEM
            WHERE MaCauHinh = %s
        """,
        (config_id,),
    )

    for program_id in program_ids:
        cursor.execute(
            """
                INSERT INTO CAU_HINH_PHAN_MEM
                (MaCauHinh, MaPhanMem)
                VALUES (%s, %s)
            """,
            (config_id, program_id),
        )

    conn.commit()
    cursor.close()
    conn.close()

    request.session["success"] = "Cập nhật phần mềm thành công!"

    return RedirectResponse(
        url=f"/admin/config/{config_id}",
        status_code=303,
    )


# ====================================Phan mem========================


def get_programs(per_page, offset, keyword):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
            SELECT *
            FROM PHAN_MEM
            WHERE 
                TenPhanMem ILIKE %s
                OR NhaPhatHanh ILIKE %s
            LIMIT %s OFFSET %s
        """,
        (
            f"%{keyword}%",
            f"%{keyword}%",
            per_page,
            offset,
        ),
    )

    programs = cursor.fetchall()

    cursor.close()
    conn.close()

    return programs


def get_sum_programs(keyword):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
            SELECT COUNT(MaPhanMem)
            FROM PHAN_MEM
            WHERE 
                TenPhanMem ILIKE %s
                OR NhaPhatHanh ILIKE %s
        """,
        (
            f"%{keyword}%",
            f"%{keyword}%",
        ),
    )

    program = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    return program


@router.get("/admin/program")
def show_admin_program(
    request: Request,
    page: int = 1,
    keyword: str = "",
):
    if not has_permission(request, "quan_ly_phan_mem"):
        return RedirectResponse(url="/login", status_code=303)

    user = get_user_by_id(request.session.get("accountId"))
    avt = request.session.get("avt")

    per_page = 10  # moi bang hien 10 dong
    offset = (page - 1) * per_page
    programs = get_programs(per_page, offset, keyword)
    amount = get_sum_programs(keyword)
    success = request.session.pop("success", None)

    return templates.TemplateResponse(
        request=request,
        name="admin/program.html",
        context={
            "programs": programs,
            "page": page,
            "user": user,
            "avt": avt,
            "amount": amount,
            "per_page": per_page,
            "keyword": keyword,
            # "rooms": rooms,
            "success": success,
        },
    )


@router.post("/admin/program")
def add_program(
    request: Request,
    program_name: str = Form(""),
    program_version: str = Form(""),
    program_publisher: str = Form(""),
    program_img: str = Form(""),
    success: int = 1,
):
    if not has_permission(request, "quan_ly_phan_mem"):
        return RedirectResponse(url="/login", status_code=303)
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
            INSERT INTO PHAN_MEM
            (TenPhanMem, PhienBan, NhaPhatHanh, AnhPhanMem)
            VALUES (%s, %s, %s, %s)
            RETURNING MaPhanMem
        """,
        (
            program_name,
            program_version,
            program_publisher,
            program_img,
        ),
    )

    conn.commit()
    cursor.close()
    conn.close()

    request.session["success"] = "Thêm phần mềm thành công!"

    return RedirectResponse(
        url="program",
        status_code=303,
    )


from fastapi.responses import JSONResponse


@router.get("/admin/program/{program_id}/compatibility")
def get_program_compatibility(
    request: Request,
    program_id: int,
):
    if not has_permission(request, "quan_ly_phan_mem"):
        return RedirectResponse(url="/login", status_code=303)
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT
                c.MaCauHinh,
                c.CPU,
                c.RAM,
                c.OCung,
                c.CardManHinh
            FROM CAU_HINH c
            JOIN CAU_HINH_PHAN_MEM cp
                ON c.MaCauHinh = cp.MaCauHinh
            WHERE cp.MaPhanMem = %s
            ORDER BY c.MaCauHinh
            """,
            (program_id,),
        )

        rows = cursor.fetchall()

        configs = [
            {
                "MaCauHinh": row[0],
                "CPU": row[1],
                "RAM": row[2],
                "OCung": row[3],
                "CardManHinh": row[4],
            }
            for row in rows
        ]

        return JSONResponse(content=configs)

    finally:
        cursor.close()
        conn.close()


@router.post("/admin/program/{program_id}/delete")
def delete_program(
    request: Request,
    program_id: int,
):
    if not has_permission(request, "quan_ly_phan_mem"):
        return RedirectResponse(url="/login", status_code=303)
    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            DELETE FROM CAU_HINH_PHAN_MEM
            WHERE MaPhanMem = %s
            """,
            (program_id,),
        )

        cursor.execute(
            """
            DELETE FROM PHAN_MEM
            WHERE MaPhanMem = %s
            """,
            (program_id,),
        )

        if cursor.rowcount == 0:
            conn.rollback()
            request.session["success"] = "Phần mềm không tồn tại."
        else:
            conn.commit()
            request.session["success"] = "Xóa phần mềm thành công!"

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()

    return RedirectResponse(
        url="/admin/program",
        status_code=303,
    )


@router.post("/admin/program/{program_id}/edit")
def edit_config(
    request: Request,
    program_id: int,
    program_name: str = Form(""),
    program_version: str = Form(""),
    program_publisher: str = Form(""),
    program_img: str = Form(""),
):
    if not has_permission(request, "quan_ly_phan_mem"):
        return RedirectResponse(url="/login", status_code=303)
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE PHAN_MEM
        SET TenPhanMem = %s,
            PhienBan = %s,
            NhaPhatHanh = %s,
            AnhPhanMem = %s
        WHERE MaPhanMem = %s
        """,
        (
            program_name,
            program_version,
            program_publisher,
            program_img,
            program_id,
        ),
    )

    conn.commit()
    cursor.close()
    conn.close()

    request.session["success"] = "Cập nhật phần mềm thành công!"

    return RedirectResponse(
        url=f"/admin/program",
        status_code=303,
    )


# ====================================Phong thuc hanh========================


def get_rooms(per_page, offset, keyword):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
            SELECT
                p.MaPhong,
                p.TenPhong,
                COUNT(mt.MaMayTinh) AS TongSoMay,
                p.TinhTrangPhong
            FROM PHONG p
            LEFT JOIN MAY_TINH mt
                ON mt.MaPhong = p.MaPhong
            GROUP BY
                p.MaPhong
            HAVING
                p.TenPhong ILIKE %s
                OR COUNT(mt.MaMayTinh)::TEXT ILIKE %s
            ORDER BY p.MaPhong
            LIMIT %s OFFSET %s;
        """,
        (
            f"%{keyword}%",
            f"%{keyword}%",
            per_page,
            offset,
        ),
    )

    rooms = cursor.fetchall()

    cursor.close()
    conn.close()

    return rooms


def get_sum_rooms(keyword):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
            SELECT COUNT(*)
            FROM (
                SELECT p.MaPhong
                FROM PHONG p
                LEFT JOIN MAY_TINH mt
                    ON mt.MaPhong = p.MaPhong
                GROUP BY p.MaPhong
                HAVING
                    p.TenPhong ILIKE %s
                    OR COUNT(mt.MaMayTinh)::TEXT ILIKE %s
            ) AS matched_rooms;
        """,
        (
            f"%{keyword}%",
            f"%{keyword}%",
        ),
    )

    room = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    return room


def get_staffs_room():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
            SELECT *
            FROM CAN_BO
        """,
    )

    staffs = cursor.fetchall()

    cursor.close()
    conn.close()

    return staffs


def get_configs_room():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
            SELECT *
            FROM CAU_HINH
        """,
    )

    configs = cursor.fetchall()

    cursor.close()
    conn.close()

    return configs


@router.get("/admin/room")
def show_admin_room(
    request: Request,
    page: int = 1,
    keyword: str = "",
):
    if not has_permission(request, "quan_ly_phong"):
        return RedirectResponse(url="/login", status_code=303)

    user = get_user_by_id(request.session.get("accountId"))
    avt = request.session.get("avt")
    staffs = get_staffs_room()
    configs = get_configs_room()

    per_page = 10  # moi bang hien 10 dong
    offset = (page - 1) * per_page
    rooms = get_rooms(per_page, offset, keyword)
    amount = get_sum_rooms(keyword)
    success = request.session.pop("success", None)
    error = request.session.pop("error", None)

    return templates.TemplateResponse(
        request=request,
        name="admin/room.html",
        context={
            "rooms": rooms,
            "staffs": staffs,
            "configs": configs,
            "page": page,
            "user": user,
            "avt": avt,
            "amount": amount,
            "per_page": per_page,
            "keyword": keyword,
            "success": success,
            "error": error,
        },
    )


@router.post("/admin/room")
def add_room(
    request: Request,
    room_name: str = Form(""),
    config_id: str = Form(""),
    staff_id: str = Form(""),
    machine_count: int = Form(...),
):
    if not (
        has_permission(request, "quan_ly_phong")
        and has_permission(request, "quan_ly_may_tinh")
    ):
        return RedirectResponse(url="/login", status_code=303)
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
            INSERT INTO PHONG
            (TenPhong, MaCanBo, MaCauHinh)
            VALUES (%s, %s, %s)
            RETURNING MaPhong
        """,
        (
            room_name,
            staff_id,
            config_id,
        ),
    )

    roomId = cursor.fetchone()[0]

    if machine_count:
        for machine in range(1, machine_count + 1):
            computerId = f"P{room_name}M{machine}"

            cursor.execute(
                """
                INSERT INTO MAY_TINH (MaMayTinh, MaPhong, TinhTrangMay)
                VALUES (%s, %s, %s)
                """,
                (computerId, roomId, 0),
            )

    conn.commit()
    cursor.close()
    conn.close()

    request.session["success"] = "Thêm phòng thành công!"

    return RedirectResponse(
        url="room",
        status_code=303,
    )


@router.post("/admin/room/{room_id}/delete")
def delete_room(
    request: Request,
    room_id: int,
):
    if not has_permission(request, "quan_ly_phong"):
        return RedirectResponse(url="/login", status_code=303)
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT MaPhong FROM PHONG WHERE MaPhong = %s FOR UPDATE", (room_id,))
        if cursor.fetchone() is None:
            conn.rollback()
            request.session["error"] = "Phòng không tồn tại hoặc đã được xóa."
            return RedirectResponse(url="/admin/room", status_code=303)

        cursor.execute(
            """
                SELECT COUNT(*) FROM BAO_CAO_TINH_TRANG
                WHERE MaPhong = %s OR MaMayTinh IN (
                    SELECT MaMayTinh FROM MAY_TINH WHERE MaPhong = %s
                )
            """,
            (room_id, room_id),
        )
        report_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM YEU_CAU_THU WHERE MaPhong = %s", (room_id,))
        schedule_count = cursor.fetchone()[0]
        dependencies = []
        if report_count:
            dependencies.append(f"{report_count} báo cáo tình trạng")
        if schedule_count:
            dependencies.append(f"{schedule_count} buổi thực hành đã xếp")
        if dependencies:
            conn.rollback()
            request.session["error"] = (
                f"Không thể xóa phòng {room_id} vì còn "
                + " và ".join(dependencies)
                + ". Vui lòng xử lý dữ liệu liên quan trước khi xóa."
            )
            return RedirectResponse(url="/admin/room", status_code=303)

        cursor.execute(
            """
            DELETE FROM MAY_TINH
            WHERE MaPhong = %s
            """,
            (room_id,),
        )

        cursor.execute(
            """
            DELETE FROM PHONG
            WHERE MaPhong = %s
            """,
            (room_id,),
        )

        if cursor.rowcount == 0:
            conn.rollback()
            request.session["error"] = "Phòng không tồn tại."
        else:
            conn.commit()
            request.session["success"] = "Xóa phòng thành công!"

    except ForeignKeyViolation:
        conn.rollback()
        request.session["error"] = (
            "Không thể xóa phòng vì phòng hoặc máy tính trong phòng "
            "đang được dữ liệu khác sử dụng."
        )
    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()

    return RedirectResponse(
        url="/admin/room",
        status_code=303,
    )


# ==================chi tiet phong thuc hanh =========================


def get_room(roomId):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
            SELECT
                p.MaPhong,
                p.TenPhong,
                ch.CPU AS CPU,
                ch.MaCauHinh,
                p.TinhTrangPhong
            FROM PHONG p
            LEFT JOIN CAU_HINH ch
                ON ch.MaCauHinh = p.MaCauHinh
            WHERE MaPhong = %s
        """,
        (roomId,),
    )

    room = cursor.fetchone()

    cursor.close()
    conn.close()

    return room


def get_computer(room_id, keyword, per_page, offset):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM MAY_TINH
        WHERE MaPhong = %s
          AND (
              MaMayTinh::TEXT ILIKE %s
              OR TinhTrangMay::TEXT ILIKE %s
          )
        ORDER BY MaMayTinh
        LIMIT %s OFFSET %s
        """,
        (
            room_id,
            f"%{keyword}%",
            f"%{keyword}%",
            per_page,
            offset,
        ),
    )

    computers = cursor.fetchall()

    cursor.close()
    conn.close()

    return computers


def get_sum_computer(room_id, keyword):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
            SELECT COUNT(*)
            FROM MAY_TINH
            WHERE MaPhong = %s
            AND (
                MaMayTinh::TEXT ILIKE %s
                OR TinhTrangMay::TEXT ILIKE %s
            )
        """,
        (
            room_id,
            f"%{keyword}%",
            f"%{keyword}%",
        ),
    )

    amount = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    return amount


@router.get("/admin/room/{room_id}")
def show_admin_room_detail(
    request: Request,
    room_id: int,
    keyword: str = "",
    page: int = 1,
):
    if not has_permission(request, "quan_ly_phong"):
        return RedirectResponse(url="/login", status_code=303)
    conn = get_connection()
    cursor = conn.cursor()

    user = get_user_by_id(request.session.get("accountId"))
    avt = request.session.get("avt")

    success = request.session.pop("success", None)
    error = request.session.pop("error", None)

    per_page = 10  # moi bang hien 5 dong
    offset = (page - 1) * per_page

    room = get_room(room_id)
    configs = get_configs_room()
    amount = get_sum_computer(
        room_id,
        keyword,
    )
    computers = get_computer(room_id, keyword, per_page, offset)
    cursor.close()
    conn.close()

    return templates.TemplateResponse(
        request=request,
        name="admin/room-detail.html",
        context={
            "room": room,
            "configs": configs,
            "computers": computers,
            "user": user,
            "avt": avt,
            "success": success,
            "page": page,
            "amount": amount,
            "per_page": per_page,
            "keyword": keyword,
            "success": success,
            "error": error,
        },
    )


@router.post("/admin/room/{room_id}")
def update_room(
    request: Request,
    room_id: int,
    room_name: str = Form(""),
    config_id: Optional[int] = Form(None),
    room_status: int = Form(...),
):
    if not has_permission(request, "quan_ly_phong"):
        return RedirectResponse(url="/login", status_code=303)
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE PHONG
        SET TenPhong = %s,
            MaCauHinh = %s,
            TinhTrangPhong = %s
        WHERE MaPhong = %s
        """,
        (
            room_name,
            config_id,
            room_status,
            room_id,
        ),
    )

    conn.commit()
    cursor.close()
    conn.close()

    request.session["success"] = "Cập nhật phòng thành công!"

    return RedirectResponse(
        url=f"/admin/room/{room_id}",
        status_code=303,
    )


@router.get("/admin/room/{room_id}/computer/{computer_id}/delete")
def delete_computer_room(
    request: Request,
    room_id: int,
    computer_id: str,
):
    if not has_permission(request, "quan_ly_may_tinh"):
        return RedirectResponse(url="/login", status_code=303)
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
            DELETE FROM MAY_TINH
            WHERE MaMayTinh = %s
            AND MaPhong = %s
        """,
        (
            computer_id,
            room_id,
        ),
    )

    conn.commit()
    cursor.close()
    conn.close()

    request.session["success"] = "Đã xóa máy tính ra khỏi phòng!"

    return RedirectResponse(
        url=f"/admin/room/{room_id}",
        status_code=303,
    )


@router.post("/admin/room/{room_id}/computer/add")
def add_computer_room(
    request: Request,
    room_id: int,
    machine_count: int = Form(...),
):
    if not has_permission(request, "quan_ly_may_tinh"):
        return RedirectResponse(url="/login", status_code=303)

    if machine_count < 1 or machine_count > 59:
        request.session["error"] = "Số lượng máy phải nhỏ hơn hoặc bằng 60!"
        return RedirectResponse(
            url=f"/admin/room/{room_id}",
            status_code=303,
        )

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT TenPhong
            FROM PHONG
            WHERE MaPhong = %s
            FOR UPDATE
            """,
            (room_id,),
        )

        room = cursor.fetchone()
        prefix = f"P{room[0]}M"

        cursor.execute(
            """
            SELECT MaMayTinh
            FROM MAY_TINH
            WHERE MaPhong = %s
            """,
            (room_id,),
        )

        computers = cursor.fetchall()

        max_number = 0
        for computer in computers:
            computer_id = str(computer[0])
            match = re.fullmatch(
                re.escape(prefix) + r"(\d+)",
                computer_id,
            )
            if match:
                number = int(match.group(1))
                max_number = max(max_number, number)

        for number in range(
            max_number + 1,
            max_number + machine_count + 1,
        ):
            new_computer_id = f"{prefix}{number}"

            cursor.execute(
                """
                INSERT INTO MAY_TINH
                    (MaMayTinh, MaPhong, TinhTrangMay)
                VALUES (%s, %s, %s)
                """,
                (new_computer_id, room_id, 0),
            )

        conn.commit()
        request.session["success"] = "Thêm máy tính thành công!"

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()

    return RedirectResponse(
        url=f"/admin/room/{room_id}",
        status_code=303,
    )


@router.post("/admin/room/{room_id}/computer/{computer_id}/update")
def update_computer_status(
    request: Request,
    room_id: int,
    computer_id: str,
    computer_status: int = Form(...),
):
    if not has_permission(request, "quan_ly_may_tinh"):
        return RedirectResponse(url="/login", status_code=303)

    if computer_status not in (0, 1, 2, 3):
        request.session["error"] = "Tình trạng máy tính không hợp lệ!"
        return RedirectResponse(
            url=f"/admin/room/{room_id}",
            status_code=303,
        )

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            UPDATE MAY_TINH
            SET TinhTrangMay = %s
            WHERE MaMayTinh = %s
              AND MaPhong = %s
            """,
            (computer_status, computer_id, room_id),
        )

        if cursor.rowcount == 0:
            conn.rollback()
            request.session["error"] = "Không tìm thấy máy tính!"
        else:
            conn.commit()
            request.session["success"] = "Cập nhật tình trạng máy tính thành công!"

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()

    return RedirectResponse(
        url=f"/admin/room/{room_id}",
        status_code=303,
    )


# ====================================Tai khoan========================


def get_accounts(per_page, offset, keyword, role, status):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
            SELECT 
                tk.MaTaiKhoan
                ,tk.TenDangNhap
                ,tk.VaiTro
                ,tk.TrangThai
                ,cb.TenCanBo
                ,cb.Email
                ,gv.TenGiangVien
                ,gv.Email
            FROM TAI_KHOAN_DANG_NHAP tk
            LEFT JOIN CAN_BO cb ON cb.MaTaiKhoan = tk.MaTaiKhoan
            LEFT JOIN GIANG_VIEN gv ON gv.MaTaiKhoan = tk.MaTaiKhoan
            WHERE
            (
                %s = ''
                OR cb.TenCanBo ILIKE %s
                OR gv.TenGiangVien ILIKE %s
                OR tk.TenDangNhap ILIKE %s
            )
            AND (%s IS NULL OR tk.VaiTro = %s)
            AND (%s IS NULL OR tk.TrangThai = %s)
            LIMIT %s OFFSET %s
        """,
        (
            keyword,
            f"%{keyword}%",
            f"%{keyword}%",
            f"%{keyword}%",
            role,
            role,
            status,
            status,
            per_page,
            offset,
        ),
    )

    accounts = cursor.fetchall()

    cursor.close()
    conn.close()

    return accounts


def get_sum_accounts(keyword, role, status):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
            SELECT COUNT(DISTINCT tk.MaTaiKhoan)
            FROM TAI_KHOAN_DANG_NHAP tk
            LEFT JOIN CAN_BO cb ON cb.MaTaiKhoan = tk.MaTaiKhoan
            LEFT JOIN GIANG_VIEN gv ON gv.MaTaiKhoan = tk.MaTaiKhoan
            WHERE 
            (
                %s = ''
                OR cb.TenCanBo ILIKE %s
                OR gv.TenGiangVien ILIKE %s
                OR tk.TenDangNhap ILIKE %s
            )
            AND (%s IS NULL OR tk.VaiTro = %s)
            AND (%s IS NULL OR tk.TrangThai = %s)
        """,
        (
            keyword,
            f"%{keyword}%",
            f"%{keyword}%",
            f"%{keyword}%",
            role,
            role,
            status,
            status,
        ),
    )

    account = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    return account


@router.get("/admin/account")
def show_admin_account(
    request: Request,
    page: int = 1,
    keyword: str = "",
    role: str = "",
    status: str = "",
):
    if not has_permission(request, "xem_tai_khoan"):
        return RedirectResponse(url="/login", status_code=303)

    user = get_user_by_id(request.session.get("accountId"))
    avt = request.session.get("avt")

    per_page = 10  # moi bang hien 10 dong
    offset = (page - 1) * per_page
    role = role if role != "" else None
    status = status if status != "" else None
    accounts = get_accounts(per_page, offset, keyword, role, status)
    amount = get_sum_accounts(keyword, role, status)

    success = request.session.pop("success", None)
    error = request.session.pop("error", None)
    pending_account_id = request.session.pop("pending_account_id", None)
    account_created = request.session.pop("account_created", False)

    return templates.TemplateResponse(
        request=request,
        name="admin/account.html",
        context={
            "accounts": accounts,
            "page": page,
            "user": user,
            "avt": avt,
            "amount": amount,
            "per_page": per_page,
            "keyword": keyword,
            "success": success,
            "status": status,
            "success": success,
            "error": error,
            "pending_account_id": pending_account_id,
            "account_created": account_created,
        },
    )


def generate_username(email):
    username = email.split("@")[0].lower()
    return username + "ctu"


password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def generate_setup_token():
    return secrets.token_urlsafe(32)


def hash_setup_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@router.post("/admin/account")
def add_account(
    request: Request,
    account_email: str = Form(""),
    account_name: str = Form(""),
    account_birth: str = Form(""),
    account_gender: str = Form(""),
    account_tel: str = Form(""),
    account_role: str = Form(""),
):
    if not has_permission(request, "cap_tai_khoan"):
        return RedirectResponse(url="/login", status_code=303)
    conn = get_connection()
    cursor = conn.cursor()

    account_email = account_email.strip()
    account_name = account_name.strip()
    account_tel = account_tel.strip()
    birth_date = date.fromisoformat(account_birth)

    try:
        while True:
            account_username = generate_username(account_email)
            cursor.execute(
                """
                SELECT 1
                FROM TAI_KHOAN_DANG_NHAP
                WHERE TenDangNhap = %s
                """,
                (account_username,),
            )
            if cursor.fetchone() is None:
                break

        cursor.execute(
            """
            INSERT INTO TAI_KHOAN_DANG_NHAP
                (TenDangNhap, MatKhau, VaiTro, AnhDaiDien, TrangThai)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING MaTaiKhoan
            """,
            (
                account_username,
                hash_password(secrets.token_urlsafe(16)),
                int(account_role),
                "https://cdn2.fptshop.com.vn/small/avatar_trang_1_cd729c335b.jpg",
                1,
            ),
        )
        account_id_new = cursor.fetchone()[0]
        request.session["pending_account_id"] = account_id_new
        if account_role == "1":
            cursor.execute(
                """
                INSERT INTO GIANG_VIEN
                    (TenGiangVien, GioiTinh, NgaySinh,
                     SoDienThoai, Email, MaTaiKhoan)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    account_name,
                    int(account_gender),
                    birth_date,
                    account_tel,
                    account_email,
                    account_id_new,
                ),
            )
        else:
            cursor.execute(
                """
                INSERT INTO CAN_BO
                    (TenCanBo, GioiTinh, NgaySinh,
                     SoDienThoai, Email, MaTaiKhoan)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    account_name,
                    int(account_gender),
                    birth_date,
                    account_tel,
                    account_email,
                    account_id_new,
                ),
            )

        conn.commit()
        request.session["success"] = "Cấp tài khoản thành công!"
        request.session["pending_account_id"] = account_id_new
        request.session["account_created"] = True
        return RedirectResponse(url="/admin/account", status_code=303)
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


@router.post("/admin/account/send-email/{account_id}")
async def send_account_setup_email(
    request: Request,
    account_id: int,
):
    if not has_permission(request, "gui_email_thiet_lap_tai_khoan"):
        return RedirectResponse(url="/login", status_code=303)
    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                tk.MaTaiKhoan,
                tk.TenDangNhap,
                tk.VaiTro,
                tk.TrangThai,
                COALESCE(gv.Email, cb.Email) AS Email
            FROM TAI_KHOAN_DANG_NHAP tk
            LEFT JOIN GIANG_VIEN gv
                ON gv.MaTaiKhoan = tk.MaTaiKhoan
            LEFT JOIN CAN_BO cb
                ON cb.MaTaiKhoan = tk.MaTaiKhoan
            WHERE tk.MaTaiKhoan = %s
            """,
            (account_id,),
        )
        account = cursor.fetchone()

        if account is None:
            return JSONResponse(
                {
                    "error": False,
                    "message": "Không tìm thấy tài khoản.",
                },
                status_code=404,
            )

        account_id_db, username, role, status, email = account

        if status != 1:
            return JSONResponse(
                {
                    "success": False,
                    "message": "Tài khoản đang bị khóa.",
                },
                status_code=400,
            )

        # Tạo token và thời hạn 24 giờ
        setup_token = generate_setup_token()
        token_hash = hash_setup_token(setup_token)
        expires_at = datetime.now() + timedelta(hours=24)

        cursor.execute(
            """
            INSERT INTO THIET_LAP_TAI_KHOAN
                (MaTaiKhoan, TokenHash, HetHan, DaSuDung)
            VALUES (%s, %s, %s, FALSE)
            ON CONFLICT (MaTaiKhoan)
            DO UPDATE SET
                TokenHash = EXCLUDED.TokenHash,
                HetHan = EXCLUDED.HetHan,
                DaSuDung = FALSE
            """,
            (
                account_id_db,
                token_hash,
                expires_at,
            ),
        )
        conn.commit()

        # Tạo liên kết thiết lập mật khẩu
        base_url = os.getenv(
            "APP_BASE_URL",
            "http://127.0.0.1:8000",
        ).rstrip("/")

        setup_link = f"{base_url}/account/setup?token={setup_token}"

        await send_account_email(
            to_email=email,
            username=username,
            setup_link=setup_link,
        )

        return JSONResponse(
            {
                "success": True,
                "message": f"Đã gửi email đến {email}.",
            }
        )

    except Exception:
        if conn:
            conn.rollback()

        # Ghi lỗi chi tiết ở terminal để tiện sửa lỗi
        import logging

        logging.exception("Lỗi gửi email thiết lập tài khoản")

        return JSONResponse(
            {
                "success": False,
                "message": (
                    "Không gửi được email. " "Kiểm tra cấu hình SMTP và Terminal."
                ),
            },
            status_code=500,
        )

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@router.get("/account/setup")
def show_setup_password(request: Request, token: str):
    return templates.TemplateResponse(
        request=request,
        name="admin/setup_password.html",
        context={"token": token},
    )


@router.post("/account/setup")
def setup_password(
    request: Request,
    token: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
):
    if not token.strip():
        return templates.TemplateResponse(
            request=request,
            name="admin/setup_password.html",
            context={
                "token": token,
                "error": "Liên kết thiết lập mật khẩu không hợp lệ.",
            },
            status_code=400,
        )

    if password != confirm_password:
        return templates.TemplateResponse(
            request=request,
            name="admin/setup_password.html",
            context={
                "token": token,
                "error": "Mật khẩu xác nhận không khớp.",
            },
            status_code=400,
        )

    if (
        len(password) < 8
        or not re.search(r"[A-Z]", password)
        or not re.search(r"[a-z]", password)
        or not re.search(r"[0-9]", password)
        or not re.search(r"[^A-Za-z0-9]", password)
    ):
        return templates.TemplateResponse(
            request=request,
            name="admin/setup_password.html",
            context={
                "token": token,
                "error": "Mật khẩu cần có ít nhất 8 ký tự, gồm chữ hoa, chữ thường, chữ số và ký tự đặc biệt.",
            },
            status_code=400,
        )

    token_hash = hash_setup_token(token)
    conn = None
    try:
        conn = get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT MaTaiKhoan, HetHan, DaSuDung
                FROM THIET_LAP_TAI_KHOAN
                WHERE TokenHash = %s
                FOR UPDATE
                """,
                (token_hash,),
            )
            setup = cur.fetchone()

            if not setup:
                conn.rollback()
                return templates.TemplateResponse(
                    request=request,
                    name="admin/setup_password.html",
                    context={
                        "token": "",
                        "error": "Liên kết không hợp lệ hoặc đã bị thay thế.",
                    },
                    status_code=400,
                )

            if setup["dasudung"]:
                conn.rollback()
                return templates.TemplateResponse(
                    request=request,
                    name="admin/setup_password.html",
                    context={
                        "token": "",
                        "error": "Liên kết này đã được sử dụng.",
                    },
                    status_code=400,
                )

            if (
                setup["hethan"] <= datetime.now(setup["hethan"].tzinfo)
                if setup["hethan"].tzinfo
                else setup["hethan"] <= datetime.now()
            ):
                conn.rollback()
                return templates.TemplateResponse(
                    request=request,
                    name="admin/setup_password.html",
                    context={
                        "token": "",
                        "error": "Liên kết đã hết hạn. Vui lòng yêu cầu gửi email mới.",
                    },
                    status_code=400,
                )
            account_id = setup["mataikhoan"]

            password_hashed = hash_password(password)
            cur.execute(
                """
                UPDATE TAI_KHOAN_DANG_NHAP
                SET MatKhau = %s
                WHERE MaTaiKhoan = %s
                """,
                (password_hashed, account_id),
            )

            if cur.rowcount != 1:
                conn.rollback()
                return templates.TemplateResponse(
                    request=request,
                    name="admin/setup_password.html",
                    context={
                        "token": "",
                        "error": "Không tìm thấy tài khoản cần cập nhật.",
                    },
                    status_code=400,
                )

            cur.execute(
                """
                UPDATE THIET_LAP_TAI_KHOAN
                SET DaSuDung = TRUE
                WHERE MaTaiKhoan = %s
                """,
                (account_id,),
            )

        conn.commit()
        request.session["success"] = (
            "Thiết lập mật khẩu thành công. Vui lòng đăng nhập."
        )
        return RedirectResponse(
            url="/login",
            status_code=303,
        )

    except Exception:
        if conn:
            conn.rollback()

        return templates.TemplateResponse(
            request=request,
            name="admin/setup_password.html",
            context={
                "token": token,
                "error": "Đã xảy ra lỗi khi thiết lập mật khẩu. Vui lòng thử lại.",
            },
            status_code=500,
        )

    finally:
        if conn:
            conn.close()


@router.post("/admin/account/{role}/{account_id}/delete")
def delete_account(request: Request, account_id: int, role: int):
    if not has_permission(request, "xoa_tai_khoan"):
        return RedirectResponse(url="/login", status_code=303)
    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT MaTaiKhoan
            FROM TAI_KHOAN_DANG_NHAP
            WHERE MaTaiKhoan = %s
            """,
            (account_id,),
        )

        if cursor.fetchone() is None:
            conn.rollback()
            request.session["error"] = "Tài khoản không tồn tại."
            return RedirectResponse(url="/admin/account", status_code=303)

        if role == 1:
            cursor.execute(
                """
                DELETE FROM GIANG_VIEN
                WHERE MaTaiKhoan = %s
                """,
                (account_id,),
            )
        elif role == 0:

            cursor.execute(
                """
                SELECT MaCanBo
                FROM CAN_BO
                WHERE MaTaiKhoan = %s
                """,
                (account_id,),
            )
            staff_id_del = cursor.fetchone()
            if staff_id_del:
                cursor.execute(
                    """
                    UPDATE PHONG
                    SET MaCanBo = NULL
                    WHERE MaCanBo = %s
                    """,
                    (staff_id_del[0],),
                )
            cursor.execute(
                """
                DELETE FROM CAN_BO
                WHERE MaTaiKhoan = %s
                """,
                (account_id,),
            )

        cursor.execute(
            """
            DELETE FROM TAI_KHOAN_DANG_NHAP
            WHERE MaTaiKhoan = %s
            """,
            (account_id,),
        )

        if cursor.rowcount == 0:
            conn.rollback()
            request.session["error"] = "Tài khoản không tồn tại."
        else:
            conn.commit()
            request.session["success"] = "Xóa tài khoản thành công!"

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return RedirectResponse(
        url="/admin/account",
        status_code=303,
    )


@router.get("/admin/account/{account_id}/detail")
def account_detail(request: Request, account_id: int):
    if not has_permission(request, "xem_tai_khoan"):
        return RedirectResponse(url="/login", status_code=303)
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    tk.MaTaiKhoan,
                    tk.TenDangNhap,
                    tk.VaiTro,
                    tk.TrangThai,
                    cb.TenCanBo,
                    cb.GioiTinh,
                    cb.NgaySinh,
                    cb.SoDienThoai,
                    cb.Email,
                    gv.TenGiangVien,
                    gv.GioiTinh,
                    gv.NgaySinh,
                    gv.SoDienThoai,
                    gv.Email
                FROM TAI_KHOAN_DANG_NHAP tk
                LEFT JOIN CAN_BO cb ON cb.MaTaiKhoan = tk.MaTaiKhoan
                LEFT JOIN GIANG_VIEN gv ON gv.MaTaiKhoan = tk.MaTaiKhoan
                WHERE tk.MaTaiKhoan = %s
                """,
                (account_id,),
            )
            row = cursor.fetchone()

        if not row:
            return JSONResponse(
                {"error": "Không tìm thấy tài khoản."},
                status_code=404,
            )
        is_teacher = str(row[2]) == "1"
        return {
            "id": row[0],
            "username": row[1],
            "role": str(row[2]),
            "status": int(row[3]),
            "name": row[9] if is_teacher else row[4],
            "gender": row[10] if is_teacher else row[5],
            "birth": (
                row[11].isoformat()
                if is_teacher and row[11]
                else (row[6].isoformat() if row[6] else "")
            ),
            "tel": row[12] if is_teacher else row[7],
            "email": row[13] if is_teacher else row[8],
        }
    finally:
        conn.close()


@router.post("/admin/account/{account_id}/status")
def update_account_status(
    request: Request,
    account_id: int,
    status: int = Form(...),
):
    if not has_permission(request, "cap_nhat_trang_thai_tai_khoan"):
        return RedirectResponse(url="/login", status_code=303)

    if status not in (0, 1):
        request.session["error"] = "Trạng thái không hợp lệ."
        return RedirectResponse(url="/admin/account", status_code=303)

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE TAI_KHOAN_DANG_NHAP
                SET TrangThai = %s
                WHERE MaTaiKhoan = %s
                """,
                (status, account_id),
            )

            if cursor.rowcount == 0:
                conn.rollback()
                request.session["error"] = "Tài khoản không tồn tại."
            else:
                conn.commit()
                request.session["success"] = (
                    "Mở khóa tài khoản thành công."
                    if status == 1
                    else "Khóa tài khoản thành công."
                )
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return RedirectResponse(url="/admin/account", status_code=303)


# ====================================Duyet yeu cau========================


def get_required(
    per_page,
    offset,
    created_date_from,
    created_date_to,
    status,
    account_id=None,
):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    status_val = int(status) if status is not None and str(status).isdigit() else None
    date_from_val = (
        created_date_from.strip()
        if created_date_from and created_date_from.strip()
        else None
    )
    date_to_val = (
        created_date_to.strip()
        if created_date_to and created_date_to.strip()
        else date_from_val
    )

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
                , EXISTS (
                    SELECT 1
                    FROM THONG_BAO tb
                    WHERE tb.MaTaiKhoan = %s
                      AND tb.LoaiThongBao = %s
                      AND tb.MaDoiTuong = yc.MaYeuCau
                      AND tb.DaXem = FALSE
                ) AS "ChuaXem"
            FROM YEU_CAU_XEP_LICH yc
            JOIN HOC_PHAN hp ON hp.MaHocPhan = yc.MaHocPhan
            JOIN PHAN_MEM pm ON pm.MaPhanMem = yc.MaPhanMem
            JOIN GIANG_VIEN gv ON gv.MaGiangVien = yc.MaGiangVien
            LEFT JOIN QUAN_TRI_VIEN qtv ON qtv.MaQuanTriVien = yc.MaQuanTriVien
            LEFT JOIN TUAN_HOC tbd ON tbd.MaTuanHoc = yc.MaTuanBatDau
            LEFT JOIN TUAN_HOC tkt ON tkt.MaTuanHoc = yc.MaTuanKetThuc
            LEFT JOIN YEU_CAU_THU yct ON yct.MaYeuCau = yc.MaYeuCau
            WHERE (%s IS NULL OR %s = '' OR yc.NgayYeuCau::date >= %s::date)
                AND (%s IS NULL OR %s = '' OR yc.NgayYeuCau::date <= %s::date)
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
            account_id,
            NOTIFICATION_TYPE_SCHEDULE_REQUEST,
            date_from_val,
            date_from_val,
            date_from_val,
            date_to_val,
            date_to_val,
            date_to_val,
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


def get_sum_required(created_date_from, created_date_to, status):
    conn = get_connection()
    cursor = conn.cursor()

    status_val = int(status) if status is not None and str(status).isdigit() else None
    date_from_val = (
        created_date_from.strip()
        if created_date_from and created_date_from.strip()
        else None
    )
    date_to_val = (
        created_date_to.strip()
        if created_date_to and created_date_to.strip()
        else date_from_val
    )

    cursor.execute(
        """
            SELECT COUNT(DISTINCT yc.MaYeuCau)
            FROM YEU_CAU_XEP_LICH yc
            JOIN HOC_PHAN hp ON hp.MaHocPhan = yc.MaHocPhan
            WHERE (%s IS NULL OR %s = '' OR yc.NgayYeuCau::date >= %s::date)
                AND (%s IS NULL OR %s = '' OR yc.NgayYeuCau::date <= %s::date)
                AND (%s IS NULL OR yc.TrangThai = %s)
        """,
        (
            date_from_val,
            date_from_val,
            date_from_val,
            date_to_val,
            date_to_val,
            date_to_val,
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


@router.get("/admin/accept")
def show_accept(
    request: Request,
    page: int = 1,
    created_date_from: str = "",
    created_date_to: str = "",
    status: Optional[str] = Query(None),
):
    if not has_permission(request, "xem_yeu_cau_xep_lich"):
        return RedirectResponse(url="/login", status_code=303)

    account_id = request.session.get("accountId")
    user = get_user_by_id(account_id)
    avt = request.session.get("avt")

    per_page = 10
    offset = (page - 1) * per_page

    status_int = int(status) if (status is not None and status != "") else None
    amount = get_sum_required(created_date_from, created_date_to, status_int)
    required = get_required(
        per_page,
        offset,
        created_date_from,
        created_date_to,
        status_int,
        account_id,
    )
    semester = get_semester_current()

    success = request.session.pop("success", None)

    return templates.TemplateResponse(
        request=request,
        name="admin/accept.html",
        context={
            "user": user,
            "avt": avt,
            "required": required,
            "per_page": per_page,
            "page": page,
            "amount": amount,
            "created_date_from": created_date_from,
            "created_date_to": created_date_to,
            "status": status,
            "semester": semester,
            "success": success,
        },
    )


@router.post("/admin/accept/{required_id}/read")
def mark_required_as_read(request: Request, required_id: int):
    if not (
        has_permission(request, "xem_yeu_cau_xep_lich")
        and has_permission(request, "xem_thong_bao_ca_nhan_quan_tri")
    ):
        return RedirectResponse(url="/login", status_code=303)

    mark_notifications_read(
        request.session.get("accountId"),
        NOTIFICATION_TYPE_SCHEDULE_REQUEST,
        required_id,
    )
    return {"success": True}


@router.post("/admin/accept/{required_id}/accept")
def accept_required(
    required_id: int,
    request: Request,
):
    if not has_permission(request, "duyet_yeu_cau_xep_lich"):
        return RedirectResponse(url="/login", status_code=303)
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            UPDATE YEU_CAU_XEP_LICH
            SET TrangThai = 1
            WHERE MaYeuCau = %s AND TrangThai = 0
            RETURNING MaYeuCau
            """,
            (required_id,),
        )
        conn.commit()
        return {"success": True, "message": "Đã duyệt yêu cầu thành công."}
    except Exception:
        conn.rollback()
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": "Có lỗi khi cập nhật trạng thái."},
        )
    finally:
        cursor.close()
        conn.close()


@router.post("/admin/accept/{required_id}/refuse")
def refuse_required(
    required_id: int,
    request: Request,
    reason: str = Body(..., embed=True),
):
    if not has_permission(request, "duyet_yeu_cau_xep_lich"):
        return RedirectResponse(url="/login", status_code=303)
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            UPDATE YEU_CAU_XEP_LICH
            SET TrangThai = 3
            , LyDo = %s
            WHERE MaYeuCau = %s AND TrangThai = 0
            RETURNING MaYeuCau
            """,
            (
                reason,
                required_id,
            ),
        )
        conn.commit()
        return {"success": True, "message": "Đã từ chối yêu cầu thành công."}
    except Exception:
        conn.rollback()
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": "Có lỗi khi cập nhật trạng thái."},
        )
    finally:
        cursor.close()
        conn.close()


# ================================XEP LICH THUC HANH =================


def get_all_year():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
            SELECT DISTINCT NamHoc
            FROM HOC_KY
            ORDER BY NamHoc DESC
        """,
    )
    years = cursor.fetchone()
    cursor.close()
    conn.close()
    return years


def get_all_room():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
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
        LEFT JOIN MAY_TINH mt
            ON p.MaPhong = mt.MaPhong
        LEFT JOIN CAU_HINH_PHAN_MEM cpm
            ON p.MaCauHinh = cpm.MaCauHinh
        GROUP BY
            p.MaPhong,
            p.TenPhong,
            p.TinhTrangPhong,
            p.MaCauHinh
        ORDER BY p.TenPhong;
    """)

    rooms = cursor.fetchall()
    cursor.close()
    conn.close()

    return rooms


def check_room_suitable(room, required):
    if room[2] != 1:
        return False

    if room[4] is None:
        return False

    if room[3] < required["SoLuongMay"]:
        return False

    if required["MaPhanMem"] not in room[5]:
        return False

    return True


def get_weeks_by_semester(semester_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT MaTuanHoc, TenTuanHoc, NgayBatDau, NgayKetThuc
        FROM TUAN_HOC
        WHERE MaHocKy = %s
        ORDER BY NgayBatDau ASC
        """,
        (semester_id,),
    )

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    weeks = []
    for row in rows:
        weeks.append(
            {
                "id": row[0],
                "name": row[1],
                "start": row[2].strftime("%Y-%m-%d"),
                "end": row[3].strftime("%Y-%m-%d"),
            }
        )

    return weeks


def get_required_for_waiting():
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute("""
        SELECT
            yc.MaYeuCau AS "MaYeuCau"
            , yc.BuoiThucHanh AS "BuoiThucHanh"
            , yc.SoLuongMay AS "SoLuongMay"
            , yc.MaPhanMem AS "MaPhanMem"
            , yc.NgayThucHanh AS "NgayThucHanh"
            , yc.MaTuanBatDau AS "MaTuanBatDau"
            , yc.MaTuanKetThuc AS "MaTuanKetThuc"
            , tbd.TenTuanHoc AS "TuanBatDau"
            , tkt.TenTuanHoc AS "TuanKetThuc"
            , yc.TrangThai AS "TrangThai"
            , hp.TenHocPhan AS "TenHocPhan"
            , yc.NhomHocPhan AS "NhomHocPhan"
            , gv.TenGiangVien AS "TenGiangVien"
            , STRING_AGG(
                DISTINCT yct.thu::text,
                ',' ORDER BY yct.thu::text
            ) AS "DanhSachThu"
            , CASE 
                WHEN yc.NgayThucHanh IS NOT NULL THEN 0 
                ELSE 1
            END AS "LoaiYeuCau"
        FROM YEU_CAU_XEP_LICH yc
        JOIN HOC_PHAN hp
            ON hp.MaHocPhan = yc.MaHocPhan
        JOIN GIANG_VIEN gv
            ON gv.MaGiangVien = yc.MaGiangVien
        LEFT JOIN YEU_CAU_THU yct
            ON yct.MaYeuCau = yc.MaYeuCau
        LEFT JOIN TUAN_HOC tbd 
            ON tbd.MaTuanHoc = yc.MaTuanBatDau
        LEFT JOIN TUAN_HOC tkt 
            ON tkt.MaTuanHoc = yc.MaTuanKetThuc
        WHERE yc.TrangThai = 1
        GROUP BY
            yc.MaYeuCau
            , hp.TenHocPhan
            , yc.NhomHocPhan
            , gv.TenGiangVien
            , tbd.TenTuanHoc
            , tkt.TenTuanHoc
        ORDER BY yc.NgayYeuCau DESC
    """)

    result = cursor.fetchall()
    cursor.close()
    conn.close()

    return result


def get_scheduled_requests():
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute("""
        SELECT
            yc.MaYeuCau AS "MaYeuCau",
            yct.MaPhong AS "MaPhong",
            yct.Thu AS "Thu",
            yct.MaTuanHoc AS "MaTuanHoc",
            yc.BuoiThucHanh AS "BuoiThucHanh",
            TO_CHAR(yc.NgayThucHanh, 'YYYY-MM-DD') AS "NgayThucHanh",
            yc.MaTuanBatDau AS "MaTuanBatDau",
            yc.MaTuanKetThuc AS "MaTuanKetThuc",
            yc.SoLuongMay AS "SoLuongMay",
            yc.MaPhanMem AS "MaPhanMem",
            hp.TenHocPhan AS "TenHocPhan",
            yc.NhomHocPhan AS "NhomHocPhan", 
            gv.TenGiangVien AS "TenGiangVien"
        FROM YEU_CAU_XEP_LICH yc
        JOIN HOC_PHAN hp
            ON hp.MaHocPhan = yc.MaHocPhan
        JOIN GIANG_VIEN gv
            ON gv.MaGiangVien = yc.MaGiangVien
        JOIN YEU_CAU_THU yct
            ON yct.MaYeuCau = yc.MaYeuCau
        WHERE yc.TrangThai IN (1, 2)
          AND yct.MaPhong IS NOT NULL
        ORDER BY yc.MaYeuCau, yct.Thu, yct.MaTuanHoc
    """)

    result = cursor.fetchall()
    cursor.close()
    conn.close()

    return result


@router.get("/admin/calendar")
def show_calendar(
    request: Request,
    page: int = 1,
    created_date_from: str = "",
    created_date_to: str = "",
    status: Optional[str] = Query(None),
):
    if not has_permission(request, "xep_lich_thuc_hanh"):
        return RedirectResponse(url="/login", status_code=303)

    account_id = request.session.get("accountId")
    user = get_user_by_id(account_id)
    avt = request.session.get("avt")

    per_page = 10
    offset = (page - 1) * per_page

    status_int = int(status) if (status is not None and status != "") else None
    amount = get_sum_required(created_date_from, created_date_to, status_int)
    required = get_required(
        per_page, offset, created_date_from, created_date_to, status_int
    )
    semester_current = get_semester_current()
    all_year = get_all_year()
    all_room = get_all_room()
    all_scheduled = get_scheduled_requests()
    all_required_waiting = get_required_for_waiting()

    weeks = []
    if semester_current:
        weeks = get_weeks_by_semester(semester_current[0])

    success = request.session.pop("success", None)

    return templates.TemplateResponse(
        request=request,
        name="admin/calendar.html",
        context={
            "user": user,
            "avt": avt,
            "required": required,
            "per_page": per_page,
            "page": page,
            "amount": amount,
            "created_date_from": created_date_from,
            "created_date_to": created_date_to,
            "status": status,
            "semester_current": semester_current,
            "all_year": all_year,
            "all_room": all_room,
            "weeks": weeks,
            "all_scheduled": all_scheduled,
            "all_required_waiting": all_required_waiting,
            "success": success,
        },
    )


# ============= LUU LICH DA XEP ==================
# Xử lý xóa trước:
# - Xóa mọi tuần → xóa hết thứ đó.
# - Xóa một tuần → nếu có lịch lặp thì bung thành từng ngày → bỏ ngày cần xóa → ghi lại ngày còn giữ.

# Xử lý thêm/đổi lịch sau:
# - Xếp mọi tuần → thay lịch của thứ đó bằng lịch lặp mới.
# - Xếp một ngày → giữ các ngày cũ, thêm hoặc đổi phòng đúng ngày được chọn.

# Cập nhật trạng thái → còn lịch có phòng thì 2, hết thì 1.


@router.post("/admin/calendar/save")
def save_calendar_schedule(request: Request, payload: dict = Body(...)):
    if not has_permission(request, "xep_lich_thuc_hanh"):
        return RedirectResponse(url="/login", status_code=303)

    schedules = payload.get("schedules")
    removed_days = payload.get("removedDays", [])
    removed_day_weeks = payload.get("removedDayWeeks", [])
    if not all(
        isinstance(value, list)  # kiem tra du lieu
        for value in (schedules, removed_days, removed_day_weeks)
    ):
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": "Dữ liệu lịch không hợp lệ."},
        )

    try:
        # gom lich can xep
        placements = []
        for item in schedules:
            if not isinstance(item, dict):
                raise ValueError
            required_id = int(item["requiredId"])
            room_id = int(item["roomId"])
            day = int(item["day"])
            week_id = int(item["weekId"])
            if min(required_id, room_id, week_id) <= 0 or not 0 <= day <= 6:
                raise ValueError
            placements.append(
                {
                    "required_id": required_id,
                    "room_id": room_id,
                    "day": day,
                    "week_id": week_id,
                    "current_week_only": bool(item.get("currentWeekOnly")),
                }
            )

        # gom thu can xoa o all tuan
        removals = []
        for key in removed_days:
            required_id, day = (int(value) for value in str(key).split(":"))
            if required_id <= 0 or not 0 <= day <= 6:
                raise ValueError
            removals.append((required_id, day, None))

        # gom thu can xoa o cac tuan cu the
        for key in removed_day_weeks:
            required_id, day, week_id = (int(value) for value in str(key).split(":"))
            if required_id <= 0 or not 0 <= day <= 6 or week_id <= 0:
                raise ValueError
            removals.append((required_id, day, week_id))

    except (KeyError, TypeError, ValueError):
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": "Dữ liệu lịch không hợp lệ."},
        )

    conn = get_connection()
    cursor = conn.cursor()
    touched_requests = set()  # luu thay doi loai bo trung
    requested_ids = {required_id for required_id, _, _ in removals} | {
        item["required_id"] for item in placements
    }
    try:
        previous_recipients = get_schedule_notification_accounts(
            cursor,
            requested_ids,
        )

        # =========== Phần xóa yc ========
        # duyet tung yc can xoa
        for required_id, day, week_id in removals:
            cursor.execute(
                """
                    SELECT MaTuanBatDau, MaTuanKetThuc
                    FROM YEU_CAU_XEP_LICH
                    WHERE MaYeuCau = %s AND TrangThai IN (1, 2)
                """,
                (required_id,),
            )
            required = cursor.fetchone()
            if not required:
                continue
            week_start, week_end = required

            # xoa o all tuan
            if week_id is None:
                cursor.execute(
                    """
                        DELETE FROM YEU_CAU_THU
                        WHERE MaYeuCau = %s AND Thu = %s
                          AND MaTuanHoc IS NOT NULL
                    """,
                    (required_id, day + 2),
                )

            # xoa o tuan cu the
            else:
                if (
                    week_start is None
                    or week_end is None
                    or not week_start <= week_id <= week_end
                ):
                    conn.rollback()
                    return JSONResponse(
                        status_code=400,
                        content={
                            "success": False,
                            "message": "Tuần được chọn không nằm trong thời gian yêu cầu.",
                        },
                    )
                cursor.execute(
                    """
                        DELETE FROM YEU_CAU_THU
                        WHERE MaYeuCau = %s AND Thu = %s AND MaTuanHoc = %s
                    """,
                    (required_id, day + 2, week_id),
                )
            if cursor.rowcount:
                touched_requests.add(required_id)

        # ============= Phần xếp lịch mới ==========
        slot_rooms = {}
        for item in placements:
            required_id = item["required_id"]
            weekday = item["day"] + 2
            cursor.execute(
                """
                    SELECT NgayThucHanh, MaTuanBatDau, MaTuanKetThuc, BuoiThucHanh
                    FROM YEU_CAU_XEP_LICH
                    WHERE MaYeuCau = %s AND TrangThai IN (1, 2)
                """,
                (required_id,),
            )
            required = cursor.fetchone()
            if not required:
                conn.rollback()
                return JSONResponse(
                    status_code=400,
                    content={
                        "success": False,
                        "message": f"Yêu cầu {required_id} không còn ở trạng thái có thể xếp lịch.",
                    },
                )
            practice_date, week_start, week_end, session = required
            if week_start is None or week_end is None:
                week_start = week_end = item["week_id"]
            if not week_start <= item["week_id"] <= week_end:
                conn.rollback()
                return JSONResponse(
                    status_code=400,
                    content={
                        "success": False,
                        "message": "Tuần được chọn không nằm trong thời gian yêu cầu.",
                    },
                )

            # ngay co dinh
            if practice_date:
                week_ids = [item["week_id"]]
            # chỉ xếp 1 tuần
            elif item["current_week_only"]:
                week_ids = [item["week_id"]]
            else:
                cursor.execute(
                    """
                        SELECT MaTuanHoc
                        FROM TUAN_HOC
                        WHERE MaTuanHoc BETWEEN %s AND %s
                        ORDER BY NgayBatDau
                    """,
                    (week_start, week_end),
                )
                week_ids = [row[0] for row in cursor.fetchall()]

            for target_week_id in week_ids:
                cursor.execute(
                    """
                        SELECT NgayBatDau, NgayKetThuc
                        FROM TUAN_HOC
                        WHERE MaTuanHoc = %s
                    """,
                    (target_week_id,),
                )
                target_week = cursor.fetchone()
                if not target_week:
                    conn.rollback()
                    return JSONResponse(
                        status_code=400,
                        content={
                            "success": False,
                            "message": "Không tìm thấy tuần được chọn.",
                        },
                    )
                target_date = target_week[0] + timedelta(days=item["day"])
                if target_date > target_week[1] or (
                    practice_date and target_date != practice_date
                ):
                    conn.rollback()
                    return JSONResponse(
                        status_code=400,
                        content={
                            "success": False,
                            "message": "Ngày được chọn không hợp lệ với yêu cầu.",
                        },
                    )

                cursor.execute(
                    """
                        SELECT 1
                        FROM YEU_CAU_THU
                        WHERE MaYeuCau = %s AND Thu = %s
                          AND (MaTuanHoc IS NULL OR MaTuanHoc = %s)
                        LIMIT 1
                    """,
                    (required_id, weekday, target_week_id),
                )
                if not cursor.fetchone():
                    conn.rollback()
                    return JSONResponse(
                        status_code=400,
                        content={
                            "success": False,
                            "message": "Thứ này không thuộc yêu cầu thực hành.",
                        },
                    )
                # kiem tra da xep vao phong nao chua
                slot_key = (required_id, weekday, target_week_id)
                existing_room = slot_rooms.get(slot_key)
                if existing_room is not None and existing_room != item["room_id"]:
                    conn.rollback()
                    return JSONResponse(
                        status_code=400,
                        content={
                            "success": False,
                            "message": "Một buổi thực hành không thể được xếp vào nhiều phòng.",
                        },
                    )
                slot_rooms[slot_key] = item["room_id"]

                cursor.execute(
                    """
                        SELECT 1
                        FROM YEU_CAU_THU yct
                        JOIN YEU_CAU_XEP_LICH yc ON yc.MaYeuCau = yct.MaYeuCau
                        WHERE yct.MaPhong = %s
                          AND yct.Thu = %s
                          AND yct.MaTuanHoc = %s
                          AND yc.BuoiThucHanh = %s
                          AND yc.TrangThai = 2
                          AND yc.MaYeuCau <> %s
                        LIMIT 1
                    """,
                    (item["room_id"], weekday, target_week_id, session, required_id),
                )
                if cursor.fetchone():
                    conn.rollback()
                    return JSONResponse(
                        status_code=409,
                        content={
                            "success": False,
                            "message": "Phòng đã có lịch thực hành khác vào buổi này.",
                        },
                    )

                cursor.execute(
                    """
                        INSERT INTO YEU_CAU_THU
                            (MaYeuCau, Thu, MaPhong, NgayThucHanh, MaCanBo, MaTuanHoc)
                        VALUES (%s, %s, %s, %s, NULL, %s)
                        ON CONFLICT (MaYeuCau, Thu, MaTuanHoc)
                            WHERE MaTuanHoc IS NOT NULL
                        DO UPDATE SET
                            MaCanBo = CASE
                                WHEN YEU_CAU_THU.MaPhong IS DISTINCT FROM EXCLUDED.MaPhong
                                THEN NULL
                                ELSE YEU_CAU_THU.MaCanBo
                            END,
                            MaPhong = EXCLUDED.MaPhong,
                            NgayThucHanh = EXCLUDED.NgayThucHanh
                        WHERE YEU_CAU_THU.MaPhong IS DISTINCT FROM EXCLUDED.MaPhong
                           OR YEU_CAU_THU.NgayThucHanh IS DISTINCT FROM EXCLUDED.NgayThucHanh
                    """,
                    (
                        required_id,
                        weekday,
                        item["room_id"],
                        practice_date,
                        target_week_id,
                    ),
                )
                if cursor.rowcount:
                    touched_requests.add(required_id)

        for required_id in touched_requests:
            cursor.execute(
                """
                    SELECT COUNT(*)
                    FROM YEU_CAU_THU
                    WHERE MaYeuCau = %s AND MaPhong IS NOT NULL
                """,
                (required_id,),
            )
            status = 2 if cursor.fetchone()[0] else 1
            cursor.execute(
                "UPDATE YEU_CAU_XEP_LICH SET TrangThai = %s WHERE MaYeuCau = %s",
                (status, required_id),
            )

        notify_schedule_recipients(
            cursor,
            touched_requests,
            previous_recipients,
        )
        conn.commit()
        return {"success": True}
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


# =========== XEP LICH CAN BO ========


@router.get("/admin/staff")
def show_staff_schedule(request: Request):
    if not has_permission(request, "xem_phan_cong_can_bo"):
        return RedirectResponse(url="/login", status_code=303)

    user = get_user_by_id(request.session.get("accountId"))
    semester = get_semester_current()
    weeks = get_weeks_by_semester(semester[0]) if semester else []
    all_room = get_all_room()
    all_scheduled = get_scheduled_requests()

    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("""
            SELECT MaCanBo AS "MaCanBo", TenCanBo AS "TenCanBo"
            FROM CAN_BO
            ORDER BY TenCanBo
        """)
    staffs = cursor.fetchall()

    assignments = []
    if semester:
        cursor.execute(
            """
                SELECT
                    yct.MaYeuCau AS "MaYeuCau",
                    yct.MaPhong AS "MaPhong",
                    yct.Thu AS "Thu",
                    yct.MaTuanHoc AS "MaTuanHoc",
                    yct.MaCanBo AS "MaCanBo",
                    cb.TenCanBo AS "TenCanBo"
                FROM YEU_CAU_THU yct
                JOIN CAN_BO cb ON cb.MaCanBo = yct.MaCanBo
                JOIN TUAN_HOC th ON th.MaTuanHoc = yct.MaTuanHoc
                JOIN HOC_KY hk ON hk.MaHocKy = %s
                WHERE yct.MaCanBo IS NOT NULL
                  AND th.MaHocKy = hk.MaHocKy
            """,
            (semester[0],),
        )
        assignments = cursor.fetchall()
    cursor.close()
    conn.close()

    return templates.TemplateResponse(
        request=request,
        name="admin/staff.html",
        context={
            "user": user,
            "semester_current": semester,
            "all_room": all_room,
            "weeks": weeks,
            "all_scheduled": all_scheduled,
            "staffs": staffs,
            "staff_assignments": assignments,
        },
    )


@router.post("/admin/staff/assign")
def assign_staff_to_schedule(request: Request, payload: dict = Body(...)):
    if not has_permission(request, "phan_cong_can_bo"):
        return JSONResponse(
            status_code=403,
            content={
                "success": False,
                "message": "Bạn không có quyền thực hiện thao tác này.",
            },
        )

    try:
        required_id = int(payload["requiredId"])
        room_id = int(payload["roomId"])
        week_id = int(payload["weekId"])
        day = int(payload["day"])
        session = int(payload["session"])
        staff_id = (
            int(payload["staffId"]) if payload.get("staffId") is not None else None
        )
        if (
            min(required_id, room_id, week_id) <= 0
            or (staff_id is not None and staff_id <= 0)
            or not 0 <= day <= 6
            or session not in (1, 2, 3)
        ):
            raise ValueError
    except (KeyError, TypeError, ValueError):
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": "Thông tin phân công không hợp lệ."},
        )

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
                SELECT NgayBatDau, NgayKetThuc
                FROM TUAN_HOC
                WHERE MaTuanHoc = %s
            """,
            (week_id,),
        )
        week = cursor.fetchone()
        if not week:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Không tìm thấy tuần được chọn."},
            )

        target_date = week[0] + timedelta(days=day)
        if target_date > week[1]:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "Ngày được chọn không thuộc tuần học.",
                },
            )
        weekday = target_date.isoweekday() + 1

        cursor.execute(
            """
                SELECT yct.MaCanBo, gv.MaTaiKhoan, old_cb.MaTaiKhoan
                FROM YEU_CAU_XEP_LICH yc
                JOIN YEU_CAU_THU yct ON yct.MaYeuCau = yc.MaYeuCau
                JOIN GIANG_VIEN gv ON gv.MaGiangVien = yc.MaGiangVien
                LEFT JOIN CAN_BO old_cb ON old_cb.MaCanBo = yct.MaCanBo
                WHERE yc.MaYeuCau = %s
                  AND yc.TrangThai = 2
                  AND yc.BuoiThucHanh = %s
                  AND (
                        yc.NgayThucHanh = %s
                        OR (
                            yc.NgayThucHanh IS NULL
                            AND yc.MaTuanBatDau <= %s
                            AND yc.MaTuanKetThuc >= %s
                        )
                  )
                  AND yct.MaPhong = %s
                  AND yct.Thu = %s
                  AND yct.MaTuanHoc = %s
            """,
            (
                required_id,
                session,
                target_date,
                week_id,
                week_id,
                room_id,
                weekday,
                week_id,
            ),
        )
        assignment = cursor.fetchone()
        if not assignment:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "Ô lịch này không có lịch thực hành hợp lệ.",
                },
            )

        old_staff_id, teacher_account_id, old_staff_account_id = assignment
        staff_name = None
        new_staff_account_id = None
        if staff_id is not None:
            cursor.execute(
                "SELECT TenCanBo, MaTaiKhoan FROM CAN_BO WHERE MaCanBo = %s",
                (staff_id,),
            )
            staff = cursor.fetchone()
            if not staff:
                return JSONResponse(
                    status_code=400,
                    content={
                        "success": False,
                        "message": "Không tìm thấy cán bộ được chọn.",
                    },
                )
            staff_name = staff[0]
            new_staff_account_id = staff[1]

        cursor.execute(
            """
                UPDATE YEU_CAU_THU
                SET MaCanBo = %s
                WHERE MaYeuCau = %s
                  AND MaPhong = %s
                  AND Thu = %s
                  AND MaTuanHoc = %s
            """,
            (staff_id, required_id, room_id, weekday, week_id),
        )
        if cursor.rowcount == 0:
            return JSONResponse(
                status_code=409,
                content={
                    "success": False,
                    "message": "Lịch tuần này không còn tồn tại.",
                },
            )

        if old_staff_id != staff_id:
            for account_id in {
                teacher_account_id,
                old_staff_account_id,
                new_staff_account_id,
            } - {None}:
                insert_notification(
                    cursor,
                    account_id,
                    NOTIFICATION_TYPE_SCHEDULE,
                    required_id,
                )

        conn.commit()
        return {
            "success": True,
            "staffId": staff_id,
            "staffName": staff_name,
            "date": target_date.isoformat(),
            "weekId": week_id,
            "weekday": weekday,
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


# ====================================Bao cao tinh trang========================


@router.get("/admin/report")
def show_admin_reports(
    request: Request,
    created_date: Optional[date] = Query(default=None),
):
    if not has_permission(request, "quan_ly_phong"):
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
                    cb.TenCanBo,
                    bc.MaMayTinh,
                    bc.TinhTrangCuThe,
                    CASE
                        WHEN bc.MaMayTinh IS NULL THEN p.TinhTrangPhong
                        ELSE mt.TinhTrangMay
                    END AS TinhTrangHienTai,
                    COALESCE(tb.DaXem, TRUE) AS DaXem
                FROM Bao_cao_tinh_trang bc
                JOIN PHONG p ON p.MaPhong = bc.MaPhong
                JOIN CAN_BO cb ON cb.MaCanBo = bc.MaCanBo
                LEFT JOIN MAY_TINH mt
                    ON mt.MaMayTinh = bc.MaMayTinh
                   AND mt.MaPhong = bc.MaPhong
                LEFT JOIN THONG_BAO tb
                    ON tb.MaDoiTuong = bc.MaBaoCao
                   AND tb.MaTaiKhoan = %s
                   AND tb.LoaiThongBao = 'BAO_CAO_TINH_TRANG'
                WHERE bc.NgayGui = %s
                ORDER BY bc.MaBaoCao DESC
            """,
            (request.session.get("accountId"), selected_date),
        )
        reports = cursor.fetchall()
        cursor.close()
    finally:
        conn.close()

    return templates.TemplateResponse(
        request=request,
        name="admin/report.html",
        context={
            "user": get_user_by_id(request.session.get("accountId")),
            "avt": request.session.get("avt"),
            "reports": reports,
            "created_date": selected_date,
            "success": request.session.pop("success", None),
        },
    )


@router.post("/admin/report/{report_id}/read")
def mark_report_as_read(request: Request, report_id: int):
    if not (
        has_permission(request, "quan_ly_phong")
        and has_permission(request, "xem_thong_bao_ca_nhan_quan_tri")
    ):
        return RedirectResponse(url="/login", status_code=303)

    account_id = request.session.get("accountId")
    mark_notifications_read(
        account_id,
        NOTIFICATION_TYPE_STATUS_REPORT,
        report_id,
    )
    return {"success": True}


@router.post("/admin/report/{report_id}/status")
def update_reported_status(
    request: Request,
    report_id: int,
    status: int = Form(...),
    created_date: Optional[date] = Form(default=None),
):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
                SELECT MaPhong, MaMayTinh
                FROM Bao_cao_tinh_trang
                WHERE MaBaoCao = %s
            """,
            (report_id,),
        )
        report = cursor.fetchone()
        if report is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy báo cáo.")

        if not has_permission(
            request,
            "quan_ly_may_tinh" if report[1] is not None else "quan_ly_phong",
        ):
            raise HTTPException(
                status_code=403,
                detail="Bạn không có quyền thực hiện thao tác này.",
            )

        room_id, computer_id = report
        if computer_id is not None:
            if status not in (0, 1, 2, 3):
                raise HTTPException(
                    status_code=422,
                    detail="Tình trạng máy tính không hợp lệ.",
                )
            cursor.execute(
                """
                    UPDATE MAY_TINH
                    SET TinhTrangMay = %s
                    WHERE MaMayTinh = %s AND MaPhong = %s
                """,
                (status, computer_id, room_id),
            )
        else:
            if status not in (-1, 0, 1):
                raise HTTPException(
                    status_code=422,
                    detail="Tình trạng phòng không hợp lệ.",
                )
            cursor.execute(
                """
                    UPDATE PHONG
                    SET TinhTrangPhong = %s
                    WHERE MaPhong = %s
                """,
                (status, room_id),
            )

        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail="Không tìm thấy máy tính hoặc phòng cần cập nhật.",
            )

        conn.commit()
        request.session["success"] = "Cập nhật tình trạng thành công."
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    redirect_url = "/admin/report"
    if created_date:
        redirect_url += f"?created_date={created_date.isoformat()}"
    return RedirectResponse(url=redirect_url, status_code=303)

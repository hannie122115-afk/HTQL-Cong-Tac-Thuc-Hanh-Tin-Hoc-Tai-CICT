from fastapi import APIRouter, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from pwdlib import PasswordHash
from typing import List
from datetime import date
from datetime import datetime, timedelta
from psycopg2.extras import RealDictCursor
import re, secrets, string, hashlib, os

from email_service import send_account_email
from database import get_connection

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
def show_admin(request: Request):
    role = request.session.get("role")

    if role != 2:
        return RedirectResponse(url="/login", status_code=303)

    user = get_user_by_id(request.session.get("accountId"))
    avt = request.session.get("avt")

    return templates.TemplateResponse(
        request=request,
        name="admin/index.html",
        context={
            "user": user,
            "avt": avt,
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
    role = request.session.get("role")
    if role != 2:
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
    role = request.session.get("role")
    if role != 2:
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
    role = request.session.get("role")
    if role != 2:
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
    role = request.session.get("role")
    if role != 2:
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
    role = request.session.get("role")
    if role != 2:
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
    role = request.session.get("role")
    if role != 2:
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
    role = request.session.get("role")
    if role != 2:
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
    role = request.session.get("role")
    if role != 2:
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
    role = request.session.get("role")
    if role != 2:
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
    role = request.session.get("role")
    if role != 2:
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
    role = request.session.get("role")
    if role != 2:
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
    role = request.session.get("role")
    if role != 2:
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
                cb.TenCanBo AS TenCanBo,
                p.TinhTrangPhong
            FROM PHONG p
            LEFT JOIN MAY_TINH mt
                ON mt.MaPhong = p.MaPhong
            LEFT JOIN CAN_BO cb
                ON cb.MaCanBo = p.MaCanBo
            GROUP BY
                p.MaPhong,
                cb.MaCanBo
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
    role = request.session.get("role")
    if role != 2:
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
    role = request.session.get("role")
    if role != 2:
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
    role = request.session.get("role")
    if role != 2:
        return RedirectResponse(url="/login", status_code=303)
    conn = get_connection()

    try:
        cursor = conn.cursor()

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
            request.session["success"] = "Phòng không tồn tại."
        else:
            conn.commit()
            request.session["success"] = "Xóa phòng thành công!"

    except Exception:
        conn.rollback()
        raise

    finally:
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
                cb.TenCanBo AS TenCanBo,
                cb.MaCanBo AS MaCanBo,
                ch.CPU AS CPU,
                ch.MaCauHinh,
                p.TinhTrangPhong
            FROM PHONG p
            LEFT JOIN CAN_BO cb
                ON cb.MaCanBo = p.MaCanBo
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
    role = request.session.get("role")
    if role != 2:
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
    configs = get_all_room()
    amount = get_sum_computer(
        room_id,
        keyword,
    )
    computers = get_computer(room_id, keyword, per_page, offset)
    staffs = get_staffs_room()

    cursor.close()
    conn.close()

    return templates.TemplateResponse(
        request=request,
        name="admin/room-detail.html",
        context={
            "room": room,
            "configs": configs,
            "computers": computers,
            "staffs": staffs,
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
    config_id: int = Form(...),
    staff_id: int = Form(...),
    room_status: int = Form(...),
):
    role = request.session.get("role")
    if role != 2:
        return RedirectResponse(url="/login", status_code=303)
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE PHONG
        SET TenPhong = %s,
            MaCauHinh = %s,
            MaCanBo = %s,
            TinhTrangPhong = %s
        WHERE MaPhong = %s
        """,
        (
            room_name,
            config_id,
            staff_id,
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
    role = request.session.get("role")
    if role != 2:
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
    role = request.session.get("role")
    if role != 2:
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
    role = request.session.get("role")
    if role != 2:
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
    admin_role = request.session.get("role")
    if admin_role != 2:
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
    admin_role = request.session.get("role")
    if admin_role != 2:
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
    admin_role = request.session.get("role")
    if admin_role != 2:
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
    admin_role = request.session.get("role")
    if admin_role != 2:
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
    admin_role = request.session.get("role")
    if admin_role != 2:
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
    admin_role = request.session.get("role")
    if admin_role != 2:
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

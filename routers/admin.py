from fastapi import APIRouter, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from typing import List
import re

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

    if role != 0:
        return RedirectResponse(url="/login", status_code=303)

    user = get_user_by_id(request.session.get("accountId"))
    avt = request.session.get("avt")

    return templates.TemplateResponse(
        request=request, name="admin/index.html", context={"user": user, "avt": avt}
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
    if role != 0:
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
    if role != 0:
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
    if role != 0:
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
    if role != 0:
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
    if role != 0:
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
    if role != 0:
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
    if role != 0:
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
    if role != 0:
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
    if role != 0:
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
    if role != 0:
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
    if role != 0:
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
    if role != 0:
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
    if role != 0:
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
    if role != 0:
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
    if role != 0:
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
    if role != 0:
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
    if role != 0:
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
    if role != 0:
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
    if role != 0:
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
    if role != 0:
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

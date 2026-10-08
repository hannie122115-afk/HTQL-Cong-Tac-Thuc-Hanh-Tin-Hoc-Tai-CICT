from fastapi import APIRouter, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from typing import List

from database import get_connection

router = APIRouter()

templates = Jinja2Templates(directory="templates")


# Trang chu
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
                Cpu LIKE %s
                OR Ram LIKE %s
                OR OCung LIKE %s
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
                Cpu LIKE %s
                OR Ram LIKE %s
                OR OCung LIKE %s
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


# ====================================Chi tiet cau hinh may========================


def get_program(keyword):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
            SELECT *
            FROM PHAN_MEM
            WHERE 
                TenPhanMem LIKE %s
                OR NhaPhatHanh LIKE %s
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
                pm.TenPhanMem LIKE %s
                OR pm.NhaPhatHanh LIKE %s
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
                pm.TenPhanMem LIKE %s
                OR pm.NhaPhatHanh LIKE %s
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
